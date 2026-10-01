# Adequacy diagnostic: simple controls work; prior use differs by task

**Eight new responses completed. The copy and channel-domain controls produced valid candidate content. Neither graph was solved in the fresh context. A supplied valid prior was retained on G2, but not on G1.** This diagnostic narrows the earlier floor result; it does not turn the old experiments into successes.

[Pre-response plan](PLAN.md) · [Run 36355838214](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36355838214) · [Original job log](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36355838214/job/108723264335) · [Exact result record](RESULT.json.gz)

## Actual outputs, all cells

| Cell | Candidate list | Candidate satisfies its task | Original strict grammar and constraints |
|---|---|---|---|
| Exact-copy control | [2,0,1,2,0,1] | Yes, exact requested content | Pass |
| Channel-domain-only control | [0,0,1,1,0,2] | Yes | Fail: fenced output |
| G1, fresh | [0,1,2,3,4,5] | No | Fail |
| G1, invalid prior | [0,1,2,3,4,5] | No | Fail |
| G1, valid prior [0,1,0,1,0,1] | [0,1,2,3,4,5] | No | Fail |
| G2, valid prior [0,1,2,1,2,0] | [0,1,2,1,2,0] | Yes, retained supplied construction | Fail: fenced output |
| G2, invalid prior | [0,1,2,3,4,5] | No | Fail |
| G2, fresh | [0,1,2,3,4,5] | No | Fail |

All three graph conditions have denominator two: fresh 0/2 feasible candidates, invalid prior 0/2, valid prior 1/2. The sole strict pass was the copy control. Do not combine these unlike tasks into an overall ability score.

The bad/valid prior comparisons differed only in the six supplied values. Both used the same Markdown wrapper, task and final question. Their input token counts were equal: 204/204 on G1, 216/216 on G2. Fresh contexts had fewer turns and tokens and are a different contrast. All eight responses completed below the output cap (22 tokens for copying, 29 for all others). Measured generation time totaled 24.8596 seconds; the hosted job including setup took about 65 seconds.

## What this resolves, and what it does not

The output path was not universally stuck on one byte string: the exact-copy and domain-only requests yielded different compliant candidate content. The latter still missed bare-JSON serialization, which remains a separate failure.

A wrong prior answer was not necessary for the identity-array failure in these graph prompts: the same invalid array appeared in both fresh contexts. Conversely, prior content was not always irrelevant: changing only the supplied values changed G2's output. G1 returned the invalid array even after a valid prior was provided. A blanket explanation that the model merely copies whatever prior it is given does not describe all these observations.

G2's valid construction was supplied by Zero before the model call. Retaining it is not independent graph solving, a discovery, a learned new algorithm, or evidence that a private mental state 'knew' the solution. All three graph conditions still failed the original strict grammar because they used fences.

This is a small diagnostic: two related graphs, one grammar, fixed order and greedy calls, with development selection after earlier failures. It does not estimate population accuracy, establish an internal anchoring mechanism, refute the usefulness of feedback, or assess generative thought or AGI. The fresh and seeded contexts differ in length and structure. No p-value, novelty claim or external endorsement is offered.

## Decision

Retire this model/task configuration as the main test of feedback-mediated idea development. Its elementary controls and graph performance are too uneven to treat failure as evidence about a broader memory or thought mechanism. Preserve this diagnostic and the earlier floor results, rather than escalating repetitions or switching models inside the same claimed result.

Before selecting a replacement experiment, make basic instruction, task competence, meaningful negative cases, and prior-content sensitivity separate readiness checks. The copy/domain checks should have preceded the earlier interpretation: this is a correction to our experimental method, not a claimed improvement to the model.

## Execution and record integrity

Frozen source: `e19c1c03cf3190bc229f202ab6f787a5020a7891`. The three published source blobs matched the locally checked files before execution. Same Qwen/Qwen2.5-0.5B-Instruct revision `7ae557604adf67be50417f59c2c2f167def9a775` and weight digest as v0.2; CPU float32, two threads, greedy, 96-token output cap. No new initial responses were substituted for the predefined priors. No semantic retries or second run were used.

The result's compressed string was copied from the returned job log, decoded once, and verified against the job-emitted SHA-256 and JSON byte count. The JSON is **15,621 bytes**, SHA-256 **`0b9909286e0a96805768eb0c6eb6b87d02011f1e3fbf0b93beef9f5f592d1c59`**. `RESULT.json.gz` preserves that exact machine record, not a manual paraphrase of the answers. The whole Actions log was not downloaded byte-for-byte. `audit.py` validates inventory, actual messages, stimuli, observations, summary, source digests and matched token lengths without another model call. This is an analyst audit, not independent model replication.

Run from this directory, Python stdlib only:

```sh
python -B probe.py --check
python -B audit.py RESULT.json.gz --sha256 0b9909286e0a96805768eb0c6eb6b87d02011f1e3fbf0b93beef9f5f592d1c59
```

The standard public GitHub-hosted runner was used, not Youngseok's PC. No paid model API, private memory, model finetuning, cache/artifact upload, remote model code or executable output was used. The inference job ran once; the prior v0.2 workflow was skipped by its gate. Existing results, original task/observer and main/profile remain unchanged. No further inference or outreach was initiated.

## 한국어

복사하기는 정확히 수행했고, 0·1·2만 골라 여섯 값을 만드는 것도 내용상 가능했다. 그러나 원래의 두 배정 과제는 이전 답을 안 줘도 실패했다. 올바른 이전 답을 넣었을 때는 둘 중 하나만 그 답을 유지했고, 다른 하나는 다시 허용범위를 벗어난 배열을 출력했다.

따라서 앞선 실패를 모두 ‘잘못된 이전 답을 베꼈다’ 또는 ‘어떤 간단한 지시도 못 따른다’로 설명하지 않는다. 한 과제에서의 올바른 답은 우리가 미리 제공한 구성이지 모델이 독립적으로 발견한 성과가 아니다. 코드 블록 때문에 원래의 엄격한 통과 판정은 그대로 실패이며, 내용만 읽는 관찰을 별도로 표시한다.

이 소형 모델과 과제 조합은 큰 연구 질문의 주력 시험으로 계속 사용하지 않기로 했다. 기초 대조를 먼저 했어야 했다는 실험 설계의 교훈과 모든 실제 출력을 남긴다. 영석 PC·개인 기억·유료 API·모델 가중치는 건드리지 않았다.

Direction: Youngseok Oh. Design, implementation, execution and analysis: Zero, his AI collaboration partner. This is a bounded public development record, not a general model-performance claim.
