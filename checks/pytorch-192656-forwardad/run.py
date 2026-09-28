"""Run a bounded comparison using exact Python sources and one CPU wheel."""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path


REFS = {
    "parent": "061ace3a865340a4f6a351e5ef8f3a7f37b6645e",
    "candidate": "eb9c90dd1f2b67cadf9f7681176f1b5fab074423",
}
EXPECTED = {
    "parent": {
        "torch/_subclasses/functional_tensor.py": "91fd79c21e9119a530958514d1de8520098cbaa8f8ad8cf41ad6d898d047a2ad",
        "torch/autograd/forward_ad.py": "289adf8dbb998f011fbe189852bd9f95931c0fe36c12922aacaaa877b96e4a23",
    },
    "candidate": {
        "torch/_subclasses/functional_tensor.py": "5e5235ce069c7eae3a06cb0c97e3411e9dfcf190e39abc2d0ad1b275e90a6a51",
        "torch/autograd/forward_ad.py": "d493b00c81ea6d359b13673c5777c339774f0bd55d93dbaefe10d41c6ef69954",
    },
}
CONTROLS = {
    "test_eager_oracle",
    "test_readonly_matches_eager",
    "test_clone_mutation_matches_eager",
}
MUTATION_TEST = "test_intermediate_tangent_mutation_matches_eager"
PREFIX = "FORWARDAD_OBSERVATIONS="


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def execute(command, stem, receipt, timeout=180):
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        process = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, env=environment
        )
        stdout, stderr, code = process.stdout, process.stderr, process.returncode
        timed_out = False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timed_out = error.stdout or "", error.stderr or "", None, True
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
    (receipt / (stem + ".stdout.log")).write_text(stdout)
    (receipt / (stem + ".stderr.log")).write_text(stderr)
    result = {"returncode": code, "timed_out": timed_out}
    write_json(receipt / (stem + ".process.json"), result)
    return result, stdout


def clear_cache(target):
    cache = target.parent / "__pycache__"
    if cache.is_dir():
        for entry in cache.glob(target.stem + ".*.pyc"):
            entry.unlink()


def parsed_observations(stdout):
    lines = [line[len(PREFIX):] for line in stdout.splitlines() if line.startswith(PREFIX)]
    if len(lines) != 1:
        raise RuntimeError("expected one complete observation record")
    return json.loads(lines[0])


def check_report(report, expected_hashes, package_root):
    if report["torch_version"].split("+")[0] != "2.13.0":
        raise RuntimeError("unexpected CPU torch wheel version")
    if report["cuda_available"] or report["cuda_build"] is not None or report["hip_build"] is not None:
        raise RuntimeError("expected CPU-only experiment")
    for module, source in report["sources"].items():
        path = "torch/" + module.removeprefix("torch.").replace(".", "/") + ".py"
        installed = package_root / Path(path).relative_to("torch")
        if Path(source["path"]).resolve() != installed.resolve():
            raise RuntimeError("test imported source outside the disposable wheel")
        if source["sha256"] != expected_hashes[path]:
            raise RuntimeError("loaded source hash differs from exact upstream source")
    if set(report["sources"]) != {"torch.autograd.forward_ad", "torch._subclasses.functional_tensor"}:
        raise RuntimeError("incomplete loaded-source provenance")


