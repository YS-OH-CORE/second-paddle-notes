# Same score, different decisions

**Youngseok Oh (오영석) × Zero (ChatGPT) | 24 September 2026 KST**

**Observed:** all three memory views scored **31/48** across all six answer orders, but some individual decisions changed with option order. Correct and deliberately reversed relationship annotations yielded the same choices in every matched cell. This does not establish an advantage from the added relations.

This is a diagnostic follow-up to the [first CPU memory pilot](README.md), related to [Note 14](../../notes/14-interaction-is-the-event.md). It is not the full held-out study or an independent replication.

## What was frozen and executed

The first pilot yielded 5/8 under each view with a fixed answer arrangement. The [diagnostic protocol and code](https://github.com/YS-OH-CORE/second-paddle-notes/blob/6d8ae732bc53da3874a2fc10c66582fb5c1de8f6/experiments/memory-cpu-pilot/option_order.py) were committed before the new inference. The diagnostic exhausts every option order rather than selecting one that scores well.

- Same model and weights: `Qwen/Qwen2.5-0.5B-Instruct` at `7ae557604adf67be50417f59c2c2f167def9a775`.
- Same eight fictional English cases, questions, system instruction and three memory views.
- **8 cases × 3 views × 6 permutations = 144 forward passes.** One per cell; no sampling, answer-dependent retries, exclusions or prompt revisions. Only answer contents move among A/B/C. Each semantic answer occupies each position twice.
- Score the largest A/B/C next-token logit, then map the selected letter back to the original semantic answer. No free-form response or real-world action was evaluated.
- [Completed run 35894984091](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35894984091), job `107296558500`, [workflow ada4fd8b](https://github.com/YS-OH-CORE/second-paddle-notes/blob/ada4fd8b080e07968fb424769a4b3375cdf6f280/.github/workflows/memory-option-order-20260924.yml).

## Results: the unit remains eight paired cases

The denominator 48 is eight cases repeated under six option orders, not 48 independent questions.

| Memory view | Correct decisions, all orders | Cases changing semantic answer across orders | Cases correct in all six orders |
|---|---:|---:|---:|
| Chronological statements | 31/48 | 2/8 | 4/8 |
| Same statements + correct relations | 31/48 | 3/8 | 4/8 |
| Same statements + reversed relations | 31/48 | 3/8 | 4/8 |

For a single global permutation, each view scores either 5/8 or 6/8. Reporting only the best arrangement would hide the instability.

| Fictional case | Chronology: correct / 6 | Correct relations: correct / 6 | Reversed relations: correct / 6 |
|---|---:|---:|---:|
| Publication permission withdrawn | 3 | 3 | 3 |
| Publication permission restored | 4 | 3 | 3 |
| Assistant's meeting suggestion not selected | 0 | 1 | 1 |
| Assistant's meeting suggestion accepted | 6 | 6 | 6 |
| Outline is a temporary step | 6 | 6 | 6 |
| Slides task replaced by outline only | 6 | 6 | 6 |
| Childhood preference not established | 0 | 0 | 0 |
| Childhood preference explicitly confirmed | 6 | 6 | 6 |

**A decision that changes:** in the permission-withdrawal case, the current instruction remains *do not publish*. Label the original answers 0=keep private, 1=publish, 2=no decision. Arrangements `012, 021, 102, 120, 201, 210` yield semantic choices `1, 1, 0, 0, 1, 0` in every view. This is arrangement sensitivity in this setup, not evidence of a universal preference for a particular letter or a live permission violation.

**An error that remains:** the model selects the assistant's violin guess in all 18 observations of the unestablished-childhood-preference case. The fictional user never establishes that fact. Option order therefore cannot explain every error here. These are repetitions of one case, not 18 independent false-memory incidents.

**Equal scores do not mean equal choices:** correct and reversed relations yield identical choices in all 48 matched cells. They differ from chronology in two cells, with one gain offset by one loss. The first pilot's no-accuracy-advantage observation persists, but its identical-choices-across-views observation must remain scoped to the original answer order.

## Prior work and interpretation

Answer-order sensitivity is not our discovery. [Pezeshkpour and Hruschka (2023)](https://arxiv.org/abs/2308.11483) and [Gupta et al. (2024)](https://arxiv.org/abs/2406.19470) study this concern on other tasks/models. This project contributes an inspectable diagnostic for these specific memory/provenance cases, not a replication of their datasets.

Do not advertise relation labels as improving memory from these runs. Keep order balancing and semantic-identity scoring in future evaluation. Test whether a model understands the relation notation before attributing a null to representation or model size. The next claim-bearing comparison needs genuinely new cases and a frozen protocol, not more editing of these eight items until a preferred format wins.

## Evidence and reproducibility

[Original complete output artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35894984091/artifacts/10766019830): scripts, resolved environment, metadata, execution log, report, and all 144 raw records with full prompts, logits, semantic mappings and token counts. Its configured retention ends 30 September 2026 UTC. The authors retrieved a byte-identical archive before expiry; this does not promise permanent availability of the Actions link.

Archive SHA-256: `e85d77194332280346d2e87b4a491e0a6bed5da902caea9a9c4167f1c889dee9`.
Diagnostic script SHA-256: `559369a3e9c652898d6ee9f99b7951c04461fa71998988664fc02171af924a0e`.
Base script SHA-256: `9f22d6f753eceef2847be49076fa6ae8f60a0e967ed48a8e631706f84f4514c4`.
Weights SHA-256: `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.

A separate deterministic calculation checked grid coverage, semantic mapping, raw argmax choices, aggregate scores, and the unchanged original-order prompts. All 24 original-order choices matched the first run; logits were not bit-identical (maximum difference about `4.01e-5`). This is bookkeeping verification, not independent model replication. Token count stayed constant across permutations within each case/view. Chronology remained shorter than the relation views, so this is not a token-matched test of the benefit of memory structure.

Execution: standard GitHub-hosted Ubuntu, CPU float32, two threads, PyTorch 2.6.0 and Transformers 4.51.3. Forward passes took 187.703 seconds in this particular run, excluding setup/loading. No personal computer, API credential, paid model endpoint or GPU was used. No new subscription or recurring schedule was created. The runtime network guard is a Python fixture guard, not an OS sandbox. Setup warnings are retained.

**Limits:** one small model, eight reused development cases, short prompts, forced-choice logits, authored oracle relations. No frontier-model result, long-history reconstruction, actual tool action, independent recognition or validation of a person's memory is claimed.

## 한국어

같은 대화와 모델을 두고 보기 순서만 모두 바꿨다. 세 기억 형식 모두 총 48회 중 31회를 맞혔지만, 순서가 바뀌어도 항상 맞는 대화는 8개 중 4개였다. 사용자가 공개 허가를 철회한 대화는 보기 순서에 따라 답이 흔들렸다. 사용자의 과거를 조수가 추측한 대화는 순서를 전부 바꿔도 추측을 사실처럼 골랐다.

배열에 민감한 오답과 배열을 바꿔도 남는 오답을 구분할 근거가 생겼다. 올바른 관계 표시와 반대로 만든 표시가 같은 선택을 만든 만큼, 이 결과를 관계 기억 기술의 우수성으로 홍보하지 않는다. 기존 점수와 실패를 보존하고, 더 유리한 배열만 선택하지 않았다.

Question direction: **Youngseok Oh**. Diagnostic design, implementation, orchestration and analysis: **Zero (ChatGPT)**. Model weights: **Qwen team**. No external reviewer, institution or model provider has endorsed these results.
