# All execution attempts

These four runs belong to the same CPU-only review experiment. Setup failures are retained as setup failures; none is counted as a scheduler test result. Run links are canonical public GitHub Actions links. Downloaded ZIPs passed CRC validation and matched the recorded SHA-256 values before extraction.

## Attempt 1: precompiled base wheel unavailable

- [Run 36451518079](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36451518079)
- Workflow commit: `729845f635b61ab4d6f07415e55a563714f5a2a4`
- The automatic CPU precompiled-wheel lookup for base `94d14629247955c69d40bdf2a9d7e3bd45954452` returned HTTP 404. Our install pipeline did not yet use `pipefail`, so the shell continued and subsequently encountered missing `torch`.
- **Zero tests executed.** This was an environment/setup failure, not a candidate failure. The overall job failed even though an intermediate pipeline did not propagate its install error correctly.
- Preserved files: [attempt1](receipts/attempt1/). The test addition and patch were prepared, but preparation is not execution.
- Downloaded artifact: ID `10983607315`, 4,971 bytes, SHA-256 `f751d719c2f9deb0e16e9e5bcff65a7b26f64e7e3795844c0d76130b304bdb0f`.

## Attempt 2: our wheel inspector was too strict

- [Run 36452491157](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36452491157)
- Workflow commit: `9bda23f8f4ddb652c817937d1f664b25c5de5d89`
- The official v0.30.0 CPU release asset passed the expected size and digest checks. Our inspector then rejected the difference between the wheel filename's platform tag and the embedded `WHEEL` tag.
- **Zero tests executed.** The release publishing script intentionally retags the filename only. The later inspector accepts this specific platform-only difference while requiring unchanged Python/ABI tags, compatible host tags, the expected digest, the CPU package version, and compatible Torch requirements.
- [Publisher's script at its release source commit](https://github.com/vllm-project/vllm/blob/ced6857afa0ea7b2e3f0846a62e1394e90f15607/.buildkite/scripts/detect-manylinux-tag.py).
- This run uploaded **no artifact**: the inspector's intermediate files were outside the then-configured upload directory. [tag-check-excerpt.log](receipts/attempt2/tag-check-excerpt.log) is an explicitly selected excerpt from the public job log containing the traceback and no-artifact warning, **not a full raw job log or a recovered wheel artifact**.
- The actual embedded `WHEEL` metadata is preserved from attempts 3 and 4, not attributed to this missing artifact.

## Attempt 3: GPU torchcodec selected in the CPU environment

- [Run 36452985480](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36452985480)
- Workflow commit: `09c32a244d1831d256ac8302134ea7575d184870`
- The CPU development environment installation passed. Importing the scheduler then reached a GPU `torchcodec` build that required unavailable `libnvrtc.so.13`.
- **Zero tests executed.** This was a dependency import failure, not evidence about abort handling. The command's `--torch-backend cpu` setting alone did not select CPU torchcodec.
- Preserved install/package/wheel inspection files: [attempt3](receipts/attempt3/). The scheduler import failure itself appears in the linked job log; this artifact does not contain a test-result log for that failed import.
- Downloaded artifact: ID `10983419838`, 13,032 bytes, SHA-256 `65bb82281e6cd643f654b1ddb382bcfe9ebfc74952d39e9a7c8a39edd5896dcf`.

## Attempt 4: completed comparison

- [Run 36453327818](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36453327818)
- Workflow commit: `491a2d4cb6a5b94b6f9a0678e90a4a9ed98b7f96`
- Explicitly installed `torchcodec==0.14.0+cpu` from the official CPU package index, consistent with the frozen upstream CPU test requirements.
- Candidate: **13 passed, 0 failed, 0 errors, 0 skipped**, exit 0, no timeout.
- Deliberately removed deferred cleanup: **2 failed, 0 errors, 0 skipped**, 11 deselected, exit 1, no timeout. Both failures were the waiting-statistics comparison `(0, 1)` versus `(1, 0)`.
- The original production scheduler file was restored byte-for-byte; its final Git diff was empty.
- A successful workflow means that this specified comparison and restoration checks matched. It does not mean the deliberately broken variant passed its tests.
- Preserved raw logs, JSON, JUnit XML, patch, package list, wheel metadata, and summary: [attempt4](receipts/attempt4/).
- Downloaded artifact: ID `10984129701`, 19,679 bytes, SHA-256 `c15efd607db1fc8ffd8165d6ccdab97b73a9199c2906df1d20d37b35ba589d77`.

## Retention and integrity

The original Actions artifacts have a 30-day retention setting. These extracted text receipts are committed here to keep the evidence inspectable after that expiration. `file-manifest.json` records byte counts and SHA-256 hashes for all files in this report directory except the manifest itself. No signed artifact-download URL, credentials, or private conversation transcript is included.

AI assistance was used in this verification work. The upstream design and implementation remain the original author's work.

Zero × Youngseok Oh
