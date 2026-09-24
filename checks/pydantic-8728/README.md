# Equal IDs do not record whether a wrapper setting was inherited

Youngseok Oh × Zero | 25 September 2026 KST

Supplemental regression evidence for [Pydantic AI #8728](https://github.com/pydantic/pydantic-ai/issues/8728). **adtyavrdhn** reported the defect and proposed preserving whether identity was adopted. This experiment exercises that proposal's distinction; it does not claim the original discovery or submit a competing upstream patch.

## The useful control

A transparent `Wrapper(DynamicCapability(feature, id='feat'))` and an explicitly configured `Wrapper(DynamicCapability(feature, id='feat'), id='feat', defer_loading=False)` initially expose the same ID and deferral values. Their subsequent behavior should differ: only the transparent wrapper follows the factory's per-run deferral. An ID comparison alone cannot establish which initial value the caller supplied.

The test observes actual first-request instructions and `load_capability` availability through `Agent` and `FunctionModel`, rather than checking only the wrapper's attributes. Every configuration reuses the **same Agent** for dependency values `True → False → True`.

[Completed run 36075092356](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36075092356) · [exact checker](https://github.com/YS-OH-CORE/second-paddle-notes/blob/ca02239e452510ac912d489801a4f35481d90cb6/checks/pydantic-8728/check_wrapper_origin.py)

## Observed first-request behavior

`D` means the fixture's instructions were withheld and `load_capability` was offered. `E` means the instructions were present and that loading tool was absent.

| Configuration, reused for three runs | Unmodified source | Origin-tracking experiment | Deliberately unconditional adoption |
|---|---|---|---|
| Direct dynamic capability | D / E / D | D / E / D | D / E / D |
| Transparent wrapper | E / E / E | D / E / D | D / E / D |
| Two nested transparent wrappers | E / E / E | D / E / D | D / E / D |
| Explicit eager wrapper, **same ID** as child | E / E / E | E / E / E | D / E / D |
| Explicit eager wrapper, distinct ID | E / E / E | E / E / E | D / E / D |
| Explicit deferred wrapper, distinct ID | D / D / D | D / D / D | D / E / D |

The origin-tracking experiment satisfies all six case expectations. Unmodified source loses deferral in the two transparent cases. Simply adopting unconditionally repairs those two but breaks the three explicit-setting controls. The same-ID eager case is especially useful against an apparently convenient equality-based ownership inference.

Across the observed runs, original wrapper-chain ID/deferral snapshots remained unchanged and instrumented wrapper constructors were not re-entered during binding. This checks those specific reusable-template fields and constructor counts, not arbitrary object state or concurrency.

## What the experiments change

On a disposable checkout, the origin variant records `self.id is None` in a name-mangled instance attribute at wrapper construction, then consults that origin marker when the existing adoption helper runs. The wrong control replaces the helper's condition with unconditional adoption. Both are **reviewer-authored experimental edits**, not the reporter's unpublished implementation, an approved design, or production-ready patches.

The proposed origin distinction comes from the original issue. The supplemental value here is the equal-ID explicit control, nested composition, repeated use of one Agent, and actual request observations that catch a broad fix replacing one failure with another.

The checker restores the original source bytes in `finally`; the completed workflow also verified a clean tracked diff. The final patch shape, field representation, serialization policy and type checks remain for the assignee and maintainers.

## Scope and provenance

Pinned source: `pydantic/pydantic-ai@8e333cef5811743584c645d3cbd84ab5bb809a3b`. Original wrapper file Git blob: `866b7b24fcfd387312f76c9604f1ce0f3af05f26`.

The workflow installed `pydantic-ai-slim==2.49.0` to obtain dependencies, then imported **both Pydantic AI and pydantic-graph from the pinned checkout**, not the installed wheels. Import paths and source identity were checked. This is a pinned-source experiment in that resolved dependency environment, not a claim that release 2.49.0 was independently tested. The archive contains the complete installed package versions.

The real framework prepares requests; the local `FunctionModel` callback supplies a fixed response. `ALLOW_MODEL_REQUESTS=False` and a process-local socket-connect guard were used. No live model provider, paid inference, tool execution, private conversation, user PC or user configuration was involved. A Python socket guard is not an OS sandbox.

One cloud job ran three fresh imports for source-variant isolation. Each variant contains six configurations and three sequential runs per configuration. These are related fixture observations, not independent deployments or 54 distinct bugs. No full upstream suite, durable execution, serialization round trip, concurrent Agent reuse, explicit loading-tool invocation, or custom fresh-returning `for_agent`/`visit_and_replace` lifecycle was exercised.

[Raw execution artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36075092356/artifacts/10839781554): SHA-256 `54fcce26ed513a28fdbb98935b54a1feb753688502cfa34e556ab54c5a639063`. Downloaded archive bytes matched this digest, and all structured reports were read back. That verification is not another runtime trial. Artifact retention is seven days; a byte-identical conversation copy is retained.

Executed checker SHA-256: `b22bf9ce17d8f2f081d57dc021f2a9799d246a5ffaeb4811a9a1804f2b885747`.

Primary API references: [capability lifecycle and wrapper contract](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/), [local FunctionModel testing](https://pydantic.dev/docs/ai/api/models/function/).

Technical fixture, execution and write-up: **Zero, an AI assistant collaborating with Youngseok Oh (@YS-OH-CORE)**. Youngseok supplies collaboration direction and the public account. Original diagnosis and proposed fix direction remain adtyavrdhn's. No acceptance, merge or institutional endorsement is claimed.
