/* Approval Trace Check v0.1.0. User-supplied JSON is data, never code. */
(function(root) {
  'use strict';
  const SCHEMA = 'approval-trace-v1';
  const LIMIT = 1024 * 1024;
  const MAX_EVENTS = 3000;
  const TYPES = new Set(['propose', 'approve', 'execute', 'cancel', 'expire']);
  const messages = {
    DUPLICATE_ID: ['Request ID was reused.', '요청 ID가 재사용됐어.'],
    UNKNOWN_REQUEST: ['No preceding proposal for this request.', '앞선 요청 등록이 없어.'],
    SCOPE_MISMATCH: ['Event scope differs from the proposal.', '요청과 다른 작업 공간을 가리켜.'],
    NOT_CURRENT: ['A newer proposal has replaced this request.', '더 새 요청이 이 요청을 대체했어.'],
    NOT_PENDING: ['Approval does not target a pending request.', '승인 대기 중인 요청이 아니야.'],
    NOT_APPROVED: ['Execution lacks a live approval.', '실행에 유효한 승인이 없어.'],
    PAYLOAD_CHANGED: ['Executed text differs from the proposed text.', '실행 내용이 처음 요청과 달라.'],
    REPEATED_EXECUTION: ['More than one execution attempt for this request.', '같은 요청의 실행 시도가 반복됐어.'],
    ALREADY_TERMINAL: ['Cancellation/expiry followed execution or prior closure.', '실행 또는 이전 종료 뒤에 취소·만료가 기록됐어.']
  };
  function plain(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }
  function nonempty(v) { return typeof v === 'string' && v.length > 0 && v.length <= 256; }
  function difference(a, b) {
    let i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    return {unit: 'UTF-16 code unit', offset: i, proposed_length: a.length, executed_length: b.length};
  }
  function validate(doc) {
    if (!plain(doc) || doc.schema !== SCHEMA || !Array.isArray(doc.events)) {
      throw new Error('Expected {"schema":"approval-trace-v1","events":[...]}');
    }
    if (doc.events.length > MAX_EVENTS) throw new Error('At most 3000 events are supported.');
    doc.events.forEach((e, i) => {
      if (!plain(e) || !TYPES.has(e.type) || !nonempty(e.request_id) || !nonempty(e.scope)) {
        throw new Error('Event '+(i+1)+': type, nonempty request_id and scope are required.');
      }
      if (['propose', 'execute'].includes(e.type) && typeof e.payload !== 'string') {
        throw new Error('Event '+(i+1)+': payload must be a string (empty is allowed).');
      }
      const allowed = new Set(['type', 'request_id', 'scope']);
      if (['propose', 'execute'].includes(e.type)) allowed.add('payload');
      if (Object.keys(e).some(k => !allowed.has(k))) {
        throw new Error('Event '+(i+1)+': unknown field. Normalize the trace explicitly first.');
      }
    });
    if (Object.keys(doc).some(k => !['schema','events'].includes(k))) {
      throw new Error('Unknown top-level field. Only schema and events are supported.');
    }
  }
  function audit(doc) {
    validate(doc);
    const requests = new Map(), current = new Map(), attemptCounts = new Map(), rows = [], issues = [];
    let attempts = 0, validAttempts = 0;
    doc.events.forEach((e, index) => {
      const row = {event: index+1, type: e.type, request_id: e.request_id, scope: e.scope, issues: []};
      function flag(code, detail) {
        const item = {event:index+1, code, request_id:e.request_id, scope:e.scope};
        if (detail) item.detail = detail;
        row.issues.push(code); issues.push(item);
      }
      let r = requests.get(e.request_id);
      if (e.type === 'execute') {
        attempts++;
        const count = (attemptCounts.get(e.request_id) || 0) + 1;
        attemptCounts.set(e.request_id, count);
        if (count > 1) flag('REPEATED_EXECUTION');
      }
      if (e.type === 'propose') {
        if (r) flag('DUPLICATE_ID');
        else {
          const previous = requests.get(current.get(e.scope));
          if (previous && ['pending','approved'].includes(previous.state)) previous.state = 'superseded';
          r = {id:e.request_id, scope:e.scope, payload:e.payload, state:'pending'};
          requests.set(e.request_id, r); current.set(e.scope, e.request_id);
        }
      } else if (!r) flag('UNKNOWN_REQUEST');
      else if (e.type === 'execute') {
        if (r.scope !== e.scope) flag('SCOPE_MISMATCH');
        if (current.get(e.scope) !== e.request_id) flag('NOT_CURRENT');
        if (r.state !== 'approved') flag('NOT_APPROVED');
        if (r.payload !== e.payload) flag('PAYLOAD_CHANGED', difference(r.payload, e.payload));
        if (!row.issues.length) validAttempts++;
        // Log records an attempt, including a failed/unauthorized one. No rollback or retry.
        r.state = 'executed';
      } else if (r.scope !== e.scope) flag('SCOPE_MISMATCH');
      else if (e.type === 'approve') {
        if (current.get(e.scope) !== e.request_id) flag('NOT_CURRENT');
        if (r.state !== 'pending') flag('NOT_PENDING');
        if (!row.issues.length) r.state = 'approved';
      } else {
        if (current.get(e.scope) !== e.request_id) flag('NOT_CURRENT');
        if (!['pending','approved'].includes(r.state)) flag('ALREADY_TERMINAL');
        if (!row.issues.length) r.state = e.type === 'cancel' ? 'cancelled' : 'expired';
      }
      row.state_after = r ? r.state : null;
      rows.push(row);
    });
    return {
      schema:'approval-trace-report-v1', auditor_version:'0.1.0',
      status: issues.length ? 'violations_observed' : attempts ? 'no_violation_observed' : 'no_execution_observed',
      policy:'single-live-request-per-scope; exact-payload; one-execution-attempt',
      event_count:doc.events.length, execution_attempts:attempts, valid_execution_attempts:validAttempts,
      issues, rows,
      limits:['Only the supplied ordered trace is checked. Missing, forged or reordered events are not detectable.',
        'This does not authenticate consent, interpret meaning, execute tasks, or prove a system is safe.',
        'Payload comparison is exact JavaScript string equality, not original transport-byte verification.']
    };
  }
  function parseAndAudit(text) {
    if (typeof text !== 'string') throw new Error('Expected JSON text.');
    if (new TextEncoder().encode(text).length > LIMIT) throw new Error('Input exceeds 1 MiB.');
    return audit(JSON.parse(text));
  }
  const api = Object.freeze({audit, parseAndAudit, messages, SCHEMA, LIMIT, MAX_EVENTS});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ApprovalTrace = api;
})(globalThis);
