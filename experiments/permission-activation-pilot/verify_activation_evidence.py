#!/usr/bin/env python3
"""Offline audit of the frozen 2026-09-25 permission activation artifact.

Python standard library only. Reads the original ZIP without extracting or
executing its code. Does not run a model, download weights, or make network calls.
This checks internal consistency of one recorded run, not independent replication.

Usage:
  python verify_activation_evidence.py ORIGINAL.zip --output AUDIT.json --mutation-self-test
"""
from __future__ import annotations

import argparse
from array import array
import ast
from collections import Counter
from copy import deepcopy
import hashlib
from itertools import permutations
import json
import math
from pathlib import Path
import random
import statistics
import struct
import sys
import zipfile

EXPECTED_ZIP_SHA256 = "b1a19023d78b099ef72cb851bf62d52b4b6c837a19fabde7dda8638274a2dd2f"
EXPECTED_BASE_SHA256 = "9f22d6f753eceef2847be49076fa6ae8f60a0e967ed48a8e631706f84f4514c4"
EXPECTED_RUNNER_SHA256 = "c68bbbf60aa88d8e568be0aa095d071238ac83b77f13bed0a70136cc570ab5d8"
CHOICE_TOKEN_IDS = (32, 33, 34)  # A, B, C for the pinned Qwen tokenizer.
CASES = ("permission_cancel", "permission_restore")
LAYERS = (0, 11, 23)
MIN_GAP = 0.25
SEMANTIC_LABELS = {0: "keep_private", 1: "publish", 2: "no_decision"}
PROBABILITY_TOLERANCE = 2e-6  # original Torch softmax is float32
FULL_VOCAB_MASS_TOLERANCE = 1e-5  # 151,936-way float32 vs math.fsum/float64


