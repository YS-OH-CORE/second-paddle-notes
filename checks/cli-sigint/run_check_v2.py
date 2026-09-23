"""Narrow correction to the first four-case orchestrator, not a product fix.

Run 35805232482 reached the mock and reproduced exit 130 without a closing
notice, but our baseline assertion incorrectly required absolutely empty stdout.
A pre-existing tirith availability warning was printed in BOTH normal and
interrupted runs. Do not disable scanning or discard that raw output.
Compare original/candidate stdout exactly and test the diagnostic separately.
The first run stopped after two baseline processes, before candidate execution.

This adapter fetches the exact prior orchestrator and makes the changes below
in memory. Halldrix's mock, upstream revision, dependencies, signal timing and
network restriction remain unchanged. The candidate wording is neutral about
who sent the signal. Nothing here claims tool cleanup or completed finalization.
"""
import hashlib
import urllib.request

URL = 'https://raw.githubusercontent.com/YS-OH-CORE/second-paddle-notes/0928493b2e1ce777fcf38866ce3cc69174270eb1/checks/cli-sigint/run_check.py'
SHA = 'bc91ca921c29c4bd422ce4f06e99546a624fe5a8204c7369fb258472afedb052'
with urllib.request.urlopen(URL, timeout=20) as response:
    raw = response.read(15000)
assert hashlib.sha256(raw).hexdigest() == SHA
text = raw.decode('utf-8')
changes = [
    ("not original_interrupt['stdout'].strip()",
     "'MOCK_REPLY_OK' not in original_interrupt['stdout'] and 'Turn interrupted' not in (original_interrupt['stdout'] + original_interrupt['stderr_tail'])"),
    ("not fixed_interrupt['stdout'].strip()",
     "fixed_interrupt['stdout'] == original_interrupt['stdout']"),
    ("'original_reproduces_silence'", "'original_has_no_closing_notice'"),
]
for old, new in changes:
    assert text.count(old) == 1, old
    text = text.replace(old, new)
assert text.count('Turn interrupted by user.') == 2
text = text.replace('Turn interrupted by user.', 'Turn interrupted.')
exec(compile(text, 'pinned_cli_check_with_stdout_correction', 'exec'))
