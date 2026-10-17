# Real on-disk Honcho config reaches provider startup

**Completed: four configuration cases passed on the pinned proposed fix.** Two deliberate local detector controls failed the expected disabled-setting cases, while their enabled cases still passed. [Results, evidence and limits](RESULTS.md) · [Structured log summary](OBSERVED.json) · [Test to inspect or adapt](test_real_config.py).

This addresses the concrete test request in the **automated** review https://github.com/NousResearch/hermes-agent/pull/73935#discussion_r3684494258 . It is not a personal endorsement or invitation from the account holder. Target: `saurabhmeddo/hermes-agent` at `91b3b31dc91aec04abac8be5d240f2d0ad491054`, not current Hermes or the standalone handoff plugin.

The test uses a real synthetic honcho.json, the real config loader, provider, session manager and startup file migration. Only the remote SDK boundary is doubled. An inactive provider is not accepted as evidence of suppression. Four cases cover root false, explicit host false overriding true, explicit host true overriding false, and legacy default true.

[Completed hosted run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36358747015) used test source `bd62b97a953ca19a73186617f447ee3c5b4c4a3c`. Two earlier source-acquisition attempts stopped before pytest; [their record](SETUP_ATTEMPTS.md) is preserved. The test itself was unchanged. The completed attempt did not relax the 64 MiB selected-source limit.

No user PC, private memory, model inference, paid model API, live Honcho backend or production changes. The runner fetches public source and should be used in a disposable environment. Direct pytest uses --noconftest; this is not a full upstream suite, current-main validation, or proof of universal read-only operation. No schedule or repeated run on result edits.

Implementation under test: its original contributor. Test design, execution and analysis: Zero, AI collaboration partner with Youngseok Oh's project direction. No new bug, upstream adoption, merge or institutional endorsement is claimed.
