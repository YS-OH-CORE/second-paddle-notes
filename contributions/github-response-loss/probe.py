"""Lose a GitHub Contents API response on purpose, then recover from provider state.

The only remote effect is creation of one deterministic JSON marker on the current
same-repository PR branch. The sender never reads the PUT response. Recovery does
not trust a local success flag: it reads GitHub's contents and commit history.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

EXIT_AFTER_SEND = 73
API = "api.github.com"
USER_AGENT = "second-paddle-response-loss-probe"


def need(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def request_json(method: str, api_path: str, token: str, body: object | None = None):
    raw = canonical(body) if body is not None else None
    req = urllib.request.Request(
        "https://" + API + api_path,
        data=raw,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
            **({"Content-Type": "application/json", "Content-Length": str(len(raw))} if raw is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read(500_001)
            need(len(data) <= 500_000, "HTTP_BODY_TOO_LARGE")
            return response.status, json.loads(data) if data else None
    except urllib.error.HTTPError as exc:
        data = exc.read(500_001)
        need(len(data) <= 500_000, "HTTP_ERROR_BODY_TOO_LARGE")
        try:
            parsed = json.loads(data) if data else None
        except json.JSONDecodeError:
            parsed = {"unparsed_bytes": len(data)}
        return exc.code, parsed


def sender(repo: str, branch: str, marker_path: str, marker: bytes, token: str, commit_message: str) -> None:
    body = canonical({
        "message": commit_message,
        "content": base64.b64encode(marker).decode("ascii"),
        "branch": branch,
    })
    path = "/repos/" + repo + "/contents/" + urllib.parse.quote(marker_path, safe="/")
    conn = http.client.HTTPSConnection(API, timeout=20)
    conn.putrequest("PUT", path)
    conn.putheader("Authorization", "Bearer " + token)
    conn.putheader("Accept", "application/vnd.github+json")
    conn.putheader("X-GitHub-Api-Version", "2022-11-28")
    conn.putheader("User-Agent", USER_AGENT)
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Content-Length", str(len(body)))
    conn.endheaders()
    conn.send(body)
    # This marker proves only that Python handed the complete request body to the
    # TLS socket. There is deliberately no getresponse() call.
    Path(os.environ["LOSS_EVIDENCE_DIR"], "sender-before-exit.json").write_bytes(canonical({
        "pid": os.getpid(),
        "request_body_sha256": hashlib.sha256(body).hexdigest(),
        "marker_sha256": hashlib.sha256(marker).hexdigest(),
        "marker_path": marker_path,
        "branch": branch,
        "point": "complete request body handed to TLS socket; HTTP response unread",
        "at_ns": time.monotonic_ns(),
    }))
    os._exit(EXIT_AFTER_SEND)


def fetch_marker(repo: str, branch: str, marker_path: str, token: str):
    path = "/repos/" + repo + "/contents/" + urllib.parse.quote(marker_path, safe="/") + "?ref=" + urllib.parse.quote(branch, safe="")
    return request_json("GET", path, token)


def fetch_branch(repo: str, branch: str, token: str):
    return request_json("GET", "/repos/" + repo + "/git/ref/heads/" + urllib.parse.quote(branch, safe="/"), token)


def fetch_commits(repo: str, branch: str, marker_path: str, token: str):
    query = urllib.parse.urlencode({"sha": branch, "path": marker_path, "per_page": 5})
    return request_json("GET", "/repos/" + repo + "/commits?" + query, token)


def recover(repo: str, branch: str, marker_path: str, marker: bytes, token: str, commit_message: str) -> dict:
    expected_blob = hashlib.sha1(b"blob " + str(len(marker)).encode() + b"\0" + marker).hexdigest()
    observations = []
    deadline = time.monotonic() + 12
    found = None
    while time.monotonic() < deadline:
        status, body = fetch_marker(repo, branch, marker_path, token)
        observations.append({"status": status, "at_ns": time.monotonic_ns()})
        if status == 200:
            found = body
            break
        need(status == 404, "UNEXPECTED_CONTENTS_STATUS")
        time.sleep(0.35)
    retry = None
    if found is None:
        # Provider status stayed absent. Retry the same create-only operation once.
        # If the first request races in late, GitHub's same-path create contract
        # rejects the second create; recovery then re-reads authoritative state.
        status, body = request_json("PUT", "/repos/" + repo + "/contents/" + urllib.parse.quote(marker_path, safe="/"), token, {
            "message": commit_message,
            "content": base64.b64encode(marker).decode("ascii"),
            "branch": branch,
        })
        retry = {"status": status, "body_kind": type(body).__name__}
        need(status in (201, 409, 422), "UNEXPECTED_RETRY_STATUS")
        for _ in range(20):
            status, body = fetch_marker(repo, branch, marker_path, token)
            observations.append({"status": status, "at_ns": time.monotonic_ns()})
            if status == 200:
                found = body
                break
            need(status == 404, "UNEXPECTED_POST_RETRY_STATUS")
            time.sleep(0.25)
    need(found is not None, "MARKER_NOT_RECOVERED")
    need(found["sha"] == expected_blob, "REMOTE_BLOB_DIFFER")
    remote = base64.b64decode(found["content"], validate=True)
    need(remote == marker, "REMOTE_CONTENT_DIFFER")

    ref_status, ref = fetch_branch(repo, branch, token)
    need(ref_status == 200, "BRANCH_LOOKUP_FAILED")
    commits_status, commits = fetch_commits(repo, branch, marker_path, token)
    need(commits_status == 200 and isinstance(commits, list) and commits, "COMMIT_LOOKUP_FAILED")
    matching = [row for row in commits if row.get("commit", {}).get("message") == commit_message]
    need(len(matching) == 1, "PROVIDER_COMMIT_NOT_UNIQUE")
    provider_commit = matching[0]["sha"]
    need(ref["object"]["sha"] == provider_commit, "MARKER_NOT_BRANCH_HEAD")
    return {
        "status": "recovered_from_provider_state",
        "first_lookup_status": observations[0]["status"],
        "lookup_count": len(observations),
        "retry": retry,
        "marker_path": marker_path,
        "marker_sha256": hashlib.sha256(marker).hexdigest(),
        "remote_blob_sha1": found["sha"],
        "provider_commit_sha": provider_commit,
        "branch_head_sha": ref["object"]["sha"],
        "commit_message": commit_message,
        "exact_remote_bytes": True,
    }


def orchestrate() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ["TARGET_BRANCH"]
    token = os.environ["GH_RESPONSE_LOSS_TOKEN"]
    run_id = os.environ["GITHUB_RUN_ID"]
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    root = Path(os.environ["LOSS_EVIDENCE_DIR"])
    root.mkdir(parents=True, exist_ok=True)
    operation_id = "github-contents-response-loss-" + run_id + "-" + run_attempt
    marker_path = "provider-evidence/" + operation_id + ".json"
    commit_message = "Record provider response-loss marker " + operation_id + " [skip ci]"
    initial_status, initial_ref = fetch_branch(repo, branch, token)
    need(initial_status == 200, "INITIAL_BRANCH_LOOKUP_FAILED")
    initial_head = initial_ref["object"]["sha"]
    marker = canonical({
        "schema": 1,
        "operation_id": operation_id,
        "purpose": "synthetic provider-state marker; no user data",
        "repository": repo,
        "branch": branch,
        "parent_head_before_request": initial_head,
        "run_id": run_id,
        "run_attempt": run_attempt,
    })
    env = dict(os.environ)
    command = [sys.executable, str(Path(__file__).resolve()), "--role", "sender",
               "--repo", repo, "--branch", branch, "--marker-path", marker_path,
               "--commit-message", commit_message]
    proc = subprocess.run(command, env=env, timeout=30, check=False)
    after_sender_ns = time.monotonic_ns()
    need(proc.returncode == EXIT_AFTER_SEND, "SENDER_DID_NOT_EXIT_AT_FAULT")
    sender_record = json.loads((root / "sender-before-exit.json").read_text(encoding="utf-8"))
    need(sender_record["marker_sha256"] == hashlib.sha256(marker).hexdigest(), "SENDER_MARKER_DIFFER")
    need(sender_record["at_ns"] < after_sender_ns, "FAULT_ORDER")
    result = recover(repo, branch, marker_path, marker, token, commit_message)
    need(result["provider_commit_sha"] != initial_head, "BRANCH_DID_NOT_ADVANCE")
    evidence = {
        "status": "verified",
        "scope": "Real GitHub Contents API response loss on a same-repository disposable evidence marker; provider-state reconciliation, not general exactly-once",
        "sender_returncode": proc.returncode,
        "initial_branch_head": initial_head,
        "sender_record": sender_record,
        "recovery": result,
    }
    (root / "observations.json").write_bytes(canonical(evidence))
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("orchestrate", "sender"), default="orchestrate")
    parser.add_argument("--repo")
    parser.add_argument("--branch")
    parser.add_argument("--marker-path")
    parser.add_argument("--commit-message")
    args = parser.parse_args()
    if args.role == "sender":
        token = os.environ["GH_RESPONSE_LOSS_TOKEN"]
        run_id = os.environ["GITHUB_RUN_ID"]
        run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
        status, ref = fetch_branch(args.repo, args.branch, token)
        need(status == 200, "SENDER_BRANCH_LOOKUP_FAILED")
        marker = canonical({
            "schema": 1,
            "operation_id": "github-contents-response-loss-" + run_id + "-" + run_attempt,
            "purpose": "synthetic provider-state marker; no user data",
            "repository": args.repo,
            "branch": args.branch,
            "parent_head_before_request": ref["object"]["sha"],
            "run_id": run_id,
            "run_attempt": run_attempt,
        })
        sender(args.repo, args.branch, args.marker_path, marker, token, args.commit_message)
    orchestrate()


if __name__ == "__main__":
    main()
