"""Actual-package CPU checks for Transformers issue #49093.

The reporter lucaluo925 supplied both diagnoses and candidate line changes.
This checker adds isolated/combined-fix tests and unchanged-behavior controls.
It imports each complete logits_process module; no source-selected stand-ins,
model weights, tokenizers, generation endpoints, or real blocked words are used.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
from pathlib import Path
import platform
import socket
import tempfile


SOURCE_COMMIT = "89b6b17574892ec0770551537a3fe69d6886703e"
EXPECTED_BLOB = "7ff6a32c026efb139cc89996e07181f141cce971"
FIX_A_OLD = "isinstance(token_id, (int, np.integer)) and token_id > 0 for token_id in sequence[0]"
FIX_A_NEW = "isinstance(token_id, (int, np.integer)) and token_id >= 0 for token_id in sequence[0]"
FIX_B_OLD = "if len(sequence_ids) > input_ids.shape[1]:"
FIX_B_NEW = "if len(sequence_ids) - 1 > input_ids.shape[1]:"


def json_values(tensor):
    def encode(v):
        if isinstance(v, list):
            return [encode(x) for x in v]
        if v == float("-inf"):
            return "-inf"
        if v == float("inf"):
            return "+inf"
        return v
    return encode(tensor.tolist())


def run(output: Path):
    import torch
    import transformers
    from transformers import GenerationConfig
    from transformers.generation import logits_process as installed

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    source_path = Path(inspect.getfile(installed))
    original_bytes = source_path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(original_bytes)).encode() + b"\0" + original_bytes).hexdigest()
    if blob != EXPECTED_BLOB:
        raise RuntimeError(f"Source identity mismatch: {blob}")
    source = original_bytes.decode()
    if source.count(FIX_A_OLD) != 1 or source.count(FIX_B_OLD) != 1:
        raise RuntimeError("Expected exactly one occurrence of each reported source condition")
    output.mkdir(parents=True, exist_ok=False)
    (output / "upstream_logits_process.py").write_bytes(original_bytes)
    observations = []
    network_attempts = []
    previous_socket = (socket.socket.connect, socket.socket.connect_ex)

    def no_network(*_args, **_kwargs):
        network_attempts.append("connect")
        raise RuntimeError("CPU fixture execution must not make network connections")

    socket.socket.connect = socket.socket.connect_ex = no_network
    try:
        for variant, fix_a, fix_b in (("original", False, False), ("zero_only", True, False),
                                      ("prefix_only", False, True), ("both", True, True)):
            variant_source = source
            if fix_a:
                variant_source = variant_source.replace(FIX_A_OLD, FIX_A_NEW)
            if fix_b:
                variant_source = variant_source.replace(FIX_B_OLD, FIX_B_NEW)
            variant_path = output / f"logits_process_{variant}.py"
            variant_path.write_text(variant_source, encoding="utf-8")
            # The package-qualified name preserves actual relative imports.
            spec = importlib.util.spec_from_file_location(
                f"transformers.generation._zero_sequence_bias_{variant}", variant_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            S = module.SequenceBiasLogitsProcessor
            N = module.NoBadWordsLogitsProcessor
            context = {}

            def scores(batch):
                return torch.arange(batch * 6, dtype=torch.float32).reshape(batch, 6) / 4

            def check(processor, ids, changes):
                inputs = torch.tensor(ids, dtype=torch.long)
                logits = scores(inputs.shape[0])
                input_before, logits_before = inputs.clone(), logits.clone()
                expected = logits.clone()
                for row, col, delta in changes:
                    expected[row, col] += delta
                actual = processor(inputs, logits)
                context.setdefault("comparisons", []).append({"input_ids": ids,
                    "expected": json_values(expected), "actual": json_values(actual)})
                assert torch.equal(actual, expected), "full output tensor differs"
                assert torch.equal(inputs, input_before), "input_ids mutated"
                assert torch.equal(logits, logits_before), "scores mutated"
                return actual

            def round_trip(rules):
                with tempfile.TemporaryDirectory() as path:
                    GenerationConfig(sequence_bias=deepcopy(rules)).save_pretrained(path)
                    restored = GenerationConfig.from_pretrained(path, local_files_only=True)
                    serialized = json.loads((Path(path) / "generation_config.json").read_text())
                    assert restored.sequence_bias == rules
                    assert serialized["sequence_bias"] == rules
                    context["round_trip_sequence_bias"] = restored.sequence_bias
                    return restored.sequence_bias

            def zero_unigram_empty():
                dictionary = check(S({(0,): -1.25}), [[], []], [(0, 0, -1.25), (1, 0, -1.25)])
                listed = check(S([[[0], -1.25]]), [[], []], [(0, 0, -1.25), (1, 0, -1.25)])
                assert torch.equal(dictionary, listed)

            def zero_unigram_config():
                rules = round_trip([[[0], 0.75]])
                check(S(rules), [[1], [3]], [(0, 0, 0.75), (1, 0, 0.75)])

            def complete_prefix_additive():
                rules = {(1, 3, 4): -2.0, (3, 4): 0.5, (4,): 0.25}
                check(S(rules), [[1, 3], [2, 3], [3, 1]],
                      [(0, 4, -1.25), (1, 4, 0.75), (2, 4, 0.25)])

            def complete_prefix_badwords_eos():
                check(N([[0], [3, 4]], eos_token_id=0), [[3], [2]], [(0, 4, float("-inf"))])

            def zero_prefix_config_joint():
                rules = round_trip([[[0, 4], -2.5]])
                check(S(rules), [[0], [3]], [(0, 4, -2.5)])

            def insufficient_prefix_control():
                check(S({(1, 3, 4): -2.0}), [[3], [1]], [])
                check(S({(1, 3, 4): -2.0, (2,): 0.25}), [[], []], [(0, 2, 0.25), (1, 2, 0.25)])

            def longer_context_control():
                check(S({(3, 4): -2.5}), [[1, 3], [1, 2]], [(0, 4, -2.5)])

            def negative_id_control():
                for rules in ({(-1,): -1.0}, [[[-1], -1.0]]):
                    try:
                        S(rules)
                    except ValueError:
                        continue
                    raise AssertionError("negative ID unexpectedly accepted")

            def out_of_vocabulary_control():
                for rules in ({(6,): -1.0}, [[[6], -1.0]]):
                    try:
                        S(rules)(torch.tensor([[1]]), scores(1))
                    except ValueError:
                        continue
                    raise AssertionError("out-of-vocabulary ID unexpectedly accepted")

            def nonzero_unigram_control():
                check(S([[[2], 0.5], [[4], -1.25]]), [[3], [1]],
                      [(0, 2, 0.5), (1, 2, 0.5), (0, 4, -1.25), (1, 4, -1.25)])

            cases = [("zero_unigram_empty", "A", zero_unigram_empty),
                     ("zero_unigram_config", "A", zero_unigram_config),
                     ("complete_prefix_additive", "B", complete_prefix_additive),
                     ("complete_prefix_badwords_eos", "B", complete_prefix_badwords_eos),
                     ("zero_prefix_config_joint", "A+B", zero_prefix_config_joint),
                     ("insufficient_prefix_control", "control", insufficient_prefix_control),
                     ("longer_context_control", "control", longer_context_control),
                     ("negative_id_control", "control", negative_id_control),
                     ("out_of_vocabulary_control", "control", out_of_vocabulary_control),
                     ("nonzero_unigram_control", "control", nonzero_unigram_control)]
            for name, requirement, fn in cases:
                context = {}
                row = {"variant": variant, "case": name, "requirement": requirement}
                try:
                    fn()
                    row.update(passed=True)
                except Exception as exc:
                    row.update(passed=False, error_type=type(exc).__name__, error=str(exc))
                row.update(context)
                expected_pass = requirement == "control" or (requirement == "A" and fix_a) or (
                    requirement == "B" and fix_b) or (requirement == "A+B" and fix_a and fix_b)
                row["expected_pass"] = expected_pass
                row["matches_expected"] = row["passed"] == expected_pass
                observations.append(row)
                print("CHECK_ROW " + json.dumps(row, allow_nan=False), flush=True)
    finally:
        socket.socket.connect, socket.socket.connect_ex = previous_socket
    report = {"source_commit": SOURCE_COMMIT, "source_git_blob": blob,
              "source_sha256": hashlib.sha256(original_bytes).hexdigest(),
              "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "issue": "https://github.com/huggingface/transformers/issues/49093",
              "original_diagnosis_and_candidate_fixes": "lucaluo925",
              "supplemental_checking": "Zero, AI assistant collaborating with Youngseok Oh",
              "execution_kind": "complete actual package modules, actual CPU PyTorch; synthetic score fixtures",
              "new_model_inference_passes": 0, "network_attempts_during_checks": len(network_attempts),
              "python": platform.python_version(), "transformers": transformers.__version__,
              "versions": {name: importlib.metadata.version(name) for name in
                  ("torch", "transformers", "numpy", "huggingface-hub", "tokenizers", "safetensors")},
              "direct_url": importlib.metadata.distribution("transformers").read_text("direct_url.json"),
              "case_counts": {v: {"passed": sum(r["passed"] for r in observations if r["variant"] == v),
                                    "total": sum(r["variant"] == v for r in observations)}
                              for v in ("original", "zero_only", "prefix_only", "both")},
              "all_outcomes_match_predicted_matrix": all(r["matches_expected"] for r in observations),
              "rows": observations,
              "limits": ["Only logits processor CPU float32 fixtures; no full generate() or real model call.",
                         "Candidate edits are exactly the issue reporter's two source changes.",
                         "Not an upstream PR, accepted contribution, or external independent replication."]}
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("CHECK_SUMMARY " + json.dumps({k: v for k, v in report.items() if k != "rows"}, allow_nan=False), flush=True)
    assert len(observations) == 40
    assert not network_attempts
    assert report["all_outcomes_match_predicted_matrix"], "Unexpected matrix; inspect preserved results"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args().out)
