# Provider-Neutral Model-Run Dry-Run

This directory turns the statistical requirements in [`../MODEL_EVALUATION_PROTOCOL.md`](../MODEL_EVALUATION_PROTOCOL.md) into an executable, provider-neutral offline path. It makes **no API or SDK calls**, uses only the Python standard library, opens no network connection, and incurs no cost.

The committed outputs select the 16 public `correct`/`shuffled` primary cases from the already-public 40-case smoke set, repeat each twice, and therefore contain 32 deterministic fixture trials. They test plumbing only. They are **not hidden data, not language-model responses, and not model-performance evidence**.

## Separation boundary

`build_bundle.py` emits two deliberately separate files:

- `artifacts/public-smoke.requests.jsonl` is the only bundle a model runner may receive. It contains a random-looking `trial_id`, task content, and response grammar. It contains no source case ID, evaluator template ID, scope, condition label, repeat number, expected action, or gold field.
- `artifacts/public-smoke.evaluator-mapping.jsonl` is evaluator-only. It joins each opaque trial to source identity, template, scope, condition, repeat, allowed actions, and gold. A real runner must never receive this file.

Request order is a deterministic seeded shuffle. Trial IDs are deterministic SHA-256-derived opaque labels. The public fixture exposes its seed for reproducibility. The builder rejects evaluator-only keys found anywhere inside model-facing task content. For hidden candidates, it compares order-independent canonical JSON fingerprints for the entire case/gold bundles and for every individual record and task payload. Reformatting whitespace, changing JSON key order, reordering records, or merely replacing a public case ID therefore cannot disguise public-smoke reuse.

Hidden-candidate mode is deliberately fail-closed to the protocol defaults: at least 24 templates; exactly one source case in every `relevant`/`irrelevant` × `correct`/`shuffled` cell; at least five repeats per cell; identical paired content outside `links`; equal link counts and canonical serialized lengths; the same link identities and action multiset; and a shuffled permutation with no fixed points. It also requires a separately generated seed value at least 128 bits wide. This toolkit provides no relaxed-design switch. The committed public mock remains two repeats because it is plumbing evidence only, never a hidden study. A registered hidden run still follows all seed-generation, commitment, and access rules in the protocol. Merely changing `study_kind` never turns public or leaked data into a claim-bearing study.

## Raw response contract

The first response is final and must contain exactly these three physical records, in order:

```text
ACTION: <one allowed action_id, or the exact token REFUSAL>
PROBABILITIES: {"<every allowed action_id>": <number>, ...}
EXPLANATION: <one optional sentence, or empty>
```

`parse_responses.py` first verifies the frozen request hash, then checks record count and order, the allowed action set, duplicate probability keys, finite and representable values in `[0,1]`, exact key coverage, and a total within `1e-6` of `1`. Huge integers that overflow floating-point conversion are retained as malformed raw output rather than crashing the parser. It never uses an explanation to repair an action. Every parsed record retains the unedited `raw_response`, including refusals and malformed outputs. The scorer reparses that retained text and rejects any parsed field that does not match it.

The reserved `REFUSAL` token permits an exact, non-heuristic explicit-refusal rate. Other prose refusals remain invalid output rather than being reclassified by subjective text analysis.

## Metrics and decision boundary

`score_model_eval.py` pairs `correct` and `shuffled` trials by template and repeat. The primary estimate is:

```text
(relevant exact accuracy under correct - relevant exact accuracy under shuffled)
-
(irrelevant false-action rate under correct - irrelevant false-action rate under shuffled)
```

It reports exact accuracy, irrelevant false actions, strict invalid outputs, action-invalid outputs, explicit refusals, multiclass Brier score, and log loss. A missing or malformed probability distribution receives Brier `2.0` and log loss `-log(1e-6)`. Probability validity is scored independently; a parseable first action is never reconstructed from the explanation.

Uncertainty is a two-sided 95% percentile bootstrap that resamples templates as clusters and retains all repeats within each selected template. The default and enforced minimum is 10,000 resamples. The registered statistical effect criterion is a point estimate of at least `delta = 0.10` and a lower interval bound above zero.

For the committed deterministic fixture, the metrics deliberately say `DRY_RUN_ONLY_NOT_MODEL_EVIDENCE`, set `claim_supported` to `false`, and explain that even a passing software fixture cannot support a model claim. For a future model run, the score is still not sufficient by itself: registration, frozen hidden cases, independent leakage audit, model identity, raw release, exclusions, integrity hashes, and stop-condition checks remain mandatory.

## Reproduce the complete public dry-run

From this directory with Python 3.10 or newer:

```bash
python run_public_smoke_dry_run.py
python run_public_smoke_dry_run.py --check
python -m unittest discover -s tests -v
```

The first command regenerates six committed artifacts. The second rebuilds them in a temporary directory and requires byte-for-byte equality. Both make zero model calls.

The individual provider-neutral stages are:

```bash
python build_bundle.py
python make_mock_responses.py
python parse_responses.py
python score_model_eval.py
```

To use the tooling later with a separately approved and preregistered hidden set, give `build_bundle.py` hidden case/gold JSONL paths, freeze the resulting hashes before any response, deliver only the request bundle to the runner, capture the untouched three-record responses, and keep the evaluator mapping unavailable until the raw run ledger is frozen. Follow every remaining gate in the parent protocol; this directory does not provide an endpoint adapter or authorize model access, spending, or publication claims.
