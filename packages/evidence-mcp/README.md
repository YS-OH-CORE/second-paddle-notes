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

Only the builder needs a source checkout. Once the wheel is built, consumers install the wheel itself without the repository. `--check` reports the actual interpreter and arguments for a stdio-capable host. The command installed by pip is `second-paddle-evidence`; it starts the MCP server only when invoked without `--check`. No application configuration is edited. This package is not on PyPI, so use the actual wheel file, not an unqualified package-name install.

Prerequisites: Python 3.10+, independently installed Node.js 22+ on PATH, and the wheel's declared `mcp==2.2.0` dependency. Pip downloads dependencies unless they are available locally. This is not a dependency-free executable. The launcher does not download Node, install other software, or open an HTTP listener. Input/output and limitations remain those of [the underlying tools](../../tools/evidence-mcp/README.md).

## What is preserved

The wheel contains the required sibling layout internally, so the original runtime files need no rewrite. The builder checks fixed source blobs, includes all three original licenses, and writes wheel RECORD hashes. Startup checks the bundle's SHA-256 map. These detect mismatched files; they are not a user signature or independent certification. Rebuilds use fixed ZIP entries without compression variability and refuse to overwrite an existing wheel.

## Installed behavior checked on 2026-09-13 (Korea time)

[Run 34710660702](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34710660702) completed on both hosted Linux and Windows. Each built the wheel twice, checked its identical bytes, installed it with dependencies into a new environment whose path contains spaces and Korean, and passed `pip check`. The installed package was imported from that environment, not the checkout.

The actual pip-generated console command was launched from a separate working directory. In each environment, a real MCP client discovered both tools and made five synthetic calls: matching approval, changed payload, duplicate raw input, a valid empty-result projection after the invalid input, and an error-result projection. Text and structured results agreed; errors remained errors. The child with Node removed from PATH returned exit 2, a `NODE_MISSING` diagnostic and no stdout. Both final environments used Python 3.12 and Node.js 22.23.2. Other Python/Node versions and macOS were not covered by this installation run.

The output wheel is **32,918 bytes**, SHA-256:

```text
0e509a17ee164189abea151996cb084de6fc55990ee0ce4d8a9a70bed5b984bd
```

It is byte-identical across the two operating systems and the local build. The final run's `evidence-wheel-ubuntu-latest` and `evidence-wheel-windows-latest` artifacts contain it under `wheel-dist/`, alongside actual installation observations. Artifacts have 14-day retention and downloading them may require a GitHub sign-in. There is no PyPI publication or separate GitHub Release for this preview; the retained build source can reproduce the wheel after artifacts expire.

Both original artifacts were downloaded and opened. Their ZIP CRC, wheel RECORD and bundled-file hashes, actual package locations, five response pairs per operating system, missing-Node output and dependency checks were inspected. The client recorded no external socket attempts during the stdio exercise; installing dependencies used package downloads. This is ten synthetic tool calls, not ten user installations or measured model behavior.

| Returned artifact | Bytes | SHA-256 |
|---|---:|---|
| Linux 10303401390 | 20,308 | `184c277574ffaf68ba06920ed7f5eedf4aa9a1b610837a7c92cf3fc863b18811` |
| Windows 10303122004 | 20,415 | `3e5c930519edc3a5dc28bf55df30167c352fe3e282d07ca062b6126f34920a65` |

### Earlier verifier failure preserved

The first Windows run, 34710538238, installed the same wheel and completed all five calls, then failed the verifier's final process-launch assertion. Python's Windows audit event supplied `executable=None` and a quoted command-line string; our recorder had treated that string as a list of characters. The verifier now preserves the original fields and checks the exact platform-specific launch representation. The package, wheel, dependencies and behavioral assertions were unchanged. The failed artifact 10302089411 remains an 18,167-byte original ZIP with SHA-256 `824a61758efcfbeca0c4756b7e35bdeb8ab18366f25f2369377a196ba08e50c8`.

Local preparation also checked wheel creation, RECORD entries, a no-dependency pip install, `--version`, and the expected missing-SDK diagnostic. Full SDK installation and calls are the hosted results above. The final executable verifier is commit `f2a1fc8346558ab2c3576808aff987a8c67cc4ae`; later explanation-only changes do not alter the tested files. [PR #27](https://github.com/YS-OH-CORE/second-paddle-notes/pull/27) records publication status.

Sources: [PyPA wheel specification](https://packaging.python.org/en/latest/specifications/binary-distribution-format/) and [entry points](https://packaging.python.org/en/latest/specifications/entry-points/).

New packaging scripts are MIT-licensed under the included original [evidence tools license](../../tools/evidence-mcp/LICENSE). Existing code retains its original notices. Prepared by Youngseok Oh with Zero (ChatGPT).

## 한국어

저장소 전체를 받아 폴더 위치를 맞추지 않아도 두 도구를 설치할 수 있게 묶었습니다. 같은 설치파일을 Windows와 Linux의 새 환경에 각각 설치하고, 설치된 명령으로 두 도구를 조회하고 호출했습니다. 한글과 공백이 있는 설치 경로에서도 확인했습니다.

Python과 Node.js는 여전히 필요합니다. 이 파일은 언어 모델이나 자동 실행 예약을 포함하지 않으며, 사용할 AI 앱의 연결 설정은 별도로 선택해야 합니다. 사용자의 PC나 기존 앱은 변경하지 않았습니다. 공개 실행 결과에는 설치파일과 원본 관측이 14일간 보관되며, 위의 빌드 코드는 같은 파일을 다시 만들 수 있도록 남아 있습니다.
