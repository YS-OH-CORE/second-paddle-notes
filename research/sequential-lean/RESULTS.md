# Observed result: the finite sequential core passed Lean verification

Research direction: Youngseok Oh. Formalization: Zero (ChatGPT).
Recorded 2026-09-16 KST. This is a scoped formalization result, not peer review or formal verification of the entire sequential-efficiency manuscript.

## Exact executed evidence

- Tested source commit: `628bdd9105ecdb0a3aee27b346a34cdc7443eb3e`.
- GitHub Actions run: [34993005092](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34993005092), job `104462119028`, completed successfully.
- Original artifact: `10406402851`, `sequential-lean-proof`, 259,307 bytes.
- Original ZIP SHA-256: `fedc84a17afd4641bd43aa96e90f1347c9f142703bbd7248e36f5fe4a62bda8a`.
- Lean 4.29.0, toolchain commit `98dc76e3c0a9b856c9b98726b713fb04fab16740`.
- Mathlib commit `8a178386ffc0f5fef0b77738bb5449d50efeea95`; complete dependency manifest retained.

The original ZIP was downloaded and opened. CRC/path checks, its exact digest, recorded source commit, and all four Lean-source SHA-256 values were checked against the contents. `verification.json` records `passed_declared_formal_scope`.

`lake build` returned 0 and built Core, Concrete, Process and the root module. The printed transitive axiom sets of all 13 requested declarations contain only `propext`, `Classical.choice`, and `Quot.sound`. No unfinished-proof or native-evaluation axiom occurs in those final declarations. Source scanning also rejects explicit new axioms, unfinished proofs and kernel bypass constructs. Three retained build warnings suggest shorter tactic syntax; they are not unfinished proof goals.

`lake env leanchecker ZeroAudit` returned 0. Its successful default output is empty. The pinned Lean 4.29.0 checker source was separately read: the target is a module-name prefix, missing object files cause failure, and every matching module is replayed from its imported environment. This is a recheck by the Lean kernel, not an independent external proof checker or a fresh replay of all mathlib dependencies.

## The mechanically checked implication

`Concrete.lean` defines the current-prefix, at-most-one-flip policy type directly. There are 676 encoded deterministic plans. Kernel reduction checks both unsafe source laws for every plan using the inherited rational multiplier, with common denominator `3000000000000000001`. Symbolic Lean proofs extend the support inequality to arbitrary real convex mixtures.

`Process.lean` constructs a capital process from these mixtures. Mixture weights and a stopping decision may be arbitrary functions of the observed finite history. They must be nonnegative and normalized at every history. It proves the local capital inequality from the actual score rather than assuming it separately.

The final theorem `ZeroAudit.concrete_five_percent` states that, for every natural finite horizon and every such history-dependent process and stopping rule, capital started at 1 has probability at most 1/20 of ever reaching 20 before that finite tree terminates. The probability is the explicitly defined recursive finite-tree mass. This is not an empirical sample of stopping policies.

`Core.lean` also proves a generic stopped-drift numerator bound for every finite tree satisfying local drift I and an upper terminal value B:

`I * expected_duration <= B - initial_value`.

The local drift value and terminal cap are assumptions of that generic theorem; the numerical KL drift is not proved by writing them as assumptions.

## Negative controls actually rejected

1. Increasing the tested rational score by 1% was rejected by `decide +kernel`, explicitly reporting the universal proposition false.
2. Claiming the 5% bound for a leaf already at capital 20, without the initial-capital-one condition, failed with an unsolved False goal.

Both compiler invocations returned 1 for the intended mathematical reasons, not missing imports or environment setup. Their complete logs are in the original artifact.

## What remains outside this formalization

- The exact algebraic KL minimizer, log enclosures, global information-rate optimality and asymptotic mean-cost coefficient.
- Infinite-horizon measure-theoretic limits and the full expected stopping-time theorem.
- The raw-archive/status reduction, real-world labeling, pairing, source authenticity and physical one-fault/fresh-conditional-law contract.
- End-to-end verification of the Python SequentialAudit implementation.
- Independent referee review, historical novelty, or empirical AI performance.

The concrete score is the predecessor's conservative, renormalized rational implementation. Formal validity of that score does not upgrade it to the exact algebraically optimal score. The formal process has a declared null direction; applying reflected semantics to the other direction and interpreting a real archive remain separate correspondence obligations.

## Failed attempts retained, not counted as successful verification

Run34990477485 failed before jobs because the job-level environment used an unavailable runner context. Run34991123952 installed Lean but stopped at a missing dependency manifest. Run34991308213 accepted Core but exposed noncomputable real definitions, a sum rewrite and an elaboration limit in Concrete. Run34991782693 left a finite-sum division rewrite unresolved. Run34992608044 accepted Core and Concrete but left the arithmetic normalization `(3+1+1+1)/6=1` in Process. Their source history remains in this PR; downloaded failure artifacts are retained in the conversation bundle. The theorem statements, rational score and allowed fault model were not weakened to obtain the final success.

Only this results document is added after the tested source commit. Main and the original research artifacts remain unchanged. The draft PR is a public inspection surface, not an academic submission. No reviewer has been contacted and no recurring task was created. The successful original artifact is retained by Actions for one day; a separate original-byte copy is delivered in the conversation bundle.
