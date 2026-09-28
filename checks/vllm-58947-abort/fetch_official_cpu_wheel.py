#!/usr/bin/env python
"""Download and inspect a fixed official CPU wheel; never install or execute it."""

import argparse
import email
import hashlib
import json
import platform
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.tags import parse_tag, sys_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

FILENAME = "vllm-0.30.0+cpu-cp38-abi3-manylinux_2_39_x86_64.whl"
URL = "https://github.com/vllm-project/vllm/releases/download/v0.30.0/" + urllib.parse.quote(FILENAME)
SHA256 = "0ee75278b3626c5d0b7c310c6d62afae93e900f4eac339c91e333fde5108ed78"
SIZE = 147429514
BINARY_SOURCE = "ced6857afa0ea7b2e3f0846a62e1394e90f15607"
PYTHON_SOURCE = "365706a27300453ba9218c1585a64a1f44b54254"
TARGET_TORCH = Version("2.13.0+cpu")


class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != "https":
            raise ValueError("Refusing non-HTTPS release asset redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    name, version, _, filename_tags = parse_wheel_filename(FILENAME)
    supported = set(sys_tags())
    if platform.machine() != "x86_64" or not filename_tags.intersection(supported):
        raise RuntimeError("Requires compatible x86_64 Python and glibc >= 2.39")
    if name != "vllm" or version != Version("0.30.0+cpu"):
        raise ValueError("Unexpected package or CPU version")
    manifest = {
        "release_url": "https://github.com/vllm-project/vllm/releases/tag/v0.30.0",
        "wheel_url": URL,
        "publisher_sha256": SHA256,
        "expected_size_bytes": SIZE,
        "binary_source_commit": BINARY_SOURCE,
        "python_source_commit": PYTHON_SOURCE,
        "target_torch": str(TARGET_TORCH),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner": default_environment(),
        "libc": platform.libc_ver(),
        "validated": False,
    }
    (out / "selection.json").write_text(json.dumps(manifest, indent=2) + "\n")
    wheel_path = out / FILENAME
    digest = hashlib.sha256()
    size = 0
    opener = urllib.request.build_opener(HTTPSRedirects())
    with opener.open(URL, timeout=60) as response, wheel_path.open("xb") as dest:
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > SIZE:
                raise ValueError("Release asset exceeds published size")
            digest.update(chunk)
            dest.write(chunk)
    if size != SIZE or digest.hexdigest() != SHA256:
        raise ValueError("Release asset differs from published size or SHA256")
    with zipfile.ZipFile(wheel_path) as wheel:
        members = wheel.namelist()
        names = [n for n in members if n.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError("Expected one wheel METADATA")
        metadata_name = names[0]
        wheel_name = metadata_name.rsplit("/", 1)[0] + "/WHEEL"
        if members.count(wheel_name) != 1:
            raise ValueError("Expected one matching WHEEL")
        metadata_raw = wheel.read(metadata_name)
        wheel_raw = wheel.read(wheel_name)
    (out / "METADATA").write_bytes(metadata_raw)
    (out / "WHEEL").write_bytes(wheel_raw)
    metadata = email.message_from_bytes(metadata_raw)
    wheel_metadata = email.message_from_bytes(wheel_raw)
    if canonicalize_name(metadata["Name"]) != "vllm" or Version(metadata["Version"]) != version:
        raise ValueError("Wheel METADATA package/version differs from fixed CPU filename")
    actual_tags = set().union(*(parse_tag(t) for t in wheel_metadata.get_all("Tag", [])))
    if actual_tags != filename_tags or not actual_tags.intersection(supported):
        raise ValueError("WHEEL tags differ from filename or are incompatible")
    marker_env = default_environment()
    marker_env["extra"] = ""
    torch_requirements = []
    for raw_requirement in metadata.get_all("Requires-Dist", []):
        requirement = Requirement(raw_requirement)
        if canonicalize_name(requirement.name) != "torch":
            continue
        if requirement.marker and not requirement.marker.evaluate(marker_env):
            continue
        if requirement.url or not requirement.specifier:
            raise ValueError("Torch dependency lacks a verifiable version constraint")
        if not requirement.specifier.contains(TARGET_TORCH, prereleases=True):
            raise ValueError(f"Release wheel requires incompatible Torch: {raw_requirement}")
        torch_requirements.append(raw_requirement)
    if not torch_requirements:
        raise ValueError("No applicable Torch requirement in wheel METADATA")
    manifest.update({
        "validated": True,
        "wheel_path": str(wheel_path),
        "wheel_sha256": digest.hexdigest(),
        "wheel_size_bytes": size,
        "wheel_metadata_version": metadata["Version"],
        "applicable_torch_requirements": torch_requirements,
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # The installer consumes this only after successful digest/metadata checks.
    (out / "wheel-location.txt").write_text(str(wheel_path) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
