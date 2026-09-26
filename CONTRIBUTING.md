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

Read [REPLICATION.md](REPLICATION.md) first, then use the repository's **Replication report** issue form so missing runs, failures, and exclusions are not lost.

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

### Public replies and complete-payload review

These requirements also apply when this project's contributors post to another project's issue or PR. That project's contribution policy and the account owner's authorization still apply.

**Review the complete outgoing payload, not just the body supplied to a mail tool.** Do not use a notification-email reply fallback when that tool may automatically append an uninspectable quote chain, signatures, headers or personalized notification links. Prepare a clean body and wait for a usable authorized direct-comment route instead. A 403 is a permission blocker, not a reason to repeatedly retry or change identities. An already authorized same-account alternative must still respect the destination's rules.

Before publication, inspect the body and run the small read-only [public-comment preflight](tools/public-comment-preflight/preflight.py):

```sh
python tools/public-comment-preflight/preflight.py --self-test
python tools/public-comment-preflight/preflight.py --body /path/to/reviewed_comment.md
```

The preflight flags known notification links and reply addresses, some credential-bearing URLs and token/header patterns, and recognizable email quotes. It reports rule names, not the matching values. Exit 1 requires review; exit 2 means the check could not complete. Exit 0 means **only that the listed patterns were absent**: it is not authorization to send or a guarantee that all private information was detected. It does not inspect a mail tool's later additions, intercept connector calls, automatically clean a posted comment or revoke an exposed value.

Use canonical public issue, commit and file URLs in public evidence. Never copy personalized notification links, token-bearing reply recipients or a raw mailbox transcript into a public report. Keep any failure receipt free of those values too.

After a write, read the destination again and verify the account, target, evidence links and complete posted text. A successful send response is not sufficient. After an ambiguous timeout, reconcile the existing destination before another write. If removal cannot be completed, record it as pending and explain the specific access or owner action needed rather than calling it resolved.

Local check record, 26 September 2026: the preflight accepted three synthetic clean examples and flagged fourteen synthetic examples, rejected oversized input, and returned the expected CLI outcomes for a flagged body and invalid UTF-8. A prepared replacement body was checked without sending it. This tests the local detector only; it is not validation of Gmail's quote handling or evidence that an existing public comment was repaired. No live email was sent to test this rule.

## Evidence labels

Keep these states distinct:

- **Original:** direct source material with clear authorship.
- **Translation:** a rendering into another language.
- **Hypothesis:** a claim that can be wrong.
- **Design:** a proposed procedure, not a result.
- **Observed:** directly read from the relevant run or destination.
- **Unverified:** not run or not independently confirmed.

The maintainers may decline a contribution that cannot preserve these boundaries, even when its underlying idea is interesting.
