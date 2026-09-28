"""Compare intermediate dual-tangent mutation with eager execution.

Run in a disposable CPU PyTorch environment after applying either source variant.
This tests the Python dispatch_functionalize path from PR 192656 only.
"""

import atexit
import hashlib
import json
import platform
from pathlib import Path

import torch
import torch.autograd.forward_ad as fwAD
import torch._subclasses.functional_tensor as functional_tensor
from torch.testing._internal.common_utils import run_tests, TestCase


OBSERVATIONS = []
STATUSES = {}


def observe(mode, variant):
    primal = torch.tensor([1.0, 2.0], dtype=torch.float64)
    tangent = torch.tensor([3.0, 4.0], dtype=torch.float64)

    def f(dual):
        work = dual * 2
        inspected = fwAD.unpack_dual(work).tangent
        if inspected is None:
            raise RuntimeError("unpack_dual returned no tangent for intermediate dual")
        if variant == "mutate":
            inspected.add_(10)
        elif variant == "clone":
            inspected.clone().add_(10)
        elif variant != "readonly":
            raise ValueError(variant)
        return work * 3

    function = f if mode == "eager" else functional_tensor.dispatch_functionalize(f)
    entry = {"mode": mode, "variant": variant}
    try:
        with fwAD.dual_level():
            dual = fwAD.make_dual(primal, tangent)
            result = function(dual)
            result_primal, result_tangent = fwAD.unpack_dual(result)
            entry.update(
                primal=result_primal.tolist(),
                tangent=None if result_tangent is None else result_tangent.tolist(),
                input_primal_after=primal.tolist(),
                input_tangent_after=tangent.tolist(),
            )
    except Exception as error:
        entry.update(error_type=type(error).__name__, error=str(error))
        OBSERVATIONS.append(entry)
        raise
    OBSERVATIONS.append(entry)
    return entry


class TestIntermediateTangentAlias(TestCase):
    def run(self, result=None):
        active_result = result if result is not None else self.defaultTestResult()
        returned = super().run(active_result)
        state = "ok"
        detail = None
        for attribute, label in (
            ("failures", "FAIL"),
            ("errors", "ERROR"),
            ("skipped", "SKIP"),
            ("expectedFailures", "EXPECTED_FAILURE"),
        ):
            for test, explanation in getattr(active_result, attribute, []):
                if test is self or test.id() == self.id():
                    state, detail = label, explanation
        for entry in getattr(active_result, "unexpectedSuccesses", []):
            test = entry[0] if isinstance(entry, tuple) else entry
            if test is self or test.id() == self.id():
                state = "UNEXPECTED_SUCCESS"
        STATUSES[self._testMethodName] = {"state": state, "detail": detail}
        return returned

    def test_eager_oracle(self):
        mutated = observe("eager", "mutate")
        cloned = observe("eager", "clone")
        self.assertEqual(mutated["primal"], [6.0, 12.0])
        self.assertEqual(mutated["tangent"], [48.0, 54.0])
        self.assertEqual(cloned["tangent"], [18.0, 24.0])
        self.assertEqual(mutated["input_primal_after"], [1.0, 2.0])
        self.assertEqual(mutated["input_tangent_after"], [3.0, 4.0])

    def compare_with_eager(self, variant):
        expected = observe("eager", variant)
        actual = observe("functional", variant)
        self.assertEqual(actual["primal"], expected["primal"])
        self.assertEqual(actual["input_primal_after"], expected["input_primal_after"])
        self.assertEqual(actual["input_tangent_after"], expected["input_tangent_after"])
        self.assertEqual(actual["tangent"], expected["tangent"])

    def test_readonly_matches_eager(self):
        self.compare_with_eager("readonly")

    def test_clone_mutation_matches_eager(self):
        self.compare_with_eager("clone")

    def test_intermediate_tangent_mutation_matches_eager(self):
        self.compare_with_eager("mutate")


def report():
    sources = {}
    for module in (fwAD, functional_tensor):
        path = Path(module.__file__).resolve()
        sources[module.__name__] = {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    print(
        "FORWARDAD_OBSERVATIONS="
        + json.dumps(
            {
                "torch_version": torch.__version__,
                "binary_git_version": torch.version.git_version,
                "python": platform.python_version(),
                "cuda_available": torch.cuda.is_available(),
                "cuda_build": torch.version.cuda,
                "hip_build": torch.version.hip,
                "sources": sources,
                "observations": OBSERVATIONS,
                "statuses": STATUSES,
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    atexit.register(report)
    run_tests()
