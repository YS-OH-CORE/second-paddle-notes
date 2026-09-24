# Memory pilot: review the evidence without a model

**Youngseok Oh (오영석) × Zero (ChatGPT) | Evidence snapshot 2026-09-24**

Two completed development runs, eight fictional conversations, and an offline calculator. This release preserves the original result archives outside their seven-day Actions retention window. It is an evidence snapshot, not a new model, validated memory system, or new model experiment.

## Start in one minute

Download `ZERO_MEMORY_CPU_RAW_20260924.zip`, `ZERO_MEMORY_ORDER_RAW_20260924.zip`, `verify_evidence.py`, and this guide into the same new directory. Do **not** unpack or run the scripts inside the original ZIPs. With Python 3.10+:

```sh
python -B -S verify_evidence.py
```

The calculator reads bounded ZIP members, checks their hashes, recalculates choices from the saved logits, maps letters back to answer meanings, and checks complete case coverage. It installs nothing and makes no network or model calls. It does not judge whether the authored answer key is scientifically valid. Downloading and reading the raw records needs no model subscription or GPU.

Optional: download `test_verifier.py` alongside it and run `python -B -S test_verifier.py`. Those six checks include deliberately damaged data and validate this calculator, not language-model ability. `AUDIT.json` is the saved author-side calculator output. No result from an outside reviewer is implied.

## What the existing runs actually show

The initial 24 recorded forward passes scored 5/8 under each view. The later run exhausted all six answer arrangements, yielding 31/48 for each view, with four of eight cases correct in every order. These are **eight reused cases**, not 168 independent questions. Both runs used one pinned `Qwen2.5-0.5B-Instruct` model; they do not evaluate modern frontier models or anyone's real personal history.

In the permission-withdrawal case, the selected answer changes with the answer arrangement. In the unestablished-childhood-preference case, the model chooses an assistant's violin guess in every arrangement. Correct versus reversed relation annotations yield identical choices in all 48 matched cells. The original reports and all errors remain unchanged.

### An interpretation limit made explicit in this audit

The actual system prompt says that optional relationship metadata may be imperfect and that the statements are the source. Every condition contains the complete short chronological conversation. Consequently, identical choices with correct and reversed annotations **cannot establish that the model is unable to understand relationships**. They are also compatible with following the instruction to prioritize source statements. Existing results establish no accuracy advantage for the added labels in this setup; they do not identify the cause of that null. This is an author-side qualification of interpretation, not a correction to the scores.

Likewise, this is currently a **short-context reading/provenance diagnostic**, not a test of memory retrieval, compression, or reconstruction over long histories. Before increasing model size or running more of these same items, a future protocol should independently test relation-notation comprehension and source-priority decisions, and use genuinely new held-out cases for any claim about memory representations. No such follow-up is claimed in this release.

### A forced-choice concern checked using the existing records

A/B/C carried at least 99.84% of the recorded next-token probability mass across the 168 rows. The recorded unrestricted vocabulary top token matches the selected label on all 168 rows. This narrows the concern that A/B/C selection was choosing among tokens the model would barely emit. It still does not test full generated responses: these fields were recorded by the original runner, and the complete vocabulary logit vector was not retained for an independent re-inference.

## Reproducible source trail

- Initial run: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35887197137
- Initial source: https://github.com/YS-OH-CORE/second-paddle-notes/blob/c713b8c8f46ccb249e8076d3989cae775e494009/experiments/memory-cpu-pilot/pilot.py
- All-order run: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35894984091
- All-order protocol: https://github.com/YS-OH-CORE/second-paddle-notes/blob/6d8ae732bc53da3874a2fc10c66582fb5c1de8f6/experiments/memory-cpu-pilot/option_order.py
- Complete descriptive report: https://github.com/YS-OH-CORE/second-paddle-notes/blob/dbd48bbb31b0e03f2855f196e79bc809822fdd38/experiments/memory-cpu-pilot/OPTION_ORDER_REPORT.md

The two ZIPs retain original prompts, logs, environment information, logits and metadata. Their SHA-256 values are embedded in `verify_evidence.py`; `SHA256SUMS` also covers this release's files. Hashes establish byte correspondence, not scientific truth or an independent signature. Release assets remain subject to owner control and GitHub availability; this is not a perpetual-storage guarantee.

## Context in prior research

Option-order sensitivity was studied by Pezeshkpour and Hruschka, *Large Language Models Sensitivity to The Order of Options in Multiple-Choice Questions* (2023, https://arxiv.org/abs/2308.11483), and Gupta et al., *Changing Answer Order Can Decrease MMLU Accuracy* (2024, https://arxiv.org/abs/2406.19470). It is not a discovery claimed here. LongMemEval explicitly evaluates knowledge updates and abstention alongside other long-term-memory abilities (Wu et al., https://arxiv.org/abs/2410.10813). Our small synthetic reading check does not replace or replicate those benchmarks.

## Useful review questions

1. Is any specific gold label ambiguous given the **user statements**, rather than the assistant's assertions? Identify the case and exact wording.
2. Does the source-priority system instruction explain why reversed metadata has no effect? What is the smallest new control that separates that explanation from failure to comprehend the notation?
3. Can another reader obtain the same saved-record counts with an independently written calculator? That would be bookkeeping reproduction, distinct from rerunning the model under the original environment.

Technical feedback belongs in a focused issue at https://github.com/YS-OH-CORE/second-paddle-notes/issues. No purchase, endorsement, star, or testimonial is requested. Reviewers should use synthetic examples rather than upload private conversations.

## 한국어

이 자료는 결과를 믿어 달라는 소개문이 아니라, 원자료에서 직접 다시 계산할 수 있는 작은 검토 묶음이다. 모델을 설치하거나 API를 결제할 필요 없이 저장된 168행의 계산을 확인할 수 있다. 원본 ZIP은 수정하지 않았다.

이번 재검토에서 점수는 그대로였지만 해석을 더 좁혔다. 애초에 ‘관계 표시는 틀릴 수 있으니 원문을 우선하라’고 지시했다. 따라서 올바른 표시와 반대 표시에서 답이 같다는 이유만으로 ‘관계를 이해하지 못한다’고 말할 수는 없다. 실제로 기록된 것은 이 작은 읽기 과제에서 추가 표시의 정확도 이득을 보지 못했다는 사실이다.

오영석의 질문 방향과 Zero의 실험 설계·실행·분석·문안 작업을 구분한다. 기존 모형은 Qwen 팀의 것이고, 계산은 GitHub-hosted CPU에서 수행됐다. 이번 배포는 새 모델 실행, 외부 검증, 회사의 인정, 사용자의 과거 복원 결과가 아니다. 의견과 반론을 받을 수 있는 검토 가능한 증거 묶음이다.
