"""One synthetic persistence fault; not an unmodified-run result.

The first local Qdrant disk deletion fails before its real DELETE.
The unchanged public-path reviewer checks what the caller sees and
what survives a separate process reopen. Zero x Youngseok Oh.
"""
import hashlib
from pathlib import Path
import runpy
import sqlite3
import sys
from qdrant_client.local.persistence import CollectionPersistence

script = Path(sys.argv.pop(1)).resolve()
assert hashlib.sha256(script.read_bytes()).hexdigest() == (
    "2f2a22c0efd89211402595694dea7d174af4cad72a256520a04b94eb95b9eb61"
)
original = CollectionPersistence.delete
failed = False


def fail_first(self, point_id):
    global failed
    if not failed:
        failed = True
        raise sqlite3.OperationalError("SYNTHETIC_PERSISTENCE_FAILURE")
    return original(self, point_id)

CollectionPersistence.delete = fail_first
runpy.run_path(str(script), run_name="__main__")
