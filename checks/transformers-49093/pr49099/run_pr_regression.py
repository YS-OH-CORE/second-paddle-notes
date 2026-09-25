"""Run the proposed regression in the actual upstream test module.

Original diagnosis/fix: lucaluo925; PR implementation: aniketkrs.
Supplemental test/execution: Zero, AI collaboration partner of Youngseok Oh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


BASE = "89b6b17574892ec0770551537a3fe69d6886703e"
HEAD = "e435677fb9981b3f2bfc7abeaabcb394e47c29e2"
SOURCE = "src/transformers/generation/logits_process.py"
TEST_FILE = "tests/generation/test_logits_process.py"
TEST_BLOB = "baa9a5e5133f91fd9ec974d37b92df5af6071d56"
BASE_BLOB = "7ff6a32c026efb139cc89996e07181f141cce971"
HEAD_BLOB = "4638fce3a2dd880dacdab148f73de28cd4280987"
NEW_TEST = "test_bias_dist_processor_zero_token_roundtrip_full_prefix"
TESTS = (NEW_TEST, "test_bias_dist_processor", "test_no_bad_words_dist_processor")
PATCH_SHA = "1538319d621789142fd1f0bb450e4dec4a573bbfe18036b25840ec191a7c11ff"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def run(root, patch):
    out = root / "output"
    out.mkdir(parents=True, exist_ok=False)
    report = {"success": False, "base_commit": BASE, "pr_head_commit": HEAD,
              "issue": "https://github.com/huggingface/transformers/issues/49093",
              "request": "https://github.com/huggingface/transformers/issues/49093#issuecomment-5827315466",
              "pr": "https://github.com/huggingface/transformers/pull/49099",
              "patch_sha256": sha(patch), "runner_sha256": sha(Path(__file__)),
              "run_id": os.environ.get("GITHUB_RUN_ID"),
              "workflow_commit": os.environ.get("GITHUB_SHA"), "variants": []}

    def call(argv, cwd=root, env=None, timeout=180, required=True):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env,
                                text=True, capture_output=True, timeout=timeout)
        with (out / "execution.log").open("a", encoding="utf-8") as stream:
            stream.write("COMMAND " + str(argv) + "\nSTDOUT\n" + result.stdout
                         + "\nSTDERR\n" + result.stderr + "\n")
        print(result.stdout[-6000:] + result.stderr[-2000:], flush=True)
        if required:
            result.check_returncode()
        return result

    def checkout(owner, revision, name):
        archive = root / (name + ".zip")
        url = f"https://github.com/{owner}/transformers/archive/{revision}.zip"
        with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as stream:
            size = 0
            for part in iter(lambda: response.read(1024 * 1024), b""):
                size += len(part)
                assert size <= 300 * 1024 * 1024
                stream.write(part)
        dest = root / name
        dest.mkdir()
        with zipfile.ZipFile(archive) as z:
            for item in z.namelist():
                assert (dest / item).resolve().is_relative_to(dest.resolve())
            z.extractall(dest)
        children = list(dest.iterdir())
        assert len(children) == 1 and children[0].is_dir()
        report.setdefault("archives", {})[name] = {"url": url, "sha256": sha(archive)}
        return children[0]

    try:
        assert report["patch_sha256"] == PATCH_SHA
        shutil.copy2(patch, out / "roundtrip.patch")
        shutil.copy2(__file__, out / "run_pr_regression.py")
        base = checkout("huggingface", BASE, "base")
        head = checkout("aniketkrs", HEAD, "head")
        for folder, expected in ((base, BASE_BLOB), (head, HEAD_BLOB)):
            assert blob((folder / SOURCE).read_bytes()) == expected
            assert blob((folder / TEST_FILE).read_bytes()) == TEST_BLOB
            call(["git", "apply", "--check", patch], cwd=folder)
            call(["git", "apply", patch], cwd=folder)
        assert (base / TEST_FILE).read_bytes() == (head / TEST_FILE).read_bytes()
        shutil.copy2(head / TEST_FILE, out / "proposed_test_logits_process.py")
        call([sys.executable, "-m", "venv", root / "venv"], timeout=30)
        py = root / "venv/bin/python"
        call([py, "-m", "pip", "install", "--disable-pip-version-check", "torch==2.12.0",
              "--index-url", "https://download.pytorch.org/whl/cpu"], timeout=240)
        call([py, "-m", "pip", "install", "--disable-pip-version-check", head,
              "pytest>=8,<9", "parameterized>=0.9", "accelerate>=1.1.0", "psutil", "pytest-env",
              "ruff==0.14.10"], timeout=240)
        (out / "environment.txt").write_text(
            call([py, "-m", "pip", "freeze", "--all"]).stdout, encoding="utf-8")
        call([py, "-m", "ruff", "check", TEST_FILE], cwd=head)
        call([py, "-m", "ruff", "format", "--check", TEST_FILE], cwd=head)
        report["target_file_ruff_check_and_format"] = "passed"
        original_head = (head / SOURCE).read_text(encoding="utf-8")
        old_a = "and token_id >= 0 for token_id in sequence[0]"
        new_a = "and token_id > 0 for token_id in sequence[0]"
        old_b = "if prefix_length > input_ids.shape[1]:"
        new_b = "if len(sequence_ids) > input_ids.shape[1]:"
        assert original_head.count(old_a) == original_head.count(old_b) == 1

        for name, folder, revert in (("base", base, None), ("pr_head", head, None),
                                      ("pr_revert_zero", head, "A"), ("pr_revert_prefix", head, "B")):
            if folder == head:
                content = original_head
                if revert == "A":
                    content = content.replace(old_a, new_a)
                if revert == "B":
                    content = content.replace(old_b, new_b)
                (folder / SOURCE).write_text(content, encoding="utf-8")
            target_out = out / name
            target_out.mkdir()
            shutil.copy2(folder / SOURCE, target_out / "logits_process.py")
            env = dict(os.environ, PYTHONPATH=str(folder / "src"), PYTHONDONTWRITEBYTECODE="1",
                       TRANSFORMERS_TEST_DEVICE="cpu", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                       HF_HUB_DISABLE_TELEMETRY="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                       TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
            probe = ("import json,torch,transformers; from transformers.generation import logits_process; "
                     "print(json.dumps({'package':transformers.__file__,'source':logits_process.__file__,"
                     "'torch':torch.__version__,'transformers':transformers.__version__}))")
            identity = json.loads(call([py, "-B", "-c", probe], cwd=folder, env=env, timeout=90).stdout)
            assert Path(identity["source"]).resolve() == (folder / SOURCE).resolve()
            assert Path(identity["package"]).resolve() == (folder / "src/transformers/__init__.py").resolve()
            xml = target_out / "junit.xml"
            result = call([py, "-B", "-m", "pytest", "-q", "-o", "addopts=", "--junitxml=" + str(xml),
                           *[TEST_FILE + "::LogitsProcessorTest::" + name for name in TESTS]],
                          cwd=folder, env=env, timeout=120, required=False)
            (target_out / "pytest.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            tree = ET.parse(xml)
            cases = list(tree.iter("testcase"))
            assert len(cases) == 3, "Collection must execute exactly the three selected tests"
            assert {c.get("name") for c in cases} == set(TESTS)
            assert not list(tree.iter("error")) and not list(tree.iter("skipped"))
            failures = [c for c in cases if c.find("failure") is not None]
            expected_fail = name != "pr_head"
            assert len(failures) == int(expected_fail)
            assert result.returncode == int(expected_fail)
            failure_text = None
            if expected_fail:
                assert failures[0].get("name") == NEW_TEST
                failure_text = failures[0].find("failure").text or ""
                if name in ("base", "pr_revert_zero"):
                    assert "ValueError" in failure_text and "positive integers" in failure_text
                else:
                    assert "AssertionError" in failure_text and "Tensor-likes are not" in failure_text
                    assert "Mismatched elements: 1 / 12" in failure_text
            row = {"variant": name, "returncode": result.returncode, "identity": identity,
                   "source_sha256": sha(folder / SOURCE), "source_git_blob": blob((folder / SOURCE).read_bytes()),
                   "executed": len(cases), "passed": len(cases) - len(failures),
                   "failed": len(failures), "failure_text": failure_text,
                   "tests": [{"name": c.get("name"), "passed": c.find("failure") is None} for c in cases]}
            report["variants"].append(row)
            print("REGRESSION_ROW " + json.dumps(row), flush=True)
        (head / SOURCE).write_text(original_head, encoding="utf-8")
        report.update(success=True, executed_tests=12, full_upstream_test_module=True,
                      repository_conftest_enabled=True, model_calls=0,
                      scope="three selected unittest methods; CPU; actual source base/head and two single-fix reversions")
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("REGRESSION_REPORT " + json.dumps(report), flush=True)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.root.resolve(), args.patch.resolve()))
