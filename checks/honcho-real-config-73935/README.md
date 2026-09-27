# Real on-disk Honcho config reaches provider startup

Status: test candidate; no execution outcome claimed yet. Prepared by Zero with Youngseok Oh's direction.

This addresses the concrete test request in the **automated** review https://github.com/NousResearch/hermes-agent/pull/73935#discussion_r3684494258 . It is not a personal endorsement or direct invitation from the account holder. The target is that proposed fix's pinned head `91b3b31dc91aec04abac8be5d240f2d0ad491054`, not current Hermes or the standalone handoff plugin.

The new pytest file writes synthetic `honcho.json`, MEMORY.md, USER.md and SOUL.md into a temporary HOME/HERMES_HOME. It keeps the real config loader, provider, session manager, and file-migration code. Only the remote SDK factory/object graph is doubled; no real transport or account is called. Socket connections are guarded during the test.

Four configs cover root false, host false overriding root true, host true overriding root false, and omitted/default true. Startup readiness and context reading must occur before the upload assertions; a disabled or broken provider cannot count as success. The enabled paths must reach all three file uploads with their synthetic content. The disabled paths must not. Original config bytes must remain unchanged.

After the unmodified head passes, the driver deliberately bypasses only the startup guard, then separately replaces the config's disk value with True. These are local detector controls, not upstream bugs or candidate fixes. Each should fail just the two disabled-config cases. Source files are restored after the run. Four unique cases, not twelve distinct discoveries.

Execution is bounded to one seven-minute standard public GitHub-hosted job on opening this draft branch; no cache or artifact upload, user PC, model inference, paid model API, private records, credentials, schedule or automatic repeat on edits. Public source archive and selected contents each have a 64 MiB limit. Dependencies stay in a disposable venv. The local ChatGPT runtime could compile these files but could not fetch dependencies due to DNS failure; that is not a runtime test result.

Limits: direct pytest with --noconftest, not the full upstream suite. It does not test live Honcho, CLI/gateway admission, arbitrary profile concurrency, or every lifecycle hook. It must not be used as proof of universal read-only execution. It adds tests only; the patch implementation remains its original contributor's work.

Source review also found a newer standalone handoff at https://github.com/NousResearch/hermes-plugin-honcho/tree/32dfd0ba62ae0e8dad82d55fc81515e8c4a181a9 . Its HANDOFF.md explicitly calls it a handoff copy rather than an officially maintained Nous plugin. Do not transfer this old-head test result to that separate snapshot without running it there. No competing implementation or release is proposed.
