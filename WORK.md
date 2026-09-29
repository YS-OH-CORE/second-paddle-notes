# Youngseok Oh (오영석) × Zero

## Selected work: agent reliability and evaluation review with traceable results

[External recognition & adoption](recognition/README.md) · [외부 반응·채택 기록](recognition/README.ko.md)

Human–AI collaboration on reproducible failures, regression tests, reviewable fixes, and evaluation reporting. This page presents externally acknowledged contributions, with the original evidence and material corrections beside each claim.

**한국어 소개는 아래에 있습니다.**

**Evidence at a glance:** [Case 01: request-bound approvals](#case-01--keeping-an-approval-attached-to-its-own-request) · [Case 02: explicit stop handling and an E2E correction](#case-02--explicit-stop-handling-and-an-end-to-end-correction) · [Case 03: adopted TAM evaluation-report review](#case-03--checking-the-numbers-and-narrowing-the-claim) · [Case 04: recipient-confirmed Signal source review](#case-04--keeping-personal-notes-separate-from-agent-prompts) · [Case 05: adopted real-HTTP regression](#case-05--proving-http-recovery-through-the-real-transport) · [Case 06: explicit deletion failure](#case-06--keeping-unsupported-deletion-from-reporting-success) | [Case 07: adopted MCP timeout correction](#case-07--closing-a-connection-that-arrives-after-its-deadline)

## Case 01 | Keeping an approval attached to its own request

**Project:** Hermes Agent, proposed multiline model-command feature  
**Contribution:** request-binding review, reproducible cases, regression tests, and a production patch  
**Evidence checked:** 2026-09-12

**Outcome:** the feature's PR author applied the contributed patch and binding tests to their branch and credited **@YS-OH-CORE** in the commit. At this check, the upstream PR remained open and unmerged. [Author's confirmation][ack] · [Crediting commit][commit] · [Current PR][pr]

> “thanks @YS-OH-CORE for the exemplary review”
>
> MestreY0d4-Uninter, author of the proposed feature, in the [public implementation follow-up][ack]. This is an excerpt about this contribution, not an institutional endorsement.

### The problem

A user could request a model switch with a task attached, leave its approval pending, then request a different model switch. The old task was kept in a conversation-level slot. A later approval could consume that older task instead of only the request associated with the new approval. The [implementation commit][commit] describes this failure and the repair.

The important question was not merely whether the user had clicked “approve.” It was **which request that approval belonged to**, including when messages or callbacks arrived late.

### What the collaboration contributed

The [submitted patch and design][design] bind a fresh request-local token before the confirmation is shown. A callback can consume its own token, rather than whichever text happens to occupy the conversation slot later. Replaced or revoked callbacks cannot consume a successor's payload. The dispatcher also stops restaging old payloads after delayed presentation.

The accompanying [regression tests][tests] cover late presentation, fast approval, help while a request is pending, a failed replacement proposal, boundary revocation, and preservation of the supplied request's whitespace. These exercise real dispatch/confirmation code with controlled transport and model fixtures.

**Roles:** this contribution was prepared under **Youngseok Oh's @YS-OH-CORE account with Zero (ChatGPT)**. MestreY0d4-Uninter authored the original feature, integrated the repair, and reported a separate local re-test. Hermes project maintainers decide upstream review and merge. [Contribution design][design] · [Commit attribution][commit]

### What the recipient checked

The following counts are **the PR author's local re-test report**, not a new test run performed while writing this page. The parenthetical detail in the [original English reply][ack] specifies eight failures out of ten binding cases:

| Selected checks | Before the binding patch | After the binding patch |
|---|---:|---:|
| Ten added binding cases | 8 failed, 2 passed | 10 passed |
| Fifteen existing model-command checks | Not reported as a new baseline here | 15 passed, unchanged |

The author also reports unrelated or pre-existing full-suite failures. These selected results should not be described as an entirely passing application suite or a production error rate. The tests use controlled fixtures, not a live user's conversation. [Original report][ack] · [Adopted test file][adopted-tests]

### Check the contribution without taking this page on trust

**1. Read the recipient's acknowledgment.** It identifies the two contributed files, the SHA-256 check they performed, and their local test results. [Open the reply][ack]

**2. Read the applied commit.** It credits @YS-OH-CORE and shows the two production-module changes and added test file. [Open commit 501be10c][commit]

**3. Compare the test's identity.** The previously submitted file and the file at that adopted commit both return Git blob **`98ec718af91f6ac5fc7cb4470f95dba56f858e30`**. This identifies the same Git file content, separately from the author's reported execution results. [Submitted test][tests] · [Adopted test][adopted-tests] · [Machine-readable source record](work/approval-binding.evidence.json)

This case documents **external contributor use and credit at the PR-branch stage**. It does not establish a merged release, paid engagement, or a blanket endorsement of other work. The date above is a snapshot; use the linked PR for later status.

### Follow-through | 21 September 2026

**Continued use after integration.** The PR author [reported applying our port guidance][port-followup] at head `8c0090dc9a`. During that port, the contributed binding tests exposed an interaction between newer switch locking and delayed confirmation display. The author separated confirmation registration from display and repaired the test environment. Those additional integration fixes and the reported validation are the author's work.

The [binding-test file at that head][current-binding-tests] still has Git blob `98ec718af91f6ac5fc7cb4470f95dba56f858e30`, matching the earlier adopted file. This is a checked file-identity link, not a new execution of the tests for this page.

**A separate finding remains under review.** Our [21 September follow-up][late-decline-review] supplies a controlled source-extraction reproducer and an atomic, request-ID-scoped cleanup candidate for a late declined prompt that can remove a newer confirmation. It is a submitted technical finding, not an adopted repair. Full gateway integration and reachability under the real connector's transport contract remain to be checked.

**Status at this check:** PR #22982 is open and unmerged at the head above. The recipient explicitly leaves live Slack field validation outstanding. The original contribution, the recipient's later fixes, and the unconfirmed follow-up are separate evidence, not a single completed deployment.

## Case 02 | Explicit stop handling and an end-to-end correction

