# Install the evidence tools without keeping a repository checkout

Current preview: **`second-paddle-evidence 0.1.0a2`**. It contains the existing two-tool MCP entry, approval checker and result projection. The approval algorithm remains 0.1.1. This release corrects the result wrapper's model-view boundary; it does not change the underlying local-copy helper.

> **Already using 0.1.0a1?** Its `project_tool_result` wrapper can copy protocol metadata or other unselected fields into ordinary model-facing output. Use 0.1.0a2 for that entry point. Select model-visible data **before** putting it in a prompt, tool argument or log: an output rejection cannot undo earlier exposure. Ordinary content is not automatically secret-checked. The prior release and its evidence remain available for inspection, with a supersession notice.

## Download and install

**[Download 0.1.0a2 and its original evidence](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/evidence-v0.1.0a2)**. These public release assets are separate from the 14-day Actions copies. The recorded public download checks used no authentication headers or cookies.

With Python and Node.js already available, choose a fresh environment and install the exact wheel:

```sh
python -m venv .venv
.venv/bin/python -m pip install "https://github.com/YS-OH-CORE/second-paddle-notes/releases/download/evidence-v0.1.0a2/second_paddle_evidence-0.1.0a2-py3-none-any.whl#sha256=b801b9f2f8fe6973c980161d0ee2ff0241eada55b313c1b635a90d13eb6425ff"
.venv/bin/python -m second_paddle_evidence --check
```

