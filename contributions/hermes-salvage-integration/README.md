# Consolidated Hermes lifecycle: selected outer-inbound integration

This is supplemental AI-assisted test work with Zero (ChatGPT), not a competing implementation. The production repair and original defect findings remain with Hermes PR107013's contributors and PR107979's consolidating maintainer.

The prior helper-only review applies to `b2f009d4f289597a5eace6b9c7a169901c3a5af8`. This contribution runs new, identical outer-inbound tests on that earlier candidate and the consolidated `c9122c0cc9544653611d1e2c5151f77bb41a743d`. Historical pass counts are not relabelled as results for the new tree. The latter source now reads successfully through the normal repository connection after the earlier HTTP429. The chat container has no GitHub DNS access, so execution is on an explicitly scoped hosted runner, not a claimed local run.

## What actually executes

Real `_handle_message`, its outer finalizer, `_hm_cmd_moa`, durable reaped-session eviction, shared stop core, model snapshot/restoration and transcript-lease helpers. A real temporary SessionStore/SQLite database ends a session; the same routing key reattaches to the same ID for `ws_orphan_reap` or resolves a new ID for `idle`. Actual asyncio locks serialize the same-ID case, and two different locks coexist in the different-ID case. Controlled Events place the old finalizer after the successor's slot has been claimed.

Eight cases: four replacement cases (two ID paths, with/without a preexisting model override), two stop-without-successor cases, two ordinary-completion positive controls. The current tree's two original adjacent test files also run without modification.

## What is deliberately not executed

Admission/authorization and emergency-stop gates, unrelated command/plugin discovery, actual capacity accounting, cache/persistent-active-state I/O, durable active-turn markers, the complete `_handle_message_with_agent` body including auto-reset policy/hygiene, provider/model calls, real platform delivery, a running gateway server, process cancellation and every possible interleaving are not qualified. Capacity and agent work are recording fixtures. The original upstream `_make_runner` test fixture is reused rather than attributed as our production implementation. This is neither an exactly-once proof nor a claim that the maintainer accepted our review.

## Run and inspect

Provide clean, exact source checkouts and the dependencies specified in `.github/workflows/hermes-salvage-integration.yml`, then run `verify.py --base <older-tree> --head <consolidated-tree> --out <new-folder>`.

The verifier records source hashes, test identity, three XML reports, stdout/stderr and per-case observations before accepting results. Setup errors are not counted as the target regression. No production file or original test is edited. A workflow being present is not a successful execution: inspect the concrete run and returned artifact. Publication initially contains unexecuted tests; observed outcomes belong in the PR's dated execution record.

Primary context: https://github.com/NousResearch/hermes-agent/pull/107979 and https://github.com/NousResearch/hermes-agent/pull/107013 . Related earlier integration review concepts by andrexibiza are credited in the upstream discussion; this new harness and its exact execution must stand on their own evidence.
