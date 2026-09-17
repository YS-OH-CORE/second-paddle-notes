# Pinned open-weight execution and handoff smoke

Prepared by Zero (ChatGPT) for Youngseok Oh, 2026-09-17.

This is an engineering smoke test for a controllable, no-inference-key execution route. It is not a new benchmark, an independent scientific review, or a model ranking. All prompts are newly authored synthetic data. No private conversation, external correspondence, user identity document, or withdrawn research is included.

## What runs

Qwen's official Qwen3-4B Q4_K_M GGUF is downloaded at an immutable repository revision and checked against its published SHA-256. The llama.cpp b10964 Ubuntu CPU archive is also checked against its published release digest. A temporary server binds only to 127.0.0.1; built-in agent tools and web UI are disabled. No API key, provider account or autonomous shell access is given to the model.

One exact-copy control, four direct decisions, and two writer/executor pairs make at most nine generation requests. The four decisions distinguish an accepted user revision from an explicitly unaccepted assistant proposal, before and after consistent option renaming plus row-order reversal. These are simple sanity checks sharing one decision structure, not independent task families. The two handoffs use exactly the text returned by the writer, without the original task conversation or an answer key in the successor request. The same model process serves stateless requests with prompt caching disabled; distinct models or process-level isolation are not claimed.

`retained` is only a declaration in generated JSON. It does not verify file preservation or agent tool execution. This intentionally narrow route check does not substitute for the larger artifact-based evaluation or external specification review.

Generation uses non-thinking mode, greedy decoding, seed 17, 256 output tokens maximum and 4096 context tokens. These choices bound an engineering check, not optimal model performance. Every error, truncated answer and overlength handoff remains visible; there are no inference retries or post-hoc repairs. Expected outcomes are in the driver but are not sent in model requests; the model has no filesystem tools. The fixtures are author-specified development material, not preregistered or held-out data.

## Run

On a compatible Linux x86_64 host with Python 3.12+ and roughly 5 GB of spare memory:

```sh
python -B -m unittest -v test_smoke
python -B smoke.py --out /a/new/output/directory
```

The output directory must not exist. Runtime and model downloads use about 2.6 GB temporarily and require internet access. The model is not kept running after the invocation. The script records input/output, usage if reported, digests and version metadata. It prints a bounded synthetic receipt to stdout. Do not extend this public workflow to personal or confidential inputs.

The associated one-shot verification branch uses a standard public GitHub-hosted runner with read-only repository permission, no stored secrets, no artifact uploads/cache writes and no recurring schedule. Default-branch content is not changed.

## Sources and licenses

- Model and Apache 2.0 license: https://huggingface.co/Qwen/Qwen3-4B-GGUF
- Pinned model revision: bc640142c66e1fdd12af0bd68f40445458f3869b
- Model filename: Qwen3-4B-Q4_K_M.gguf
- Model SHA-256: 7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5
- Runtime release and MIT license: https://github.com/ggml-org/llama.cpp/releases/tag/b10964
- Runtime SHA-256: 9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443
- Current public-runner billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- The separate hosted GitHub Models service retired on 2026-07-30. This harness does not call it: https://github.blog/changelog/2026-07-30-github-models-is-now-retired/

New harness source: MIT. Model weights and runtime retain their original licenses and are not redistributed in this repository.
