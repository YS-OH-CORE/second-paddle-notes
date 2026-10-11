# v0.2 completed: richer feedback arrived, but the small baseline did not repair its proposal

**Observation coverage improved; model construction success did not.** Stop this small-baseline pass rather than increase repetitions or silently swap models.

[Pre-response source and plan](https://github.com/YS-OH-CORE/second-paddle-notes/tree/b6a0889164ec62bd5b1ff2d4b5c9f01aca026fce/experiments/generation-feedback-pilot/v02) · [Hosted run 36332320437](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36332320437) · [Full log](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36332320437/job/108656504713) · [Complete machine record, gzip JSON](RESULT.json.gz)

## What changed, and what did not

v0.1's strict evaluator, task prompts, system message and saved initial responses remain byte-identical. v0.2 uses those four public initial responses as fixed seeds in twelve **new continuation** calls. The same pinned Qwen2.5-0.5B-Instruct weights, CPU float32, greedy decoding, 96-new-token budget and library versions are used. The public hosted job ran once; no user's PC, private memory, paid model API, finetuning, or tool action was involved.

Three predeclared cues follow each seed: the original coarse format-invalid notice, an explicit fence-only notice, and a layered notice that also lists the actually invalid values and explains the distinction between station positions and channel values. No correct construction is supplied. Actual transmitted messages are retained in the machine record.

## All planned responses

| Cue | New calls | Readable six-integer proposals | Domain-valid proposals | Feasible proposals | Original strict successes |
|---|---:|---:|---:|---:|---:|
| Coarse format-invalid notice | 4 | 4 | 0 | 0 | 0 |
| Explicit formatting notice | 4 | 4 | 0 | 0 | 0 |
| Format plus candidate diagnostics | 4 | 4 | 0 | 0 | 0 |

Every new raw response was the same fenced JSON object containing `[0, 1, 2, 3, 4, 5]`. Only 0, 1, 2 were allowed channels. All responses ended at 29 output tokens, not the 96-token cap. Inputs were 228–337 tokens. Total measured generation time was 51.1843 seconds; the complete hosted job including setup took about 109 seconds.

For G3, all three continuations changed the prior seed `[0, 3, 1, 4, 2, 5]` into `[0, 1, 2, 3, 4, 5]`, without making it feasible. That change was not specific to the layered cue. The other three cases retained their seed's raw response. No response or cell was dropped.

Unlike v0.1, the layered condition **did transmit specific candidate information**: three out-of-domain station/value entries, the allowed domain, and an empty equal-value-pair list with a warning that this alone does not establish feasibility. Inspection of the actual inputs confirms delivery. No feasible improvement was observed in this run. This distinguishes a repaired feedback-observability bottleneck from an observed improvement in model responses; it does not reveal whether a latent internal representation changed.

## Acceptance remains separate from observation

The observer can read a candidate from one whole JSON fence while preserving the old strict rejection. It does not rewrite a value, choose among multiple proposed answers, or count unknown information as success. Here all twelve readable candidates still violate the value domain, so even the diagnostic feasibility count is zero. These are not correct solutions penalized only for formatting.

All values in `[0,1,2,3,4,5]` are distinct, so equal-value-pair counts are zero. That narrow property is retained but cannot compensate for illegal channel values. Unknown candidates produce null diagnostics, rather than an invented empty set of conflicts.

## Verification and provenance

Ten observer tests passed before inference, including 32,768 exhaustive bare/fenced representation checks. These are software checks, not model generations. The frozen source hashes were verified at job start, and the model safetensors hash matched v0.1.

`audit_result.py` checks all twelve expected cells, reconstructs each exact cue and seed from frozen source, recomputes every observation and summary, and verifies the result bytes against the length and SHA-256 emitted by the inference job. This is an analyst audit, not independent model replication.

Uncompressed record: **27,687 bytes**, SHA-256 **`ad7051056bac34d164228b04e6e8ee60d23cd9d271fab5b41466469b77c21bc1`**. `RESULT.json.gz` contains that exact JSON, including every actual message, response, token sequence, model-file hash and diagnostic. The gzip envelope was re-created locally.

An initial manual copy of the compressed log string failed validation and was not accepted as evidence. The record was then reconstituted from the returned log fields and frozen source; its complete JSON bytes matched the runner's independently emitted length and digest exactly. No model response was regenerated. This transfer history is recorded rather than describing the reconstructed file as a direct byte download of the full Actions log.

From this directory, Python standard library only:

```sh
python -B -m unittest -v test_observe
python -B audit_result.py
```

The existing draft PR57 carries this follow-up; `main`, the profile, and prior experiment results are unchanged. The inference workflow only allows the transition from the v0.1 result head and attempt 1, so later result edits cannot silently rerun it.

## What this supports

The new observation route exposes information that the previous all-or-nothing gate omitted. With this specific small model, four previously failed seeds and these cues, extra diagnostic feedback did not yield a feasible repair. We now have a complete documented floor result, not a positive performance result.

These reused public graphs share one grammar; conditions have unequal input lengths; single greedy trials do not estimate variability. The result does not show that detailed feedback never helps, that the model cannot solve any alternative phrasing, or that generative thought is invalid. This is not an AGI test, an internal-mechanism finding, or a novel general refinement algorithm. Generate-and-refine approaches predate this study, including [Self-Refine](https://arxiv.org/abs/2303.17651).

Before spending another run, test task/model adequacy and distinguish following a supplied prior answer from independently constructing a new one. That is a next design question, not an additional result. No further model runs or public researcher outreach were initiated for this report.

## 한국어

지난 검사기는 겉형식에서 멈췄다. 이번에는 원래 점수는 유지하면서 실제 제안의 값과 관계를 읽고, 그 관측을 모델에게 전달했다. 같은 첫 제안에서 피드백 세 종류로 총 12번 새 답변을 만들었지만 모두 같은 배열이 나왔고, 조건을 만족하는 제안은 여전히 없었다.

관찰기를 고친 것과 모델 답변이 나아진 것은 별개다. 구체적 정보를 전달한 경로까지는 확인했지만, 이 모델과 입력 조건에서는 그 정보가 유효한 수정으로 이어지지 않았다. 동일한 소형 모델을 더 반복하며 결과를 찾지 않고 이 시험은 여기서 마감한다. 처음 후보, 새 후보, 기존 점수와 새 관측은 모두 보존한다.

Conceptual direction: Youngseok Oh. Design, execution, code and analysis: Zero, his AI collaboration partner. No claim of independent review, external adoption, institutional endorsement or a general model-quality judgment.