On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`. The hash fragment pins the reviewed wheel. Dependencies are downloaded separately. `--check` reports the actual interpreter and arguments for an opt-in stdio MCP host; it does not edit an application's configuration. The installed command is `second-paddle-evidence`. Run without `--check` when the host is ready to communicate over stdio, not as an interactive chat. Existing installations do not update themselves; deliberately point the host to the chosen environment after checking it.

Prerequisites: Python 3.10+, independently installed Node.js 22+ on PATH, and the wheel's declared `mcp==2.2.0` dependency. Python 3.12 and Node.js 22.23.2 are the tested combination. Pip downloads dependencies unless they are available locally. This is not a dependency-free executable. The launcher does not download Node, install other software, or open an HTTP listener. Input/output and limitations remain those of [the underlying tools](../../tools/evidence-mcp/README.md). This package is not on PyPI; use the exact URL or downloaded wheel, not an unqualified package-name install.

## Model-view input boundary

`project_tool_result` accepts a selected model-view result: `content`, `structuredContent`, and `isError`. In protocol envelope, block and resource positions it rejects `_meta`; unselected fields and explicitly non-assistant audiences are also rejected. The returned error uses a fixed code and does not echo the rejected data. It does not silently delete fields from the caller's original response.

A key spelled `_meta` inside selected `structuredContent`, or inside quoted text, is ordinary application data and remains intact. The local helper intentionally retains source copies in a trusted application; it is not a model-view sanitizer. Preserve the original separately, and select an appropriate view before invoking this MCP tool. General MCP extension metadata is not universally confidential, so this is an explicit application boundary, not a secret-classification claim.

## Executed correction and publication, 2026-09-13

[PR #31](https://github.com/YS-OH-CORE/second-paddle-notes/pull/31) contains the correction. The installed comparison in [run 34748252871](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34748252871) used the same 12 synthetic inputs with public a1 and candidate a2 over actual MCP stdio. Six restricted-input cases placed a synthetic marker in a1's ordinary output; a2 returned fixed errors without that marker. The six allowed-data cases retained their text/structured results and error flags. Twenty-one unit tests passed, including the original sixteen service tests.

[Run 34748252840](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34748252840) installed the same corrected wheel in fresh Windows and Linux environments and ran five existing consumer cases on each. Both environments produced the exact **35,543-byte** wheel with SHA-256 `b801b9f2f8fe6973c980161d0ee2ff0241eada55b313c1b635a90d13eb6425ff`. The eight-file bundle identifies wrapper source `e40eba4b7b985c716644ec736ac72288f8e6cdd7`; only the wrapper's `service.py` and `server.py` differ from a1's bundled files. The packaging source tested for this wheel is `fabb5375056dc51500183d3ec510aeb4ac94defb`.

[Publication run 34748770402](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34748770402) reused those exact files. It published a2, downloaded all six public assets without authentication, checked their bytes, and added a warning to a1 without replacing its assets. Its returned artifact, 10315420984, is **81,591 bytes**, SHA-256 `e90fcecac645b058322a92f43b188242f9990ad33dda3789e2b0f51ce3362c23`. The returned original comparison and installation ZIPs, wheel RECORD, bundle hashes, individual responses and download records were inspected after an interrupted conversation. That inspection is not a new SDK run.

These are synthetic boundary and installation observations. No real user's private data, provider call, model-selected action, production incident or independent certification was involved. The first publication attempt left an uploaded draft; the later run completed that exact inspected draft. It did not create a second copy or replace prior assets.

## Build from source instead

```sh
python packages/evidence-mcp/build_wheel.py --out /path/to/new-dist
python -m venv .venv
# Linux/macOS interpreter; on Windows use .venv\Scripts\python.exe
.venv/bin/python -m pip install /path/to/new-dist/second_paddle_evidence-0.1.0a2-py3-none-any.whl
.venv/bin/python -m second_paddle_evidence --check
```

Only the builder needs a source checkout. Once the wheel is built, consumers install the wheel itself without the repository or its three sibling source folders. Check that the checkout is the a2 packaging source; historical tags intentionally build their historical versions.

## What is preserved

The wheel contains the required sibling layout internally. The builder checks fixed source blobs, includes all three original licenses, and writes wheel RECORD hashes. Startup checks the bundle's SHA-256 map. These detect mismatched files; they are not a user signature or independent certification. Rebuilds use fixed ZIP entries without compression variability and refuse to overwrite an existing wheel.

## Historical 0.1.0a1 installation evidence

The following records concern **a1**, not the corrected a2 wheel. They remain here to preserve what was previously checked. They did not exercise the later-discovered model-view boundary. For the complete former installation page, see its [unchanged pre-correction snapshot](https://github.com/YS-OH-CORE/second-paddle-notes/blob/e4fc1864d809c89f582a67298bf45bfc3c1eef6c/packages/evidence-mcp/README.md).

[Run 34710660702](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34710660702) completed on both hosted Linux and Windows. Each built the wheel twice, checked its identical bytes, installed it with dependencies into a new environment whose path contains spaces and Korean, and passed `pip check`. The installed package was imported from that environment, not the checkout.

The actual pip-generated console command was launched from a separate working directory. In each environment, a real MCP client discovered both tools and made five synthetic calls: matching approval, changed payload, duplicate raw input, a valid empty-result projection after the invalid input, and an error-result projection. Text and structured results agreed; errors remained errors. The child with Node removed from PATH returned exit 2, a `NODE_MISSING` diagnostic and no stdout. Both final environments used Python 3.12 and Node.js 22.23.2. Other Python/Node versions and macOS were not covered by this installation run.

The **historical a1** wheel is 32,918 bytes, SHA-256 `0e509a17ee164189abea151996cb084de6fc55990ee0ce4d8a9a70bed5b984bd`. Its original source/license bundle was byte-identical to commit `bd926be1322758b9ea9ab9a6da5ffcb87d440a0c`. The old release assets remain unchanged; use a2 for new model-facing projection installations.

Both original artifacts were downloaded and opened. Their ZIP CRC, wheel RECORD and bundled-file hashes, actual package locations, five response pairs per operating system, missing-Node output and dependency checks were inspected. The client recorded no external socket attempts during the stdio exercise; installing dependencies used package downloads. This is ten synthetic tool calls, not ten user installations or measured model behavior.

| Historical artifact | Bytes | SHA-256 |
|---|---:|---|
| Linux 10303401390 | 20,308 | `184c277574ffaf68ba06920ed7f5eedf4aa9a1b610837a7c92cf3fc863b18811` |
| Windows 10303122004 | 20,415 | `3e5c930519edc3a5dc28bf55df30167c352fe3e282d07ca062b6126f34920a65` |

### Historical public acquisition

[Run 34714897106](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34714897106) fetched the a1 public release and all five assets with no authentication headers or cookies. A fresh Linux environment installed the downloaded wheel and passed the same five synthetic consumer cases, dependency check and missing-Node control. Returned artifact 10304662186 is 61,657 bytes, SHA-256 `b18437ac7dbe9c99911b0f2fb61870eda3d27abd5e9e9a0f24c5f58b82db5099`. The first a1 publishing run had uploaded its files before a draft-by-tag lookup failed; a numeric-ID reconciliation completed the same draft. See [PR #28](https://github.com/YS-OH-CORE/second-paddle-notes/pull/28). This is the earlier acquisition check, not evidence of a2 behavior.

### Earlier verifier failure preserved

The first Windows run, 34710538238, installed the same a1 wheel and completed all five calls, then failed the verifier's final process-launch assertion. Python's Windows audit event supplied `executable=None` and a quoted command-line string; our recorder had treated that string as a list of characters. The verifier was corrected; the package and behavioral assertions were unchanged. Original artifact 10302089411 remains 18,167 bytes with SHA-256 `824a61758efcfbeca0c4756b7e35bdeb8ab18366f25f2369377a196ba08e50c8`.

The original executable installation verifier is commit `f2a1fc8346558ab2c3576808aff987a8c67cc4ae`. [PR #27](https://github.com/YS-OH-CORE/second-paddle-notes/pull/27) records the first packaging publication. Actions copies have finite retention; release assets and versioned source remain subject to repository availability and owner control, not perpetual-storage guarantees.

Sources: [PyPA wheel specification](https://packaging.python.org/en/latest/specifications/binary-distribution-format/) and [entry points](https://packaging.python.org/en/latest/specifications/entry-points/).

New packaging scripts are MIT-licensed under the included original [evidence tools license](../../tools/evidence-mcp/LICENSE). Existing code retains its original notices. Prepared by Youngseok Oh with Zero (ChatGPT).

## 한국어

현재 설치 안내는 **0.1.0a2 수정본**을 가리킵니다. 이전 a1 연결부가 내부용으로 구분해 둔 부가정보까지 AI가 읽는 출력에 복사할 수 있었던 부분을 고쳤습니다. 혼합된 입력은 원문을 몰래 삭제해 처리하지 않고, 내용을 되풀이하지 않는 오류로 돌려줍니다. 일반 본문이나 선택된 구조화 자료 안의 정상적인 같은 이름 항목은 유지합니다.

단, AI에게 입력하는 순간 이미 공개된 정보를 출력 차단이 되돌리지는 못합니다. **모델에게 보여 줄 자료를 먼저 고른 다음** 이 도구에 전달해야 합니다. 개인정보 자동 탐지기나 모든 유출을 막는 장치는 아닙니다.

Windows와 Linux 설치 결과, 이전·수정본 비교, 실제 공개 다운로드 기록을 함께 공개했습니다. 이 문서에서 버전을 바꾼다고 기존 설치가 자동으로 바뀌지는 않습니다. 사용할 환경과 AI 앱 연결은 사용자가 선택하며, 사용자 PC나 앱 설정을 자동 변경하지 않습니다.
