# Evidence Tools 0.1.0a2: keep the model-view boundary explicit

Packaged source tested at `fabb5375056dc51500183d3ec510aeb4ac94defb`; bundled wrapper source at `e40eba4b7b985c716644ec736ac72288f8e6cdd7`. These identifiers distinguish the executed code from later publication-only changes.

This release corrects **our MCP wrapper**. In 0.1.0a1, the local-copy helper's retained result metadata could be serialized into the wrapper's ordinary text/structured output. Version0.1.0a2 rejects protocol-position `_meta`, unselected envelope/block fields and explicitly non-assistant audiences with fixed error codes. It does not silently delete those fields from your original data.

The local helper still preserves source copies inside a trusted application. Its behavior is unchanged. Ordinary `_meta` keys inside already-selected `structuredContent` or quoted text remain ordinary data, not a reason to erase content.

**Select the model-visible input before invoking this tool.** An output rejection cannot undo information already exposed in a model prompt, tool argument or log. This is not a general secret classifier, nor evidence that actual private data was exposed in a production installation.

## Install the correction

The tested installation combination is Python3.12 and Node.js22 on Windows/Linux. The package declares Python>=3.10, separately installed Node>=22, and `mcp==2.2.0`. Other combinations were not covered by these install runs.

```sh
python -m venv .venv
.venv/bin/python -m pip install "https://github.com/YS-OH-CORE/second-paddle-notes/releases/download/evidence-v0.1.0a2/second_paddle_evidence-0.1.0a2-py3-none-any.whl#sha256=b801b9f2f8fe6973c980161d0ee2ff0241eada55b313c1b635a90d13eb6425ff"
.venv/bin/python -m second_paddle_evidence --check
```

On Windows use `.venv\Scripts\python.exe`. Use the printed interpreter/arguments in the host you explicitly choose. No application configuration is edited. This is an opt-in stdio tool, not a chat model, hosted service or scheduler.

## Executed evidence

[Visibility run34748252871](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34748252871) called separately installed a1 and a2 through actual MCP stdio. Across12 cases per version, six synthetic restricted-field cases appeared in the old output and none appeared in the new output. The six allowed-data controls had identical responses, including ordinary quoted/structured keys, absence, and the error flag. All original16 service tests plus five new boundary-test methods passed.

[Windows/Linux install run34748252840](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34748252840) installed the exact new wheel into fresh environments and reused the original five synthetic calls per OS. Both produced the same35,543-byte wheel and verified installed entry points, dependency consistency and missing-Node diagnostics. These cases were not chosen by a language model.

The attached wheel is copied from the inspected execution artifacts, not rebuilt for publication. Three original ZIPs retain the comparison and OS-install records; provenance and SHA256SUMS connect them. The earlier preparation failure was a mismatched source pin caused by a final-newline difference, not an observed behavioral test failure; source identity checks remained enabled after the discrepancy was explained.

[Detailed contract and observed limits](https://github.com/YS-OH-CORE/second-paddle-notes/blob/main/tools/evidence-mcp/VISIBILITY.md) · [PR31](https://github.com/YS-OH-CORE/second-paddle-notes/pull/31).

Old release assets remain unchanged for auditability. Upgrade deliberately; old downloads and existing installations do not update themselves. Release availability remains subject to repository/account availability. No real private input, provider request, external user adoption or independent certification is claimed. Prepared by Youngseok Oh with Zero (ChatGPT).
