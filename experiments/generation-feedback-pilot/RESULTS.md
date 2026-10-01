# Generation-feedback pilot v0.1: completed, with a measurement bottleneck

**Twelve actual model generations completed. No improvement in feasible proposals was observed. The intended constraint-specific feedback comparison was not reached.**

Plan/source commit: `30ed301628bdfbbba4a4e3046b6f9931709115df`.
[Public run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36330674416) · [Full job log](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36330674416/job/108651861049) · [Recorded response excerpt](OBSERVED.json).

The plan was committed before the draft PR started inference. Execution was on standard GitHub-hosted Ubuntu 24.04, not Youngseok's PC. No paid model API, model training, private conversation, external action, or operational-memory change was involved. The public standard runner completed normally. Its green check means the run completed, not that the model solved the task.

## Observed, not simulated

Model: **Qwen/Qwen2.5-0.5B-Instruct**, revision `7ae557604adf67be50417f59c2c2f167def9a775`, CPU float32, greedy decoding, two threads. Python 3.12.14, torch 2.10.0+cpu, Transformers 4.57.1. All twelve responses ended at 29 generated tokens, below the 96-token cap. Responses span 27 September 2026 15:45:37–15:46:10 UTC (28 September in Korea).

| Stage | Returned the declared JSON grammar | Feasible constructions |
|---|---:|---:|
| Initial proposal | 0 / 4 | 0 / 4 |
| Neutral reconsideration | 0 / 4 | 0 / 4 |
| Checker-feedback branch | 0 / 4 | 0 / 4 |

All responses were wrapped in a Markdown JSON fence despite the requested bare JSON grammar. Ten returned the array `[0, 1, 2, 3, 4, 5]`; two, G3 initial and neutral, returned `[0, 3, 1, 4, 2, 5]`. G3's checker-feedback branch changed its proposal to the former array. The permitted channel values were only 0, 1, and 2.

The primary parser was not changed. A separately labeled post-hoc inspection confirms that even ignoring the Markdown wrapper would not make these candidates feasible: every response contains out-of-range channel values. This is not merely a cosmetic formatting failure being counted against an otherwise correct construction.

## Why this does not answer the intended feedback question

The predeclared checker sent only `{"format_valid":false}` whenever the initial response failed grammar. Consequently **none of the four feedback branches received the specific conflicting-pair feedback** that would exercise the intended proposal/counterexample mechanism. This is an important limitation of this instrument on this small baseline, not proof that specific feedback cannot help.

A candidate changed in one branch without becoming feasible. That observable change is neither evidence of general creativity nor something to erase because it did not solve the task. Original proposals, later proposals, and their separate validation states remain visible. We have not measured or named an internal thought process.

## Software and evidence checks

Ten evaluator tests passed both before publication in the ChatGPT working container and before inference in the hosted runner. One test exhausts all 2,916 candidate assignments across the four graphs against a separately written partition-based oracle. The graphs have 66, 12, 42 and 24 feasible constructions respectively; the target was not a unique memorized answer. Four graphs share one grammar, not four independent task families.

`OBSERVED.json` transcribes selected fields from the connector-fetched job log, including every raw response string and timestamps. It is explicitly not a byte-for-byte download of the full log. Complete transmitted messages, rendered prompts, token IDs, generation configuration and model-file digests remain in the linked job log, subject to GitHub's retention. `recompute.py` independently re-applies the frozen task evaluator to this excerpt and rejects incomplete/duplicate inventories. Its post-hoc wrapper inspection cannot alter primary scores. This is an analyst readback, not an independent external model replication.

All twelve planned cells were retained. No repeated run, semantic retry, prompt repair, replacement model, or cherry-picked subset was used to obtain a positive result. Source and plan hashes were checked by the runner before generation. The prototype remains on its research branch; the existing profile and earlier experiments are unchanged.

## Next design decision, not a second experiment

Before another model run, split the feedback into distinct observations: outer serialization, candidate extraction, allowed-value domain, and pairwise constraints. Do not let one outer-format failure erase every other useful observation about the proposal. Keep the original strict outcome alongside these diagnostics rather than retroactively fixing answers. Reassess baseline suitability and freeze any changed prompts or parser rules as a new exploratory version.

This development run does not test the claim that hallucination is a basic unit of thought, the user's full account of local intelligence, or any AGI criterion. It studies a small construction task and exposed an output/feedback bottleneck. Generate-evaluate-refine methods predate this work; see the primary references in [the frozen plan](PLAN.md).

## 한국어

실제 소형 모델을 네 과제에서 처음 제안, 단순 재검토, 검사 피드백 뒤 재제안으로 나누어 총 12회 실행했다. 실행 자체는 끝났지만, 조건을 만족하는 제안은 이번에 나오지 않았다. 과제는 채널 0·1·2만 허용했는데 모델은 3·4·5도 넣었고, 요청하지 않은 코드 블록도 붙였다.

중요한 점은 검사기가 첫 형식 단계에서 멈춰 모든 피드백을 `format_valid=false`로만 돌려줬다는 것이다. 따라서 구체적인 반례가 제안을 발전시키는지를 충분히 시험하지 못했다. 이 결과를 ‘생성은 쓸모없다’ 또는 ‘환각은 오류일 뿐이다’라는 결론으로 사용하지 않는다. 원래 후보와 바뀐 후보는 모두 남기고, 다음 시험에서 관찰과 판정을 더 세밀하게 분리할 근거로 삼는다.

검사 성공 표시와 모델 성공을 구별한다. 사용자 컴퓨터·개인 기억·유료 API는 사용하지 않았다. 모델 가중치도 바꾸지 않았다.

Experimental framing, implementation, execution and analysis by Zero, with Youngseok Oh's project direction. Qwen and the cited researchers retain credit for their model and prior methods.
