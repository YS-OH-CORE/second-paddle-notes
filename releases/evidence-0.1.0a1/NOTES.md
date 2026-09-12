# Two read-only checks, ready to install

Use this preview when an MCP client needs to check an approval/execution trace or preserve structured output that would otherwise be invisible to a text-only consumer.

- `check_approval_trace`: compare the original ordered JSON trace against the declared request/approval policy.
- `project_tool_result`: add a text view of an existing structured result only when content is empty, preserving errors and the original response separately.

## Install the wheel

Prerequisites: Python 3.12 and Node.js 22 on PATH are the tested combination. The package declares Python >=3.10 and requires Node >=22; other combinations have not received the same installation check. Pip installs `mcp==2.2.0` and its dependencies. No model/API key is needed.

Create a Python environment you choose for these tools, then use its interpreter:

```sh
python -m venv .venv
.venv/bin/python -m pip install "https://github.com/YS-OH-CORE/second-paddle-notes/releases/download/evidence-v0.1.0a1/second_paddle_evidence-0.1.0a1-py3-none-any.whl#sha256=0e509a17ee164189abea151996cb084de6fc55990ee0ce4d8a9a70bed5b984bd"
.venv/bin/python -m second_paddle_evidence --check
```

On Windows use `.venv\Scripts\python.exe` in place of `.venv/bin/python`. The check prints an absolute interpreter and module arguments for a stdio-compatible MCP host. Choose that host's connection settings yourself; the command does not edit them. Run without `--check` only when the host is ready to communicate over stdio. This is not an interactive chat program.

[Full input/error contract and host guidance](https://github.com/YS-OH-CORE/second-paddle-notes/tree/e0399c96bf2bdcbcd841eafa5f257070751a624e/tools/evidence-mcp) · [Packaging source](https://github.com/YS-OH-CORE/second-paddle-notes/tree/e0399c96bf2bdcbcd841eafa5f257070751a624e/packages/evidence-mcp)

## What these downloads contain

The wheel is the **exact 32,918-byte file** previously installed and exercised on Windows and Linux in [run 34710660702](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34710660702). It is copied from the returned artifacts, not rebuilt or revised for this release. Version 0.1.0a1 is the distribution version; its embedded approval checker remains 0.1.1.

`ORIGINAL-linux.zip` and `ORIGINAL-windows.zip` preserve those actual installation results byte-for-byte. `PROVENANCE.json` connects source, run and file identities. `SHA256SUMS` covers the wheel and those evidence files. These release attachments are separate from the 14-day Actions artifact copies. They remain subject to repository availability and owner control, not a promise of perpetual storage or immutable signing.

The original checks used five synthetic cases per operating system, including malformed input followed by a valid call and preservation of error flags. No language model chose those calls, and no external adoption is asserted. The release workflow separately verifies public unauthenticated downloads and an installation from the published wheel; consult its completed results rather than inferring them from this page's existence.

## Scope

This preview inspects supplied data. It does not authorize actions, recover missing events, authenticate human consent, or certify a system safe. The host must treat returned data as tool data. Existing inputs and errors retain the documented meanings. There is no scheduler, network-listening server or automatic configuration change. Dependencies and Node remain separate prerequisites. Not published on PyPI.

Prepared by Youngseok Oh with Zero (ChatGPT). Original utility attribution and MIT notices are included in the wheel. This release does not change unrelated project licenses.

## 한국어

기존 두 도구를 설치파일 하나로 받을 수 있는 공개 미리보기입니다. 위 다운로드는 GitHub Actions의 임시 보관 파일과 분리되어 있습니다. 기존에 Windows와 Linux에서 확인한 설치파일과 원본 실행 기록을 그대로 옮겼습니다.

Python과 Node.js는 필요합니다. `--check`로 환경과 연결 인수를 확인한 뒤 사용할 AI 앱에 연결합니다. 설치나 연결을 자동으로 대신 수행하지 않으며, 이 파일은 언어 모델이나 예약 실행기를 포함하지 않습니다. 공개 파일과 실행 근거를 함께 제공합니다.
