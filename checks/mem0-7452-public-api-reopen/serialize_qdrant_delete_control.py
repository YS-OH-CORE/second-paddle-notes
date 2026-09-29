"""Diagnostic scheduling control, not a production patch.

Run the unchanged public-path assertions with local Qdrant persistence
DELETE operations serialized. No records or expectations are altered.
Zero x Youngseok Oh.
"""
import hashlib
from pathlib import Path
import runpy
import sys
import threading

from qdrant_client.local.persistence import CollectionPersistence

script = Path(sys.argv.pop(1)).resolve()
assert hashlib.sha256(script.read_bytes()).hexdigest() == (
    "2f2a22c0efd89211402595694dea7d174af4cad72a256520a04b94eb95b9eb61"
)
original_delete = CollectionPersistence.delete
lock = threading.Lock()


def serial_delete(self, point_id):
    with lock:
        return original_delete(self, point_id)


CollectionPersistence.delete = serial_delete
runpy.run_path(str(script), run_name="__main__")
