# Observed development result: inference ran; task agreement was zero

Youngseok Oh with Zero (ChatGPT), 2026-09-14.

[Run 34825090312](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34825090312)
completed on its first hosted attempt at source
`70907908fe1d84efe837ee81b3524996addfc074`. This is the first separate-model
execution of these development inputs, not a rerun of earlier MCP/skill checks.

## Results under the pre-output protocol

The model was the pinned Qwen3.5-0.8B Q8_0 GGUF, executed on four CPU threads
with nonthinking template settings, greedy decoding and a 256-token output cap.
All 16 fresh server processes returned a response. All responses ended with
`finish_reason=stop`, all reported zero cached prompt tokens, and all parsed as
JSON objects without repair. The generation sequence took about 116.94 seconds;
this excludes workflow setup and weight downloads and is not a speed benchmark.

| Descriptive result | Prose (8) | Structured JSON history (8) |
| --- | ---: | ---: |
| Parseable complete JSON objects | 8 | 8 |
| Full structural output contract valid | 2 | 5 |
| Exact task set and clarification boolean correct | **0** | **0** |
| Counterfactual pairs with both items correct (out of 4) | **0** | **0** |
| Truncated outputs | 0 | 0 |
| Total input tokens | 3,872 | 4,210 |
| Total output tokens | 396 | 341 |

The input formats have different token lengths. No statistical superiority,
long-term-memory capability, independent label validation or population estimate
follows from these eight author-created development cases.

## What the raw outputs show

Nine of the 16 responses placed event IDs such as `E1`/`E2`, or event-order
numbers such as `1`/`2`, in `next_tasks`, which required task IDs such as A/B/C.
The other seven returned an empty task array. All 16 returned
`clarification_required=false`. Thus even looking only at task-set/boolean values,
without scoring the other output fields, yields zero agreement. This is not zero
merely because of Markdown fences, a terse evidence citation, or output truncation.

| Author development case | Prose next_tasks | JSON-history next_tasks | Expected task set / clarification |
| --- | --- | --- | --- |
| D01: cancel A only | [] | [] | B / false |
| D02: cancel B only | E1,E2 | 1,2 | A / false |
| D03: user explicitly reassigns A | E1,E2,E3 | 1,2,3 | A,B / false |
| D04: same text from assistant | E1,E2,E3 | E1,E2 | B / false |
| D05: actual A cancellation | [] | [] | B / false |
| D06: quoted cancellation example | E1,E2 | [] | A,B / false |
| D07: A/B target unknown, C definite | E1,E2 | [] | C / true |
| D08: A cancelled, B/C definite | E1,E2 | [] | B,C / false |

The author key was retained separately and was not in the model requests. This
interpretation of the outputs is an author analysis, not a blinded human review.
It identifies observable task/event-ID confusion and empty plans. It does not
uniquely establish whether language competence, model scale, prompt design,
output-contract wording or inference implementation caused the failures.

The model/runtime produced normal responses and no context truncation. Server
logs also retain warnings about deprecated enable_thinking CLI spelling, CORS
without a key on the loopback-only server, and unused blk.24 tensors. These were
not suppressed. An independent equivalence check against the original inference
implementation was not performed; do not infer it from checksum correspondence.
Server /props records show defaults, not the full effective per-request sampler
state. The exact overriding requests and raw responses are preserved.

## Original evidence inspected

Original artifact `10339577023`: 117,007 bytes, 83 JSON/JSONL/log members,
SHA-256 `1cdcfeb098afeb135722383ad0089185f9eac429e6711b998603befa8de002f7`.
The downloaded ZIP passed CRC. Offline readback compared the 16 separate requests,
responses and process records with run.json and the exact prior input file;
checked source/weight/runtime pins, fresh ordered PIDs, build fingerprints,
cache/truncation values and actual token counts; then scored without output repair.

The executing runner matched the prepared 9,295-byte source, SHA-256
`71ea1dbaacf566e180452b304f33cecf2a1f98e72e143cf0db58f54bd19d1aa4`.
The downloaded model was 833,592,096 bytes with the pre-recorded weight digest.
The loaded runtime's build fingerprint was `b10809-5266f24da` and its executable
SHA-256 was `07723ae07835bdf11cf0d00d68eb4df8308df0603f689c64c9f841a626cad01d`.
Runtime/model digests are recorded and checked by the runner; binaries themselves
are not in the output archive.

The scoring policy was committed before inference. The separate local scorer
was fixed before reading returned model outputs, SHA-256
`49249f4c5e04be5401cf2c110e2c849db76bcdf0ba15854b877db3b1c1ad262f`.
This is not an independent preregistration or external adjudication. The delivered
conversation bundle includes the original artifact, scorer, unchanged author key,
input map and detailed per-item scores for repeatable offline readback. Actions
retention is only one day; the bundle is the additional original-byte copy.

## Decision, not a favorable retest

Do not choose structured history on the basis of 5 versus 2 structurally valid
outputs: both formats failed all task-state checks. Do not expand the benchmark,
fine-tune this model, or repeat the prompts until scores improve as the default
next action. Before a meaningful memory-format study, separately test whether a
candidate understands the task-ID/event-ID distinction and can follow a simpler
output contract. An English or task-label control would be a new explicitly
labeled diagnostic, not a repaired version of this zero-score run. No such control
or new model execution has yet been performed here.

The achieved step is a real, inspectable model execution path and a negative
measurement that changes what should be tested next, not evidence that the desired
memory effect exists. No paid model API, private user data, user-PC installation,
new recurring task or previous-source edit was involved.
