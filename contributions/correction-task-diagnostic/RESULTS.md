# Copying worked; none of the ten planning diagnostics matched

Youngseok Oh with Zero (ChatGPT), 2026-09-14.

[Run 34832711493](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34832711493)
completed on the first hosted attempt at
`3cbbbe285bd273a3ac3da4f8d0564fa44f4fb071`. The unchanged PR50 model runner,
model weights, runtime binary and generation settings were used. Twelve fresh
server processes returned twelve complete, untruncated JSON objects. Ten requests
were planning probes derived from two opposite cancellations; two were literal
copy controls. They are not twelve independent user cases.

## Predetermined descriptive outcomes

| Condition | Task-ID set agreement | Structurally valid output | Returned task arrays, in pair order |
| --- | ---: | ---: | --- |
| Korean, original full contract, labeled events | 0/2 | 1/2 | [], [E1,E2] |
| Korean, next_tasks only, labeled events | 0/2 | 2/2 | [], [] |
| Korean, next_tasks only, no event prefixes | 0/2 | 2/2 | [], [] |
| English, next_tasks only, labeled events | 0/2 | 2/2 | [A,B], [A,B] |
| English, next_tasks only, no event prefixes | 0/2 | 2/2 | [], [] |
| Korean / English literal copy controls | 2/2 | 2/2 | [B], [A] |

For every planning pair the correct task arrays were [B] then [A]. None of the
five planning pairs had both answers correct. The two full-contract anchors also
failed the original joint task/clarification-boolean criterion. The other groups
request no clarification field, so their new task-only score is not the old
PR50 joint metric. All twelve were syntactically valid JSON, and eleven respected
the requested structural contract. Structural validity was not task correctness.
The copy outputs matched the supplied JSON content exactly, not merely its parse.

The two anchor request objects were identical to the original PR50 requests,
and their response choices/content/termination were identical to PR50 as well.
Metadata such as response IDs and timestamps were not expected to be identical.
The old 0/8 scores in both memory formats remain unchanged; these are separately
recorded follow-up diagnostics, including two explicit anchor repetitions.

## What this rules out, narrowly

An absolute inability to emit the requested one-field JSON is not a sufficient
explanation: both copy controls succeeded. Asking for only next_tasks removed
extra output fields but did not recover a correct plan in these examples.
Removing event prefixes removed that source of event-ID competition, but did not
recover the remaining task either. English translation was not a sufficient fix:
labeled English retained both tasks, while unlabeled English retained neither.

These findings do not identify a unique internal cause. Language, detailed task
wording, output demands, the rules about fictional records/no actual execution,
small-model ability, quantization, chat template and numerical runtime behavior
remain possible contributors. The English translation was authored here, not
independently checked. Shorter contracts and removed labels also change input
length. Two histories cannot establish a population effect or a universal failure.
Copy success does not certify model/runtime equivalence or general competence.

## Decision applied

The current model/setup has not passed this study's basic planning entry check.
Do not enlarge the memory-format benchmark, add more wrappers, or tune toward
favorable scores as the default next step. Preserve these outputs and pause this
measurement branch. A future capability baseline or implementation check must be
explicitly separate and meet a real study need before resuming the larger question.
No further model run was started in response to these results. This neither
confirms nor disproves the value of preserving a user's corrections or history.

## Evidence read back

Artifact `10342638735`: 80,834 bytes, 63 members, 232,562 expanded bytes,
SHA-256 `e583d25fc0dd42484036352c4cb92c386ab640457f2ebb30c8bcb45732005df3`.
The original ZIP was downloaded and opened. CRC/path/member checks passed, and
the frozen local scorer checked each request/response/record against run.json,
the exact prepared inputs, settings and author key. All server return codes were
zero, every finish reason was stop, every cached-prompt token count was zero,
and all twelve PIDs were distinct and ordered without overlapping lifetimes.

New source SHA-256:
`333d4bacbf4d704e8656470139ecd802a4755bd89c77240e0defe11ea1785f13`.
Input SHA-256:
`c63a3a6c888c12cef617242d4c8a322e73c7a89d146c5b387612095b62d8c562`.
The prior runner, downloaded runtime archive, weight file and executing binary
matched PR50's recorded identities. The binary SHA-256 remained
`07723ae07835bdf11cf0d00d68eb4df8308df0603f689c64c9f841a626cad01d`.
The same runtime deprecation/unused-tensor warnings remain in the original logs;
no independent numerical-equivalence check was performed.

Actual input/output tokens by group were 952/88, 756/22, 720/22, 634/32, 602/22,
and 72/14 respectively: 3,736 input and 200 output tokens total. Generation spans
about 55.55 seconds excluding setup/downloads, not an end-to-end speed benchmark.
The different token counts are reported, not called matched budgets.

The scorer/key hashes match the pre-output protocol. Seven local scorer-edge
checks were preparation only, not seven extra model tests. No output repair,
retry, model swap or label change occurred after viewing responses. Scoring is
an author analysis rather than independent adjudication. The conversation bundle
retains the original ZIP, all raw responses, source, key, frozen scorer and the
prior original archive needed to check the anchor comparison. The hosted artifact
expires after one day; repository ownership and archival availability still apply.

No paid inference API, private user record, user-PC/profile installation, previous
source modification or recurring automation was involved. Only this results note
was added after the executed source commit. The workflow's success means the
experiment executed; it is not a pass on planning competence.
