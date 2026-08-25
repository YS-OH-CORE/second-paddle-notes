# Replication Guide

This repository has **zero independently submitted or verified external replications** as of 2026-08-25. The committed outputs in `experiments/rule-use-eval/results/` come from deterministic program fixtures; they are not language-model results and do not count as external replication.

This guide defines the minimum evidence needed for a replication report to become inspectable. It does not guarantee acceptance or verification.

## What counts

A useful replication reruns a named note or executable artifact under a documented protocol and reports every planned run. A conceptual agreement, a model self-report, a screenshot without raw output, or one selected success is not a replication.

Use the [**Replication report** GitHub issue form](https://github.com/YS-OH-CORE/second-paddle-notes/issues/new?template=replication.yml). Identify whether the run was:

- **Independent:** no author or maintainer helped choose prompts, settings, exclusions, or interpretations after the protocol was fixed.
- **Partially independent:** some author or maintainer assistance occurred; describe it.
- **Author-assisted:** the run was conducted or materially guided by an author or maintainer.

All three may be informative, but they are not interchangeable.

## Minimum evidence package

Provide enough information for another person to reconstruct the run:

1. repository commit SHA or release tag, note or experiment path, case-set version, and scorer version;
2. model provider, exact model or endpoint identifier, dated model version when available, and access method;
3. run date, time zone, runner identity or role, and execution environment;
4. complete system, developer, user, and tool prompts that could affect the output, or stable public files plus hashes;
5. inference and tool settings, including temperature, `top_p`, token limits, reasoning setting if exposed, tool availability, response format, timeout, retry policy, and concurrency;
6. seed for every run, or an explicit statement that the provider offered no controllable seed or did not guarantee determinism;
7. number of planned and completed runs, ordering or randomization method, and any preregistered stopping rule;
8. raw, unedited outputs for **all** runs, including errors, refusals, timeouts, and other failures;
9. exclusions and manual judgments, with the rule, reason, decision maker, and timing of each decision;
10. commands or code used to run and score the evaluation, computed metrics, and checksums for the submitted files.

If a provider silently updates a model behind a stable alias, report the alias and the most precise dated identifier or response metadata available. Do not infer an unobserved version.

## Suggested public artifact layout

```text
replication/
  README.md
  environment.txt
  protocol.md
  prompts/
  settings.json
  raw_outputs.jsonl
  exclusions.jsonl
  metrics.json
  manifest.sha256
```

Raw outputs should preserve ordering and provider metadata while removing secrets and prohibited personal data. Keep an untouched private original only if lawful and necessary; publish a documented redaction map rather than silently rewriting outputs.

## Reporting results honestly

- Separate the preregistered primary metric from exploratory observations.
- Report denominators, uncertainty, failures, exclusions, and all repeated runs.
- Distinguish a software reproduction from a claim-bearing model evaluation.
- Do not generalize from one model, one date, one prompt, or one successful example.
- Do not call a report “verified” until another person has checked the files, commands, and claimed result. Repository maintainers will record verification explicitly if it occurs.
- A failed or null replication is welcome when it meets the same evidence standard.

## Privacy, security, and rights

Never publish API keys, credentials, private account data, non-public conversations, private filenames, medical information, exact private locations, or identifying information about third parties. Provider request IDs and logs can also contain account metadata; inspect them before publication.

Submit only prompts, datasets, outputs, and code that you created or have permission to share. Link to restricted or copyrighted source material instead of copying it when redistribution is not allowed. Quote only the minimum needed for critique, preserve attribution, and label translations and AI-assisted text accurately.

Redaction must not change the evaluated meaning. State exactly what was removed and why. If safe public evidence cannot support the claim, report the limitation instead of uploading sensitive material.

## Maintainer review

A report can be listed as **submitted**, **runnable**, **reproduced**, or **not reproduced**. These labels describe evidence state, not contributor quality. Review may check artifact hashes, commands, raw-output completeness, scoring, exclusions, and whether the stated independence level matches the record.

Until such a review is publicly recorded, the external-replication count remains unchanged.
