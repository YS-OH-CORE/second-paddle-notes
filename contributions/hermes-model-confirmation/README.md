# Review of model-switch confirmation replacement

AI-assisted review prepared with Zero (ChatGPT) for Youngseok Oh's project.
Target: NousResearch/hermes-agent PR22982, head
`addb69bc409dae7d1c0ae9f2dc571fd4a39d8fc8` in
MestreY0d4-Uninter/hermes-agent. This is a proposed-branch review, not a claim
that the behavior has shipped in a released Hermes version.

## Question

Does approval of a NEW single-line `/model` request accidentally route the
inline request attached to an OLDER pending confirmation in the same session?
The older confirmation is either superseded or deliberately expired through
the actual confirmation registry under a controlled clock.

The new test reuses the PR's own fixture. Gateway dispatch, model-command
handling and slash-confirm registration/resolution are real imported code.
Model resolution, warning policy, adapter sends, the storage facade and the
final agent are fixture doubles. No model, platform message or private user
session is used. Observing a payload at the fake agent boundary is not evidence
that a real downstream action executed.

## Execution and candidate

Run only against a clean disposable checkout of the pinned head:

```sh
python verify.py --upstream /path/to/disposable-checkout --out /path/to/new-results
```

The verifier runs the two new assertions on the original source, requiring
actual assertion failures rather than import errors. It then makes a narrow
candidate edit in that disposable checkout: discard a session's previous
inline payload before processing each new `/model` command. It reruns both
assertions and the PR's nine existing tests. It emits the exact candidate diff,
three XML reports and per-case routing observations. The candidate addresses
sequential replacement only; it is not a proof of concurrency-safe binding to
confirmation identity, persistence or all platform behavior.

The read-only public CI uses a pinned source and isolated dependencies. Check
the actual run and returned files: this document's presence does not establish
successful execution, maintainer agreement or an upstream merge. It creates no
periodic job, model API call, new account or user installation.

This contribution is separate from the earlier replay-classifier report and
from Process Receipt. It does not modify either existing deliverable. The
original Nous Research MIT notice is preserved in LICENSE.upstream; the review
code and candidate are offered under the same license.
