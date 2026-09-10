# Process Receipt 0.1.0 (alpha)

**Download an already built wheel, install it, and record what actually happens to a trusted command.**

This release promotes the exact wheel previously built and tested in [run 34539459938](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34539459938). It is not a rebuild, a new model, or a PyPI upload. The downloadable wheel is no longer available only through a 30-day Actions artifact.

## Download and install

Linux/POSIX, Python 3.10 or newer:

```sh
curl --fail --location --output second_paddle_process_receipt-0.1.0-py3-none-any.whl \
  https://github.com/YS-OH-CORE/second-paddle-notes/releases/download/process-receipt-v0.1.0/second_paddle_process_receipt-0.1.0-py3-none-any.whl
printf '%s  %s\n' \
  6c4242fcf26685e9b0740ac634aca0bdc4c5c4a1e3532da224d102f74c1a73e8 \
  second_paddle_process_receipt-0.1.0-py3-none-any.whl | sha256sum --check -
python3 -m venv .process-env
.process-env/bin/python -m pip install --no-index --no-deps \
  second_paddle_process_receipt-0.1.0-py3-none-any.whl
.process-env/bin/process-receipt --help
```

Use a new environment name if `.process-env` already exists. A wheel is an installation package; inspect code before trusting any downloadable program. The checksum checks identity with this release, not a publisher-independent signature.

For a real job, use a NEW receipt filename:

```sh
.process-env/bin/process-receipt --receipt result.json --stop-file STOP --timeout 30 -- python3 your_job.py
```

Creating `STOP` requests termination. An existing stop prevents launch. The tool does not remove the stop file or overwrite an existing receipt. Read `status`, `task_started`, `child_exit_code`, and `direct_child_exit_observed` separately. `completed` means an observed exit code 0, not proof the job did what its user intended.

## Exact published files

- `second_paddle_process_receipt-0.1.0-py3-none-any.whl`: 10,088 bytes, SHA-256 `6c4242fcf26685e9b0740ac634aca0bdc4c5c4a1e3532da224d102f74c1a73e8`.
- `SHA256SUMS`: checksums for the wheel and provenance.
- `BUILD_PROVENANCE.json`: public source commit, build run, artifact identity and module identity.

Build source: `388efef41ae8f0a754ba5508fc7fcccc819a97c0`. The release tag points to the publication commit, which adds the distribution procedure but does not change this wheel's runtime. The generic repository release `v0.1.0` remains separate; this tool has its own `process-receipt-v0.1.0` tag.

GitHub's automatic source-code archives cover the whole repository. The utility's MIT license applies only to its newly authored tool files, not all research notes in those source archives.

## Scope

Author-run engineering checks, not third-party adoption or independent validation. Linux tested; the pure-Python wheel filename does not provide Windows support. The tool observes its direct child's exit, not every detached or remote process. It cannot undo completed effects or guarantee instant cancellation, and it inherits the caller's environment. Only run commands you trust.

Project: **Youngseok Oh's Second Paddle Notes**. Implementation and publication prepared with **Zero (ChatGPT)**. No OpenAI review or endorsement is implied.

## 한국어

이제 GitHub 작업 기록 안의 임시 첨부가 아니라, 이 공개 배포 페이지에서 설치파일을 직접 받을 수 있다. 기존에 검증한 파일을 그대로 게시하며 새 모델이나 서비스 가입은 필요 없다. 공개 다운로드 뒤의 별도 설치 확인은 배포 워크플로 결과에서 확인한다. 작성자의 확인과 다른 사람의 채택은 구분한다.
