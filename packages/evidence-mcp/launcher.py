"""Installed stdio entry; never installs dependencies or changes host settings."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

VERSION = '0.1.0a1'


def preflight() -> dict:
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / 'bundle.json').read_text(encoding='utf-8'))
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256((base / '_bundle' / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('BUNDLED_SOURCE_CHANGED: reinstall the reviewed wheel; do not edit its bundled files.')
    try:
        sdk = importlib.metadata.version('mcp')
    except importlib.metadata.PackageNotFoundError:
        raise RuntimeError('MCP_MISSING: install this wheel with pip dependencies in an isolated environment.') from None
    if sdk != '2.2.0':
        raise RuntimeError('MCP_VERSION_MISMATCH: this preview was packaged for mcp==2.2.0.')
    node = shutil.which('node')
    if node is None:
        raise RuntimeError('NODE_MISSING: Node.js 22 or newer must be on the host PATH.')
    try:
        version = subprocess.check_output([node, '--version'], text=True, timeout=5).strip()
        major = int(version.lstrip('v').split('.')[0])
    except (OSError, ValueError, subprocess.SubprocessError):
        raise RuntimeError('NODE_UNAVAILABLE: could not read the installed Node.js version.') from None
    if major < 22:
        raise RuntimeError('NODE_TOO_OLD: Node.js 22 or newer is required.')
    return {'status': 'ready', 'distribution_version': VERSION, 'mcp': sdk, 'node': version,
            'source_commit': manifest['source_commit'], 'verified_files': len(manifest['sha256']),
            'package_location': str(base),
            'stdio_connection': {'command': sys.executable, 'args': ['-m', 'second_paddle_evidence']}}


def main() -> int:
    parser = argparse.ArgumentParser(description='Read-only evidence tools over MCP stdio.')
    parser.add_argument('--check', action='store_true', help='Check installed prerequisites and print a connection descriptor; do not start a server.')
    parser.add_argument('--version', action='version', version=VERSION)
    args = parser.parse_args()
    try:
        checked = preflight()
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.check:
        print(json.dumps(checked, ensure_ascii=True, sort_keys=True))
        return 0
    server = Path(__file__).resolve().parent / '_bundle' / 'evidence-mcp' / 'server.py'
    sys.path.insert(0, str(server.parent))
    # Existing server and helper bytes are preserved; sibling paths are inside the wheel.
    runpy.run_path(str(server), run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
