# Tool persistence: preserve callable names as well as body text

Youngseok Oh × Zero | 25 September 2026 KST

Supplemental reproduction for [smolagents #2833](https://github.com/huggingface/smolagents/issues/2833). BlueX888 reported the blanket replacement and proposed removing it. This review contributes parameter-name and method-name-substring regressions, a deliberately insufficient count-one control, and a check of an already-corrupted export. No competing PR or new repair is claimed.

[Completed execution](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36081728457) · [Exact checker](https://github.com/YS-OH-CORE/second-paddle-notes/blob/50598d1541939266f9c7d23d1f40312c0bbe89be/checks/smolagents-2833/check_tool_roundtrip.py) · [Workflow](https://github.com/YS-OH-CORE/second-paddle-notes/blob/732c95d6f7f85f0183eed5c04a4b5a2624be52a7/.github/workflows/smolagents-2833-serialization-20260925.yml)

## Results

At `227ef5e49ddd82339295939072f0223249aa8d38`, the real decorator and `Tool.to_dict()` / `Tool.from_dict()` were exercised. The same tools were also written with `Tool.save(make_gradio_app=False)`, the resulting files read, and those bytes passed to `Tool.from_code()`. Saved code bytes matched the corresponding dictionary code exactly. No saved-file result is substituted for a Hub upload or Agent integration test.

| Authored fixture | Unmodified replacement | Replacement with count=1 | Remove the replacement |
|---|---|---|---|
| Decorated `search`, URL literal in body | `/search` becomes `/forward` | Same incorrect URL | Original URL retained |
| Decorated `label(label_value: str)` | Parameter becomes `forward_value`; load rejected | Same load rejection | Original keyword call works |
| Decorated `ward(value: str)` | Method `forward` becomes `forforward`; load rejected | Same load rejection | Original call works |
| Decorated noncolliding `plain` | Original call works | Original call works | Original call works |
| Explicit `Tool` subclass named `search` | Original URL retained | Original URL retained | Original URL retained |

Both restoration paths produced the table's outcomes. The `ward` body is simply `return value`: the tool name does not appear in its original body, but it is a substring of the generated `forward` definition. Thus replacement can damage the definition itself, not only the body. `count=1` remains unsafe because it changes the first matching substring, which can be a parameter, a definition, or a body literal. It was a reviewer-authored negative control, not a proposal attributed to the reporter.

For `label`, the recorded load error reports actual parameters `{'forward_value'}` versus expected `{'label_value'}`. For `ward`, no concrete `forward` override remains, and validation sees the inherited generic parameters. These are actual captured loading exceptions, not hypothetical failing calls. The original live fixture outputs and input dictionaries remained unchanged after export.

The removal experiment preserves all five fixture behaviors. This is bounded supporting evidence for the reporter's direction, not full test-suite success or an accepted patch.

## Existing exports are a separate boundary

The original process first wrote a dictionary containing the corrupted URL. Loading that exact old dictionary in the removal variant still returned `/forward`. Its bytes and checksum remained unchanged. Changing the exporter prevents this tested corruption in new exports; it does not reconstruct the author's intent inside previously changed saved code. Regenerate from a trusted original implementation where available rather than globally reversing every occurrence of `forward`.

## Scope, provenance and reproducibility

One cloud job, five related fixtures across three source variants, with fresh imports per variant. Ordinary package methods executed; AST was used only to inspect saved declarations, not to replace the runtime under test. Every tool returns inert strings. No real endpoint, model, account, private record, user PC, Gradio app, Agent loop, remote executor or Hub upload was used. Only the fixture code authored in this checker was loaded as executable tool code. Hugging Face offline flags and a Python socket-connect guard were enabled; that guard is not an OS sandbox.

The source file was temporarily edited only in a disposable checkout and restored in `finally`. The completed workflow also checked `git diff --exit-code`. Source blob: `931acfeccb6f2663b6c073bfa0fd8f0088c01eac`. Python 3.12.3 on Ubuntu 24.04; package metadata `smolagents 1.27.0.dev0`. Dependency versions were resolved during setup and recorded in `environment.txt`, not installed from a complete frozen lockfile. Child stderr was empty for all three variants. One prior public-source download from the assistant container failed DNS resolution before tests; the cloud execution completed on its first attempt.

[Original ZIP](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36081728457/artifacts/10842276837) includes saved tools, raw reports, exact source variants, environment and license notice. The downloaded ZIP matched GitHub's reported digest, and the reports and checker bytes were inspected after download. This is readback verification, not another independent execution.

- Archive SHA-256: `3c0f8510868099e9543c12a11646d2b83af690327806f5ae620cf67a50c48de6`
- Checker SHA-256: `62dd6a8a4f255817b3c9c198d75726b04d99a073ea00bc0d3b974bff4646f766`
- Actions artifact expiry: 25 October 2026, 01:22:47 UTC. A conversation copy is retained; neither location implies permanent storage.

Original diagnosis and removal direction: **BlueX888**. Supplemental fixtures, execution and writing: **Zero, an AI collaborator with Youngseok Oh (@YS-OH-CORE)**. Youngseok provides collaboration direction and the public account. No independent manual human audit, upstream acceptance or deployed fix is claimed.
