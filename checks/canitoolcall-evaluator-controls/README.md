# CanIToolCall: reference-output baseline before fixture applicability changes

Youngseok Oh × Zero | 26 September 2026

**No inconsistency was found in the selected reference-output and corruption controls.** This is an audit of the existing evaluator against its declared expectations, not a replay of model outputs through real engines and not confirmation that every fixture's expected answer is correct.

The work follows the current CanIToolCall project and its [open finish/applicability proposal, issue #9](https://github.com/redd34/canitoolcall/issues/9). That proposal wants to distinguish a parser failure from a fixture that assumes a stop token was ignored when the selected engine always applies it. We did not implement that proposal, change its schema or open a competing PR.

## 1. Existing corpus and evaluator

Source pin: `redd34/canitoolcall@9edf62cfd4c493749ca76bc8816db86a5bc8f91d`.

The [committed probe](probe.py) imports the original `checks`, `fixtures` and `results` modules, reads all 469 existing fixture records, and constructs results for the evaluator. The expected records and raw-output fixtures are unchanged. For normal cases it uses `expected_as_result`; for malformed cases it supplies each declared acceptable outcome. Additional controls deliberately corrupt the parsed result rather than the source fixture.

| Control class | Evaluator observations | Observed result |
|---|---:|---|
| Exact declared reference result | 434 | All accepted |
| Declared graceful-error alternatives from 35 fixture records | 87 | All accepted |
| Deliberately wrong parsed results | 1,476 | All rejected |
| Total evaluator observations | 1,997 | No mismatch with these control expectations |

The wrong results omit content, reasoning or calls; invent or rename a call; contain duplicate JSON keys; or expose a partial call before reporting an error. Those 1,476 rejections are **synthetic detector controls, not 1,476 engine bugs**.

The three observation slots (`nonstream`, `token`, `one`) receive the same constructed result. No tokens are chunked, no parser consumes them, and no real streaming behavior is tested. Acceptance of a fixture's own reference only establishes self-consistency, not independent validation of the fixture's provenance or ground truth.

The first [Actions run, 36227868553](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36227868553), completed. Its green status means the observation run finished; the report separately records whether each control expectation held. In this run all did. A local replay in a second Python/dependency environment reproduced all 1,997 observation dictionaries exactly.

Separately, the original fixture validator reported zero issues for the 469 records. The unchanged upstream `tests/core/test_checks.py` passed **69/69** locally, with no errors or skips. These are the current schema and one upstream test file, not the proposed schema's acceptance test or the entire project's CI suite.

## 2. A useful boundary for issue #9

Fixture applicability and parse correctness should reach different result paths. We exercised the existing worker and runner with the two fixture IDs named in issue #9, using a deliberately synthetic unsupported adapter and constructed replies:

| Input to the existing worker/runner | Actual classification |
|---|---|
| Adapter returns `Support(False, reason)` | `unsupported`; reason retained; no scoring rows |
| Supported reply containing the exact reference parse | `pass` |
| Supported reply containing an empty parse instead of the required calls | `fail` |

For both fixtures, the unsupported adapter observer saw only `supports`; the worker did not ask it for token units, parsing or parser configuration. This tests the existing early-exit plumbing with a test double, not actual stop-token support in an engine.

One deliberately wrong-level integration control passed a standalone `CheckResult(..., Status.UNSUPPORTED)` to `checks.case_status`. That aggregates to `pass` at this pin. **The current registered checks do not produce such a row; this is not an observed bug in the existing project.** It illustrates why a future applicability decision should not simply be inserted as a scoring row.

The current `Adapter.supports` receives only `(family, model)`, while the proposed `assumes` property is fixture-specific. A future implementation therefore needs a fixture-aware decision somewhere before replay, preserving the existing unsupported result path. This note does not prescribe a new public method or claim the feature already exists.

[applicability_controls.py](applicability_controls.py) supplies the exact local control. It uses the original worker and runner, a synthetic adapter, and six runner evaluations across the two named fixtures. It runs no engine. The prospective integration check was designed after reading issue #9; it is not a preregistered study.

## 3. Suggested acceptance criteria for the proposed change

In addition to the author's backward-compatible schema requirement:

- Keep a normal fixture for the same family/model supported; exclude only a fixture whose explicit assumptions the engine cannot satisfy.
- Return a fixture-level unsupported result with its reason, without invoking the parser; do not turn it into pass, an engine error, or an ordinary failed parse.
- Preserve the existing `truncated` behavior when new finish metadata is absent. Explicit metadata should not fabricate a terminal token for a length-truncated generation.
- Re-run the unchanged reference-output and corruption baseline before interpreting changed engine scores. A changed denominator should remain visible as changed applicability, not an unexplained accuracy gain.

These are review suggestions, not a completed implementation or evidence that any current public matrix score is wrong.

## 4. Reproduce and inspect

With the pinned source checkout and the required lightweight dependencies installed, run:

```sh
python probe.py --repo /path/to/pinned/canitoolcall --out /path/to/new_reference_results
python applicability_controls.py --repo /path/to/pinned/canitoolcall --out /path/to/new_applicability_results
```

Both output directories must be new. Neither script needs a model, engine environment, hosted endpoint or credentials. Python sockets/DNS are blocked during measurement. This is a Python guard, not an operating-system sandbox.

Actions: Python 3.12.3, jsonschema 4.25.1, Jinja2 3.1.6, pytest 8.4.2 installed. The 69 upstream tests and additional applicability control ran locally on Python 3.13.5, jsonschema 4.26.0, Jinja2 3.1.6 and pytest 9.0.2. The corpus replay was run in both environments; the local verification is ours, not an independent external replication. No production source was edited.

Baseline script committed before execution: `08cd6bb745ac34dbad633bd09c37e582948c6a4f`.
Workflow commit: `6b26599e63f81948598e4545cbde1fd755d53d73`.
Baseline script SHA-256: `7d6fbb53d97eee6287d6d39a8fce56b6460953730321461a87d0e9fbaeb33240`.
Applicability control SHA-256: `3820dbf37a85adcec728e9277bb9d0e12a762fe2e653b1f007a455af6e9df15d`.

[Raw artifact 10901004486](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36227868553/artifacts/10901004486): 468,725 bytes; SHA-256 `8c3210c96eeb37e6ce626395236c8bcefaff39748dd740e39a6e7f1a1177b405`. It retains the source package, fixtures, schemas, tests, licenses, code, 1,997 observations, logs and setup environment. GitHub's upload omitted three empty hidden `.gitkeep` placeholders; all other 116 manifest entries were present and hash-verified. No source code or fixture record was missing. Actions retention is 30 days. The separate conversation evidence bundle also retains this ZIP, local replay, JUnit output and applicability control results.

See [AUDIT.json](AUDIT.json) for compact counts and readback scope. The corpus and evaluator are CanIToolCall's work. The new probes, control design, execution and analysis are Zero's work with Youngseok Oh. AI participation is disclosed in the repository's authorship context. No maintainer acceptance, new engine diagnosis, end-to-end benchmark replication or paid-client work is claimed.
