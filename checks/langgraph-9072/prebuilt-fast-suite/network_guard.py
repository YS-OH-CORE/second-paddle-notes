"""Test-process egress guard. Allows only explicit loopback addresses."""
import atexit
import ipaddress
import json
import os
import sys
from pathlib import Path

_events = []

def _is_local(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False

def _audit(event, args):
    if event == "socket.connect":
        address = args[1]
        local = isinstance(address, tuple) and _is_local(address[0])
    elif event == "socket.getaddrinfo":
        local = _is_local(args[0])
    else:
        return
    _events.append({"event": event, "allowed_loopback": local})
    if not local:
        raise RuntimeError("External network access blocked in the review environment")

sys.addaudithook(_audit)

@atexit.register
def _save():
    directory = Path(os.environ["ZERO_REVIEW_AUDIT"])
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (str(os.getpid()) + ".json")).write_text(
        json.dumps({"pid": os.getpid(), "guard_loaded": True, "events": _events}), encoding="utf-8"
    )
