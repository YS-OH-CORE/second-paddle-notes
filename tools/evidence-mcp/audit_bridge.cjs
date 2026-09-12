'use strict';
// Input is passed on stdin to a fixed checker. It is never a command or filename.
const fs = require('node:fs');
const checker = require('../approval-trace-check/audit.js');
try {
  const report = checker.parseAndAudit(fs.readFileSync(0, 'utf8'));
  process.stdout.write(JSON.stringify({ok: true, report}));
} catch (error) {
  const info = {code: error.code === 'DUPLICATE_JSON_MEMBER' ? error.code : 'INVALID_TRACE'};
  if (info.code === 'DUPLICATE_JSON_MEMBER') {
    for (const name of ['line', 'column', 'offset', 'first_offset']) {
      if (Number.isInteger(error[name])) info[name] = error[name];
    }
    info.unit = 'UTF-16 code unit';
  }
  process.stdout.write(JSON.stringify({ok: false, error: info}));
}
