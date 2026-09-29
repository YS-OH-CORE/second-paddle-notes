import atexit,json,runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parent
audit=[]
def guard(event,args):
    if event in {"socket.connect","socket.bind"}:
        address=args[1]
        host=address[0] if isinstance(address,tuple) else None
        allowed=host in {"127.0.0.1","::1"}
        audit.append({"event":event,"loopback":allowed})
        if not allowed: raise RuntimeError("Non-loopback networking excluded from this fixture")
    elif event=="socket.getaddrinfo":
        if args[0] not in {None,"127.0.0.1","::1","localhost"}:
            raise RuntimeError("External DNS excluded from this fixture")
sys.addaudithook(guard)
atexit.register(lambda:(root/"network-audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8"))
runpy.run_path(str(root/"socket_probe.py"),run_name="__main__")
