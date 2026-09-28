# SGLang #41404: proposed bounded CPU environment

Status: source-inspected draft, **not installed or executed**. No CI job or external change was made while preparing these files. The target is frozen at [`d574752ef39eb3ef73f87c40dca95d76222f9483`](https://github.com/sgl-project/sglang/commit/d574752ef39eb3ef73f87c40dca95d76222f9483).

Use Python 3.12, uv 0.9.28, Torch 2.13.0+cpu, torchvision 0.28.0, and real Triton 3.8.0. Install SGLang through its existing alternate-platform `srt_empty` / `runtime_common` extras. This is a bounded derivative of official package paths, not a claim to reproduce the complete upstream CI environment.

The package files themselves document the entry point: [`python/pyproject_other.toml`](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/pyproject_other.toml) says to copy it to `pyproject.toml` and install `.[srt_empty]`. `srt_empty` supplies `runtime_base`; `runtime_common` adds compressed-tensors, outlines, timm, and xgrammar needed by broader runtime imports. Specifying both extras is harmless; their shared base is resolved once. This avoids the default main-package NVIDIA dependency set. The same source pairs Torch 2.13.0 with torchvision 0.28.0 for MPS; CPU builds are selected here by uv's `--torch-backend cpu`.

```bash
uv venv --python 3.12
cp python/pyproject.toml "$RUNNER_TEMP/sglang-original-pyproject.toml"
trap 'cp "$RUNNER_TEMP/sglang-original-pyproject.toml" python/pyproject.toml' EXIT
cp python/pyproject_other.toml python/pyproject.toml
SGLANG_BUILD_RUST_EXTS=none uv pip install --python .venv/bin/python \
  --torch-backend cpu --editable 'python[srt_empty,runtime_common]' \
  torch==2.13.0 torchvision==0.28.0 triton==3.8.0
cp "$RUNNER_TEMP/sglang-original-pyproject.toml" python/pyproject.toml
trap - EXIT
```

`SGLANG_BUILD_RUST_EXTS=none` is an explicitly supported build setting in [`python/setup.py`](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/setup.py); it short-circuits Cargo discovery. No Rust extensions or CPU kernel package should be needed by this fixture. Keep the frozen runtime and test files unchanged and restore the original active pyproject after installation. The draft workflow does so even if installation fails.

Set `SGLANG_IS_IN_CI=true` and `SGLANG_TEST_MAX_RETRY=0`. The second setting disables `CustomTestCase`'s default CI retry. Leave `SGLANG_USE_CPU_ENGINE` unset. The [hosted upstream CPU-unit workflow](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/.github/workflows/_pr-test-stage-cpu.yml) also leaves it unset; it uses Python 3.10 and the heavier default `python[dev]` install. The registered test is assigned to that workflow's `base-a-test-cpu` suite. With a CPU-only Torch wheel and no platform plugin, the [platform resolver](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/sglang/srt/platforms/__init__.py) falls back to the base `SRTPlatform`. This is the intended platform for the control-flow fixture; the import probe must establish compatibility. It is not the Xeon inference engine.

The separate [CPU inference pyproject](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/pyproject_cpu.toml) pins Torch 2.14.0 and torchvision 0.29.0. The [CPU server instructions](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/docs/docs/hardware-platforms/cpu_server.mdx) and [Xeon Dockerfile](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/docker/xeon.Dockerfile) additionally build the CPU `sgl_kernel` package and set the CPU-engine / AMX environment. That is a substantially different execution path and is unnecessary for this experiment. Availability of Torch 2.14.0 CPU wheels was not investigated because this route does not require them.

The complete upstream [test module](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/test/registered/unit/disaggregation/test_deferred_decode_kv_release.py) imports actual decode, common manager, NIXL manager, Mooncake manager, and `CustomTestCase` classes. Its existing fixture uses `__new__` to avoid initializing transports and patches explicit boundary operations. Run it directly:

```bash
SGLANG_IS_IN_CI=true SGLANG_TEST_MAX_RETRY=0 \
  .venv/bin/python test/registered/unit/disaggregation/test_deferred_decode_kv_release.py -v
```

The direct unittest runner itself does not require `pytest` or `expecttest`. The fixture does not initialize a model or live transport, and the inspected `sgl_eval_utils` module imports external `sgl_eval` inside its evaluation function. Full transitive import compatibility remains to be verified by execution. Additional harness dependencies may be installed explicitly if a separate test driver needs them.

Import considerations verified in the frozen source:

- [`utils/common.py`](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/sglang/srt/utils/common.py) and [`memory_pool.py`](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/sglang/srt/mem_cache/memory_pool.py) import Triton unconditionally. Install the real package even on a CPU host.
- [`nixl/conn.py`](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/sglang/srt/disaggregation/nixl/conn.py) guards the NIXL bindings import and defers engine initialization. [`parallel_state.py`](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/sglang/srt/distributed/parallel_state.py) imports the Mooncake engine inside the initialization function. Neither engine is initialized by the bare fixture.
- The checksum import reaches [`kernels/ops/memory/adler32.py`](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/sglang/kernels/ops/memory/adler32.py), whose JIT compilation is inside the called function. No checksum execution is intended here.
- [`test_utils.py`](https://github.com/sgl-project/sglang/blob/d574752ef39eb3ef73f87c40dca95d76222f9483/python/sglang/test/test_utils.py) contains an official `maybe_stub_sgl_kernel()` helper for machines without usable GPU kernels. The target does not call it. The initial draft **does not call it either**. If an actual import failure later proves that an unused GPU boundary needs this official helper, record that adjustment explicitly in a separate attempt; never replace decode, tracker, transport-manager control flow, or the target test module with stubs or extracted source.

`env_probe.py` loads the complete target via Python's import machinery, verifies actual module paths and bytes against the frozen Git blobs, records SHA-256 hashes and Torch binary provenance, verifies CPU-build properties, confirms the real `CustomTestCase`, and counts discovered tests. It does not execute or interpret a bug witness. The workflow then executes the full upstream test in a fresh process and retains raw stdout, stderr, and exit code. Installation or import failure is environment evidence, not evidence for or against the proposed lifecycle defect. Preserve `packages.txt`: unpinned transitive runtime dependencies are otherwise time-dependent.

The draft expects `env_probe.py` at `checks/sglang-41404-deferred-release/env_probe.py` in the notes repository. Root may merge this setup into its final witness driver; no draft here establishes any test result, GPU behavior, live RDMA safety, full serving correctness, or performance claim.
