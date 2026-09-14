# Checked, opt-in skills

Prepared by Youngseok Oh with Zero (ChatGPT).

## GitHub Write Reconcile 0.1.0a1

[Public preview and checksums](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/github-reconcile-v0.1.0a1)
· [Korean getting-started guide](../packages/reconcile-skill/START_HERE.ko.md)
· [Publication evidence](../packages/reconcile-skill/PUBLICATION.md)
· [Skill source](github-write-reconcile/SKILL.md)

A standalone Python command and complete skill folder for checking an expected
GitHub file before deciding what to do after a lost write response. Four distinct
outcomes: matching content, conflict, absence at one snapshot, or unknown.
It reads only; every result has retry_authorized=false.

The small runtime ZIP includes the original 12-file skill and a package verifier.
The separate evidence ZIP retains original successful and failed records plus
matching source. It is not the existing evidence-mcp wheel and does not update it.

After extracting the runtime ZIP into a new directory:

```sh
python -B -S VERIFY.py
python -B -S github-write-reconcile/scripts/reconcile.py --intent github-write-reconcile/examples/completed-retry.json
```

The first command is offline. The second reads an existing public record.
Python 3.10+ is required; network/access/rate-limit problems remain unknown.
Hermes installation is optional and requires the whole skill folder, not just
SKILL.md. Nothing here installs into or overwrites an existing user profile.

The command, real Hermes skill loader, and real Hermes terminal-to-GitHub path
were checked separately in PR45, PR46 and PR47. The harness selected those tasks;
model-selected behavior and the user's live installation remain untested.
