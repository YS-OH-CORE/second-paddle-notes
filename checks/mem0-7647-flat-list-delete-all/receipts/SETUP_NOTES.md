# Setup events and run accounting

Before any measured deletion test, a system-Python virtual-environment bootstrap failed because Ubuntu ensurepip was unavailable. A diagnostic command also failed at shell argument quoting; no test ran in that command. Scripts were subsequently staged as UTF-8 files and executed directly through WSL.

The successful setup is recorded in SETUP.json: an isolated uv binary came from the official PyPI artifact with its SHA-256 checked against published metadata, an isolated Hatch tool was installed, and Hatch created the project test environment. No system package installation was required.

The measured software observations consist of one preliminary native Chroma/sync/populated smoke case, then the full baseline, PR and selective-control matrices in that order. All 49 observations are retained, including the 12 PR failures. There were no discarded or repeated full-matrix runs. The smoke case is separate and is not added to any 16-case denominator.

PR observation mode exits zero when collection completes; its 12 failed behavioral cases are not passing tests. The three main process statuses appear in RUNS.json. Selected unit checks are separate from that matrix; VALIDATION_CONTEXT.json records the driver context and a source check taken after those checks.

The public Hatch configuration removes the original machine-specific environment path. The remaining configuration is the one used for environment resolution; dependencies.json records the actual installed versions.
