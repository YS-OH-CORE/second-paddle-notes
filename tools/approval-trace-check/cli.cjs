#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const {parseAndAudit, LIMIT} = require('./audit.js');
try {
  if (process.argv.length !== 3) throw new Error('Usage: node cli.cjs trace.json');
  const fd = fs.openSync(process.argv[2], 'r');
  let data;
  try {
    const buf = Buffer.alloc(LIMIT + 1);
    let n = 0, next;
    while (n < buf.length && (next = fs.readSync(fd, buf, n, buf.length-n, null)) > 0) n += next;
    if (n > LIMIT) throw new Error('Input exceeds 1 MiB.');
    data = new TextDecoder('utf-8', {fatal:true}).decode(buf.subarray(0,n));
  } finally { fs.closeSync(fd); }
  const report = parseAndAudit(data);
  process.stdout.write(JSON.stringify(report,null,2)+'\n');
  process.exitCode = report.status === 'violations_observed' ? 1 : 0;
} catch (error) {
  process.stderr.write('Input not assessed: '+error.message+'\n');
  process.exitCode = 2;
}
