"""Fetch one whole, pinned upstream module for this isolated reproduction."""
import hashlib
from pathlib import Path
from urllib.request import urlopen

URL = "https://raw.githubusercontent.com/vllm-project/vllm/25b0add7b8a1c944d5c4e364f2de6aa82497a2ad/vllm/entrypoints/serve/utils/sse_keep_alive.py"
EXPECTED = "ec9ef177b07bd3f7f906527ff68870601cb7784e"


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


if __name__ == "__main__":
    destination = Path(__file__).with_name("sse_keep_alive.py")
    if destination.exists():
        if blob_sha(destination.read_bytes()) != EXPECTED:
            raise RuntimeError("Refusing to overwrite a different source file")
    else:
        with urlopen(URL, timeout=30) as response:
            source = response.read(65537)
        if len(source) > 65536 or blob_sha(source) != EXPECTED:
            raise RuntimeError("Source identity mismatch")
        destination.write_bytes(source)
    print("Whole upstream module verified:", EXPECTED)
