# Source acquisition attempt history

1. Run 36358248219 / job 108730150823 installed dependencies but stopped before extraction or tests: the complete upstream ZIP exceeded the registered 64 MiB bound.
2. Run 36358576690 / job 108731086812 switched to shallow blob-filtered sparse checkout, but the broad source/config extension selection still exceeded 64 MiB. It also stopped before any pytest cases.
3. The next setup keeps the pinned head, test cases and limits, but narrows selection to root Python and the real import packages (agent, hermes_cli, tools, plugins, gateway, cron). A separate local synthetic Git tree verified that these patterns exclude tests, website and unrelated JSON assets. Selected bytes and the largest files will be logged, rather than relaxing the bound.

These are acquisition failures in our runner, not Honcho regressions or completed runtime tests. The workflow gates each documented retry to one exact prior head transition and attempt 1. No user PC, model calls, live service credentials or upstream production code are involved. All failed attempts remain visible. No runtime pass is claimed until actual assertions execute.