**Project:** Hermes Agent PR #84236  
**Contribution:** a reproduced finalizer edge case, regression cases, a narrow condition change, and a public correction to a call-path inference  
**Evidence checked:** 2026-09-23

**Outcome:** the PR author applied the proposed condition in [commit e99497e][stop-commit], whose message explicitly credits the **YS-OH-CORE review**. An explicit `user_stop` carrying a diagnostic message now keeps the visible stop fallback instead of being mistaken for a new-message redirect. The author added a five-case finalizer regression. This is verified code incorporation on the author's PR branch; [the PR][stop-pr] was open and unmerged at this check.

**Material correction, not omitted from the case:** our [original review][stop-review] reproduced the condition with the production finalizer and upstream unit fixtures. We also cited a CLI call site as motivation, while explicitly leaving end-to-end testing unperformed. The author's [real CLI comparison with a mock model endpoint][stop-response] showed no visible improvement on the cited single-query SIGINT path. His [subsequent mechanism correction][stop-topology] clarified that the main thread's wait unwinds while the turn runs on a worker abandoned during process teardown; `run_conversation` itself is not unwound by that main-thread exception. The quiet exception path prints no turn result. Our finalizer condition therefore does **not** fix that CLI no-feedback symptom. We [published the first correction][stop-correction] and [accepted the refined topology][cli-followup]. The absent log line is not, by itself, proof of the whole worker lifecycle.

The same recipient follow-up identifies and fixes a different live-signal omission: `stop_kind="user_stop"` is now stamped while the turn is still alive. That finding, its integration, and the reported 129-test run belong to **Halldrix**. They were not independently rerun for this case page. The adopted condition, the recipient's additional repair, and the unresolved CLI path are distinct results, not a single claim of end-to-end resolution.

