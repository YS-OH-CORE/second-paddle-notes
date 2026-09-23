# Turn ownership is not a display name or a cost total

23 September 2026 | Youngseok Oh (오영석) × Zero (ChatGPT)

A focused response to [Roy Tong's conformance question](https://github.com/openai/openai-agents-python/issues/5072#issuecomment-5738052880) under [kosesena's existing Realtime attribution report](https://github.com/openai/openai-agents-python/issues/5072). The original SDK bug and proposed fix belong to that report; no competing fix or new-bug claim is made here.

## Answer to the linked vector question

The three [DELEGATION-003 vectors at AgentMeasure commit 98a1189](https://github.com/roy-tong/AgentMeasure/blob/98a1189b2bc299f72eefc05997907dfc27491216/conformance/vectors/delegation-001-003.json) describe cost aggregation, double counting, and delegation lineage. They do not include the producing response's start/end ownership trace. Those examples alone therefore cannot distinguish a correct `agent_end(A)` from an incorrect `agent_end(B)` if their declared cost inputs stay the same.

This is an inspection of the pinned JSON examples, **not an execution or a finding against the complete AgentMeasure checker**. The vector file's Git blob was verified as `46ab9d5350635735b45827be312c3b0161ddcfca`.

My recommendation is a separate event-ownership/adapter case, upstream of cost aggregation: in a sequential response, the agent owning its start must own its end; a handoff changes who acts next, not who produced that response. Cost tests retain their distinct purpose. This recommendation is not a measured improvement to either project.

## Executed observation: equal names can mask the known defect

I ran the unmodified OpenAI Agents SDK at `32edd3c3ecde37a7fb6bf4b082f35f1d8f7f086b`, using the official `ScriptedRealtimeModel`, a real `RealtimeSession`, and its **public async event iterator**. No private event queue was read or changed. Each scenario contains two sequential response starts/ends; the first response either does or does not hand off from object A to object B.

| Scenario | Owner identity matches, first / second response | Display-name comparison matches, first / second |
|---|---|---|
| No-handoff control | True / True | True / True |
| Handoff, distinct names | False / True | False / True |
| Handoff, both named `worker` | False / True | **True / True** |

In the last case, the SDK accepted two distinct agent objects with the same display name and one unambiguous handoff tool. It emitted start(A), handoff(A→B), end(B), start(B), end(B). A name-only assertion passes despite the first end naming the wrong object. This is an additional **test-oracle counterexample for the already reported bug**, not a separate SDK defect or a claim that AgentMeasure currently compares names.

Within this in-process check, compare the actual `event.agent` objects with `is`. A serialized adapter needs stable agent-instance identity and response correlation, not Python memory addresses or display names. The A/B labels in this report are fixture labels derived from identity; they are not IDs emitted by the SDK. This pairing check is for sequential responses, not a proposed complete concurrent event correlator.

## Reproduction and result meaning

[Public completed execution](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35814346205) | [Pinned script](https://github.com/YS-OH-CORE/second-paddle-notes/blob/f8dec3d4fd6be609972c14241f41670198aef9db/checks/agents5072/check_turn_identity.py) | [Exact workflow](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1d1fd9ad461313c38e013717802e9bd015b3139e/.github/workflows/agents5072-identity-20260923.yml)

Run `35814346205`, job `107032551546`, on disposable Ubuntu with Python 3.12.3. The pinned checkout reports package version 0.22.3. Setup used its unchanged frozen lockfile through `uv==0.12.17`; the full resolved environment is logged. The script SHA-256 was checked before execution: `a43c3f37eb36f34414639c76a8426afd07aa9993ebfc92843f3ebd19c82a3615`.

The log's `ZERO_TURN_IDENTITY_RESULT` records `observations_confirmed=true`, `sdk_fixed=false`, `source_unchanged=true`, and `checkout_clean=true`. A green workflow means the stated bad behavior and the oracle distinction were successfully observed. **It does not mean the SDK is fixed or its full test suite passes.** All three scripted model sessions closed and detached their listeners.

Scope: synthetic normalized events, actual unmodified session/handoff logic and public event delivery. Not tested: real models, WebSockets, audio, provider event ordering, concurrent responses, billing or a complete AgentMeasure validator. Tracing was disabled; runtime socket connections were blocked in the Python fixture. Public source and dependency downloads occurred during setup. No user PC, secrets, new payment or scheduled monitoring was involved.

Observation script and analysis by Zero (ChatGPT) for Youngseok Oh / YS-OH-CORE. kosesena's original discovery, Roy Tong's vector work, and OpenAI's SDK/testing utilities remain their respective authors' work. No acknowledgment, adoption, or institutional endorsement is established by this note.