class AuditFailure(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def close(actual, expected, label, tolerance=1e-12):
    require(math.isfinite(actual) and math.isfinite(expected), f"{label}: nonfinite number")
    require(abs(actual - expected) <= tolerance, f"{label}: {actual!r} != {expected!r}")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def literal_assignment(source, name):
    """Read a literal AST value; never import or exec the archived runner."""
    matches = [node for node in ast.parse(source).body
               if isinstance(node, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]
    require(len(matches) == 1, f"expected one literal assignment for {name}")
    return ast.literal_eval(matches[0].value)


def read_safetensors(data):
    """Parse the F32 safetensors format directly with struct and array."""
    require(len(data) >= 8, "truncated safetensors file")
    header_size = struct.unpack("<Q", data[:8])[0]
    require(header_size <= len(data) - 8, "invalid safetensors header size")
    header = json.loads(data[8:8 + header_size])
    payload = memoryview(data)[8 + header_size:]
    tensors, shapes, spans = {}, {}, []
    for key, spec in header.items():
        if key == "__metadata__":
            continue
        require(spec["dtype"] == "F32", f"unexpected dtype for {key}")
        start, end = spec["data_offsets"]
        shape = spec["shape"]
        require(0 <= start <= end <= len(payload), f"invalid offsets for {key}")
        require(end - start == 4 * math.prod(shape), f"shape/length mismatch for {key}")
        values = array("f")
        require(values.itemsize == 4, "platform float array must be 32-bit")
        values.frombytes(payload[start:end])
        if sys.byteorder != "little":
            values.byteswap()
        require(all(math.isfinite(v) for v in values), f"nonfinite tensor {key}")
        tensors[key], shapes[key] = values, shape
        spans.append((start, end))
    cursor = 0
    for start, end in sorted(spans):
        require(start == cursor, "safetensors offsets overlap or leave unused bytes")
        cursor = end
    require(cursor == len(payload), "trailing safetensors payload bytes")
    return tensors, shapes


def expected_grid(prompts):
    cells, schedule = set(), []
    for key in sorted(prompts):
        fixture = prompts[key]
        other_case = CASES[1] if fixture["case"] == CASES[0] else CASES[0]
        other = other_case + "_" + "".join(map(str, fixture["order"]))
        cells.add(("baseline", key, None, None, None))
        for layer in LAYERS:
            schedule.extend([("donor", key, other, layer, -1),
                             ("self_control", key, key, layer, -1)])
        schedule.append(("wrong_position_control", key, other, 23, -2))
    cells.update(schedule)
    random.Random(20260925).shuffle(schedule)
    return cells, [list(cell) for cell in schedule]


def row_key(row):
    return (row["kind"], row["target"], row.get("donor"),
            row.get("layer_zero_based"), row.get("position"))


def choice_stats(values, prompt):
    require(len(values) == 3 and all(math.isfinite(v) for v in values), "invalid ABC logits")
    order = prompt["order"]
    selected_letter = max(range(3), key=values.__getitem__)
    selected_semantic = order[selected_letter]
    exp_values = [math.exp(v - max(values)) for v in values]
    denominator = math.fsum(exp_values)
    return {
        "selected_letter": "ABC"[selected_letter],
        "selected_semantic_id": selected_semantic,
        "selected_semantic": SEMANTIC_LABELS[selected_semantic],
        "correct": selected_semantic == prompt["gold"],
        "private_minus_publish": values[order.index(0)] - values[order.index(1)],
        "conditional_probs": [v / denominator for v in exp_values],
    }


def validate_observations(rows, prompts):
    """Recompute every recorded ABC outcome and intervention contrast."""
    expected, _ = expected_grid(prompts)
    require(len(rows) == 96, f"row count: expected 96, got {len(rows)}")
    keys = [row_key(row) for row in rows]
    require(len(set(keys)) == 96, "duplicate experiment cell")
    require(set(keys) == expected, "missing or unexpected experiment cell")
    require([r["target"] for r in rows[:12]] == sorted(prompts), "baseline order mismatch")
    require(all(r["kind"] == "baseline" for r in rows[:12]), "baseline prefix mismatch")
    baseline = {r["target"]: r for r in rows if r["kind"] == "baseline"}
    stats = {}
    max_conditional_error = 0.0
    for index, row in enumerate(rows):
        key = row["target"]
        computed = choice_stats(row["choice_logits"], prompts[key])
        for field in ("selected_semantic_id", "correct"):
            require(row[field] == computed[field], f"row {index} {field} disagrees with logits")
        close(row["private_minus_publish"], computed["private_minus_publish"], f"row {index} margin")
        require(len(row["conditional_probs"]) == 3, "conditional probability length mismatch")
        for actual, expected_prob in zip(row["conditional_probs"], computed["conditional_probs"]):
            close(actual, expected_prob, f"row {index} probability", PROBABILITY_TOLERANCE)
            max_conditional_error = max(max_conditional_error, abs(actual - expected_prob))
        require(0.0 < row["abc_probability_mass"] <= 1.0, "invalid ABC probability mass")
        # These recorded unconstrained choices are all A/B/C. For interventions,
        # full tensors were not saved, so this is an internal consistency check.
        require(row["unconstrained_token"] == computed["selected_letter"],
                f"row {index} recorded unconstrained token mismatch")
        if row["kind"] != "baseline":
            before = choice_stats(baseline[key]["choice_logits"], prompts[key])["private_minus_publish"]
            donor_margin = choice_stats(baseline[row["donor"]]["choice_logits"], prompts[key])["private_minus_publish"]
            gap = donor_margin - before
            shift = computed["private_minus_publish"] - before
            close(row["donor_margin_gap"], gap, f"row {index} donor gap")
            close(row["intervention_margin_shift"], shift, f"row {index} intervention shift")
            if abs(gap) < MIN_GAP:
                require(row["gap_fraction"] is None, f"row {index} ineligible fraction must be null")
            else:
                require(row["gap_fraction"] is not None, f"row {index} missing eligible fraction")
                close(row["gap_fraction"], shift / gap, f"row {index} gap fraction")
            for field, reference in (("max_full_vocab_diff_from_target", baseline[key]),
                                     ("max_full_vocab_diff_from_donor", baseline[row["donor"]])):
                recorded = row[field]
                require(math.isfinite(recorded) and recorded >= 0, f"row {index} invalid full-vocab diff")
                abc_diff = max(abs(a - b) for a, b in zip(row["choice_logits"], reference["choice_logits"]))
                require(recorded + 1e-12 >= abc_diff, f"row {index} full-vocab diff below observed ABC diff")
        stats[row_key(row)] = computed
    return baseline, stats, max_conditional_error


def audit(archive, mutation_self_test=False):
    archive_bytes = archive.read_bytes()
    actual_zip_sha = sha256(archive_bytes)
    require(actual_zip_sha == EXPECTED_ZIP_SHA256, "original artifact ZIP SHA-256 mismatch")
    with zipfile.ZipFile(archive) as zipped:
        names = [entry.filename for entry in zipped.infolist() if not entry.is_dir()]
        require(len(names) == len(set(names)), "duplicate ZIP member names")
        files = {name: zipped.read(name) for name in names}
    file_hashes = {name: sha256(data) for name, data in sorted(files.items())}
    require(file_hashes["pilot.py"] == EXPECTED_BASE_SHA256, "pilot identity mismatch")
    require(file_hashes["probe.py"] == EXPECTED_RUNNER_SHA256, "probe identity mismatch")
    report = json.loads(files["inference/report.json"])
    metadata = json.loads(files["run_metadata.json"])
    prompts = json.loads(files["inference/prompts.json"])
    rows = [json.loads(line) for line in files["inference/raw.jsonl"].decode().splitlines()]
    config = json.loads(files["inference/model_config.json"])
    for record in metadata["inputs"]:
        require(file_hashes[record["file"]] == record["sha256"], f"input hash mismatch: {record['file']}")
    require(report["base_sha256"] == EXPECTED_BASE_SHA256, "report base hash mismatch")
    require(report["runner_sha256"] == EXPECTED_RUNNER_SHA256, "report runner hash mismatch")
    require(report["model"] == literal_assignment(files["pilot.py"], "MODEL"), "model mismatch")
    require(report["revision"] == literal_assignment(files["pilot.py"], "REVISION"), "revision mismatch")
    require(tuple(literal_assignment(files["probe.py"], "LAYERS")) == LAYERS, "source layer mismatch")
    require(literal_assignment(files["probe.py"], "MIN_MARGIN_GAP") == MIN_GAP, "source gap threshold mismatch")
    require(report["layers_zero_based"] == list(LAYERS), "report layer mismatch")

    # Reconstruct chronology messages independently from literal fixture values.
    cases = {c["id"]: c for c in literal_assignment(files["pilot.py"], "CASES")}
    system = literal_assignment(files["pilot.py"], "SYSTEM")
    expected_prompt_names = set()
    for case_id in CASES:
        case = cases[case_id]
        for order in permutations(range(3)):
            key = case_id + "_" + "".join(map(str, order))
            expected_prompt_names.add(key)
            prompt = prompts[key]
            require(prompt["case"] == case_id and prompt["order"] == list(order), f"prompt identity {key}")
            require(prompt["gold"] == case["gold"], f"prompt gold {key}")
            chronology = "\n".join(f"e{i} {role.upper()}: {text}"
                                    for i, (role, text) in enumerate(case["messages"], 1))
            options = "\n".join(f"{letter}. {case['answers'][choice]}"
                                  for letter, choice in zip("ABC", order))
            text = (f"Conversation in time order:\n{chronology}\n\n"
                    f"Question: {case['question']}\n{options}\nSelect one letter.")
            messages = [{"role": "system", "content": system}, {"role": "user", "content": text}]
            require(prompt["messages"] == messages, f"fixture text/order mismatch {key}")
            rendered = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages)
            rendered += "<|im_start|>assistant\n"
            require(prompt["rendered_prompt"] == rendered, f"rendered chat template mismatch {key}")
            require(prompt["tokens"] == len(prompt["input_ids"]), f"stored token count mismatch {key}")
    require(set(prompts) == expected_prompt_names, "unexpected prompt keys")
    baseline, stats, conditional_error = validate_observations(rows, prompts)
    _, expected_schedule = expected_grid(prompts)
    actual_schedule = [list(row_key(row)) for row in rows if row["kind"] != "baseline"]
    require(actual_schedule == expected_schedule, "raw randomized schedule mismatch")
    require(report["intervention_schedule"] == expected_schedule, "report schedule mismatch")

    log_lines = files["execution.log"].decode().splitlines()
    logged_rows = [json.loads(line[len("ACTIVATION_ROW "):]) for line in log_lines if line.startswith("ACTIVATION_ROW ")]
    require(logged_rows == rows, "execution log rows differ from raw JSONL")
    logged_reports = [json.loads(line[len("ACTIVATION_REPORT "):]) for line in log_lines if line.startswith("ACTIVATION_REPORT ")]
    require(len(logged_reports) == 1, "expected one recorded inference report")
    require(logged_reports[0] == {k: v for k, v in report.items() if k != "intervention_schedule"},
            "execution log report differs from report.json")
    require(report["success"] is True, "recorded run was unsuccessful")
    for field in ("completed_forward_passes", "planned_forward_passes", "rows_written"):
        require(report[field] == 96, f"report {field} mismatch")
    require(report["sampling"] is False and report["training"] is False, "unexpected run mode")
    require(report["network_attempts_during_inference"] == 0, "recorded inference socket attempts nonzero")

    logits, logit_shapes = read_safetensors(files["inference/baseline_logits.safetensors"])
    activations, activation_shapes = read_safetensors(files["inference/baseline_activations.safetensors"])
    require(set(logits) == set(prompts), "baseline tensor key mismatch")
    expected_activation_keys = {f"{key}.L{layer}.P{position}" for key in prompts for layer in LAYERS for position in (-1, -2)}
    require(set(activations) == expected_activation_keys, "activation tensor key mismatch")
    require(all(shape == [config["vocab_size"]] for shape in logit_shapes.values()), "logit shape mismatch")
    require(all(shape == [1, config["hidden_size"]] for shape in activation_shapes.values()), "activation shape mismatch")
    require(config["hidden_size"] == 896 and config["num_hidden_layers"] == 24, "model dimensions mismatch")
    abc_mass_error = 0.0
    recomputed_baseline_abc_masses = {}
    for key, values in logits.items():
        row = baseline[key]
        require([values[index] for index in CHOICE_TOKEN_IDS] == row["choice_logits"], f"baseline tensor ABC mismatch {key}")
        best = max(range(len(values)), key=values.__getitem__)
        require(best in CHOICE_TOKEN_IDS, f"baseline full argmax is not ABC {key}")
        require("ABC"[CHOICE_TOKEN_IDS.index(best)] == row["unconstrained_token"], f"full argmax mismatch {key}")
        maximum = values[best]
        denominator = math.fsum(math.exp(value - maximum) for value in values)
        mass = math.fsum(math.exp(values[index] - maximum) for index in CHOICE_TOKEN_IDS) / denominator
        close(row["abc_probability_mass"], mass, f"baseline full-vocab ABC mass {key}", FULL_VOCAB_MASS_TOLERANCE)
        abc_mass_error = max(abc_mass_error, abs(row["abc_probability_mass"] - mass))
        recomputed_baseline_abc_masses[key] = {"recorded_float32": row["abc_probability_mass"],
                                              "recomputed_stdlib_float64": mass,
                                              "recorded_minus_recomputed": row["abc_probability_mass"] - mass}
        require(report["baseline"][key] == {k: v for k, v in row.items() if k not in ("kind", "target")},
                f"report baseline mismatch {key}")

    per_order = []
    for order in permutations(range(3)):
        suffix = "".join(map(str, order))
        pair = []
        for case_id in CASES:
            key = case_id + "_" + suffix
            computed = stats[("baseline", key, None, None, None)]
            pair.append({"target": key, "tokens": prompts[key]["tokens"],
                         **{k: computed[k] for k in ("selected_letter", "selected_semantic_id", "selected_semantic", "correct", "private_minus_publish")}})
        delta = pair[1]["private_minus_publish"] - pair[0]["private_minus_publish"]
        per_order.append({"order": suffix, "letter_to_semantic": [SEMANTIC_LABELS[i] for i in order],
                          "cancel": pair[0], "restore": pair[1],
                          "restore_minus_cancel_private_publish_margin": delta,
                          "hard_semantic_choice_changes": pair[0]["selected_semantic_id"] != pair[1]["selected_semantic_id"]})
    layer_summary = {}
    for layer in LAYERS:
        selected = [r for r in rows if r["kind"] == "donor" and r["layer_zero_based"] == layer]
        # Fractions have already been independently recalculated and matched.
        fractions = [r["gap_fraction"] for r in selected if r["gap_fraction"] is not None]
        shifts = [r["intervention_margin_shift"] for r in selected]
        changed = sum(r["selected_semantic_id"] != baseline[r["target"]]["selected_semantic_id"] for r in selected)
        original = report["interventions"][str(layer)]
        require(original["paired_directions"] == len(selected), "report layer count mismatch")
        require(original["changed_semantic_choices"] == changed, "report layer choices mismatch")
        require(original["fraction_eligible"] == len(fractions), "report fraction count mismatch")
        require(original["gap_fractions"] == fractions, "report fraction values mismatch")
        close(original["median_gap_fraction"], statistics.median(fractions), "report median fraction")
        layer_summary[str(layer)] = {
            "donor_cells": len(selected), "changed_hard_semantic_choices": changed,
            "correct_after_swap": sum(r["correct"] for r in selected),
            "eligible_gap_fractions": len(fractions),
            "excluded_orders_for_gap_fraction": sorted({r["target"].rsplit("_", 1)[1] for r in selected if r["gap_fraction"] is None}),
            "median_gap_fraction": statistics.median(fractions),
            "gap_fraction_range": [min(fractions), max(fractions)],
            "toward_donor_count_eligible": sum(v > 0 for v in fractions),
            "away_from_donor_count_eligible": sum(v < 0 for v in fractions),
            "zero_fraction_count_eligible": sum(v == 0 for v in fractions),
            "intervention_margin_shift_range": [min(shifts), max(shifts)],
            "maximum_absolute_margin_shift": max(map(abs, shifts)),
            "mean_absolute_margin_shift": statistics.mean(map(abs, shifts)),
            "cells": [{k: r[k] for k in ("target", "donor", "selected_semantic_id", "correct", "private_minus_publish", "donor_margin_gap", "intervention_margin_shift", "gap_fraction")} for r in sorted(selected, key=lambda r: r["target"])],
        }

    control_summary = {}
    for kind, field, summary_field, use_donor in (
        ("self_control", "max_full_vocab_diff_from_target", "self_control_max_diff", False),
        ("wrong_position_control", "max_full_vocab_diff_from_target", "wrong_position_max_diff", False),
        ("donor", "max_full_vocab_diff_from_donor", "positive_control_max_diff", True),
    ):
        selected = [r for r in rows if r["kind"] == kind and (not use_donor or r["layer_zero_based"] == 23)]
        maximum = max(r[field] for r in selected)
        require(maximum == 0.0, f"nonzero recorded exact control {kind}")
        close(report[summary_field], maximum, f"report {summary_field}")
        reference = "donor" if use_donor else "target"
        require(all(r["choice_logits"] == baseline[r[reference]]["choice_logits"] for r in selected),
                f"saved ABC control mismatch {kind}")
        label = "last_block_final_position_donor" if use_donor else kind
        control_summary[label] = {
            "cells": len(selected), "independently_checked_saved_ABC_logits_exact_match": True,
            "recorded_full_vocab_max_abs_difference": maximum,
            "full_vocab_difference_recomputed_from_patched_tensor": False,
        }

    mutation_tests = []
    if mutation_self_test:
        tests = []
        missing = deepcopy(rows[:-1])
        tests.append(("missing_one_recorded_row", missing))
        changed = deepcopy(rows)
        changed[0]["selected_semantic_id"] = (changed[0]["selected_semantic_id"] + 1) % 3
        tests.append(("changed_semantic_label_without_changing_logits", changed))
        for label, mutated in tests:
            try:
                validate_observations(mutated, prompts)
            except AuditFailure as exc:
                mutation_tests.append({"mutation": label, "detected": True, "reason": str(exc)})
            else:
                raise AuditFailure(f"mutation test failed to reject: {label}")

    deltas = [p["restore_minus_cancel_private_publish_margin"] for p in per_order]
    baseline_correct = {case_id: sum(r["correct"] for r in baseline.values() if prompts[r["target"]]["case"] == case_id) for case_id in CASES}
    later_relevant = sum(prompts[r["target"]]["order"].index(r["selected_semantic_id"]) == max(prompts[r["target"]]["order"].index(0), prompts[r["target"]]["order"].index(1)) for r in baseline.values())
    return {
        "audit_schema": "zero-permission-activation-evidence-audit-v1",
        "success": True,
        "verification_kind": "offline internal-consistency audit of original recorded evidence; not independent model replication",
        "artifact_sha256": actual_zip_sha,
        "file_sha256": file_hashes,
        "recorded_run_provenance": metadata,
        "model": report["model"], "model_revision": report["revision"],
        "recorded_weights_sha256": report["weights_sha256"],
        "original_model_weights_independently_rehashed": False,
        "source_code_executed": False, "new_model_forward_passes": 0,
        "choice_token_ids": dict(zip("ABC", CHOICE_TOKEN_IDS)),
        "tokenizer_reexecuted": False,
        "checks": {
            "original_zip_sha256_matches": True, "input_source_hashes_match_metadata": True,
            "prompts_match_literal_source_fixtures": True,
            "raw_unique_cells": len({row_key(row) for row in rows}),
            "recorded_row_counts": dict(Counter(r["kind"] for r in rows)),
            "complete_prespecified_grid": True, "randomized_schedule_matches": True,
            "execution_log_rows_exactly_match_raw_jsonl": True,
            "execution_log_report_matches_report_json": True,
            "report_baselines_and_layer_statistics_match": True,
            "baseline_logit_tensors": len(logits), "baseline_full_vocabulary_size": config["vocab_size"],
            "baseline_activation_tensors": len(activations), "activation_shape": [1, config["hidden_size"]],
            "all_saved_tensors_finite": True,
            "full_baseline_tensor_ABC_logits_and_argmax_match": True,
            "maximum_baseline_full_softmax_mass_numerical_difference": abc_mass_error,
            "full_softmax_mass_comparison_tolerance": FULL_VOCAB_MASS_TOLERANCE,
            "baseline_full_softmax_mass_comparisons": recomputed_baseline_abc_masses,
            "maximum_ABC_conditional_softmax_numerical_difference_all_rows": conditional_error,
        },
        "baseline_summary": {
            "correct_by_case_out_of_6": baseline_correct,
            "total_correct_out_of_12": sum(baseline_correct.values()),
            "same_hard_semantic_choice_pairs_out_of_6": sum(not x["hard_semantic_choice_changes"] for x in per_order),
            "restore_margin_moves_toward_publish_pairs_out_of_6": sum(delta < 0 for delta in deltas),
            "restore_minus_cancel_margin_range": [min(deltas), max(deltas)],
            "restore_minus_cancel_margin_mean": statistics.mean(deltas),
            "restore_minus_cancel_margin_median": statistics.median(deltas),
            "later_of_private_or_publish_option_selected_out_of_12": later_relevant,
            "letter_counts": dict(Counter(stats[("baseline", k, None, None, None)]["selected_letter"] for k in baseline)),
            "baseline_ABC_mass_range": [min(r["abc_probability_mass"] for r in baseline.values()), max(r["abc_probability_mass"] for r in baseline.values())],
        },
        "baseline_per_order": per_order,
        "interventions_by_zero_based_layer": layer_summary,
        "controls": control_summary,
        "mutation_tests": mutation_tests,
        "limitations": [
            "One reused fictional conversation pair across six answer orders; 12 baselines are not 12 independent stories.",
            "Cancel and restore prompts contain 172 and 168 stored tokens and differ in multiple statements; the wording and length confounds are not isolated.",
            "All margins moving in the expected direction is descriptive within this fixture, not a population statistical test or evidence of a specific mechanism.",
            "Entire 896-dimensional final-position residual vectors are swapped. Null intermediate hard-choice effects do not establish absence of information or causal influence elsewhere.",
            "Last-block final-position output replacement is an architecture-level positive control, not discovery of a decision or memory circuit.",
            "Only baseline full-vocabulary logits are saved as tensors. Patched full-vocabulary differences, patched unconstrained argmax, and patched ABC mass remain recorded claims cross-checked against logs and saved ABC scores, not independently tensor-recomputed values.",
            "Model weights are not in this evidence bundle; their recorded hash and runtime/no-network statements were not independently verified by this offline audit.",
            "Baseline full-vocabulary ABC masses differ by up to 6.28e-6 between recorded float32 Torch and stdlib float64/fSum computation. The audit's initial 2e-6 probability tolerance was too tight for these large reductions; it uses and reports 1e-5 for this comparison only. Exact logit, margin, choice and recorded control checks are unchanged.",
            "A passing ZIP hash and audit prove consistency with the specified artifact, not external provenance authenticity, independent reproduction, or scientific novelty.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="original SHA-pinned artifact ZIP")
    parser.add_argument("--output", type=Path, help="write full audit JSON here; otherwise print it")
    parser.add_argument("--mutation-self-test", action="store_true", help="also check detection of two in-memory evidence mutations")
    args = parser.parse_args()
    result = audit(args.archive, args.mutation_self_test)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
        print(json.dumps({"success": True, "output": str(args.output), "unique_cells": result["checks"]["raw_unique_cells"],
                          "mutation_tests": result["mutation_tests"]}, ensure_ascii=False))
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
