# Handoff Audit 0.1

**Find decision-relevant distinctions lost at a declared information boundary, before spending on model calls.**

[한국어](START_HERE.ko.md) · [Research question](../../briefs/context-handoff/README.md)

This is a finite software-audit prototype, not a memory replacement, model benchmark, semantic similarity detector, or newly discovered information-theory result. It runs without dependencies, credentials, network requests, or an LLM. Its input is a reviewed dataset, not executable agent output.

## Run

From this directory with Python 3.10 or newer (execution tested on Python 3.13.5):

```sh
python -B -m unittest -v test_audit
python -B demo.py
python -B audit.py example.json
```

The last command exits **1**, intentionally: the example contains an incompatible-input group. Exit **0** means no such group in the supplied inventory, not universal correctness; exit **2** means invalid/unreadable input or output creation failure. `--out NEW.json` creates a new report and refuses to overwrite a file. Ordinary operation prints only to stdout. The demo's process exit indicates execution, while each named result has its own conflict status.

## What it audits

Each case supplies an ID, the request, **all information available at the immediate decision being evaluated**, a nonempty set of acceptable action labels, and a positive integer weight. An independent expected-ID list detects a case removed or substituted after that list was defined. It cannot know that the caller forgot to put a scenario in both lists.

```json
{
  "schema": "handoff-audit/0.1",
  "scope": "Synthetic example: only this request and message are available.",
  "expected_case_ids": ["approved", "suggested"],
  "cases": [
    {"id":"approved","request":"Choose the current destination.","available":{"text":"Use B."},"acceptable_actions":["B"],"weight":1},
    {"id":"suggested","request":"Choose the current destination.","available":{"text":"Use B."},"acceptable_actions":["A"],"weight":1}
  ]
}
```

This illustrative projection erased whether the message was an approved change or only a proposal. The action labels encode the analyst's intended behavior and are **not** included in the available information. In a real evaluation, keep reviewed source histories separately to justify them. Incorrect or contradictory labels can produce a conflict without any fault in a transformation.

Cases are grouped by exact `(request, available)` equality. Typed structural JSON sorts object keys but preserves list order, whitespace inside strings, and boolean/integer distinctions. Floating-point observations are rejected rather than rounded. Supply an exact rendered prompt as a string when serialization order or bytes matter. Case IDs, weights and answer labels cannot accidentally distinguish otherwise identical inputs.

A group is incompatible when the intersection of **all** its acceptable-action sets is empty. Comparing pairs alone is insufficient: `{A,B}`, `{B,C}`, `{A,C}` overlap pairwise but have no action valid for the whole group. A common permitted clarification action removes that immediate-action conflict; it does not recover the missing answer. Clarification is never silently added by the auditor.

Default reports contain case IDs, action sets and input hashes rather than raw input contents. This is not anonymization: IDs and labels themselves may be sensitive. Review outputs before publishing them.

## The finite ceiling

For each input-equivalence group, add case weights for every acceptable action, then select the largest sum. Sum those maxima over groups and divide by the total weight. A fixed decision rule cannot choose different answers for identical available inputs. A randomized rule is a mixture of such choices and cannot exceed the same bound on this finite weighted objective.

The reported rational number is **not measured model accuracy**, a future population estimate, or a discovery that some model is limited to that score. It is only the exact maximum for the declared one-step input and caller-supplied weighted cases. State, retrieval results, caches, previous turns, or other signals available to the actual agent must be included. A new retrieval step changes the boundary and requires another analysis. No-conflict is not proof that a model uses preserved distinctions, that an action executes correctly, or that the inventory is complete.

## Applied to a pinned real transformation

`demo.py` checks the full vendored source hash and extracts only the unchanged `_adapt_tool_images_for_mistral` function from vLLM PR head `a9cdfa3b645773684b40359e11e78fb49f4c57e8`. It supplies four fictional histories assigning images X and Y to two tool calls, with unit weights. The request asks which tool returned Y. Images are URL placeholders and are not downloaded.

| Declared input/control | Histories | Distinct inputs | Incompatible groups | Finite immediate-action ceiling |
|---|---:|---:|---:|---:|
| v15 identity path | 4 | 4 | 0 | 1 |
| pre-v15 adapted messages only | 4 | 2 | 1 | 3/4 |
| adapted messages plus analyst-provided attribution | 4 | 4 | 0 | 1 |
| adapted messages; asking for the original allowed in every case | 4 | 2 | 0 | 1 |

Three histories, `AA`, `AB`, and `BB`, collapse to the same adapted messages. Their required answer about image Y is A, B, B respectively. `BA` produces the other image ordering and remains separate. Therefore 3/4 is the exact finite ceiling **for this deliberately chosen four-case, equally weighted task**, not for Mistral generally. The sidecar is a diagnostic control, not an implemented vLLM repair. The clarification control still has only two distinct inputs and does not claim successful identification.

This reuses an **already documented compatibility tradeoff**, previously exercised in [our source-attribution check](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1f89094fd2ac9c9846c852079d7118b9e94381ca/checks/vllm-58823-mistral-validator/test_provenance_boundary.py). The new work is the reusable auditor, explicit acceptable-action semantics, finite bound, and tested controls. It is not a fresh upstream bug report.

`vendor/mistral.py` matches SHA-256 `74fa5093b91ed69d79ff402f0f86633be8017f110455f0843513404d6799b6d0` and Git blob `e908ea223867dca8097216ebc310549ce2c1035c`. It was copied from the connector-returned source and accepted only after both hashes matched. The entire vLLM module is **not imported**. External type aliases are supplied for the extracted function. No Mistral validator, tokenizer, model, GPU, server, or real tool execution is part of this run.

## Checks and limitations

27 unittest methods passed in the ChatGPT working container. One independently enumerates all deterministic policies for 3,430 small weighted set/group combinations and checks the computed bound. Other checks cover joint conflicts, allowed clarification, source metadata, strict inventories, type preservation, rejection of duplicate keys, malformed input, and non-overwrite behavior. These counts are software checks, not model calls or independent research replications. `DEMO_RESULTS.json` recomputes exactly. Files and finite fixtures stay unchanged during audit.

Limits are intentionally narrow: exact declared JSON equality, not semantic equivalence; at most 1,000 cases and 4 MiB per CLI input; finite nonempty acceptable sets, not utilities or multi-step planning. This tool can identify a counterexample to the supplied interface's decision sufficiency. It cannot validate the labels, inspect hidden state, or certify the user's own memory system.

The original question is broader than reducing thought to right/wrong answers. Preserving the distinction between a generated proposal and an authorized fact can support exploration without making every proposal immediately executable. This auditor covers one information-boundary question only.

## Prior work, authorship, and scope

Structured provenance is established in [W3C PROV-DM](https://www.w3.org/TR/prov-dm/). Decision-preserving representations have a substantial prior literature, including [Abel, Hershkowitz and Littman's state-abstraction work](https://proceedings.mlr.press/v48/abel16.html). These references motivate the distinction; no new theorem or superiority claim is made.

Direction: **Youngseok Oh**. Implementation, synthesis, execution and analysis: **Zero, his AI collaboration partner**. Upstream source retains its vLLM contributors' copyright and Apache-2.0 license. Original code in this directory is offered under Apache-2.0 as well; this does not relicense the rest of the repository. See LICENSE and NOTICE.

No user PC, private memory, model API, package installation, hosted job, operational settings, or external project comment was used or changed for this prototype. No adoption or independent external review is claimed.
