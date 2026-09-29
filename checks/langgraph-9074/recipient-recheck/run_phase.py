import json, os, sys
from pathlib import Path
import fixture_check
repo, out, mode, label, revision = sys.argv[1:]
fixture_check.REF = revision
result = fixture_check.execute_child(Path(repo), Path(out), mode)
result.update(process_id=os.getpid(), phase_label=label)
Path(out, label + ".json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"phase": label, "success": result["success"], "rows": len(result["rows"]), "storage": result["storage_sha256"]}))
