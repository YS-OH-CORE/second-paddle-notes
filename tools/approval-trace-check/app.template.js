(function() {
  'use strict';
  const examples = @@EXAMPLES@@;
  const strings = {
    en:{tag:'A small tool for a consequential mismatch.',eyebrow:'REQUEST → APPROVAL → EXECUTION',title:'A request was approved.\nWas the same request executed?',lead:'Check an ordered event trace for changed payloads, stale approvals, cross-scope mixups and repeated execution attempts.',privacy:'Runs in this page. No upload, account, analytics or saved input. Examples use synthetic data.',input:'1. Choose an example or paste a trace',load:'Load example',traceLabel:'Normalized JSON trace · 1 MiB / 3,000 events maximum',check:'Check trace',file:'Open JSON file',clear:'Clear',policy:'Policy: one current request per scope. A new proposal replaces the old one. Payload text must match exactly; one execution attempt per request.',result:'2. Inspect the sequence',events:'Events',attempts:'Attempts',violations:'Findings',export:'Save report JSON',reportPrivacy:'Report includes request IDs and scopes, but not payload text. Review it before sharing.',how:'What does this check mean?',scope:'This is a trace consistency check, not an approval system. No task is executed. “No violation observed” only describes the events you supplied; it cannot detect missing or fabricated events or authenticate a person’s consent.',format:'Use schema approval-trace-v1 and an events array. Every event has type, request_id and scope. propose and execute also need a string payload, including an empty string when appropriate. approve, cancel and expire do not carry a payload. A propose event means a successfully registered proposal, not help text or a rejected proposal. Array order is the event order.',semantics:'Record execute at the start of an attempt, even when the underlying task fails. This checker does not model an already-running task being rolled back. It uses exact JavaScript string equality, including whitespace, not meaning or original transport bytes. Real system logs need an explicit adapter to this schema.',why:'The design question came from an approval/request mismatch found during an open-source review. Start with the example; the source and case record are below.',source:'Source & schema',case:'Related case',pending:'Ready to check',pendingDetail:'Choose an example or supply a trace.',changed:'Input changed',changedDetail:'Run the check again before saving a report.',invalid:'Input not assessed',bad:'Mismatch found',good:'No violation observed',none:'No execution observed',bounds:'Applies only to this supplied sequence and the stated policy.',noExec:'There is no execution attempt in the supplied trace.',labels:['Matching request','Old payload, new approval','Execution after cancellation','Repeated attempt','Two independent scopes']},
    ko:{tag:'작은 도구로, 중요한 어긋남을 확인해.',eyebrow:'요청 → 승인 → 실행',title:'승인한 요청과\n실행된 요청, 같을까?',lead:'순서대로 남긴 기록에서 내용 바뀜, 오래된 승인, 다른 작업 공간의 혼선과 반복 실행을 확인해.',privacy:'이 페이지 안에서 계산해. 업로드·계정·분석 추적·입력 저장 없음. 예시는 가상 자료야.',input:'1. 예시를 고르거나 기록을 붙여 넣어',load:'예시 불러오기',traceLabel:'정해진 형식의 JSON · 최대 1 MiB / 3,000개 이벤트',check:'기록 검사',file:'JSON 파일 열기',clear:'비우기',policy:'검사 규칙: 작업 공간마다 현재 요청 하나. 새 요청이 이전 요청을 대체해. 내용은 정확히 같아야 하고 실행 시도는 요청당 한 번이야.',result:'2. 어떤 순서였는지 확인해',events:'이벤트',attempts:'실행 시도',violations:'발견 항목',export:'검사 결과 JSON 저장',reportPrivacy:'결과에는 요청 ID와 작업 공간이 포함돼. 요청 본문은 포함하지 않아. 공유 전 확인해.',how:'이 검사는 무엇을 확인할까?',scope:'승인을 받거나 작업을 실행하는 도구가 아니라, 기록 안의 일관성을 확인하는 도구야. “위반 관측 없음”은 입력한 기록에만 해당해. 빠지거나 꾸며진 기록, 실제 사람의 동의 여부는 확인하지 못해.',format:'schema는 approval-trace-v1, events는 이벤트 배열이야. 모든 이벤트에 type, request_id, scope가 필요해. propose와 execute에는 문자열 payload도 필요하고 빈 문자열도 가능해. approve, cancel, expire에는 본문을 넣지 않아. propose는 실제로 등록된 새 제안이야. 도움말이나 거절된 제안을 대신 넣으면 안 돼. 배열 순서가 사건 순서야.',semantics:'execute는 작업 성공이 아니라 실행 시도 시작 시점에 남겨. 이미 시작한 작업을 되돌리는 상황은 이 규칙으로 모델링하지 않아. 공백까지 포함한 JavaScript 문자열을 비교하며, 의미나 전송 원본 바이트까지 비교하지는 않아. 실제 시스템 로그는 이 형식으로 연결하는 별도 변환이 필요해.',why:'출발점은 오픈소스 검토에서 만난 승인과 요청의 어긋남이었어. 먼저 예시를 눌러 봐. 코드와 실제 기여 사례는 아래에서 볼 수 있어.',source:'코드와 기록 형식',case:'관련 사례',pending:'검사 준비',pendingDetail:'예시를 고르거나 기록을 넣어 줘.',changed:'입력이 바뀌었어',changedDetail:'새 입력을 검사한 뒤 결과를 저장할 수 있어.',invalid:'입력을 검사하지 못했어',bad:'어긋남을 찾았어',good:'위반 관측 없음',none:'실행 기록 없음',bounds:'입력한 기록과 표시된 검사 규칙 안에서의 결과야.',noExec:'입력한 기록에는 실행 시도가 없어.',labels:['정상 연결','새 승인에 옛 내용','취소한 뒤 실행','같은 요청 두 번','서로 다른 작업 공간']}
  };
  const $ = id => document.getElementById(id);
  let lang = navigator.language.startsWith('ko') ? 'ko' : 'en';
  let report = null, error = '', changed = false, inputEpoch = 0;
  function invalidate(isChanged) { inputEpoch++; report=null; error=''; changed=isChanged; render(); }
  function render() {
    const t = strings[lang];
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i]').forEach(el => { el.textContent = t[el.dataset.i]; });
    document.querySelector('h1').style.whiteSpace='pre-line';
    $('lang').textContent = lang==='en' ? '한국어' : 'English';
    const selected = $('sample').value || 'stale';
    $('sample').replaceChildren();
    Object.keys(examples).forEach((key,i)=>{ const option=document.createElement('option');option.value=key;option.textContent=t.labels[i];$('sample').append(option); });
    $('sample').value=selected;
    $('sample').setAttribute('aria-label', lang==='en'?'Example':'검사 예시');
    const status = error ? t.invalid : !report ? (changed?t.changed:t.pending) :
      report.status==='violations_observed'?t.bad:report.status==='no_execution_observed'?t.none:t.good;
    $('status').textContent = status;
    $('status').className='status '+(error || report?.issues.length ? 'bad' : report?.execution_attempts ? 'good' : '');
    $('detail').textContent = error || (!report ? (changed?t.changedDetail:t.pendingDetail) : report.execution_attempts ? t.bounds : t.noExec);
    $('events').textContent = report ? report.event_count : 0;
    $('attempts').textContent = report ? report.execution_attempts : 0;
    $('violations').textContent = report ? report.issues.length : 0;
    $('export').disabled=!report;
    $('timeline').replaceChildren();
    if (report) report.rows.forEach(row=>{
      const li=document.createElement('li');li.className='event'+(row.issues.length?' bad':'');
      const title=document.createElement('div');title.className='event-title';title.textContent=String(row.event).padStart(2,'0')+'  '+row.type+' · '+row.request_id+' · '+row.scope;li.append(title);
      row.issues.forEach(code=>{const d=document.createElement('div');d.className='event-desc';d.textContent=code+': '+ApprovalTrace.messages[code][lang==='ko'?1:0];li.append(d);});
      $('timeline').append(li);
    });
  }
  function run() {
    inputEpoch++; report=null; error=''; changed=false;
    try { report=ApprovalTrace.parseAndAudit($('trace').value); }
    catch(e) { error=e.message; }
    render();
  }
  function load() { $('trace').value=JSON.stringify(examples[$('sample').value],null,2);run(); }
  $('lang').addEventListener('click',()=>{lang=lang==='en'?'ko':'en';render();});
  $('load').addEventListener('click',load);
  $('check').addEventListener('click',run);
  $('trace').addEventListener('input',()=>invalidate(true));
  $('clear').addEventListener('click',()=>{$('trace').value='';$('file').value='';invalidate(false);$('trace').focus();});
  $('file').addEventListener('change',async()=>{
    const file=$('file').files[0];if(!file)return;
    $('file').value='';invalidate(true);const ticket=inputEpoch;
    try {if(file.size>ApprovalTrace.LIMIT)throw new Error('Input exceeds 1 MiB.');
      const bytes=await file.arrayBuffer();if(ticket!==inputEpoch)return;
      $('trace').value=new TextDecoder('utf-8',{fatal:true}).decode(bytes);run();
    }catch(e){if(ticket!==inputEpoch)return;report=null;error=e.message;render();}
  });
  $('export').addEventListener('click',()=>{
    if(!report)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)+'\n'],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='approval-trace-report.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  render();load();
})();
