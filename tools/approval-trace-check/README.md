# Was the approved request the one that ran?

A small, dependency-free **approval trace checker**. Open an example, change its
sequence, and see where approval and execution stop referring to the same request.
You can also inspect your own logs after explicitly mapping them to the schema below.

**v0.1.1 correction:** duplicate JSON member names are rejected before a trace is
assessed. Previously, the native parser could keep only the last `type`, `payload`
or `events` member and produce a misleading no-violation report. A new diagnostic
identifies the second occurrence by line/column without rewriting the input.
Old downloaded copies and the earlier fixed `b0fc912f` preview remain v0.1.0;
replace a saved copy or use the updated preview link below. This is our tool's
input-handling correction, not a newly discovered Hermes defect.

**[Try v0.1.1 in a browser / 0.1.1 예시 열기](https://rawcdn.githack.com/YS-OH-CORE/second-paddle-notes/a810f7384567da024fbd0b2c2167a4967f738561/tools/approval-trace-check/index.html)**

This optional, fixed-version preview is served by independent **rawgit.hack**,
not GitHub Pages. On first entry, its external-content notice may ask you to
choose **Open the page**. That host notice loads third-party advertising resources;
ordinary visit metadata reaches the host and those providers. The checked tool
itself performs input processing in memory without input uploads. Use synthetic
examples for this hosted preview; prefer the downloaded offline copy for sensitive
traces. Availability and the host's future behavior are outside this project's
control. No sign-in is needed for the tested entry path.

**[Download the standalone HTML](https://raw.githubusercontent.com/YS-OH-CORE/second-paddle-notes/main/tools/approval-trace-check/index.html)** and open the saved file in a browser. GitHub's file view displays source; it is not a hosted interactive site. The one HTML file contains its code and styles. No account, installation, model call, upload, external font, analytics or persistent input storage is used by the page. External source links navigate only when clicked. Browser/OS restrictions may limit local HTML execution or downloads.

## Try it

The five included **synthetic** examples cover a matching request, old text routed
under a new approval, execution after cancellation, a repeated attempt, and two
independent scopes. Choose an example, press **Load example**, edit the JSON and
press **Check trace**. English and Korean controls are included.

Open a local JSON file or paste a trace. Save the resulting JSON report for further
inspection. The report omits payload text but includes request IDs and scope names:
review those before sharing. Refreshing or clearing the page discards the input.

The same checker can run in Node.js without installing packages:

```sh
node cli.cjs trace.json
```

Exit codes: `0` = no violation observed (including an explicitly labeled trace
with no execution); `1` = policy violations observed; `2` = input not assessed.
Exit0 is not proof that a job completed, that the log is complete, or that consent
was genuine. The CLI reads only the input file and writes its report to stdout.

## The deliberately narrow trace contract

```json
{
  "schema": "approval-trace-v1",
  "events": [
    {"type": "propose", "request_id": "A", "scope": "room-1", "payload": "  Draft only\n"},
    {"type": "approve", "request_id": "A", "scope": "room-1"},
    {"type": "execute", "request_id": "A", "scope": "room-1", "payload": "  Draft only\n"}
  ]
}
```

Every event has `type`, `request_id`, `scope`. Only `propose` and `execute` carry
`payload`, which must be a string and may be empty. Types are `propose`, `approve`,
`execute`, `cancel`, `expire`. Unknown fields and types are rejected. Request IDs
are unique across the supplied trace, including across scopes; use an adapter to
make a composite ID when a source system uses scope-local identifiers.

- A `propose` event is a **successfully registered** proposal. It supersedes a
  pending/approved request in the same scope. Help text and rejected proposals
  must not be mapped to `propose`.
- Approval must refer to the current pending request in the same scope. Cancelled,
  expired, superseded or consumed approvals do not become live again.
- `execute` records an **attempt beginning**, even if the task later fails. The
  executed text must equal the proposed string exactly, and only one attempt is
  permitted per request. At-least-once retry systems need a different policy or
  distinct authorized attempt IDs, not silently adjusted logs.
- Array order is the assumed event order. The tool does not infer clock order,
  concurrent linearization, or events absent from the file. Active work is not
  rolled back when a new proposal arrives. Cancellation after an attempt is
  outside this contract and is reported as a terminal-state conflict.

Limits: 1 MiB UTF-8 input, 3,000 events, 256 UTF-16 code units per ID/scope. The
comparison is JavaScript string equality, not a semantic judgment or verification
of original transport bytes. Raw JSON must have unique decoded member names in each object.
Escape-equivalent names such as `type` and `t\u0079pe` are duplicates. Identical
repeated values are also rejected; repeated names in different objects and JSON
quoted inside a payload remain ordinary data. Unicode normalization is not added.

The browser and CLI both use `parseAndAudit(text)`. `parseUniqueJSON(text)` exposes
the input check, while the low-level `audit(doc)` accepts an already parsed object
and cannot recover members discarded earlier by another parser. Feed original text
to the raw-input API instead of reserializing a lossy parse. Duplicate-input errors
have code `DUPLICATE_JSON_MEMBER`, 1-based line/column, and 0-based `offset` and
`first_offset` in UTF-16 code units. They contain no raw member name or value. An
unassessed input produces no success report; the CLI returns exit2 and the browser
disables report export, preserving the input for inspection.

This uniqueness contract is stricter than JSON grammar: [RFC8259 section4](https://www.rfc-editor.org/rfc/rfc8259.html#section-4)
recommends unique object names and documents differing receiver behavior for
repeated names. The check validates syntax with native parsing, then scans the
original string with per-object name maps before any approval assessment.

**“No violation observed” is intentionally not “safe.”** This tool checks a
supplied account of events. It cannot authenticate the author, establish a human's
actual consent, detect omitted/fabricated/reordered events, or enforce anything in
the real system. It is not an approval service or a Hermes plug-in. The only
current log integration is the explicit JSON contract above.

## Inspect and maintain

`audit.js` is the shared pure checker, `cli.cjs` its command-line wrapper.
`build.py` combines the checked-in template, app and examples into `index.html`,
with content-security-policy script hashes and `connect-src 'none'`.

```sh
python3 build.py --check
node --test test.cjs test-unique-json.cjs
```

After source edits, run `python3 build.py`, review the HTML diff, then run the
checks. The Node suite includes exact text, invalid input, at-most-once attempts,
all six orderings of a single proposal/approval/attempt, and the 20 merges of two
independent ordered three-event scopes. These are software checks, not model
benchmarks or production incident counts.

At initial publication, browser behavior was exercised in container Chromium with supplied HTML,
including JSON import/export, stale-report invalidation, inert HTML-like input,
Korean controls and a390px viewport. Direct `file://` navigation was unavailable
under that container's administrator policy; the successful browser checks used
`set_content` without changing browser policy. Native Safari/mobile and a public
hosted deployment were not tested at that stage. See the introducing PR for those results.

### Original v0.1.0 public browser entry checked on 2026-09-12

[Run 34698645714](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34698645714)
used normal public navigation in Chromium143 and WebKit26 with a390px mobile-size
viewport. Both followed the host notice through its visible button and received
the exact26813-byte published HTML (SHA-256
`d27f2b213ff2e4b32ceb930bf361b6adef8d28c3d3ed61a10c346bdfca6877ae`).
The checks covered file import, report download, changed input, Korean rendering,
computation after disconnecting the network, and no supplied trace restored on
reload. There were zero HTTP(S) requests during the tested data interactions,
separate from the host notice's advertising requests during entry. These were
Linux-hosted browsers with synthetic input, not a physical iPhone or native Safari.

The first machine GET returned403 before any browser ran. Normal browser entry
then worked, but an inspection wait used by our test script conflicted with the
page's content security policy. Locator assertions fixed the test harness; the
tool HTML and its policy were not weakened. Both earlier failed runs are retained
in [PR20](https://github.com/YS-OH-CORE/second-paddle-notes/pull/20).
A successful preview check is a dated observation, not continuous hosting health.

### v0.1.1 correction verified

[PR21](https://github.com/YS-OH-CORE/second-paddle-notes/pull/21) preserves the
five raw-input comparisons and the separate observed results. In
[Node run34701239419](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34701239419),
the unchanged24 tests plus16 added groups passed. One added group compares256
synthetic documents with Python's duplicate-aware object-pairs reader. Those
samples are not256 independent external replications.

[Live run34701239468](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34701239468)
navigated the corrected fixed-version URL in Chromium143 and mobile-size
WebKit26. Both received the exact29348-byte HTML and passed11 interaction groups,
including duplicate-file rejection, original-text preservation, disabled export,
and English/Korean position diagnostics. These are synthetic software checks,
not real-user incident counts or physical-phone tests. The old preview remains
available at its original version; use the v0.1.1 link above for the correction.

## Origin

The question grew out of an [approval/request-binding code review](../../contributions/hermes-model-confirmation/BINDING.md).
The checker is a new, simplified event-log utility, not a copy of Hermes' runtime.
[Related implementation case and roles](../../WORK.md).

Prepared by Youngseok Oh with Zero (ChatGPT). MIT applies to newly authored files
in this folder only. It does not relicense the existing repository or source
projects.

## 한국어

“승인을 받았는가”에서 한 걸음 더 들어가 **어느 요청에 대한 승인이었는가**를
확인하는 작은 도구입니다. 단일 HTML을 저장해서 열고 예시를 누르거나, 위
형식으로 정리한 자신의 기록을 검사할 수 있습니다. 입력 내용은 페이지에서
계산하며 업로드하지 않습니다. 실제 앱에 붙이려면 로그 형식을 명시적으로
연결해야 합니다. 기록에 없는 사실이나 사람의 진짜 동의까지 증명하지는
않습니다. 결과 파일에는 요청 ID와 작업 공간이 남으므로 공유 전 확인하세요.

브라우저 예시는 문서 위쪽 링크에서 바로 열 수 있습니다. 처음에는 외부 호스팅의
안내에서 **Open the page**를 누릅니다. 안내 화면에는 제3자 광고 요청이 있으므로
전체 방문 경로를 무추적이라고 부르지 않습니다. 도구가 열린 뒤 검사에 넣은 내용은
페이지 안에서 처리합니다. 민감한 기록에는 기존 내려받기 방식의 오프라인 사본을
사용하세요. 이번에는 실제 공개 주소와 휴대폰 크기의 WebKit 화면을 검사했으며,
실제 아이폰에서 시험한 것은 아닙니다.

### 0.1.1 입력 해석 교정

같은 객체에서 항목 이름이 중복되면 어느 한쪽을 판정에 쓰지 않고 위치를 알려 줍니다.
취소와 승인이 같은 항목에 함께 적힌 기록이 마지막 값만 남아 통과하던 경우를
재현해 고쳤습니다. 입력은 그대로 유지하고 판정 전에는 결과 저장을 하지 않습니다.
일반 문자열 안에서 중복 항목이 있는 JSON을 인용하는 것은 정상적으로 처리합니다.
예전 파일과 예전 고정 주소는 자동 갱신되지 않으므로 위의 새 링크나 새 파일을
사용하세요. 이미 다른 프로그램이 중복을 없앤 기록에서는 원래 중복을 복원하지
못하므로 원본 텍스트를 넣어야 합니다.
