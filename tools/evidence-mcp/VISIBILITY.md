# Copy fidelity and model visibility are different contracts

## Correction in distribution0.1.0a2

`result_text.py` is an opt-in local copy utility. Keeping its source metadata can be correct inside a trusted application. Our model-facing MCP wrapper used that complete copy as a nested JSON value, then serialized it into both `content` and `structuredContent`. With a synthetic marker at protocol `_meta`, the old wrapper returned that marker in ordinary output.

This is a boundary defect in our wrapper, not a claim that every MCP `_meta` value is inherently confidential or that actual user data leaked. For example, the [OpenAI plugin result contract](https://developers.openai.com/plugins/reference#tool-results) explicitly gives result `_meta` to the component while keeping it out of the model transcript. Generic MCP extension metadata is not by itself a universal confidentiality guarantee. A reusable model-view endpoint must not assume any complete host result can be stringified safely.

## Accepted input subset

Only `content`, `structuredContent`, and `isError` are accepted at the result-envelope level. Supported content kinds are text, image, audio, resource link and embedded resource, with their explicitly declared fields. Annotations accept audience, priority and lastModified. When audience is explicitly declared, it must include assistant for this model-facing endpoint.

| Rejected at protocol positions | Error code |
|---|---|
| `_meta` on result, content block or embedded resource | `HOST_METADATA_NOT_PROJECTABLE` |
| Undeclared result/block/annotation fields | `NON_CONTENT_FIELDS` |
| An explicit audience without assistant | `NON_MODEL_AUDIENCE` |
| A content kind not covered by this preview | `UNSUPPORTED_CONTENT_BLOCK` |

The endpoint returns `isError=true`, `status=not_assessed`, and a fixed code. Rejected values are not echoed. The original caller data is not changed and no silently redacted success view is substituted.

This is position-aware, not a word filter. A field called `_meta` inside explicitly selected application structured data, or the same characters quoted in text, remain data. Legitimate empty collections, false, zero, null and original error flags remain intact. Unknown future content types require a reviewed compatibility update, rather than implicit coercion.

## Inputs need their own boundary

**Choose model-visible inputs before exposing tool arguments.** Rejecting a tool result does not retract an input already sent to a model or logged by a host. Do not give this endpoint a private host envelope in the hope it can undo an earlier disclosure. Keep the complete original response in trusted host storage and construct the explicit model-view subset there. Do not parse and reserialize ambiguous raw JSON just to hide duplicate members; reject ambiguity at the original-input boundary first.

Nor does this code detect sensitive material deliberately placed inside ordinary text or structured data. It checks the declared transport positions and audience, not human meaning, consent or secrecy.

## Actual comparison and positive controls

Run34748252871 executed the installed public0.1.0a1 and the installed candidate0.1.0a2 via MCP stdio,12 synthetic cases per version. Six old outputs carried the synthetic marker: result `_meta`, block `_meta`, embedded-resource `_meta`, a top-level extra, user-only audience, and an annotation extra. All six new outputs were explicit unassessed errors without that marker. Six positive-control responses were identical across versions: ordinary result, ordinary `_meta` application key, quoted `_meta`, shared user/assistant audience, absent structure, and upstream error.

The original16 service test methods were unchanged; five additional methods cover position checks, content variants, source independence and positive controls. All21 passed. The old/new24-call comparison is separate from the reused five installed-command calls on each OS in run34748252840. Both Windows and Linux installed the same35,543-byte wheel, SHA256 `b801b9f2f8fe6973c980161d0ee2ff0241eada55b313c1b635a90d13eb6425ff`.

Actual returned archives were opened and checked: ZIP CRC, wheel RECORD16 entries, all8 bundle hashes, import origins, all24 input/response pairs, error flags, six unchanged controls and the two installation records. The standalone local helper and six of the eight bundled source/license files are unchanged; only wrapper service and tool description differ.

The initial CI attempt stopped before running this comparison: the server file committed without a final newline did not match a pin computed from the local newline-terminated copy. Full readback explained the byte difference, then the actual committed source and rebuilt wheel were pinned. Verification was not disabled and behavioral criteria were not relaxed. Failed run34748009784 remains available; successful executed source is fabb5375056dc51500183d3ec510aeb4ac94defb.

## Scope

No language model, confidential input, real account action or production incident was used. The test client's network guard observes that client; it is not a whole-machine egress sandbox. The original a1 release and file hashes remain historical evidence; installation of a2 must be explicit. [Release notes](../../releases/evidence-0.1.0a2/NOTES.md) record the correction; verify that publication completed rather than treating these notes as proof of a live release.

Prepared by Youngseok Oh with Zero (ChatGPT). Original source and license notices remain intact.
