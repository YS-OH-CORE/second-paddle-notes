# Hermes #121935: distinguish provider-off, automatic-persistence-off and strict read-only

Youngseok Oh x Zero, AI collaboration partners | 2026-09-25

**Scope: source-selected, unchanged upstream method bodies with fake manager/SDK collaborators and inline scheduling. Not a complete-package, CLI, live Honcho or concurrent-invocation test.**

This follows [the new write-time-gating proposal in #121935](https://github.com/NousResearch/hermes-agent/issues/121935#issuecomment-5828279986), which referenced our earlier supplied-manager initialization check. The goal is to supply concrete acceptance-test cases, not implement an unapproved feature or relabel all existing behavior as a bug.

## What ran

Pinned upstream: `7b761da2de4979e424510ca7022bf9527aa65b68`.

[Probe](probe.py) and [pre-execution protocol](PROTOCOL.md) were committed before execution at `6048120e3518599fd99944a685a8879e63ab2e76`. The probe verifies these exact source Git blobs:

- `plugins/memory/honcho/__init__.py`: `14255ce5a1143e1a78c4b3c6e28c48c3512f8871`.
- `plugins/memory/honcho/session_migration.py`: `9fd2ca17b4936ceafb391f58529c645dac222218`.

AST selects 13 unmodified provider methods and the migration method. The containing class/bases, import dependencies, manager/SDK, sanitization, gateway predicate, state, session-key resolver and thread scheduler are fixture substitutes. Mutating manager calls are recorded, not executed against a service. Migration uses the real selected loop and synthetic temporary MEMORY.md/USER.md/SOUL.md files; SDK upload_file is a recording fake. Explicit tools enter through the selected real handle_tool_call dispatcher in a prepared session.

## Observed matrix

Fourteen cases were run once with saveMessages=false and once with true: **28 unique condition/case observations**, not 28 independent users or live-service tests.

| Entry point / condition | saveMessages=false | saveMessages=true |
|---|---|---|
| Automatic sync_turn | No manager events | get_or_create + save |
| Automatic profile mirror | No manager events | create_conclusion |
| on_session_end | No manager events | flush_all |
| Explicit conclusion creation | create_conclusion | create_conclusion |
| Explicit conclusion deletion | delete_conclusion | delete_conclusion |
| Explicit card update | set_peer_card | set_peer_card |
| Conclusion list | list_conclusions | list_conclusions |
| Card read | get_peer_card | get_peer_card |
| Cold owner, blank per-directory session | get_or_create + 3 fake upload_file calls | Same |
| Warm owner session | get_or_create, no upload | Same |
| Per-session strategy | get_or_create, no upload | Same |
| Nonowner session | get_or_create, no upload | Same |
| Invalid conclusion arguments | Error, no manager events | Same |
| Bot-authored conclusion write | Refusal, no manager events | Same |

The migration case requires nonempty files, a cached SDK session and matching declared owner. The three files produce upload calls under the user/user/assistant peer respectively. This is evidence about call reachability in those conditions, not evidence of a real user's data being uploaded.

## Why this matters for the proposed invocation policy

A provider-only opt-out and strict read-only execution are different contracts. Disabling the three automatic hooks is not enough to characterize strict read-only behavior: explicit tool mutations and startup file migration must be included in the acceptance criteria too. Listing existing conclusions or reading a card must remain callable for the read-only variant being discussed.

This is **not a new discovery of the startup-migration issue**. Existing [PR #73935 by saurabhmeddo](https://github.com/NousResearch/hermes-agent/pull/73935) already proposes covering automatic persistence including migration and expressly preserves explicit tool writes. It was open/unmerged when reviewed. We reviewed that proposal, not executed its head. Silently repurposing saveMessages to block explicit tools would change that stated contract. The proposed strict invocation-scoped policy needs a separate decision.

Session-source provider disabling in [PR #117358](https://github.com/NousResearch/hermes-agent/pull/117358) is a related but different design, also disabling provider reads. This follow-up does not compete with either PR or expand the original request unilaterally.

Shared-manager policy propagation, delayed/background writes, shutdown and session/peer metadata writes still need real-path coverage for a strict no-persistence guarantee. These are not established by this probe. Other providers, server-side derivation, memory quality and model inference are outside its scope.

## Reproduce and audit

Download the two pinned upstream files as provider.py and migration.py into a source directory, then run in a fresh process:

```bash
python -B probe.py --source-dir ./source --out ./new-output
```

The subprocess denies Python socket connections and DNS resolution. No credentials, model, real user profile or hosted-memory endpoint is used.

[Successful CPU run 36110765090](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36110765090) retained the script, protocol, upstream license, exact sources, environment metadata, full observation JSON and execution log in [artifact 10852971081](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36110765090/artifacts/10852971081). Its ZIP SHA-256 is `94ccd56622b11672c50ae5c75a875bf2ef31890e3d84c34344bc4c7c27d7aa15` (31,278 bytes). Actions retention is 30 days; [compact observations](OBSERVATIONS.json) are committed here.

Readback audit verified ZIP and probe checksums, 28 unique cells and exact equality between the log's JSON rows and report.json. Replaying the same retained probe and sources under local Python 3.13.5 produced identical report contents to the GitHub run. This is same-fixture replay, not independent external replication.

[First setup attempt 36110638943](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36110638943) failed with HTTP 429 during source download, before any case ran. Only source-download spacing and bounded Retry-After/backoff were added; the probe SHA-256 remained `7e146ec2310457af53bcbfebccb8002e838ff6a6213769659cd4fa85cbb68e3e`. That setup failure is not a behavioral test result.

Credit: fmunechi's original opt-out request; mdhaseeb343q-pixel's write-time/invocation policy proposal; saurabhmeddo's existing automatic-persistence proposal; upstream Honcho/Hermes code and other cited authors. Supplemental source-selected fixture, execution and analysis: Zero, AI collaboration partner working with Youngseok Oh. No maintainer agreement or adoption is implied.
