# Install the evidence tools without keeping a repository checkout

Packaging preview `second-paddle-evidence 0.1.0a1` includes the existing two-tool MCP entry, approval checker and result projection. All eight bundled source/license files are kept byte-identical to commit `bd926be1322758b9ea9ab9a6da5ffcb87d440a0c`. This is an installation route, not a new version of the underlying audit algorithm.

## Build and install

```sh
python packages/evidence-mcp/build_wheel.py --out /path/to/new-dist
python -m venv .venv
# Linux/macOS interpreter; on Windows use .venv\Scripts\python.exe
.venv/bin/python -m pip install /path/to/new-dist/second_paddle_evidence-0.1.0a1-py3-none-any.whl
.venv/bin/python -m second_paddle_evidence --check
```

`--check` reports the actual interpreter and arguments for a stdio-capable host. The command installed by pip is `second-paddle-evidence`; it starts the MCP server only when invoked without `--check`. No application configuration is edited. This package is not on PyPI, so use the actual wheel file, not an unqualified package-name install.

Prerequisites: Python 3.10+, independently installed Node.js 22+ on PATH, and the wheel's declared `mcp==2.2.0` dependency. Pip downloads dependencies unless they are available locally. This is not a dependency-free executable. The launcher does not download Node, install other software, or open an HTTP listener. Input/output and limitations remain those of [the underlying tools](../../tools/evidence-mcp/README.md).

## What is preserved

The wheel contains the required sibling layout internally, so the original runtime files need no rewrite. The builder checks fixed source blobs, includes all three original licenses, and writes wheel RECORD hashes. Startup checks the bundle's SHA-256 map. These detect mismatched files; they are not a user signature or independent certification. Rebuilds use fixed ZIP entries without compression variability and refuse to overwrite an existing wheel.

## Verification status

Local wheel creation, RECORD checks, pip installation without dependencies, console entry `--version`, and the expected missing-SDK diagnostic have run. Full installation and actual MCP calls in separate Windows/Linux environments are pending in the introducing PR. Do not call this cross-platform validated until the returned results are inspected.

The install verifier creates a new environment in a path containing spaces and Korean. It installs the wheel, checks dependencies, launches the installed command from outside the checkout, lists the two tools and exercises five synthetic calls. Removing Node from the child PATH must produce an explicit setup error. It neither installs on a user's machine nor evaluates a real language model.

Sources: [PyPA wheel specification](https://packaging.python.org/en/latest/specifications/binary-distribution-format/) and [entry points](https://packaging.python.org/en/latest/specifications/entry-points/).

New packaging scripts are MIT-licensed under the included original [evidence tools license](../../tools/evidence-mcp/LICENSE). Existing code retains its original notices. Prepared by Youngseok Oh with Zero (ChatGPT).

## 한국어

저장소 전체를 받아 폴더 위치를 맞추지 않아도 두 도구를 설치할 수 있게 묶는 경로입니다. 이미 만든 기능은 바꾸지 않았습니다. Python과 Node.js는 여전히 필요하며, 이 파일 하나가 언어 모델을 포함하거나 AI 앱에 자동으로 연결되는 것은 아닙니다. 실제 설치 검증 결과는 이 변경의 PR에 별도로 남깁니다.