**Separate tested option, not adopted work:** using Halldrix's pinned mock-server function, Zero ran a [four-process real-CLI comparison][cli-run] and submitted a narrow exception-path candidate. It added one interruption notice on stderr, retained exit 130 and preserved stdout in that text-mode fixture. It did not prove worker finalization or tool cleanup. The initial checker's failure and remaining untested paths are [preserved with the reproduction][cli-details]. Submission is not evidence of upstream acceptance. [Worked example and reusable review template](notes/12-from-prompt-to-world.md#engineering-case-a-passing-unit-test-is-not-a-fixed-workflow).

**Human–AI roles:** Youngseok Oh sets the collaboration's problem direction and priorities. Zero (ChatGPT) supplied substantial analysis, regression authoring, execution orchestration, and review drafting. Halldrix authored the feature, integrated the condition, performed the end-to-end comparison, and supplied the correction. This is a documented collaboration, not a claim of solo human engineering credentials, research accreditation, or institutional endorsement.

**Inspect the chain:** [Original review and execution evidence][stop-review] → [Recipient's result and counterevidence][stop-response] → [Crediting code change][stop-commit] → [Our public correction][stop-correction] → [Corrected thread explanation][stop-topology] → [Separate tested CLI candidate][cli-followup].

## Case 03 | Checking the numbers and narrowing the claim

**Project:** Total Agent Memory (TAM), LongMemEval evaluation report  
**Contribution:** saved-verdict recalculation and reporting feedback  
**Evidence checked:** 2026-09-24

**Outcome:** TAM's author incorporated the reporting changes and then added explicit credit to **Youngseok Oh (@YS-OH-CORE)** and **Zero (ChatGPT)** in the project's published report. These are changes in TAM's own report, not a pending patch in our repository. [Reporting revision][tam-revision] · [Attribution commit][tam-credit] · [Pinned report and scope][tam-report]

### What changed

The [public review invitation][tam-request] asked for a second pair of eyes before the results were quoted. Our [executed check][tam-run] recomputed six accuracy cells and four paired comparisons from 400 saved question-level verdicts. All checked counts, differences and exact sign-test p-values agreed with the published summary. The code and input identities are preserved in the [bounded calculation script][tam-script]. This is a saved-record check, not fresh judgments of whether the answers were correct.

The report's introduction described one judge model and two prompts, while its LongMemEval metadata changed both model and rubric. The feedback distinguished a valid paired comparison **within** each grading configuration from an across-configuration change that cannot isolate a prompt effect. It also distinguished failure to detect a difference from demonstrated equivalence.

The author's [revision][tam-revision] clarified those claims and published exact split lists, per-type denominators, tuning history, and the ingestion/context conditions. No score changed. The newly disclosed history says the reported split had been scored before the final configuration was frozen; we read that disclosure but did not independently audit the tuning process.

### Roles and limits

The [recipient's public credit][tam-credit] explicitly identifies the substantial AI technical assistance. Youngseok Oh supplied the collaboration's direction and public account; Zero supplied technical analysis, code, execution and drafting. Vitalii Cherepanov authored the TAM method and experiments and implemented the revisions. LongMemEval and the compared methods retain their respective authorship.

This contribution does not certify retrieval, answer generation, fresh judge decisions, tuning independence, overall system quality or institutional endorsement. It does not establish an external replication of our own memory pilot. The evidence for this case is public repository history, not private correspondence. No additional model run was performed to add this case page.

**Inspect the chain:** [Public review request][tam-request] → [Saved-verdict calculation][tam-run] → [Author's reporting revision][tam-revision] → [Named human–AI attribution][tam-credit].

## Case 04 | Keeping personal notes separate from agent prompts

**Project:** Hermes Agent, Signal Note to Self configuration request  
**Contribution:** source-level implementation guidance and validation plan  
**Evidence checked:** 2026-09-25  
**Evidence class:** recipient-confirmed source review and reported live use; supplemental synthetic checks; upstream PR opened (not merged at the latest snapshot below)

**Outcome:** requester **ren2140eth** publicly named **@YS-OH-CORE**, corrected the helper name in their follow-up, and reported checking the guidance against `749220ef`. They confirmed the existing YAML-to-adapter route and boolean parser, and said the required change was smaller than the original request suggested. [Our source review][signal-review] · [Recipient's verification][signal-ack]

The request was to keep Signal's personal notepad from triggering the agent while retaining an authorized group conversation on the same account. The review located the existing configuration path, distinguished a false boolean/string from Python's truthy non-empty string, and proposed gating non-group self-messages without removing group policy or outbound-echo filtering. It also described an integration-test plan; those tests were **not executed as part of this source review**.

**Initial source-review roles and limits:** ren2140eth reported the use case, proposed the setting, and checked the guidance. Youngseok Oh set the collaboration direction; Zero, an AI assistant using ChatGPT, traced the public source and drafted the review. The evidence is the requester's public response, not a private testimonial. That initial source review did not establish a shipped option, a runtime-tested patch, a maintainer decision, or a repaired Signal account. No new code execution or recipient endorsement is implied by adding this case page.

**Inspect the chain:** [Original request][signal-request] → [Source-level guidance][signal-review] → [Named verification and reduced implementation scope][signal-ack].

### Follow-through | Recipient-reported local runtime use

In a [further public report][signal-runtime] at 2026-09-24 22:17:16 UTC (25 September KST), **ren2140eth** said they implemented the suggested shape against `749220ef` and exercised it with a linked secondary Signal device. They reported that self-messages were dropped before attachment fetching and dispatch, group sync-sents still reached the existing group/mention checks, and unset/true settings retained the previous behavior. They also reported retaining outbound-echo filtering.

This advances the record from source confirmation to **recipient-reported local implementation and runtime use**. The implementation and runtime validation are the recipient's work. Zero has not independently rerun that installation; the public report supplies snippets, not a complete checked diff or retained test artifacts. The recipient had not opened a PR when reporting. Upstream acceptance and release remain unestablished.

Our [follow-up][signal-runtime-followup] asks for the code-only diff, including its import change, and any retained synthetic fixtures so another contributor can work from the exact change. Quoted-false parsing and A(false) → B(default) → A(false) profile tests remain suggested coverage, not tests executed for this page. No competing PR or new product experiment was created by this update.

### Follow-through | Upstream PR #122033 (25 September 2026)

**The upstream submission now exists.** [Halldrix opened PR #122033](https://github.com/NousResearch/hermes-agent/pull/122033) with ren2140eth's permission, carrying the implementation and initial fixtures, adding user documentation and extending group-related coverage. At the current snapshot its head is `bb8f14060ae63968c5d34ca5024dbce7fea93001`; it is open and unmerged. The PR's 64-test result is Halldrix's report, not a new execution by Zero.

Between the earlier snippets-only report and this submission, the [exact posted patch was supplied and exercised in a separate synthetic environment](https://github.com/YS-OH-CORE/second-paddle-notes/blob/81d44747528ebb9e7154914ae1bde197d9c2a730/checks/signal-real-import-contract/README.md). That checks real YAML/adapter code with test doubles, not the recipient's live Signal installation. Its [original successful and stopped attempts are preserved](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/peer-review-evidence-20260925-v1).

The current PR's entire `gateway/platforms/signal.py` has Git blob `3fa045195ab48f1ed2fc4987f9164123a70afc9e`, matching the file inside that previously executed archive. Zero rechecked the archive bytes and the current source identity, reviewed the three-file diff, and submitted a [commit-pinned COMMENT review](https://github.com/NousResearch/hermes-agent/pull/122033#pullrequestreview-5312419768) connecting the existing evidence to the PR. File identity does not rerun the new base, its changed tests or dependencies, and COMMENT is not a merge approval.

**Roles and status:** ren2140eth authored the implementation and initial tests; Halldrix carried the upstream integration, documentation and added coverage; Zero supplied source guidance, supplemental verification and evidence handoff; Youngseok Oh supplied collaboration direction and the public account. This remains the same Case 04, not another independent success. No official merge, release, or new recipient endorsement is established by this update. Earlier paragraphs record their earlier stages rather than the current handoff state.

## Case 05 | Proving HTTP recovery through the real transport

**Project:** Hermes Agent PR #121944  
**Contribution:** real-loopback regression tests and matched execution evidence  
**Evidence checked:** 2026-09-28

**Outcome:** PR author **liuhao1024** [reported applying the test-only contribution][http503-ack]. The [recipient's commit][http503-adopted] adds the unchanged 159-line test file and a **YS-OH-CORE co-author trailer**. The PR is open and unmerged at that commit; incorporation into the author's PR branch is directly verified.

The original issue concerns a temporary HTTP 503 during tool discovery being mistaken for a reason to switch to legacy SSE. The supplemental tests run the actual MCP SDK, Hermes's HTTP response recorder, and its normal initial-connect retry. One fixture requires a second Streamable HTTP attempt and a successful tool call without an SSE GET; a genuine HTTP 405 control must still complete the legacy-SSE route. [Original report and implementation][http503-pr] · [Executed test and method][http503-report]

The [submitted commit][http503-submitted] and [recipient commit][http503-adopted] share parent `dad46f0` and complete Git tree `5555c02bb0e37b3b9721557f2bac4558b0a94728`. Their added test has the identical blob **`b36e7271a7519fa37a86bbbed813017b6f477624`**. The recipient recorded themselves as Git author and committer and credited **YS-OH-CORE** as co-author. [Exact source and attribution record](work/hermes-http503.evidence.json)

Our retained comparison of the original product PR's parent `749220ef` and fix head `dad46f0` used the same frozen dependency environment. The baseline `749220ef` failed the 503 test and passed the SSE control; the candidate's four-file run passed 41 tests in total, including both new cases. A separately inspected main also exposed the unwanted GET. The recipient subsequently reported **43/43** passing in their environment. The original **41/41** log and that **43/43** report remain separate; their count difference has not been reconciled. This page update checked source identity and attribution without running new tests. The [execution record][http503-report] retains environment differences, development corrections, and the limits of its synthetic loopback fixtures.

**Roles:** **fmunechi** supplied the original bug report, reproduction and proposed guard. **liuhao1024** authored the product repair and integrated the supplemental tests. **Youngseok Oh** supplied the collaboration direction and public account; **Zero (ChatGPT)** supplied the additional test design, execution, and review. The verified result is an adopted test contribution with public credit at the PR-branch stage. Maintainer acceptance, release, and live-service behavior remain unestablished.

## Case 06 | Keeping unsupported deletion from reporting success

**Project:** Mem0, issue #7439 and the contributor's follow-up fork  
**Contribution:** a counterexample with stored records and verification of the contributor's revised tests  
**Evidence checked:** 2026-09-29 (KST)

**Outcome:** contributor **Souptik96** [credited our check][mem0-ack] and changed their implementation and regression coverage. The revised code is present in [fork commit `127bb797`][mem0-revised]. This establishes incorporation by the recipient into their own fork. The related [PR #7464][mem0-pr] is closed and unmerged, and its recorded head is the older `cec74a8e`; it does not contain the verified follow-up revision in its recorded head.

Our [earlier check][mem0-review] used a real FAISS store with matching records. Returning an invented empty listing made `delete_all()` report success while the requested records remained. Souptik96 replaced that fallback with `NotImplementedError` for unsupported clients, propagated Chroma listing errors, and added a regression with actual FAISS records. The correction makes unsupported operations fail explicitly; it does not implement bulk deletion.

The [preserved comparison][mem0-report] used seven unchanged tests from the contributor's revised fork:

| Adapter used with the same seven tests | Passed | Failed | Errors / skips |
|---|---:|---:|---:|
| Revised fork `127bb797` | 7 | 0 | 0 / 0 |
| Only the adapter replaced by its earlier `cec74a8e` version | 1 | 6 | 0 / 0 |

The empty Chroma fixture passed in both conditions. The populated FAISS test required explicit errors and retention of its three Alice labels and one Bob label. The fixture checks retained labels; it does not audit the complete document contents and IDs.

For this page, the original JUnit reports, logs, archive checksum and source blobs were rechecked without running new tests. The selected checks use real Memory/adapter imports and offline FAISS, alongside existing dependency/history mocks, mocked Chroma and `--noconftest`. Dependency installation used version ranges. These results do not establish a passing full suite, live-provider behavior or a newly implemented deletion capability. [Exact evidence record](work/mem0-nonempty-delete.evidence.json)

**Roles:** **BlueX888** reported the original fall-through defect. **Souptik96** authored the revised implementation and tests. **Youngseok Oh** supplied the collaboration direction and public account; **Zero (ChatGPT)** supplied the counterexample, execution and review. The [project's requirement for an accepted issue][mem0-gate] remains outstanding; maintainer acceptance, merge and release are not established. Original code and test licensing stays with those files.

## Case 07 | Closing a connection that arrives after its deadline

**Project:** Model Context Protocol conformance, PR #533  
**Contribution:** a late-handshake counterexample, a runner correction, and one real-HTTP regression  
**Evidence checked:** 2026-09-29 (KST)

**Outcome:** PR author **aton-of-data** [confirmed integrating our commit under its existing authorship][mcp533-ack]. The author's current PR branch points to [the exact submitted commit `95dd2e2`][mcp533-received], credited to **Youngseok Oh / @YS-OH-CORE**. At this check, the [official PR][mcp533-pr] remains open and unmerged. This is confirmed incorporation into the submitting author's branch, not an official project merge or release.

### The missing boundary

The original PR closes sessions left open when a conformance scenario fails or times out. Our addition covers a connection whose SDK setup finishes **after** that timeout. A session can already exist on the server while the client is still waiting for the `notifications/initialized` acknowledgment. The cleanup sweep then has no returned connection to close. Once setup completes, the abandoned scenario can receive that connection and leave a session occupying the server's capacity.

The contributed change records that the scenario finished, checks this before and after connection setup, and closes a late returned connection before handing it to the abandoned scenario. It preserves the author's original tracking and three tests. The commit changes the runner by **15 added / 5 removed lines** and adds one **166-line** regression using the real runner and SDK with a synthetic capacity-one HTTP server. [Submitted correction][mcp533-submitted] · [Test at the recipient's commit][mcp533-test]

### Recipient verification and source identity

In the [public response][mcp533-ack], aton-of-data reports their own clean-checkout run with Node 22.22.2: `npm run check` passes and `npm test` records **626 passed across 48 files**. They also report that the identical contributed regression fails on their original `a95deff` head, with a leaked session, an abandoned probe and a failed healthy successor; it passes with `95dd2e2`. Their eight pre-existing runner tests still pass.

These are **the recipient's reported re-executions**, not new runs performed for this case page or a claim that their machine's full logs were independently audited. The recipient explicitly did not rerun our separate 94-assertion TypeScript/Go capacity matrix or our fork CI. Those older executions remain linked in [the original handoff][mcp533-handoff] and [reproduction record][mcp533-evidence], rather than being counted as fresh recipient results.

We verified the recipient branch's exact commit, parent, Git author and complete source-tree identity against our submitted commit. The adopted regression has Git blob `74943a4dcc926d702251abf1882f615087d9bf58`; the complete tree is `ebdb44df64e66dbf9b2060c8137e4ca360e560ee`. These are source-identity checks, not new test execution. [Machine-readable evidence](work/mcp-late-session-adoption.evidence.json)

**Roles and limits:** Youngseok Oh sets the collaboration's direction and provides the public account; Zero supplies substantial technical analysis, implementation, testing and drafting. aton-of-data authored the initial cleanup and three tests, incorporated the follow-up and reported their separate checks. A bootstrap that never resolves is not cancelled by this correction. Five scenarios bypassing `ctx.connect` remain outside its scope; routing them through the factory can change transport selection by protocol version and is a separate decision. The official maintainers retain the merge decision.

**Inspect the chain:** [Submitted code and tests][mcp533-submitted] → [Recipient's verification and credit][mcp533-ack] → [Identical commit on the recipient's branch][mcp533-received] → [Current official PR status][mcp533-pr].

## A useful starting point for collaboration

A good first case is a public, reproducible agent behavior that differs from the user's actual request, or a published evaluation claim with question-level results that can be checked. Provide the exact revision, a small synthetic example or public result file, the expected behavior or claim, and the observed result. That makes it possible to choose a reproduction, regression test, narrow patch, or saved-result audit.

[Open a public issue](https://github.com/YS-OH-CORE/second-paddle-notes/issues/new) · [Contribution guidelines](CONTRIBUTING.md) · [Authorship and existing contact](AUTHORSHIP.md)

Keep credentials, private conversations, and personal records out of public issues. An inquiry starts a scope discussion; it is not a commitment to paid work or a delivery deadline.

---

## 한국어 | 실제로 사용되고 이름이 남은 기여

**영석(Youngseok Oh)과 제로의 인간–AI 협업 사례**입니다. 이상 동작을 설명하는 데서 끝내지 않고, 재현 사례와 검사, 검토 가능한 수정안으로 연결한 과정을 보여 줍니다.

### 무엇을 고쳤는가

헤르메스의 개발 중인 모델 변경 기능에서, 새 요청을 승인했는데 이전 요청에 붙어 있던 작업이 따라갈 수 있었습니다. 요청이 대화방의 공용 보관함에만 연결돼 있어, 늦게 처리된 승인이 엉뚱한 내용을 꺼내는 문제였습니다. 수정은 승인을 더 받는 방식이 아니라, **각 승인과 그 승인에 해당하는 요청을 정확히 묶는 방식**입니다. [적용 커밋][commit]

### 어떤 기여가 돌아왔는가

영석의 **@YS-OH-CORE** 계정에서 제로와 함께 재현 방법·검사·패치를 제공했습니다. 원래 기능의 개발자 MestreY0d4-Uninter는 이를 자기 작업 브랜치에 적용했다고 밝히고, 공개 답변과 커밋 메시지에 기여를 명시했습니다. 원래 기능의 개발·통합과 보고된 로컬 재시험은 그 개발자의 작업입니다. [개발자의 답변][ack] · [커밋의 기여 표시][commit]

개발자의 원문 보고에 따르면 추가 검사 10개 중 수정 전에는 8개가 실패하고 2개가 통과했으며, 수정 후에는 10개가 모두 통과했습니다. 기존 모델 명령 검사 15개도 그대로 통과했다고 보고했습니다. 이 수치는 상대가 보고한 재시험 결과이고, 이번 소개글 작성 중 새로 실행한 시험 수치가 아닙니다. 원문의 전체 검사 관련 설명도 함께 연결했습니다. [원문 결과][ack]

**직접 확인한 코드 흔적도 있습니다.** 우리가 제출한 검사 파일과 상대가 적용한 검사 파일의 Git 식별값이 같았습니다. 감사 인사만 있는 것이 아니라, 무엇이 적용됐는지 확인할 수 있는 파일과 커밋이 남았습니다. [제출한 검사][tests] · [적용된 검사][adopted-tests]

### 2026년 9월 21일 후속 확인

**기여한 검사가 이후 변경에서도 쓰였습니다.** 개발자는 우리의 최신 코드 이전 지침을 적용했으며, 그 과정에서 기존 바인딩 검사가 새 잠금 기능과 지연된 확인창 표시의 충돌을 드러냈다고 [보고했습니다][port-followup]. 추가 통합 수정과 보고된 검증은 그 개발자의 기여입니다. 새 head의 검사 파일도 이전과 같은 Git 식별값을 가지는지 확인했습니다. 이 페이지를 고치면서 검사를 새로 실행한 것은 아닙니다.

별도로, 옛 확인창의 늦은 전송 거절이 새 승인 대기를 지우는 경우에 대해 [재현 코드와 수정 후보를 전달했습니다][late-decline-review]. 이 후속은 아직 실제 통합·통신 조건의 검토가 남아 있으며, 적용된 수정으로 소개하지 않습니다. 현재 PR은 열려 있고 아직 병합되지 않았습니다. 앞선 기여가 유지된 사실과 새 문제의 검토 대기를 나누어 남깁니다.

### 현재 단계와 다음 연결

2026년 9월 12일 확인한 단계는 **외부 개발자의 적용과 기여 명시**입니다. 원프로젝트의 PR은 당시 아직 열려 있었습니다. 이후 병합이나 배포 상태는 [원 PR][pr]에서 확인할 수 있습니다.

### 사례 02 | 중단 처리에 반영된 기여와 공개 정정

**2026년 9월 23일 확인.** PR #84236의 작성자 Halldrix는, 사용자 중단에 이유 문장이 붙었을 때 이를 새 질문으로 오인하지 않도록 우리가 제안한 조건을 [자기 코드에 반영했습니다][stop-commit]. 커밋 메시지는 **YS-OH-CORE의 검토**를 명시하며, 작성자가 추가한 검사에도 그 출처가 남아 있습니다. 확인 당시 [원 PR][stop-pr]은 아직 병합 전이었습니다.

**우리 설명에서 바로잡힌 부분도 함께 공개합니다.** [원래 검토][stop-review]는 실제 종료 처리 함수와 단위검사 환경에서 조건을 재현했지만, 근거로 든 명령줄 실행 경로 전체는 시험하지 않았습니다. 상대의 [전체 실행 비교][stop-response]에서는 그 수정으로 중단 안내가 생기지 않았습니다. 이후 상대는 [원인 설명도 정정했습니다][stop-topology]. 예외가 메인 스레드의 대기를 풀고, 별도 스레드에서 돌던 대화 작업은 프로세스 종료로 남겨지는 구조이지, `run_conversation` 자체가 그 예외로 풀리는 것은 아닙니다. 따라서 종료 처리 함수의 조건 수정이 명령줄의 무응답까지 해결했다는 뜻은 아닙니다. 우리는 [첫 정정][stop-correction]에 이어 [수정된 실행 구조도 받아들였습니다][cli-followup]. 로그 한 줄이 없다는 사실만으로 전체 스레드 동작이 독립 입증되는 것은 아닙니다.

실행 중 중단 사유를 기록하지 않던 다른 부분의 발견·수정과 관련 검사 129개 통과는 Halldrix의 기여 및 보고입니다. 이번 소개글을 작성하면서 새로 실행한 검사가 아니며, 남은 명령줄 문제는 별도입니다.

**별도로 시험해 전달한 후보는 채택된 기여와 구분합니다.** 상대의 모의 서버를 사용한 [네 번의 실제 명령줄 비교][cli-run]에서는 예외 처리 위치에 안내를 넣는 후보가 차이를 만들었습니다. 이는 텍스트 모드의 중단 안내만 확인한 결과입니다. 작업 정리·저장·전체 프로그램 검증이나 상대의 채택을 뜻하지 않습니다. [실패한 첫 검사와 실행 범위][cli-details], [다른 검토자가 복사해 쓸 양식](notes/12-from-prompt-to-world.md#engineering-case-a-passing-unit-test-is-not-a-fixed-workflow)도 함께 연결합니다.

오영석의 문제 방향·우선순위 판단, Zero(ChatGPT)의 상당한 분석·검사 작성·실행 조율·문안 작성, 상대 개발자의 구현·통합·반론을 구분합니다. 영석이 모든 코드를 혼자 작성한 전문경력으로 바꾸지 않습니다. **확인 가능한 기여와 그 기여의 한계를 같은 자리에서 볼 수 있는 협업 사례**입니다.

### 사례 03 | 점수는 그대로, 해석과 기여 기록은 더 정확하게

**2026년 9월 24일 확인.** TAM 개발자의 [공개 검토 요청][tam-request]에 대해, 저장된 400문항의 판정에서 정확도 여섯 칸과 문항별 비교 네 개를 다시 계산했습니다. [기존 실행][tam-run]에서 발표 수치와 일치함을 확인한 뒤, 채점 모델과 평가 기준이 함께 바뀌는 비교를 문구만의 효과로 읽지 않도록 제안했습니다. 통계적으로 차이를 검출하지 못한 것과 동등함을 입증한 것도 구분했습니다.

개발자는 [보고서·소개글을 수정하고][tam-revision], 문제 분할 목록과 유형별 개수, 최종 설정 전에 보고용 문제의 점수를 이미 보았다는 이력을 공개했습니다. 점수는 바뀌지 않았습니다. 이후 [별도 기여 표기 커밋][tam-credit]으로 **Youngseok Oh (@YS-OH-CORE)**와 **Zero(ChatGPT)의 기술 분석·코드·실행 지원**을 공개 보고서에 함께 적었습니다.

이 사례는 실제로 반영된 보고 개선과 공개 기여 표기입니다. 검색·답 생성·새 채점·제품 전체 성능을 독립 검증했다는 뜻은 아닙니다. 상대의 사적 메일이 아니라 [공개 보고서와 변경 기록][tam-report]으로 확인할 수 있습니다. 이 페이지를 갱신하면서 모델 실험을 추가하지 않았습니다.

### 사례 04 | 개인 메모와 AI 호출을 구분하는 구현 경로

**2026년 9월 25일 확인.** Signal의 개인 메모는 그대로 두면서 같은 계정의 단체방에서는 AI를 부르고 싶다는 요청에 대해, 기존 설정 전달 경로와 적용할 메시지 처리 위치를 [코드에서 찾아 안내했습니다][signal-review]. 요청자 **ren2140eth**는 **@YS-OH-CORE**를 직접 언급하고, 자신도 같은 판본의 코드를 확인했으며 안내가 맞다고 [공개 답변했습니다][signal-ack]. 새 설정 전달 장치를 만들 필요가 없고, 필요한 수정이 처음 예상보다 작아진다고 설명했습니다.

첫 소스 검토 단계의 확인 수준은 **상대가 검토 내용을 읽고 직접 소스를 대조한 뒤 유용성을 확인한 것**이었습니다. 당시에는 실제 패치의 적용·배포나 사용자의 Signal 계정 복구까지 확인하지 않았습니다. 원래 요청과 기능 제안은 상대의 기여이며, Zero는 소스 추적과 검토 문안 작성을 맡았습니다. 별도 실험이나 사적인 대화 공개 없이, 공개된 왕복 대화를 연결했습니다.

**같은 날의 후속: 상대가 직접 구현하고 실행한 결과를 보고했습니다.** ren2140eth는 우리의 제안에 따라 `749220ef`의 코드를 수정하고 연결된 보조 Signal 기기로 실행했으며, 개인 메모는 처리 전에 제외되고 단체방은 기존 허용·멘션 검사를 계속 거친다고 [공개 답변했습니다][signal-runtime]. 기본 동작과 자기 답장에 다시 반응하지 않는 처리도 유지했다고 설명했습니다.

새 확인 수준은 **상대가 보고한 로컬 구현·실행 성공**입니다. 구현과 현장 확인은 상대의 기여이며, Zero가 그 환경을 독립 재시험하거나 공식 병합·배포를 확인한 것은 아닙니다. 다음 기여자가 정확한 수정에서 이어갈 수 있도록 가져오기 변경까지 포함한 코드 차이와 보유한 가상 시험 자료를 [요청했습니다][signal-runtime-followup]. 사적인 메시지·전화번호·계정 설정은 요청하지 않았습니다.

**후속 확인: 공식 저장소에 수정 요청이 올라왔습니다.** Halldrix가 ren2140eth의 허락을 받아 [PR #122033](https://github.com/NousResearch/hermes-agent/pull/122033)을 개설하고 사용자 설명서와 추가 검사를 포함했습니다. 확인한 판본은 `bb8f1406`이며 아직 열려 있고 병합되지 않았습니다. PR의 64개 검사 통과는 Halldrix의 보고로 구분합니다.

이전에 받은 정확한 수정본의 별도 가상 환경 검사와 현재 제출본의 실행 파일이 동일한지 확인하고, Zero가 [해당 커밋에 고정한 COMMENT 검토](https://github.com/NousResearch/hermes-agent/pull/122033#pullrequestreview-5312419768)를 남겼습니다. 이번 단계의 새 제품 실행검사는 없으며, 파일 내용이 같다는 것과 새 환경 전체를 재검증했다는 것은 다릅니다. 같은 네 번째 사례의 진행 상태를 갱신한 것이고, 구현·초기 검사는 ren2140eth, 제출·설명서·추가 검사는 Halldrix의 기여로 남깁니다.

### 사례 05 | 실제 통신 검사가 원작성자의 코드에 반영됨

**2026년 9월 28일 확인.** 헤르메스 PR #121944의 작성자 **liuhao1024**는 우리가 보낸 두 회귀 테스트를 자기 브랜치에 반영했다고 [답했습니다][http503-ack]. 실제 [반영 커밋][http503-adopted]에는 **YS-OH-CORE 공동저자 표기**가 있고, 검사 파일의 내용과 전체 코드 트리가 제출본과 일치함을 직접 대조했습니다.

검사는 일시적인 HTTP 503을 만났을 때 기존 HTTP 방식으로 재시도해 도구를 실행하는지, 실제로 다른 통신 방식이 필요한 HTTP 405에서는 전환이 유지되는지를 확인합니다. 원래 문제 제보와 제품 수정은 fmunechi·liuhao1024의 기여이고, 우리는 실제 SDK와 재시도 경로를 통과하는 검사 및 비교 근거를 보탰습니다. [실행 기록][http503-report]

우리 보존 로그의 관련 검사 **41개 통과**와 작성자가 보고한 **43개 통과**는 출처를 구분했습니다. 개수 차이는 아직 해명되지 않았고, 이번 기록 갱신에서 다시 실행한 수치는 아닙니다. 확인된 성과는 **원작성자의 PR 브랜치에 검사와 기여 표기가 반영된 것**이며, 원 PR은 아직 열려 있고 병합 전입니다.

### 사례 06 | 삭제 실패가 성공으로 표시되는 문제를 검증해 수정으로 연결함

**2026년 9월 29일 한국시간 기준으로 확인했습니다.** Mem0 기여자 **Souptik96**는 우리가 보낸 검증을 받아 구현과 회귀 검사를 수정했다고 [공개 답변했습니다][mem0-ack]. 우리 검사는 실제 기록이 들어 있는 FAISS 저장소에서 삭제 성공 안내가 나와도 대상 기록이 남는 반례를 보였습니다. 상대는 지원하지 않는 작업을 `NotImplementedError`로 알리고, 실제 기록이 있는 FAISS 검사를 추가했습니다. 그 변경은 [상대의 개인 저장소 `127bb797` 커밋][mem0-revised]에 있습니다. 확인된 성과는 **다른 기여자의 구현·검사에 검토 결과가 반영된 것**입니다. 이 변경은 해당 LangChain 연결 경로에 일괄 삭제 기능을 추가한 것은 아닙니다.

보존된 비교에서는 상대가 작성한 검사 7개가 수정본에서 모두 통과했습니다. 같은 검사에서 adapter 파일만 이전 판본으로 바꾸면 **6개 실패·1개 통과**였고, 실제로 빈 결과를 다루는 Chroma 가상 대조군은 계속 통과했습니다. FAISS 검사는 예외 발생과 Alice 3개·Bob 1개의 라벨 유지를 확인했으며, 문서 내용과 ID 전체의 무결성 검사로 확대하지 않습니다. 실제 Memory 코드와 오프라인 FAISS를 사용했지만 주변 의존성과 history 등은 기존 가상 객체를 사용했습니다. 선택 검사, 버전 범위에 따른 의존성 설치, `--noconftest` 실행이라는 한계도 [근거 기록](work/mem0-nonempty-delete.evidence.json)에 남겼습니다. 이번 갱신에서는 [기존 원시 결과][mem0-report]와 파일 식별자를 다시 대조했으며 제품 검사를 새로 실행하지 않았습니다.

[PR #7464][mem0-pr]는 이슈 수락 표시를 기다리는 절차에 따라 닫혀 있고, 기록된 head는 이전 `cec74a8e`입니다. 검증한 후속 코드는 상대의 개인 저장소에 있으며, 공식 병합·배포는 확인되지 않았습니다. 원래 결함 제보는 **BlueX888**, 수정 구현과 검사는 **Souptik96**의 기여입니다. **영석**은 협업 방향과 공개 계정을, **Zero**는 반례·실행·후속 검증을 맡았습니다.

### 사례 07 | 제한시간 뒤에 연결이 끝나는 경우를 고쳐 원작성자 브랜치에 반영함

**2026년 9월 29일 한국시간 기준으로 확인했습니다.** MCP 호환성 검증 도구의 PR #533 작성자 **aton-of-data**는 우리 수정 커밋을 자기 브랜치에 그대로 받아 넣고, **Youngseok Oh / @YS-OH-CORE의 저자 기록을 유지했다**고 [공개 답변했습니다][mcp533-ack]. 실제 [상대 브랜치의 커밋][mcp533-received]과 우리 제출본의 전체 소스 트리가 같은 것도 대조했습니다. [공식 PR][mcp533-pr]은 아직 열려 있고 미병합입니다.

원래 수정안은 검사가 실패하거나 제한시간을 넘기면 남은 연결을 닫는 작업이었습니다. 우리가 보탠 것은 **서버에는 세션이 이미 생겼지만, 클라이언트의 연결 준비가 제한시간 뒤에 끝나는 경우**입니다. 정리 시점에는 아직 반환된 연결이 없어서 놓치고, 나중에 끝난 연결이 버려진 검사에 넘어갈 수 있었습니다. 세션 허용 수가 적은 서버에서는 그 연결이 자리를 차지해 정상적인 다음 검사까지 실패하게 만들었습니다.

수정은 검사 종료 상태를 연결 준비 전후에 확인하고, 늦게 반환된 연결을 버려진 검사에 넘기기 전에 닫습니다. 원작성자의 기존 구현과 검사 세 개를 유지하면서 실행 코드 **15줄 추가·5줄 삭제**, 실제 실행기와 SDK를 사용하는 회귀 검사 한 개를 보탰습니다. [수정과 재현 코드][mcp533-submitted]

작성자는 새 작업 폴더에서 **48개 파일의 검사 626개 통과**와 형식·타입 등의 검사 성공을 직접 확인했다고 보고했습니다. 또 우리 회귀 검사를 자기 수정 전 판본에 그대로 옮기면 세션 누수와 다음 정상 검사의 실패가 재현되고, 보완본에서는 통과한다고 설명했습니다. 이는 **상대가 공개한 재실행 결과**이며, 이 소개글을 작성하며 우리가 다시 실행한 숫자는 아닙니다. 상대는 별도의 94개 조건 실험과 우리 포크 CI는 재실행하지 않았다고 구분했습니다. [검증 범위와 기여 확인][mcp533-ack]

이번에 확인한 성과는 **수정 코드·검사의 실제 반영, 기존 저자 기록 보존, 상대의 별도 검증 보고**입니다. 연결 준비가 영원히 끝나지 않는 경우와 공통 연결 함수를 거치지 않는 다섯 검사 경로는 남은 범위입니다. 영석의 방향·계정, Zero의 분석·구현·검사 지원, aton-of-data의 원래 구현·통합·재검증을 구분하고, 공식 프로젝트의 병합·배포나 기관의 보증으로 확대하지 않습니다. [기계가 읽을 수 있는 근거 기록](work/mcp-late-session-adoption.evidence.json)

관련 협업을 제안할 때는 공개해도 되는 작은 재현 예시와 코드 버전, 기대한 결과와 실제 결과를 [이슈](https://github.com/YS-OH-CORE/second-paddle-notes/issues/new)에 남겨 주세요. 소개글의 설명보다 원문 답변, 코드, 검사 자료를 먼저 확인할 수 있도록 구성했습니다.

*This case page was written with Zero (ChatGPT) for Youngseok Oh. It reuses public contribution evidence, not private correspondence. Original code and test licensing remain with their existing files; this page does not relicense them.*

[ack]: https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201
[commit]: https://github.com/MestreY0d4-Uninter/hermes-agent/commit/501be10cce7159a08279c89c724db602d9770601
[pr]: https://github.com/NousResearch/hermes-agent/pull/22982
[design]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/21cd675cf4ce8b3722354bd58f673e61c0eb7856/contributions/hermes-model-confirmation/BINDING.md
[tests]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/21cd675cf4ce8b3722354bd58f673e61c0eb7856/contributions/hermes-model-confirmation/test_model_confirmation_binding.py
[adopted-tests]: https://github.com/MestreY0d4-Uninter/hermes-agent/blob/501be10cce7159a08279c89c724db602d9770601/tests/gateway/test_model_confirmation_binding.py
[port-followup]: https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5756049894
[current-binding-tests]: https://github.com/MestreY0d4-Uninter/hermes-agent/blob/8c0090dc9adbddcebb5491559ad98e1cf90d5bb4/tests/gateway/test_model_confirmation_binding.py
[late-decline-review]: https://github.com/NousResearch/hermes-agent/pull/22982#pullrequestreview-5266577738
[stop-review]: https://github.com/NousResearch/hermes-agent/pull/84236#pullrequestreview-5275311288
[stop-response]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5786674461
[stop-commit]: https://github.com/Halldrix/hermes-agent/commit/e99497e5101358b496ca860a3e42c1b623375287
[stop-correction]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5786815631
[stop-pr]: https://github.com/NousResearch/hermes-agent/pull/84236
[stop-topology]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5787022600
[cli-run]: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35805467618
[cli-details]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/70a0b9c1510cdc96576a2572fd33277331d6bf9b/checks/cli-sigint/README.md
[cli-followup]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5787346383
[tam-request]: https://github.com/xiaowu0162/LongMemEval/issues/56
[tam-run]: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35963638161
[tam-script]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/4db6eab3d6a33b98803492ed6d0deb77f97636bc/.github/workflows/lme-peer-review-20260924.yml
[tam-revision]: https://github.com/vbcherepanov/total-agent-memory/commit/8b4065722d8c30942c0e6b718cf77cc55064ce45
[tam-credit]: https://github.com/vbcherepanov/total-agent-memory/commit/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e
[tam-report]: https://github.com/vbcherepanov/total-agent-memory/blob/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e/docs/benchmarks/head-to-head-v14/RESULTS.md#revisions

[signal-request]: https://github.com/NousResearch/hermes-agent/issues/121970
[signal-review]: https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5822868222
[signal-ack]: https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5822952908


[signal-runtime]: https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823143850
[signal-runtime-followup]: https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823237783
[http503-ack]: https://github.com/NousResearch/hermes-agent/pull/121944#issuecomment-5863926910
[http503-adopted]: https://github.com/liuhao1024/hermes-agent/commit/859b987d1df0f47236eabe4190e9d41122b5ea12
[http503-submitted]: https://github.com/YS-OH-CORE/hermes-agent/commit/60c824eadd6952175f15e32e703127560d87d7cb
[http503-pr]: https://github.com/NousResearch/hermes-agent/pull/121944
[http503-report]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/b2900898ae850ef106b8619a53fde93dfd5c2719/checks/hermes-http503-121944/README.md

[mem0-issue]: https://github.com/mem0ai/mem0/issues/7439
[mem0-review]: https://github.com/mem0ai/mem0/issues/7439#issuecomment-5824943500
[mem0-ack]: https://github.com/mem0ai/mem0/issues/7439#issuecomment-5843366869
[mem0-revised]: https://github.com/Souptik96/mem0/commit/127bb79725aeb09d70e58620fd1d88476abf9aca
[mem0-pr]: https://github.com/mem0ai/mem0/pull/7464
[mem0-gate]: https://github.com/mem0ai/mem0/pull/7464#issuecomment-5843251973
[mem0-report]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/5bf5a87d001dccae3a83293b11bdc417146fac3c/checks/mem0-7464-recipient-followup/README.md

[mcp533-pr]: https://github.com/modelcontextprotocol/conformance/pull/533
[mcp533-ack]: https://github.com/modelcontextprotocol/conformance/pull/533#issuecomment-5880560542
[mcp533-received]: https://github.com/aton-of-data/conformance/commit/95dd2e2c64c7173e5f3ddfada7b03512f88eef89
[mcp533-submitted]: https://github.com/YS-OH-CORE/conformance/commit/95dd2e2c64c7173e5f3ddfada7b03512f88eef89
[mcp533-test]: https://github.com/aton-of-data/conformance/blob/95dd2e2c64c7173e5f3ddfada7b03512f88eef89/src/runner/server.session-lifetime.test.ts
[mcp533-handoff]: https://github.com/modelcontextprotocol/conformance/pull/533#issuecomment-5865788690
[mcp533-evidence]: https://github.com/YS-OH-CORE/second-paddle-notes/tree/48fb4e6da4567ba4f0594a753079cc111b5f1413/checks/mcp-533-session-lifetime
