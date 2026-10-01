# Formal core of the sequential audit

Youngseok Oh (research direction), Zero / ChatGPT (formalization), 2026-09-16.

Initial status: uncompiled proof attempt. Only observed compiler, kernel and
leanchecker results can establish the completed formal scope. A draft PR is not
an academic submission or independent referee review.

Core.lean proves a finite-tree crossing bound, its capital-one/threshold-twenty
5% consequence, mixture and multiplier closure, and the truncated stopped-drift
mean inequality. The trees allow arbitrary finite depth and history-dependent
real branch probabilities; these are universal proofs, not a finite policy grid.

Concrete.lean encodes current-prefix one-flip policies directly using nested
Option/Product/Bool types. Kernel evaluation checks the inherited renormalized
rational score against every one of the676 encoded policies and both unsafe
source counts. Symbolic proofs extend that support to arbitrary real mixtures.
No imported list of allegedly complete laws supplies the claim.

Not formalized: the root-defined KL saddle, logarithm interval arithmetic,
global KL optimality, asymptotic mean-cost constant, the infinite-horizon
measure-theoretic limiting argument, semantic labeling, physical freshness or
the real reader's one-fault contract. The finite tree drift theorem assumes
its local drift and terminal cap. Actual positive logarithmic drift is not
inferred just by constructing a tree. Reflection transfers the same directional
argument to the other hypothesis; a real deployment process is not instantiated.

Lean4.29.0 and mathlib8a178386ffc0f5fef0b77738bb5449d50efeea95 are pinned.
Run lake update; lake exe cache get; then set ZERO_PROOF_OUTPUT to a new directory
and run python check_run.py. It builds, checks transitive axioms, rechecks compiled
declarations with leanchecker, and requires two false claims to be rejected.
No unfinished proofs, new axioms, native proof computation or kernel bypasses are
permitted. Expected foundational axioms: propext, Classical.choice, Quot.sound.

The named same-repository branch uses standard public CPU Actions, contents:read,
no persisted checkout credentials, no cache upload and a15-minute job ceiling.
Only small proof files/logs are retained for1day. Toolchain and mathlib binaries
are not published as artifacts. Public compute minutes are unbilled under GitHub
policy; artifact storage has its separate account-wide policy. No billing setting,
original research file, user-PC configuration or existing source is changed.

New authored code follows ../../tools/evidence-mcp/LICENSE from repository root.
Lean/mathlib and the CI actions retain their own licenses.
