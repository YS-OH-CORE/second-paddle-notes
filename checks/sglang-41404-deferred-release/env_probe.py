"""Check actual SGLang imports; this is an environment probe, not a bug verdict."""

import argparse
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import unittest


HEAD = "d574752ef39eb3ef73f87c40dca95d76222f9483"
TARGET = "test/registered/unit/disaggregation/test_deferred_decode_kv_release.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    receipt = {
        "kind": "environment-import-probe",
        "expected_head": HEAD,
        "python": sys.version,
        "executable": sys.executable,
        "official_kernel_stub_helper_used": False,
        "tests_executed": 0,
        "environment": {
            name: os.environ.get(name)
            for name in (
                "SGLANG_USE_CPU_ENGINE", "SGLANG_IS_IN_CI",
                "SGLANG_TEST_MAX_RETRY", "SGLANG_BUILD_RUST_EXTS",
            )
        },
        "sources": {},
    }
    try:
        receipt["actual_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source, text=True
        ).strip()
        assert receipt["actual_head"] == HEAD
        import torch
        import triton

        receipt["torch"] = {
            "version": torch.__version__,
            "binary_git_commit": torch.version.git_version,
            "cuda_build": torch.version.cuda,
            "hip_build": torch.version.hip,
            "cuda_available": torch.cuda.is_available(),
            "file": torch.__file__,
        }
        receipt["triton"] = {"version": triton.__version__, "file": triton.__file__}
        assert torch.__version__ == "2.13.0+cpu", receipt["torch"]
        assert torch.version.cuda is None and torch.version.hip is None
        assert not torch.cuda.is_available()
        assert triton.__version__ == "3.8.0"
        assert os.environ.get("SGLANG_USE_CPU_ENGINE") in (None, "0")

        # Execute the complete, unchanged upstream test module through Python's
        # normal loader. No source extraction or replacement modules are used.
        spec = importlib.util.spec_from_file_location("deferred_release_upstream", source / TARGET)
        assert spec and spec.loader
        target = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = target
        spec.loader.exec_module(target)

        modules = {
            TARGET: target,
            "python/sglang/srt/disaggregation/decode.py": target.decode_mod,
            "python/sglang/srt/disaggregation/common/conn.py": importlib.import_module(
                "sglang.srt.disaggregation.common.conn"
            ),
            "python/sglang/srt/disaggregation/mooncake/conn.py": importlib.import_module(
                "sglang.srt.disaggregation.mooncake.conn"
            ),
            "python/sglang/srt/disaggregation/nixl/conn.py": importlib.import_module(
                "sglang.srt.disaggregation.nixl.conn"
            ),
            "python/sglang/test/test_utils.py": importlib.import_module("sglang.test.test_utils"),
        }
        for relative, module in modules.items():
            actual = Path(inspect.getfile(module)).resolve()
            expected = (source / relative).resolve()
            assert actual == expected, (relative, str(actual))
            committed = subprocess.check_output(["git", "show", f"{HEAD}:{relative}"], cwd=source)
            actual_bytes = actual.read_bytes()
            assert actual_bytes == committed, relative
            receipt["sources"][relative] = {
                "path": str(actual),
                "sha256": hashlib.sha256(actual_bytes).hexdigest(),
                "matches_frozen_git_blob": True,
            }
        from sglang.test.test_utils import CustomTestCase
        from sglang.srt.platforms import current_platform

        assert target.CustomTestCase is CustomTestCase
        receipt["custom_test_case"] = {
            "module": CustomTestCase.__module__, "source": inspect.getfile(CustomTestCase)
        }
        receipt["platform_class"] = type(current_platform).__qualname__
        receipt["upstream_test_count"] = unittest.defaultTestLoader.loadTestsFromModule(target).countTestCases()
        assert receipt["upstream_test_count"] > 0
        receipt["status"] = "import-and-source-check-passed"
    except BaseException:
        receipt["status"] = "environment-or-source-check-failed"
        receipt["traceback"] = traceback.format_exc()
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
