# Process Receipt 0.2.0a2: receipt-failure reporting correction

**An unsuccessful receipt write does not mean the command never ran.** This corrective alpha delivers the fix already implemented and native-tested in [PR #12](https://github.com/YS-OH-CORE/second-paddle-notes/pull/12).

## What was wrong

Under an injected error at final receipt synchronization, a real child had already written its output and exited. The historical POSIX module CLI could nevertheless report `Process not launched: OSError`. The portable command avoided that categorical sentence but did not retain a structured execution outcome in its error response. A separate receipt-close error could also skip restoration of the caller's signal handlers.

These were reproducible injected I/O faults, not a reported real-user data-loss incident or a physical disk-damage experiment. Inspect destination effects before deciding whether to retry work. A missing receipt or wrapper exit 2 is not evidence of non-execution.

## Corrected behavior

Both backends preserve observed execution status, `task_started`, observed direct-child exit and exit code in `ReceiptPersistenceError.summary`. The CLIs return that sanitized summary on stderr and keep exit 2. The receipt failure is separate from the execution outcome. Final-save and close handling are independent, and a close error no longer bypasses normal signal-handler restoration. No automatic retry is added.

The exact 13,000-byte Windows-tested wheel is promoted without rebuilding:

```text
second_paddle_process_receipt-0.2.0a2-py3-none-any.whl
SHA-256: 69c96c6d1be62b4031e6e0f7d5ebf874bf551f15433f75b296c685b9ce2c907d
```

`BUILD_PROVENANCE.json` identifies the tested source, native build, original artifact and runtime-module hashes. `SHA256SUMS` covers the wheel and provenance. Checksums establish identity with these published bytes, not independent security certification.

## Install or upgrade

Download the wheel from this release and verify the checksum. From an environment you have chosen to update, use its Python executable:

```sh
python -m pip install --no-index --no-deps second_paddle_process_receipt-0.2.0a2-py3-none-any.whl
process-receipt --help
```

`python` must refer to that environment's interpreter; on Windows this may be the full path to `Scripts/python.exe`, and on Linux `bin/python`. This command intentionally replaces an installed earlier version in that environment. Use a fresh virtual environment instead to retain the earlier installation. A live process that imported the earlier module must be restarted to load the update.

The public consumer check installs the exact published a1 first, then upgrades the same disposable environment to the exact public a2. It compares actual child effects and error responses before/after and checks a normal installed console command. Fault injection runs through the installed Python module CLI, not inside a Windows launcher executable. Consult completed workflow evidence; publication alone does not establish consumer success.

## Versions and scope

The old 0.1.0 and 0.2.0a1 release files are not replaced. After both public consumer jobs pass, a dated correction is appended to those two release descriptions, preserving the original notes, tags and assets. Existing installations are not updated automatically.

Python >=3.10 is declared; the prior native qualification used Python 3.12 on Windows and Linux. Windows supervises the directly launched EXE only. This is still a trusted-command alpha, not a hostile-code sandbox, background agent, durable error-output channel, exactly-once system, rollback facility or universal emergency stop. Completed effects are not reversed. The earlier local-container graceful-exit limitation remains documented in PR #10.

Project by Youngseok Oh; implementation, checks and publication prepared with Zero (ChatGPT). No independent review, OpenAI endorsement or third-party adoption is asserted. No private user conversation is included. The utility's MIT license does not relicense unrelated repository notes.

## 한국어

실제로 실행된 작업을 기록 저장 실패 때문에 '실행하지 않음'으로 오해하지 않도록 고친 실험판이다. 기록 오류와 실제 실행 결과를 나누어 돌려준다. 이미 한 일을 중복 실행하지 않도록, 기록이 없다는 이유만으로 자동 재시도하지 않는다. 이전 배포파일은 그대로 남기고 이전 배포 설명에 날짜가 있는 정정 안내를 붙인다. 사용자의 PC를 자동으로 변경하지 않는다.
