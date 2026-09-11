# Receipt I/O failure is not proof of non-execution

Unreleased source fix: **0.2.0a2**. Existing 0.1.0 and 0.2.0a1 release assets are not replaced by this change.

## Reproduced defect

The legacy POSIX `python -m process_receipt` entry point in the published code can print `Process not launched: OSError` when a real child already wrote its output and exited zero, but the final receipt `fsync` raises an I/O error. The portable entry point already avoids that false categorical statement, but loses the observed outcome in a generic error. In both backends, an exception from receipt `close` can skip restoration of the caller's signal handlers.

The regression starts a real inert child that writes a marker, then injects failure only into receipt finalization. It does not fill a disk, damage user files, or cause an actual storage-device outage. A readable receipt may still exist after the simulated sync failure. File existence is not the same observation as successful finalization.

## Changed behavior

Both backends now raise `ReceiptPersistenceError`, an `OSError` subclass, with a small `summary`. Both command-line entry points print that summary to stderr and return 2. The summary separates `receipt_finalization_confirmed=false` from the already observed `execution` fields: status, whether the child started, whether its exit was observed, exit code and stop reason. No command arguments, environment values or raw exception message are copied into this summary. Inherited child output is unchanged and can still print sensitive content; this is not a credential sandbox.

A final I/O failure does not become exit 0. It also does not erase an already observed child exit. No automatic retry occurs, and a missing receipt must not be treated as permission to execute the command again. A failure before launch still records `task_started=false`. File close and signal-handler restoration are settled separately so a close error cannot bypass handler restoration.

The normal receipt schema, existing no-overwrite behavior, stop semantics and direct-child scope are unchanged. This does not provide exactly-once execution, rollback, reliable stderr delivery after a killed supervisor, protection from a failing signal-restoration API, or recovery from a whole-machine power loss.

## Verification

`test_receipt_persistence.py` contains nine cases: seven reporting/cleanup regressions and two positive controls. Windows intentionally skips the legacy POSIX-only module entry point. `verify_persistence.py` executes the identical test source against a pinned pre-fix checkout and the current candidate, checks actual imported source paths, stores per-case observations, and refuses missing/setup-error results. Read the actual CI result before treating native verification as completed.

Local Linux observation during authoring: original 7 assertion failures / 2 passes; candidate 9 passes. Both launch real disposable child processes. Native Windows results are not inferred from that Linux run. Existing original tests and installed-command checks are retained, with the installed version expectation changed to 0.2.0a2 only.

References: [Python fsync](https://docs.python.org/3/library/os.html#os.fsync), [Python signal handlers](https://docs.python.org/3/library/signal.html#signal.signal). AI-assisted implementation and tests with Zero (ChatGPT) for Youngseok Oh's project. No independent reviewer acceptance or production incident frequency is claimed.