def classify(parent, candidate):
    failures = []
    expected_tests = CONTROLS | {MUTATION_TEST}
    for name, result in (("parent", parent), ("candidate", candidate)):
        if result["returncode"] != 1 or result["timed_out"]:
            failures.append(name + " did not finish with the expected test failure exit")
        if set(result["report"]["statuses"]) != expected_tests:
            failures.append(name + " did not execute exactly the four intended tests")
    parent_states = {k: v["state"] for k, v in parent["report"]["statuses"].items()}
    expected_parent = {name: "ERROR" for name in expected_tests}
    expected_parent["test_eager_oracle"] = "ok"
    if parent_states != expected_parent:
        failures.append("parent did not show the original missing-tangent defect with a passing eager oracle")
    parent_functional = [x for x in parent["report"]["observations"] if x["mode"] == "functional"]
    if len(parent_functional) != 3 or any(
        x.get("error_type") != "RuntimeError"
        or x.get("error") != "unpack_dual returned no tangent for intermediate dual"
        for x in parent_functional
    ):
        failures.append("parent errors did not identify the intended original defect")
    candidate_states = {k: v["state"] for k, v in candidate["report"]["statuses"].items()}
    expected_candidate = {name: "ok" for name in CONTROLS}
    expected_candidate[MUTATION_TEST] = "FAIL"
    if candidate_states != expected_candidate:
        failures.append("candidate did not pass all three controls and fail only the mutation assertion")
    functional = [x for x in candidate["report"]["observations"] if x["mode"] == "functional"]
    if len(functional) != 3 or {x["variant"] for x in functional} != {"readonly", "clone", "mutate"}:
        failures.append("candidate functional observations were incomplete")
    for observed in functional:
        expected_values = {
            "primal": [6.0, 12.0], "tangent": [18.0, 24.0],
            "input_primal_after": [1.0, 2.0], "input_tangent_after": [3.0, 4.0],
        }
        if any(observed.get(key) != value for key, value in expected_values.items()):
            failures.append("candidate " + observed["variant"] + " differs from the specific predicted signature")
    eager_mutations = [x for x in candidate["report"]["observations"] if x["mode"] == "eager" and x["variant"] == "mutate"]
    if len(eager_mutations) != 2 or any(x.get("tangent") != [48.0, 54.0] for x in eager_mutations):
        failures.append("eager mutation oracle was not observed as expected")
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = args.receipt.resolve()
    receipt.mkdir(parents=True, exist_ok=True)
    summary = {"experiment": "PyTorch PR 192656 Python source-overlay comparison", "source_refs": REFS, "target_conditions_met": False, "results": {}, "errors": []}
    spec = importlib.util.find_spec("torch")
    if spec is None or spec.origin is None:
        raise RuntimeError("torch wheel is not installed")
    package_root = Path(spec.origin).resolve().parent
    sources = {"parent": args.parent.resolve(), "candidate": args.candidate.resolve()}
    originals = {}
    try:
        for variant, root in sources.items():
            head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            if head != REFS[variant]:
                raise RuntimeError("checkout head mismatch: " + variant)
            for path, expected in EXPECTED[variant].items():
                if sha((root / path).read_bytes()) != expected:
                    raise RuntimeError("upstream source hash mismatch: " + path)
        shutil.copyfile(sources["candidate"] / "LICENSE", receipt / "LICENSE.pytorch")
        for path in EXPECTED["parent"]:
            target = package_root / Path(path).relative_to("torch")
            original = target.read_bytes()
            originals[path] = original
            backup = receipt.parent / "pytorch-forwardad-original-source" / path
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(original)
        summary["original_source_sha256"] = {path: sha(data) for path, data in originals.items()}
        # This fresh process records the original wheel before any source changes.
        probe = "import hashlib,json,platform,pathlib,torch; import torch.autograd.forward_ad as a; import torch._subclasses.functional_tensor as b; print(json.dumps({'torch_version':torch.__version__,'binary_git_version':torch.version.git_version,'python':platform.python_version(),'cuda_available':torch.cuda.is_available(),'cuda_build':torch.version.cuda,'hip_build':torch.version.hip,'sources':{m.__name__:{'path':str(pathlib.Path(m.__file__).resolve()),'sha256':hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest()} for m in (a,b)}}))"
        process, stdout = execute([sys.executable, "-c", probe], "original-wheel", receipt)
        if process["returncode"] != 0:
            raise RuntimeError("original CPU wheel import failed; inspect original-wheel logs")
        original_report = json.loads(stdout.strip())
        check_report(original_report, summary["original_source_sha256"], package_root)
        write_json(receipt / "original-wheel.json", original_report)
        summary["binary_git_version"] = original_report["binary_git_version"]
        summary["torch_version"] = original_report["torch_version"]
        for variant, root in sources.items():
            for path, expected in EXPECTED[variant].items():
                target = package_root / Path(path).relative_to("torch")
                target.write_bytes((root / path).read_bytes())
                clear_cache(target)
                if sha(target.read_bytes()) != expected:
                    raise RuntimeError("installed overlay readback mismatch: " + path)
            process, stdout = execute(
                [sys.executable, str(Path(__file__).with_name("repro.py")), "-v",
                 "--save-xml", str(receipt / "xml" / variant)],
                variant, receipt,
            )
            report = parsed_observations(stdout)
            check_report(report, EXPECTED[variant], package_root)
            if report["binary_git_version"] != original_report["binary_git_version"]:
                raise RuntimeError("wheel binary provenance changed between variants")
            process["report"] = report
            summary["results"][variant] = process
            write_json(receipt / (variant + ".json"), process)
        summary["errors"].extend(classify(summary["results"]["parent"], summary["results"]["candidate"]))
    except Exception:
        summary["errors"].append(traceback.format_exc())
    finally:
        restored = {}
        for path, original in originals.items():
            try:
                target = package_root / Path(path).relative_to("torch")
                target.write_bytes(original)
                clear_cache(target)
                restored[path] = sha(target.read_bytes()) == sha(original)
            except Exception:
                restored[path] = False
                summary["errors"].append(traceback.format_exc())
        summary["restored_original_sources"] = restored
        if set(restored) != set(EXPECTED["parent"]) or not all(restored.values()):
            summary["errors"].append("original source restoration was incomplete")
        summary["target_conditions_met"] = not summary["errors"]
        summary["interpretation"] = (
            "The exact predicted numerical discrepancy was reproduced in this Python source-overlay environment."
            if summary["target_conditions_met"]
            else "The required evidence signature was not established; inspect errors and raw observations before interpreting the run."
        )
        write_json(receipt / "SUMMARY.json", summary)
        print(json.dumps({"target_conditions_met": summary["target_conditions_met"], "errors": summary["errors"], "restored_original_sources": restored}, indent=2))
    return 0 if summary["target_conditions_met"] else 1


if __name__ == "__main__":
    sys.exit(main())
