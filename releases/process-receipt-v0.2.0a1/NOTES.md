# Process Receipt 0.2.0a1: Windows + Linux (experimental)

A small executable utility for a concrete question: **did the command actually exit, or was a stop merely requested?** This prerelease adds a Windows direct-EXE backend and a platform-selecting installed command. It is not an AI model or a background service.

This release publishes the exact 12,476-byte wheel built and tested on native Windows in [run 34569094695](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34569094695). It is not a rebuild. The earlier POSIX-only 0.1.0 release and its files are unchanged.

## Download and verify

Download `second_paddle_process_receipt-0.2.0a1-py3-none-any.whl` from the assets below. Its SHA-256 is:

```text
13b47b0416b519e42596fd0ea7a0c2c929edbdd17488ae53adfa7031745c7032
```

Python 3.10 or later is declared; executed native checks used Windows Python 3.12.10 and Linux Python 3.12.3, not every supported version. No runtime package dependencies are required. Inspect the code before running downloaded software. A checksum checks agreement with this published file, not independent security endorsement.

### Windows PowerShell

Use a new folder containing the downloaded wheel and an environment name that does not exist. Stop if any command fails.

```powershell
$Wheel = 'second_paddle_process_receipt-0.2.0a1-py3-none-any.whl'
$Expected = '13b47b0416b519e42596fd0ea7a0c2c929edbdd17488ae53adfa7031745c7032'
if ((Get-FileHash $Wheel -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected) { throw 'Checksum mismatch' }
if (Test-Path '.process-env') { throw 'Choose a new environment directory' }
py -3 -m venv .process-env
if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed' }
.process-env\Scripts\python.exe -m pip install --no-index --no-deps $Wheel
if ($LASTEXITCODE -ne 0) { throw 'Installation failed' }
.process-env\Scripts\process-receipt.exe --help
```

For a trusted executable, use a NEW receipt filename:

```powershell
.process-env\Scripts\process-receipt.exe --receipt result.json --stop-file STOP --timeout 30 -- C:\full\path\your-program.exe
```

Creating `STOP` in another terminal requests termination. An existing stop file prevents launch. Windows supervision covers only the directly launched EXE, not its descendants. A launcher or virtual-environment Python can spawn the real worker elsewhere: stopping the launcher does not prove the worker stopped. The native qualification used the real base Python EXE. Batch files are not implicitly launched through a shell.

### Linux

In a new folder containing the wheel, this subshell stops installation on an error or existing environment:

```sh
(
  set -eu
  printf '%s  %s\n' \
    13b47b0416b519e42596fd0ea7a0c2c929edbdd17488ae53adfa7031745c7032 \
    second_paddle_process_receipt-0.2.0a1-py3-none-any.whl | sha256sum --check -
  test ! -e .process-env
  python3 -m venv .process-env
  .process-env/bin/python -m pip install --no-index --no-deps second_paddle_process_receipt-0.2.0a1-py3-none-any.whl
  .process-env/bin/process-receipt --help
)
```

After successful installation:

```sh
.process-env/bin/process-receipt --receipt result.json --stop-file STOP --timeout 30 -- /full/path/your-program
```

The original `python -m process_receipt` remains POSIX-only; the portable module entry is `python -m process_receipt_cli`.

## Read the outcome precisely

`completed` means direct-child exit code zero was observed, not that the user's goal was fulfilled. An existing receipt is never replaced. A Windows stop records `finished_after_stop_request` with separate request and observed-exit fields; it does not fabricate POSIX signal evidence. Wrapper exit 130 is an outcome category, not the Windows child's exit code. Windows termination is forcible, not graceful.

This alpha inherits the caller's environment and is not a credential or hostile-code sandbox. It cannot undo completed effects, stop remote jobs, guarantee instant cancellation, or certify every descendant. All Windows versions, GUI use and supervisor-kill recovery are not qualified.

## Evidence and provenance

[Implementation and native-test boundaries](https://github.com/YS-OH-CORE/second-paddle-notes/pull/10). `BUILD_PROVENANCE.json` pins the build head, tested merge checkout, source commit, original artifact and runtime hashes. Native Linux previously tested the same module bytes in a separately built wheel. The publication workflow separately checks this exact published wheel after unauthenticated download on Windows and Linux. A release page alone is not proof those consumer jobs passed; inspect the actual workflow result and its `alpha-consumer-*` evidence.

These are author-run engineering checks, not third-party adoption or institutional certification. The local-container graceful-exit failure documented in PR10 is preserved; hosted Linux passing does not erase it. The repository's automatic source archives include unrelated notes. The utility's MIT license applies to its newly authored tool files, not all repository material.

Project by Youngseok Oh; implementation and publication prepared with Zero (ChatGPT). No OpenAI endorsement. Release API semantics: [GitHub releases documentation](https://docs.github.com/en/rest/releases/releases).

## 한국어

Windows에서도 직접 시작한 실행 파일의 종료를 확인하는 실험판이다. 기존에 검사한 설치파일을 그대로 공개하며, 개인 대화나 계정 자료는 포함하지 않는다. 승인이나 모델 판단을 대신하는 시스템이 아니라 실행 결과를 구분하는 도구다. 공개 다운로드와 설치 검사는 배포 워크플로에서 별도로 확인한다. 영석의 PC에는 설치하지 않는다.
