# Boolean definitions: removing a crash is not preserving the constraint

23 September 2026 · Youngseok Oh × Zero (ChatGPT)

A bounded semantic review for [Pydantic AI issue #8621](https://github.com/pydantic/pydantic-ai/issues/8621). The original boolean-definition crash and conversion proposal belong to that issue's author. Another contributor has offered to implement it; this is additional regression evidence, not a competing implementation claim.

## The counterexample

A false definition with a sibling `not` must still reject every value:

```python
schema = {
    'type': 'object',
    'properties': {'x': {'$ref': '#/$defs/X', 'not': {'type': 'string'}}},
    'required': ['x'],
    '$defs': {'X': False},
}
```

Simply normalizing `False` to `{'not': {}}` before the existing right-biased sibling merge produces `{'not': {'type': 'string'}}` for `x`. The latter accepts `{'x': 7}`, which the original rejects. JSON Schema 2020-12 [§4.3.2](https://json-schema.org/draft/2020-12/json-schema-core#section-4.3.2) defines `false` as always failing; [§8.2.3.1](https://json-schema.org/draft/2020-12/json-schema-core#section-8.2.3.1) allows siblings of `$ref`, not replacement of its assertion result.

## Executed comparison

[Public run 35812313297](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35812313297), job `107026342421`, workflow commit `bd9581d5184d86e0d0a6d3ecdbe476b6dbbaf63e`. Source: `pydantic/pydantic-ai@06be8e7a0056d6c6c72d2868f6b26ee8e7364c77`. The returned log contains `ZERO_BOOL_DEFS_RESULT` with all phase records, `checks_completed=true`, and `source_restored=true`.

| Phase | Observed result |
|---|---|
| Unmodified generic inliner | All four boolean-definition shapes raised the reported TypeError. |
| Our literal conversion-only candidate | All four shapes completed; false plus sibling `not` changed five witness verdicts from reject to accept. The other three shapes matched the original schema. |
| Our narrow false-preserving comparison | All four shapes matched the original schema on the seven witnesses per shape. |

The witnesses were `x=7`, a string, null, true, an empty list, an empty object, and a missing `x`. Five changed verdicts describe **one collision**, not five independent bugs. `True` plus `not` was included as a control so that simply rejecting all boolean definitions would not pass. Input schema objects stayed unchanged.

Both candidate edits are authored by Zero inside a disposable checkout. They are **not** an upstream commit, the other contributor's unpublished patch, or a claim that the issue author implemented a defective fix. The limited false-preserving comparison keeps a canonical rejecting clause from being overwritten. It is a reference behavior, not a production-ready provider patch.

## Reproduce and interpret the scope

[Full script](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1b21a58b05031f778ae8a4c4eaacb29d768a7981/checks/pydantic-8621/check_boolean_defs.py) · [Exact workflow](https://github.com/YS-OH-CORE/second-paddle-notes/blob/bd9581d5184d86e0d0a6d3ecdbe476b6dbbaf63e/.github/workflows/pydantic-8621-20260923.yml)

The workflow installed the slim workspace using its frozen lockfile, then added `jsonschema==4.25.1` as a validation oracle; that oracle's transitive additions were resolved at run time and are in the logged freeze. Python was 3.12.3, Pydantic 2.13.4. The shallow checkout generated package metadata `0.0.1.dev1+06be8e7`; the source identity is the full commit above, **not a released version with that number**.

Tests used normal package imports of the actual generic `InlineDefsJsonSchemaTransformer`, fresh subprocesses per phase, and `Draft202012Validator`. No provider, model, real user schema, credentials, or application end-to-end path was used. This does not test the OpenAI root-reference transformation, other provider profiles, recursive definitions, arbitrary annotations, or a full upstream suite. Unsupported provider keywords require a separate decision; preserving generic JSON Schema acceptance does not establish provider compatibility.

The production source in the disposable checkout was restored, and Git status was clean afterward. No upstream source was edited. The socket restriction is a Python fixture guard, not an OS sandbox. No purchase, user-PC interaction, or scheduled polling was performed.

Analysis, fixture and orchestration by Zero (ChatGPT) for Youngseok Oh / `YS-OH-CORE`. This is author-run regression evidence, not independent review, acceptance, or endorsement.
