# Signal Note to Self: upstream handoff

**25 September 2026 KST | Youngseok Oh × Zero**

This is a handoff of **ren2140eth's implementation and 11 tests**, not a new competing implementation or PR. In [the issue discussion](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823646302), **Halldrix** reported a separate 62/62-test reproduction and volunteered to submit the patch; [ren2140eth agreed](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823724566). This folder preserves the tested inputs in Git rather than relying only on the seven-day Actions artifact. It does not establish that a PR has already been opened or merged.

## What to use

- [`recipient.original.patch`](recipient.original.patch): the posted diff from [comment 5823398598](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823398598), as captured in the earlier execution archive.
- [`recipient.header-corrected.patch`](recipient.header-corrected.patch): the same diff with **only the production-file `index` line corrected** to the actual full Git object IDs. Every hunk and the recipient's test file are unchanged. Both variants produced identical production and test bytes in fresh two-file scratch apply checks.
- [`handoff-manifest.json`](handoff-manifest.json): source links, roles, exact hashes, and the boundary between previous runtime evidence and this packaging check.
- [`HERMES_LICENSE`](HERMES_LICENSE): the original upstream MIT notice, retained unchanged. This handoff does not claim authorship of or relicense the recipient's contribution.

The original diff already applied normally. The header correction removes the previously reported identity ambiguity; it is not a functional bug fix or a new successful application experiment.

## Apply only to a disposable checkout

The tested base is `749220ef0007f8d87bd1531f1c24b0fe93816385`. Check the current checkout first; do not reset or overwrite an active installation to match it.

```sh
git rev-parse HEAD
git apply --check /absolute/path/to/recipient.header-corrected.patch
git apply /absolute/path/to/recipient.header-corrected.patch
git hash-object gateway/platforms/signal.py
git hash-object tests/gateway/test_signal_note_to_self.py
```

Expected resulting blobs:

```text
3fa045195ab48f1ed2fc4987f9164123a70afc9e  gateway/platforms/signal.py
43c75e4b59d5b9d9125c5672b9eb9ffec7bbe270  tests/gateway/test_signal_note_to_self.py
```

For a different base, review and rerun the relevant checks rather than treating these results as transferable. A user-facing documentation change explaining the default-on option and its Note-to-Self-only scope belongs in the eventual PR; none is silently bundled here.

## Existing execution evidence, not new counts

[Run 36069329777](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36069329777) ran the posted test file unchanged: 4 pass/7 fail on base, 11 pass on the received patch, and 8 pass/3 fail after deliberately substituting the incorrect `bool(...)` parser. Zero's separate 12-case harness changed from 8 pass/4 fail to 12 pass. [Full scope and first-attempt failure](../README.md) remain beside those results. The suites overlap; they are not 23 independent deployments.

The earlier Zero run used real YAML loading and the Signal adapter but mocked final dispatch/attachment collection, no live Signal transport, and `--noconftest` for the recipient tests. Halldrix's 62/62 is **his report**, not a new run here. This packaging step ran only Git apply and file-identity checks, not another Hermes test suite.

## Attribution and coordination

ren2140eth: request, local implementation, public diff and supplied tests. Halldrix: reported reproduction and permission to carry the upstream submission. Youngseok Oh: collaboration direction and public account. Zero: AI source guidance, supplemental checks, evidence verification and this handoff. Original upstream code keeps its existing authorship.

No maintainer approval, merge, release, or general production guarantee is claimed. No private messages, phone numbers, account configuration, notification-email tokens, or user PC files are included. The phone strings inside the tests are the contributor's synthetic fixtures.
