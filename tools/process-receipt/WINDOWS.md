# Experimental Windows direct-process support (0.2.0a1)

Install the new alpha wheel, then use the same `process-receipt` command. This is
not WSL or emulation: the Windows backend launches an EXE using native Python
subprocess support. Python 3.10 or later is required. No runtime dependencies,
model account, admin privilege, taskkill or remote service is added.

```powershell
python -m pip install --no-index --no-deps .\second_paddle_process_receipt-0.2.0a1-py3-none-any.whl
process-receipt --receipt result.json --stop-file STOP --timeout 30 -- C:\Python313\python.exe your_job.py
```

Replace the example EXE with the actual trusted executable on your machine.
From another PowerShell in the same directory, request a stop:

```powershell
New-Item -ItemType File -Path STOP
```

An existing stop path prevents launch. Stop files are never removed and old
receipts are never overwritten. Choose fresh paths for a deliberately new run.
Arguments are passed without an implicit shell; `.bat` and `.cmd` entry points
are rejected. Explicitly launching a shell is still only supervising that shell.

## What the receipt means

`backend=windows-direct-child` records the narrower scope. A stop uses
`Popen.terminate()`, which calls Windows TerminateProcess. `kill()` is the same
operation on Windows, so this backend does not pretend a second stronger signal
exists. `grace` is the bounded wait after that request, NOT a graceful phase.

The receipt separates `termination_requests`, `termination_request_returned`,
`alive_when_stop_observed`, `direct_child_exit_observed`, and
`exit_observed_after_termination_request`. The status after an observed stop is
`finished_after_stop_request`, not the POSIX `interrupted` status. The CLI returns
130 for that observed sequence, 124 for a deadline with exit observed, 0 for
normal exit 0, and 2 for other outcomes. The child's own exit code is preserved.
`signal_exit_after_request_observed` stays false and `signals_requested` empty.
No particular Windows exit code alone is treated as proof of a stop.

This is not causal authentication: a process can exit concurrently. A completed
receipt proves what this supervisor observed, not that every child of the target
stopped or its goal was achieved. Stop-file polling, process startup, I/O and
termination can be delayed. A force-killed supervisor may leave its child alive
and only a partial receipt. Completed side effects cannot be undone.

## Native qualification

`verify_portable_install.py` installs the wheel into a fresh environment, verifies
both platform backends and the installed entry point against source, and runs
from outside the source directory. It checks exact synthetic file output,
nonzero exit, prestop, receipt collision, timeout, a running heartbeat workload,
invalid limits, identical paths, missing EXE, and batch rejection on Windows.
The worker uses the real base Python EXE, not a venv launcher. Receipt and
heartbeat observations are retained. Linux also runs the existing 40-case
software fixture and compares its output bytes with the committed references.

These are author-run native engineering checks, not independent adoption,
Windows desktop interaction, all Windows versions, or hostile-code isolation.
The installed environment and child output remain the caller's responsibility;
never run untrusted commands or sensitive commands in public CI.

References:
- https://docs.python.org/3/library/subprocess.html#subprocess.Popen.terminate
- https://docs.python.org/3/library/subprocess.html#security-considerations

New implementation and verification authored with Zero (ChatGPT) for Youngseok
Oh's existing public project. The scoped MIT license in this folder applies.
