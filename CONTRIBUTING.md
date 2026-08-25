# Contributing

This repository welcomes contributions that make an evaluation easier to falsify, reproduce, or interpret. It is not a general archive for conversations or model-generated reflections.

## Useful contributions

### Test cases

Propose a case against a specific note or evaluation track. Include:

1. the note or claim being tested,
2. the exact public-safe input and setup,
3. the behavior you expect and why,
4. a clear pass/fail or graded scoring rule,
5. at least one confound or alternative explanation,
6. whether the case is original, adapted, or replicated from prior work.

Cases are especially useful when they distinguish a real capability from prompt imitation, evaluator leakage, memorization, or a socially smooth answer.

### Critiques

Point to the exact sentence, hypothesis, control, or scoring rule at issue. State whether the problem is logical, empirical, terminological, privacy-related, or a conflict with prior work. Strong critiques include a counterexample or a cheaper test that could settle the disagreement.

### Replications

Report enough detail for another person to rerun the work:

- model and dated version or endpoint,
- system and user prompts that may affect the outcome,
- sampling and tool settings,
- case set and scorer version,
- raw outputs or a stable public location for them,
- all runs, including failures and exclusions,
- any manual judgments and who made them.

Do not describe a single successful example as a replicated result.

## How to propose a change

Open a GitHub issue for a critique, case proposal, or replication report. Use a pull request when the contribution is already expressed as a focused edit or a self-contained public-safe artifact. Keep unrelated changes separate.

## Authorship and source boundaries

- Attribute direct quotations to their actual author and link a public source when one exists.
- Mark translations as translations, AI-assisted text as AI-assisted, and editorial interpretations as interpretations.
- Do not attribute model-generated language, praise, or self-description to Youngseok Oh.
- Do not imply endorsement by OpenAI or any cited researcher or institution.
- Submit only material you created or have the right to share. Do not add a license or reuse permission on behalf of another author.

Contributor names and roles should remain attached to accepted cases, critiques, and replications. Editorial changes may improve clarity, but they must not silently change a contributor's claim or evidence status.

## Privacy and safety

Do not submit credentials, account data, private filenames, medical information, exact private locations, private messages, non-public session logs, or identifying information about third parties. Redact before opening an issue or pull request; deleting a secret after publication may not remove it from Git history or mirrors.

Use synthetic or consented data whenever possible. If a test requires sensitive or non-public source material, describe the evaluation structure without uploading that material and ask the maintainer before proceeding.

## Evidence labels

Keep these states distinct:

- **Original:** direct source material with clear authorship.
- **Translation:** a rendering into another language.
- **Hypothesis:** a claim that can be wrong.
- **Design:** a proposed procedure, not a result.
- **Observed:** directly read from the relevant run or destination.
- **Unverified:** not run or not independently confirmed.

The maintainers may decline a contribution that cannot preserve these boundaries, even when its underlying idea is interesting.
