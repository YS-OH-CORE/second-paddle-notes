# SPDX-License-Identifier: Apache-2.0
"""Offline config-only review of an existing Transformers PR review question.
Original refactor: zucchini-nlp; review question: molbap.
Supplemental tests and execution: Zero x Youngseok Oh.
"""
import argparse
import copy
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import socket
import sys
import traceback

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', USE_TORCH='0')
sys.path.insert(0, str(args.source.resolve() / 'src'))
network_attempts = []

def audit(event, values):
    if event == 'socket.connect':
        network_attempts.append(str(values[1]))
        raise RuntimeError('External calls are forbidden in this config-only review')
sys.addaudithook(audit)
import transformers
from transformers import DetrConfig, DPTConfig, MaskFormerConfig, RTDetrConfig, ResNetConfig
assert Path(transformers.__file__).resolve() == args.source.resolve() / 'src/transformers/__init__.py'
LEGACY = dict(backbone='synthetic-unused-name', use_timm_backbone=False,
              use_pretrained_backbone=False, backbone_kwargs={})
MARKER = {'keep': ['unchanged', 17]}
rows = []
for cls in [DetrConfig, RTDetrConfig, MaskFormerConfig, DPTConfig]:
    for form in ['dict', 'object']:
        row = {'config': cls.__name__, 'input_form': form}
        directory = args.out / (cls.__name__ + '-' + form)
        directory.mkdir()
        try:
            sub = ResNetConfig(depths=[1, 1, 1, 1], hidden_sizes=[8, 16, 32, 64])
            supplied = sub.to_dict() if form == 'dict' else sub
            before = copy.deepcopy(supplied) if form == 'dict' else supplied.to_dict()
            config = cls(backbone_config=supplied, **copy.deepcopy(LEGACY),
                         review_marker=copy.deepcopy(MARKER))
            serialized = config.to_dict()
            reconstructed = cls.from_dict(copy.deepcopy(serialized))
            config.save_pretrained(directory)
            saved = json.loads((directory / 'config.json').read_text(encoding='utf-8'))
            reloaded = cls.from_pretrained(directory, local_files_only=True)
            snapshots = {'constructed': serialized, 'from_dict': reconstructed.to_dict(),
                         'saved_json': saved, 'from_pretrained': reloaded.to_dict()}
            leftovers = {phase: {key: value[key] for key in LEGACY if key in value}
                         for phase, value in snapshots.items()}
            variants = [config, reconstructed, reloaded]
            checks = {
                'legacy_options_consumed': all(not fields for fields in leftovers.values()),
                'unrelated_parent_metadata_preserved': all(c.review_marker == MARKER for c in variants),
                'backbone_preserved': all(isinstance(c.backbone_config, ResNetConfig) and
                    c.backbone_config.hidden_sizes == [8, 16, 32, 64] and
                    c.backbone_config.depths == [1, 1, 1, 1] for c in variants),
                'caller_input_unchanged': (supplied if form == 'dict' else supplied.to_dict()) == before,
            }
            row.update(legacy_by_phase=leftovers, checks=checks, passed=all(checks.values()))
        except Exception as exc:
            row.update(error_type=type(exc).__name__, error=str(exc), passed=False)
            (directory / 'traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
        rows.append(row)
assert not network_attempts, network_attempts
report = {'source': str(args.source.resolve()), 'transformers_version': transformers.__version__,
          'cases': rows, 'passed': sum(r['passed'] for r in rows),
          'failed': sum(not r['passed'] for r in rows),
          'network_attempts': network_attempts,
          'scope': 'configuration construction, dict reconstruction, local save/reload only',
          'packages': {n: metadata.version(n) for n in ['huggingface-hub', 'numpy', 'tokenizers']}}
(args.out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: report[k] for k in ['passed', 'failed', 'packages']}), flush=True)
sys.exit(0 if report['failed'] == 0 else 1)
