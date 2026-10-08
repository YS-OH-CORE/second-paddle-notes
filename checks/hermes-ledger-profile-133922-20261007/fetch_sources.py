"""Fetch four hash-pinned public sources; never import or install Hermes."""
from pathlib import Path
import ast, hashlib, urllib.request

here = Path(__file__).resolve().parent
nodes = ast.parse((here / "check_ledger_profile.py").read_text(encoding="utf-8")).body
constants = {n.targets[0].id: ast.literal_eval(n.value) for n in nodes
             if isinstance(n, ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id in ("EXPECTED", "REF")}
expected, ref = constants["EXPECTED"], constants["REF"]
allowed = {"hermes_cli/web_server.py", "hermes_cli/process_identity.py",
           "hermes_cli/update_inventory.py", "hermes_constants.py"}
if set(expected) != allowed or len(ref) != 40:
    raise ValueError("Unexpected source manifest")
for name, wanted in expected.items():
    target = here / "upstream" / name
    if target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise ValueError("Refuse a redirected source path")
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != wanted:
            raise ValueError("Existing source changed: " + name)
        print("Already verified:", name)
        continue
    url = f"https://raw.githubusercontent.com/NousResearch/hermes-agent/{ref}/{name}"
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != wanted:
        raise ValueError("Source size/hash mismatch: " + name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(raw)
    print("Downloaded and verified:", name)
