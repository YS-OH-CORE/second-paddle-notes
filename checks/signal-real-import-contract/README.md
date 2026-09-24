# Signal notes stay notes: real-import checks of a received patch

Youngseok Oh × Zero | 25 September 2026 KST

## Source and authorship

This follows [Hermes #121970](https://github.com/NousResearch/hermes-agent/issues/121970). **ren2140eth** reported the use case, implemented the proposed option locally, reported their linked-device result, and then supplied [a code-only diff and 11 new tests](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823398598). They explicitly included the quoted-false and A/B/A cases suggested in our earlier review. The implementation and their test file remain their contribution.

Zero supplied the initial source guidance and the separate contract harness here, then applied and tested the exact publicly supplied diff in a fresh cloud environment. Youngseok Oh supplied the collaboration direction and public account. This is not solo human engineering work, maintainer approval, or an upstream release.

## Result from the exact received patch

[Completed execution: run 36069329777](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36069329777)

| Suite | Unmodified upstream | Exact received patch | Deliberately wrong boolean parser |
|---|---:|---:|---:|
| Recipient's 11 new tests, unchanged | 4 pass / 7 fail | **11 pass / 0 fail** | 8 pass / 3 fail |
| Zero's 12 real-import contract cases | 8 pass / 4 fail | **12 pass / 0 fail** | Not run |

The suites overlap and must not be added up as independent deployments or distinct new product fixes. The recipient also reported 62 passing tests when including the existing Signal suite; **we did not rerun that combined 62-test suite**.

The mutation replaces only `is_truthy_value(extra.get("note_to_self"), default=True)` with `bool(extra.get("note_to_self", True))`. The received tests then reject quoted `"false"`, quoted `'no'`, and the attachment-bearing self-message. This checks that those tests notice the specific incorrect parser, not just that the intended candidate is green.

On unmodified upstream, five parsing assertions and the recipient's A/B/A assertion encounter the missing `note_to_self` attribute; the attachment test detects actual unwanted dispatch. Those are feature-baseline failures, not seven separate defects. Zero's complementary behavior checks independently observe the unwanted dispatches and `[1, 1, 1]` A/B/A sequence without depending on that new attribute.

## What actually ran

Both stages use ordinary imports of the pinned source tree: real `load_gateway_config()`, real `SignalAdapter`, and real `_handle_envelope`. YAML files are written to fresh temporary homes and read by the real loader. We do not extract these functions with AST or replace the configuration loader.

The final message-dispatch callback and attachment collector are observed with test doubles. No model turn, gateway-runner authorization decision, Signal connection, real account, real message, attachment download, or delivered response is tested. A Python socket guard blocks connect calls in the test processes; it is not an OS network sandbox. Setup downloads public code and dependencies.

Zero's harness covers: unset/true compatibility, boolean false, quoted false, rejection before attachment fetching, groups with a self destination, allowed/disallowed groups, mention-required cases, outbound echoes, unrelated outbound destinations, and sequential A(false) → B(default) → A(false) home loads. On the received patch that last sequence dispatches **0, 1, 0** messages.

Zero's A/B/A uses the real context-local home override API; the recipient's A/B/A changes `HERMES_HOME` and constructs a fresh adapter in sequence. Neither is a concurrent multiplexed-profile or full profile-selector test. In Zero's mention cases, `require_mention` is assigned to the adapter for the control; mention-setting YAML propagation is outside this check.

The received test file was run with `--noconftest`, explicit pytest-asyncio, plugin autoload disabled, fresh HOME/HERMES_HOME and placeholder Signal variables. Its test functions were not edited. This excludes upstream global conftest fixtures and therefore is not the upstream suite invocation or full CI environment.

Environment: Ubuntu 24.04 runner, Python 3.12.3, PyYAML 6.0.3, httpx 0.28.1, pydantic 2.13.4, pytest 8.4.2 and pytest-asyncio 1.2.0. Selected dependencies came from the pinned pyproject; transitive versions were resolved at run time and recorded, not installed from a complete lockfile. Both base and candidate log an optional Slack-plugin import warning because `aiohttp` is not installed. Signal's tested path ran, but this is not a warning-free/full Hermes installation.

## Exact identities and a patch-header discrepancy

Upstream commit: `749220ef0007f8d87bd1531f1c24b0fe93816385`.

| Input | Identity |
|---|---|
| Original `gateway/platforms/signal.py` Git blob | `f763db86f71d50a922d23b4f324da92ff6f5683e` |
| Applied received production file, actual Git blob | `3fa045195ab48f1ed2fc4987f9164123a70afc9e` |
| Received new test file, Git blob | `43c75e4b59d5b9d9125c5672b9eb9ffec7bbe270` |
| Received test file, SHA-256 | `896701ff2436e953fa54eddac483cf430dd8541080bb587f0795ecb27ea97962` |
| Exact comment body, SHA-256 | `e5692e443a8cf8f66596065f62166f39d4d07e3758ad25ead1b13adfd6e95cfb` |
| Extracted diff, SHA-256 | `cf65741f1f02f8703898229c98c3da4b53a6d97d96fac4987864c9d427f4aa20` |

The comment's production diff header advertises `ac5b0b8465`, which does **not** match the resulting file above. The test-file header does match. Our [first exact-patch attempt](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36069060300) stopped at that identity assertion after `git apply --check` and `git apply` succeeded; it ran no runtime tests.

The successful follow-up did not merely suppress source checking. It pinned the entire comment and patch by SHA-256, restricted the diff to the two reviewed files, checked the full test-file blob, and verified that the applied production bytes equal precisely the three reviewed edits to the pinned base. It retains the advertised-header mismatch in `source_identity.json` and `summary.json`. Thus the result is about the **posted patch bytes**, not proof of identity with an unseen local file. The reason for the header discrepancy remains unknown.

## Reproduction and original output

[Exact verification workflow](https://github.com/YS-OH-CORE/second-paddle-notes/blob/0b416e97b5e4cf66973f46b262584a7fa717eae1/.github/workflows/signal-exact-recipient-20260925.yml) · [contract harness](https://github.com/YS-OH-CORE/second-paddle-notes/blob/fee8097bda33771c1f5ed0ec5b2c7a228ace3404/checks/signal-real-import-contract/check_signal_contract.py)

Use a disposable checkout and fresh environment, not an active Hermes installation: the comparison temporarily replaces the scratch production file and restores it afterward. The workflow records the received diff, unchanged test file, applied source, environment, JUnit XML, individual outcomes and setup log. The downloaded archive's SHA-256 was checked against GitHub's digest; reading it back is evidence verification, not an additional runtime experiment.

[Exact-patch raw artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36069329777/artifacts/10837676506), SHA-256 `28f9f8a081f2ebc8bc9645cd8f6cd1a7c0ca4a0b433b8eef256e753126f9e9c8`.

Before the diff arrived, a [separate initial run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36068670149) tested our reconstruction of the public snippets. Its initializer insertion location differs from the received patch. That result is not substituted for the exact-patch result above. Initial-run archive SHA-256: `124cf3bff7453177585e1af01c2ad50e43f6b1d9b873986a0371394b6e97bc54`.

Failed identity-check archive SHA-256: `7e99b1fbaf9cdd0d4acc11adadf31626adf018655e1a90158e7322856a491cb0`.

GitHub artifacts have seven-day retention. Author-side byte-identical copies were downloaded. All source mutations were confined to fresh cloud checkouts and restored; no user PC, service, private history, credential, or Signal account was accessed for these tests. No competing upstream PR is created by this review. Public feedback and runtime results do not by themselves establish merge, deployment, or endorsement.
