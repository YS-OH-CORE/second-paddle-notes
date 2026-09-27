# Mistral tool-image handoff: a runnable review kit

**Does a valid converted conversation still tell you which tool produced each image?**

This CPU-only kit accompanies [our regression review on vLLM PR #58823](https://github.com/vllm-project/vllm/pull/58823#issuecomment-5855071941). It contains seven regression checks from that review plus one explicit characterization of the PR's documented source-attribution tradeoff. It is not a replacement PR, a model benchmark, or a new vulnerability report.

## Run it

Use Python 3.12 and an isolated environment. With `uv` installed, from this directory:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt
.venv/bin/python -B run_review.py --out my-result.json
```

On Windows PowerShell, replace `.venv/bin/python` with `.venv\Scripts\python.exe` in the last two commands.

Dependency installation downloads packages. The actual test run makes no network requests, uses only fictional image URLs, and requires no GPU, API key, personal conversation, or running vLLM service. No image is fetched or decoded. `my-result.json` must be a new path; existing reports are not overwritten.

The runner exits 0 for all eight expected outcomes, 1 for failed assertions, and 2 when setup or source checks cannot complete. Direct dependencies are checked against their pinned versions. The lock lists the tested environment, not a promise of compatibility with every operating system.

## What the tests distinguish

| Question | Observed on the pinned helper and library |
|---|---|
| Does V13 reject an image in a tool message before adaptation? | Yes; the same complete history validates after adaptation. |
| Does V15 need image relocation? | No; the original object passes through. |
| Are trailing user text, image order and input immutability retained? | Yes in the tested cases; a second adaptation does not duplicate images. |
| Do duplicate, missing and unknown result IDs still fail? | Yes, using the real validator in **serving** mode. |

## The additional boundary case

Consider the same two tool calls, with the same image order:

- History A: tool A returns image X; tool B returns image Y.
- History B: tool A returns images X and Y; tool B returns an empty list.

For tokenizer version 13, the pinned fallback turns both histories into the **same data**: two empty tool results followed by a user message containing X and Y. Both outputs pass the real Mistral message validator. For version 15, the helper leaves the two distinct inputs unchanged and both validate.

This makes a narrow point: a downstream consumer given only that common V13 output cannot reconstruct which original tool owned image Y. The image parts and tool-call IDs may all still be present while their association has been lost. That association loss is already disclosed by the PR author; this test is a concrete boundary example, not a newly discovered standalone bug. Whether the compatibility tradeoff is acceptable depends on the consuming application.

`test_provenance_boundary.py` checks this explicitly, including non-mutation. No generated answer or model behavior is inferred from the result.

## Source and execution scope

- vLLM PR head: [`a9cdfa3b645773684b40359e11e78fb49f4c57e8`](https://github.com/Taimys/vllm/blob/a9cdfa3b645773684b40359e11e78fb49f4c57e8/vllm/renderers/mistral.py).
- Full source SHA-256: `74fa5093b91ed69d79ff402f0f86633be8017f110455f0843513404d6799b6d0`.
- `mistral.py` is a byte-for-byte pinned source snapshot, not imported as a module. `probe.py` verifies its hash, extracts only `_adapt_tool_images_for_mistral`, and executes that unchanged function. Its external typing alias is supplied as `dict`.
- The installed `mistral-common==1.11.7` conversion classes and message validators are real, not mocks. `Pydantic==2.13.5` and `pytest==9.1.1` are pinned.
- Full vLLM import, full-request validation, tokenizer rendering, image decoding, endpoints, GPU inference and real-user traffic are **not tested**. These checks do not supersede the PR author's broader validation.
- `RESULTS.json` is the initial eight-case run. `FRESH_ENV_RESULT.json` records a repeat in a newly created environment on the same PC. It is another environment check by Zero, not an independent external replication and not eight additional distinct cases.

The original exploratory call omitted `continue_final_message` and raised `TypeError`; the published tests all supply it explicitly. No result from that unsuccessful call is counted as validation.

## Reuse and authorship

The renderer helper and its source snapshot belong to the vLLM contributors and PR author. Their Apache-2.0 copyright header and license are preserved in `mistral.py` and `LICENSE`. Review fixtures, runner, packaging and analysis were prepared by **Zero (AI)**, with **Youngseok Oh's project direction**. This does not claim that Youngseok personally wrote or line-reviewed the code, that upstream adopted the tests, or that OpenAI, Mistral, or vLLM endorses this kit. Original kit code may be reused under Apache-2.0; that permission does not relicense upstream work.

The practical contribution is a small runnable case another developer can inspect, challenge, and add to a relevant test suite. Eight passing expectations mean seven regression contracts and one observed limitation, not eight fixes or eight discoveries.

## 한국어: 이 자료가 보여주는 것

지난 검토 댓글을 다른 개발자가 그대로 실행해 확인할 수 있는 작은 재현 묶음으로 만들었다. 실제 Mistral 메시지 검증기를 쓰지만 전체 모델이나 서버를 실행하는 시험은 아니다.

추가 사례는 ‘이미지가 남아 있고 입력 검사도 통과했다’와 ‘어느 도구가 그 이미지를 돌려줬는지까지 남아 있다’가 다르다는 것을 보여준다. 두 도구가 이미지를 하나씩 돌려준 경우와, 한 도구가 두 이미지를 모두 돌려준 경우가 구형 호환 처리 뒤에는 완전히 같은 자료가 된다. 작성자가 이미 밝힌 호환성 절충을 구체적인 검사로 표현한 것이며, 새 취약점이나 배포된 장애로 주장하지 않는다.

기존 일곱 검사와 이 대조 사례 하나를 합쳐 여덟 항목을 확인한다. 같은 검사를 새 환경에서 다시 실행했다고 서로 다른 열여섯 성과로 세지 않는다. 이 묶음에는 개인 기억·대화·인증정보가 없고, 사용자의 코덱스나 기억 프로그램도 바꾸지 않는다.

Zero × Youngseok Oh.
