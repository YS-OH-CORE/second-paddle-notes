import atexit, ipaddress, json, os, sys
from pathlib import Path
attempts = []
def check(event, args):
    if event not in ("socket.connect", "socket.getaddrinfo"):
        return
    address = args[1] if event == "socket.connect" else args[0]
    host = address[0] if isinstance(address, tuple) else address
    if host in ("localhost", None):
        return
    try:
        permitted = ipaddress.ip_address(str(host)).is_loopback
    except ValueError:
        permitted = False
    if not permitted:
        attempts.append({"event": event, "blocked": True})
        raise RuntimeError("External network is outside this synthetic checkpoint review")
sys.addaudithook(check)
def finish():
    target = os.environ.get("ZERO_AUDIT_FILE")
    if target:
        Path(target).write_text(json.dumps({"pid": os.getpid(), "events": attempts}), encoding="utf-8")
atexit.register(finish)
