# Rule-Use Smoke Evaluation

This is a small, executable companion to note 15, **“A Rule Read Is Not a Rule Running.”** It tests an observable distinction: whether predictions change when a rule–trigger–action link changes, even though the declarative content stays fixed.

This package is a **public smoke test**, not a hidden benchmark and not evidence about any language model. The included baselines are deterministic programs used to verify the harness. No model was evaluated.

## Design

The dataset contains 40 cases:

- 4 task templates;
- 2 scopes per template: a relevant trigger and an irrelevant trigger;
- 5 link conditions per scope: `correct`, `shuffled`, `reversed`, `absent`, and `irrelevant_probe`.

Within each template/scope group, the instruction, rule atoms, trigger examples, action checks, verification statement, and observed event are byte-for-byte identical. Only the structured `links` field changes. Rule text does not contain a trigger–action pair; the mapping exists only in `links`.

Public case IDs are fixed-salt SHA-256-derived opaque labels, sorted independently of generation order. They do not reveal the five-condition cycle. They are not secret identifiers: this is still a public smoke set. Template, scope, condition, and expected action exist only in the separate evaluator-side gold file. The provided baseline adapter passes only `task_content` to its decision function, and any model-facing adapter must do the same.

| Condition | Link manipulation |
|---|---|
| `correct` | Relevant triggers point to their declared actions. |
| `shuffled` | The same relevant triggers point to other declared actions. |
| `reversed` | Correct edges are represented action-to-trigger instead of trigger-to-action. |
| `absent` | No edges are supplied. |
| `irrelevant_probe` | One irrelevant trigger points to an acknowledgement-only action. |

`correct` and `shuffled` are the matched primary pair: both contain exactly three edges and have equal canonical serialized byte length within every template. `absent` is a separately reported lower-bound diagnostic. `reversed` is a directionality diagnostic. `irrelevant_probe` is an intentionally unmatched single-edge collateral probe; it is not primary evidence or a matched control.

The public gold file is deliberately separate from the cases. Because both are public, these cases are suitable for software checks and demonstrations only. A claim-bearing study would need preregistered hidden cases, repeated trials, blinded condition labels, fixed inference budgets, and uncertainty estimates.

For that future step, [`MODEL_EVALUATION_PROTOCOL.md`](MODEL_EVALUATION_PROTOCOL.md) defines the claim boundary and [`model_eval/`](model_eval/README.md) provides a provider-neutral offline bundle/parser/scorer dry run. Neither is a model result, and the dry run makes no API or network call.

## Files

- `build_dataset.py` deterministically creates or checks `data/cases.jsonl` and `data/gold.jsonl`.
- `schemas/` defines the case, gold, and prediction JSON schemas.
- `run_baseline.py` emits raw JSONL predictions.
- `score.py` validates and scores predictions.
- `results/` contains the committed raw outputs and metrics for both deterministic baselines.
- `MODEL_EVALUATION_PROTOCOL.md` preregisters the minimum gates for a future claim-bearing model study.
- `model_eval/` separates model-facing requests from evaluator-only gold and dry-runs strict parsing and scoring with deterministic fixture output.
- `generate_manifest.py` creates or checks `manifest.sha256.json`.
- `tests/` checks matched content, baseline behavior, strict validation, metrics, and committed artifacts.

## Prediction format

Submit one JSON object per line:

```json
{"case_id":"RUE-A1B2C3D4E5F6","action":"FAC_CLOSE_VALVE"}
```

Every case must appear exactly once. Duplicate, missing, or unknown case IDs are errors. An action not listed in that case's `action_checks` is also an error. Extra fields are rejected.

## Metrics

The primary smoke metric is the macro-average, across templates, of this paired difference-in-differences:

```text
(relevant accuracy under correct links - relevant accuracy under shuffled links)
-
(irrelevant false-action rate under correct links - irrelevant false-action rate under shuffled links)
```

It asks whether correct rather than equally sized shuffled links changes relevant behavior beyond any collateral change on irrelevant inputs. It is a software-level smoke contrast, not a statistical estimate from model trials.

Secondary diagnostics report:

- exact action accuracy overall and by condition/scope;
- relevant accuracy by condition;
- irrelevant false-action rate by condition;
- the correct-versus-manipulated relevant-accuracy gap;
- per-template values of the primary contrast.

## Baselines

- `link-following` uses only well-formed trigger-to-action edges in `links`. It is expected to react to the link manipulation.
- `link-ignoring` never reads `links` and always emits `NO_ACTION`. It is a deliberately weak null fixture, not a semantic reasoner and not a competitive baseline.

These are deterministic test fixtures, not cognitive models and not claims about an AI system. Confidence is not collected or scored in this smoke harness. A hidden claim-bearing study should require probability/confidence output and preregister a proper score such as Brier score or log loss.

Committed deterministic results:

| Fixture | Primary link-use contrast | Overall exact-action accuracy |
|---|---:|---:|
| `link-following` | 1.0 | 0.5 |
| `link-ignoring` | 0.0 | 0.5 |

The equal overall accuracy is useful here: the primary contrast detects *where behavior changed*, rather than rewarding a fixture merely for producing more correct outputs in aggregate.

## Reproduce

From this directory, with Python 3.10 or newer:

```bash
python build_dataset.py --check
python run_baseline.py --baseline link-following --output results/link-following.predictions.jsonl
python score.py --predictions results/link-following.predictions.jsonl --output results/link-following.metrics.json
python run_baseline.py --baseline link-ignoring --output results/link-ignoring.predictions.jsonl
python score.py --predictions results/link-ignoring.predictions.jsonl --output results/link-ignoring.metrics.json
python -m unittest discover -s tests -v
python generate_manifest.py --check
```

The committed smoke results are expected to show a primary contrast of `1.0` for `link-following` and `0.0` for `link-ignoring`. This verifies that the metric distinguishes these two programs; it does not establish performance for any model.

To verify the zero-cost model-study plumbing separately:

```bash
cd model_eval
python run_public_smoke_dry_run.py --check
python -m unittest discover -s tests -v
```

These commands regenerate the mock pipeline in a temporary directory and compare all six outputs byte-for-byte. They do not connect to a provider.
