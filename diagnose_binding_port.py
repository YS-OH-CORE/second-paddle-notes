"""Read-only source integration diagnostic for an existing contributed patch.

No upstream code execution, dependency install, remote writes, credentials,
model calls, or merge. File-level three-way results are not a project build.
"""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import urllib.error
import urllib.request

REPO = 'NousResearch/hermes-agent'
MAIN = '3eb9712180ec60191edfb9d072ddb28ffe427e4b'
HEAD = '501be10cce7159a08279c89c724db602d9770601'
API = 'https://api.github.com/repos/' + REPO


def emit(kind, **values):
    print('BINDING_DIAGNOSTIC ' + json.dumps(dict(kind=kind, **values), ensure_ascii=True), flush=True)


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Zero-source-integration-review', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read()


def blob(ref, path):
    try:
        return get('https://raw.githubusercontent.com/' + REPO + '/' + ref + '/' + path)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def h(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def conflict_blocks(text):
    lines = text.splitlines()
    blocks = []
    start = None
    for i, line in enumerate(lines):
        if line.startswith('<<<<<<< '):
            start = i
        elif line.startswith('>>>>>>> ') and start is not None:
            blocks.append({'start_line': start + 1, 'end_line': i + 1, 'context': '\n'.join(lines[max(0, start-5):min(len(lines), i+7)])})
            start = None
    return blocks


def main():
    data = json.loads(get(API + '/compare/' + MAIN + '...' + HEAD + '?per_page=1'))
    base = data['merge_base_commit']['sha']
    files = data.get('files', [])
    emit('comparison', repository=REPO, current_main=MAIN, contributed_head=HEAD, merge_base=base,
         status=data['status'], ahead_by=data['ahead_by'], behind_by=data['behind_by'],
         files=[{'path': x['filename'], 'status': x['status'], 'previous_filename': x.get('previous_filename')} for x in files],
         boundary='File-level diagnostic for returned PR changes; not a repository merge or runtime test.')
    if not files or len(files) > 20:
        raise RuntimeError('Unexpected comparison scope; stop rather than expand automatically')
    with tempfile.TemporaryDirectory(prefix='zero-binding-port-') as directory:
        root = Path(directory)
        for index, entry in enumerate(files):
            path = entry['filename']
            if entry['status'] not in ('modified', 'added'):
                emit('requires_review', path=path, reason='Change is not an ordinary add/modify; do not guess rename semantics')
                continue
            current, original, proposed = [blob(ref, path) for ref in (MAIN, base, HEAD)]
            common = dict(path=path, main_sha256=h(current), base_sha256=h(original), head_sha256=h(proposed))
            if proposed is None:
                emit('requires_review', **common, reason='Head file missing')
                continue
            if original is None:
                if current is None or current == proposed:
                    emit('add_clean', **common, bytes=len(proposed), already_present=current == proposed)
                else:
                    emit('add_add_conflict', **common)
                continue
            if current is None:
                emit('modify_delete_conflict', **common)
                continue
            paths = [root / (str(index) + '-' + tag) for tag in ('main', 'base', 'head')]
            for output, content in zip(paths, (current, original, proposed)):
                output.write_bytes(content)
            run = subprocess.run(['git', 'merge-file', '-p', '--diff3', '-L', 'current-main', '-L', 'merge-base', '-L', 'contributed-head', *map(str, paths)], capture_output=True, timeout=20)
            merged = run.stdout.decode('utf-8')
            if run.returncode != 0:
                emit('file_conflict', **common, exit_code=run.returncode, stderr=run.stderr.decode('utf-8', 'replace'), blocks=conflict_blocks(merged))
            else:
                delta = ''.join(difflib.unified_diff(current.decode('utf-8').splitlines(keepends=True), merged.splitlines(keepends=True), fromfile='a/'+path, tofile='b/'+path, n=4))
                ast_status = 'not_python'
                if path.endswith('.py'):
                    ast.parse(merged, filename=path)
                    ast_status = 'parse_ok'
                emit('file_merge_clean', **common, candidate_sha256=h(run.stdout), ast_status=ast_status,
                     delta=delta[:30000], delta_truncated=len(delta)>30000)
    emit('complete', upstream_writes=0, code_executed_from_upstream=False, dependencies_installed=False)


if __name__ == '__main__':
    main()
