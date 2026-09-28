# SPDX-License-Identifier: Apache-2.0
"""Configuration-only regression checks for Transformers PR #48282.

Original independent tests: Zero × Youngseok Oh. No model is instantiated.
"""

import copy
import json
import os
import platform
from pathlib import Path
import sys
import tempfile
import unittest

import transformers
from transformers import (
    BarkCoarseConfig,
    BarkConfig,
    BarkFineConfig,
    BarkSemanticConfig,
    EncodecConfig,
    LlavaConfig,
    MistralConfig,
    SiglipVisionConfig,
)
from transformers.models.auto.configuration_auto import CONFIG_MAPPING


PARTS = {
    "semantic_config": BarkSemanticConfig,
    "coarse_acoustics_config": BarkCoarseConfig,
    "fine_acoustics_config": BarkFineConfig,
}
SMALL = {
    "hidden_size": 24,
    "num_heads": 4,
    "num_layers": 2,
    "block_size": 64,
    "input_vocab_size": 101,
    "output_vocab_size": 103,
    "review_tag": "synthetic-config-roundtrip",
}
OBSERVED = {}


def instance_inputs():
    return {**{key: cls(**SMALL) for key, cls in PARTS.items()}, "codec_config": EncodecConfig()}


def check_bark(case, config):
    for key, cls in PARTS.items():
        actual = getattr(config, key)
        case.assertIs(type(actual), cls)
        for field, expected in SMALL.items():
            case.assertEqual(getattr(actual, field), expected)
    case.assertIs(type(config.codec_config), EncodecConfig)


class BarkConfigChecks(unittest.TestCase):
    def test_default_construction(self):
        config = BarkConfig()
        for key, cls in PARTS.items():
            self.assertIs(type(getattr(config, key)), cls)
        self.assertIs(type(config.codec_config), EncodecConfig)

    def test_instance_input_control(self):
        check_bark(self, BarkConfig(**instance_inputs()))

    def test_dict_roundtrip_from_instances(self):
        config = BarkConfig(**instance_inputs())
        serialized = config.to_dict()
        original = copy.deepcopy(serialized)
        restored = BarkConfig.from_dict(serialized)
        check_bark(self, restored)
        self.assertEqual(serialized, original)

    def test_local_save_reload_from_instances(self):
        config = BarkConfig(**instance_inputs())
        with tempfile.TemporaryDirectory() as directory:
            config.save_pretrained(directory)
            saved = json.loads((Path(directory) / "config.json").read_text())
            OBSERVED["saved_bark_model_types"] = {
                key: saved[key]["model_type"] for key in PARTS
            }
            restored = BarkConfig.from_pretrained(directory, local_files_only=True)
        check_bark(self, restored)

    def test_llava_default_auto_config_control(self):
        config = LlavaConfig()
        restored = LlavaConfig.from_dict(config.to_dict())
        for actual in (config, restored):
            self.assertEqual(actual.vision_config.model_type, "clip_vision_model")
            self.assertEqual(actual.text_config.model_type, "llama")

    def test_llava_explicit_auto_config_override_control(self):
        inputs = {
            "vision_config": {"model_type": "siglip_vision_model", "hidden_size": 32,
                              "intermediate_size": 64, "num_hidden_layers": 2,
                              "num_attention_heads": 4},
            "text_config": {"model_type": "mistral", "hidden_size": 32,
                            "intermediate_size": 64, "num_hidden_layers": 2,
                            "num_attention_heads": 4, "num_key_value_heads": 2},
        }
        original = copy.deepcopy(inputs)
        config = LlavaConfig(**inputs)
        with tempfile.TemporaryDirectory() as directory:
            config.save_pretrained(directory)
            restored = LlavaConfig.from_pretrained(directory, local_files_only=True)
        self.assertEqual(inputs, original)
        for actual in (config, restored):
            self.assertIs(type(actual.vision_config), SiglipVisionConfig)
            self.assertIs(type(actual.text_config), MistralConfig)
            self.assertEqual(actual.vision_config.hidden_size, 32)
            self.assertEqual(actual.text_config.num_key_value_heads, 2)


def dict_case(key, cls, with_model_type):
    def test(self):
        values = dict(SMALL)
        if with_model_type:
            values["model_type"] = cls.model_type
        original = copy.deepcopy(values)
        inputs = instance_inputs()
        inputs[key] = values
        config = BarkConfig(**inputs)
        check_bark(self, config)
        self.assertEqual(values, original)
    return test


for part, part_class in PARTS.items():
    for explicit in (False, True):
        setattr(BarkConfigChecks, f"test_dict_{part}_model_type_{explicit}",
                dict_case(part, part_class, explicit))


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"test": test._testMethodName, "status": "pass"})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"test": test._testMethodName, "status": "error",
                             "exception": err[0].__name__,
                             "message_prefix": str(err[1]).split(". Should contain one of")[0]})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"test": test._testMethodName, "status": "failure",
                             "exception": err[0].__name__, "message_prefix": str(err[1])})


if __name__ == "__main__":
    source = Path(os.environ["CHECK_SOURCE"]).resolve()
    module_path = Path(transformers.__file__).resolve()
    assert module_path.is_relative_to(source / "src"), module_path
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BarkConfigChecks)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    payload = {
        "python": platform.python_version(), "transformers": transformers.__version__,
        "source_module": str(module_path), "tests_run": result.testsRun,
        "passed": result.testsRun - len(result.errors) - len(result.failures) - len(result.skipped),
        "errors": len(result.errors), "failures": len(result.failures), "skipped": len(result.skipped),
        "mapping_contains": {cls.model_type: cls.model_type in CONFIG_MAPPING for cls in PARTS.values()},
        "observed": OBSERVED, "tests": result.records,
        "scope": "Configuration only; no weights, forward pass, GPU, or Hub checkpoint",
    }
    Path(sys.argv[1]).write_text(json.dumps(payload, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
