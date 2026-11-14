"""Export the frozen student policy for the browser.

The browser receives one recurrent graph whose outputs are the 15-value R15
pose, its 128-value hidden state, and the SearchHead heat/offset/presence/
evidence/identity tensors.  The Pyodide controller decodes the search tensors
and runs the sensor-only search/radio/pre360 state machine.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[3]
R15 = ROOT / 'artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15'
STUDENT = ROOT / 'benchmark/policies/student/output_optimized'
sys.path.insert(0, str(ROOT / 'benchmark/policies/student'))
import common
common.REPO = ROOT
common.R15 = R15
common.LOCAL = ROOT / 'artifacts/local_curriculum_20261020'
from model import SearchHead
from common import r15_module

Base = r15_module('radio_robust_20261015.model').RadioRobustPoseModel


class SpatialMean(nn.Module):
    def forward(self, value):
        n, c, h, w = value.shape
        return value.reshape(n, c, h * w).mean(-1).reshape(n, c, 1, 1)


def parallel_means(module):
    for name, child in list(module.named_children()):
        if isinstance(child, nn.AdaptiveAvgPool2d) and child.output_size in (1, (1, 1)):
            setattr(module, name, SpatialMean())
        else:
            parallel_means(child)


class BrowserStudent(nn.Module):
    def __init__(self, base, head):
        super().__init__()
        self.base = base
        self.head = head

    def forward(self, image, numeric, hidden):
        b = self.base.backbone
        x = image.reshape(1, 3, 360, 640) / 255.
        x = (x - b.image_mean) / b.image_std
        fine = None
        for index, layer in enumerate(b.encoder):
            x = layer(x)
            if index == 3:
                fine = x
            if index == 8:
                context = x
        channels, height, width = x.shape[1:]
        probability = x.reshape(1, channels, -1).softmax(-1)
        yy, xx = torch.meshgrid(torch.linspace(-1, 1, height), torch.linspace(-1, 1, width), indexing='ij')
        features = torch.stack(((probability * xx.flatten()).sum(-1), (probability * yy.flatten()).sum(-1), x.mean((2, 3))), -1).reshape(1, 1, -1)
        n = numeric[..., :32]
        visual = n * n.new_tensor([0. if i in (*range(11, 17), 19, 21, 22) else 1. for i in range(32)])
        visual = visual + torch.cat((torch.zeros_like(n[..., :19]), torch.full_like(n[..., 19:20], 3.1), torch.zeros_like(n[..., 20:22]), b.observation_mean[22:23].reshape(1, 1, 1), torch.zeros_like(n[..., 23:])), dim=-1)
        angles = torch.cat((visual[..., 5:6], visual[..., 9:11]), -1)
        trig = torch.stack((angles.sin(), angles.cos()), -1).reshape(1, 1, 6)
        represented = visual * visual.new_tensor([0. if i in (5, 9, 10, 24, 25, 26, 27, 28, 29) else 1. for i in range(32)]) + torch.cat((torch.zeros_like(n[..., :24]), trig, torch.zeros_like(n[..., 30:])), dim=-1)
        normalized = (represented - b.observation_mean) / b.observation_std
        normalized = torch.cat((normalized[..., :11], torch.zeros_like(n[..., 11:17]), normalized[..., 17:19], normalized[..., 19:20].clamp(-10., 10.), normalized[..., 20:21], -torch.ones_like(n[..., 21:22]), normalized[..., 22:]), -1)
        state = b.telemetry(normalized) + self.base.quality(torch.log1p(n.new_tensor([100., 10.])) - torch.log1p(n.new_tensor([.25, .025])))
        gi = F.linear(torch.cat((b.visual(features), state), -1), b.gru.weight_ih_l0, b.gru.bias_ih_l0)
        gh = F.linear(hidden, b.gru.weight_hh_l0, b.gru.bias_hh_l0)
        reset = (gi[..., :128] + gh[..., :128]).sigmoid()
        update = (gi[..., 128:256] + gh[..., 128:256]).sigmoid()
        next_hidden = (1 - update) * torch.tanh(gi[..., 256:] + reset * gh[..., 256:]) + update * hidden
        raw = b.auxiliary(next_hidden)
        absolute = self.base.visual_absolute(next_hidden)
        prediction = torch.cat((raw[..., :1], absolute[..., :3], absolute[..., 3:6] - n[..., :3], F.normalize(raw[..., 7:9], dim=-1, eps=1e-6), F.normalize(raw[..., 9:12] + raw.new_tensor([0., 0., -1.]), dim=-1, eps=1e-6), raw[..., 12:15]), -1)
        out = self.head(fine, context)
        return (prediction, next_hidden, out['heat'], out['offset'], out['presence'].reshape(1, 1), out['evidence'], out['identity'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'tidewater-game/app/public/policy/student')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    base = Base()
    saved = torch.load(STUDENT / 'base/pose.pt', map_location='cpu', weights_only=False)
    base.load_state_dict(saved['model'], strict=True)
    base.eval()
    head = SearchHead(initialize=False)
    sh = torch.load(STUDENT / 'search_best.pt', map_location='cpu', weights_only=False)
    head.load_state_dict(sh['model'], strict=True)
    head.eval()

    exported = BrowserStudent(copy.deepcopy(base), copy.deepcopy(head)).eval()
    parallel_means(exported)
    example = (torch.zeros(1, 1, 3, 360, 640), torch.zeros(1, 1, 32), torch.zeros(1, 1, 128))
    target = out / 'student.onnx'
    torch.onnx.export(
        exported, example, str(target),
        input_names=['image', 'numeric', 'hidden'],
        output_names=['prediction', 'next_hidden', 'search_heat', 'search_offset', 'search_presence', 'search_evidence', 'search_identity'],
        opset_version=17, dynamo=False)

    x = torch.randn(1, 1, 3, 360, 640) * 255
    n = torch.randn(1, 1, 32).clamp(-3, 3)
    h = torch.randn(1, 1, 128) * .1
    with torch.inference_mode():
        reference = exported(x, n, h)
        features = base.backbone.encode_images(x)
        native_pose, _, native_hidden = base.visual_features(features, n, h)
        maps = {}
        handles = [base.backbone.encoder[i].register_forward_hook(lambda m, a, v, key=key: maps.__setitem__(key, v)) for i, key in [(3, 'fine'), (8, 'context')]]
        base.backbone.encode_images(x)
        for handle in handles:
            handle.remove()
        native_head = head(maps['fine'], maps['context'])

    import onnxruntime as ort
    session = ort.InferenceSession(str(target), providers=['CPUExecutionProvider'])
    actual = session.run(None, {'image': x.numpy(), 'numeric': n.numpy(), 'hidden': h.numpy()})
    labels = ['prediction', 'next_hidden', 'search_heat', 'search_offset', 'search_presence', 'search_evidence', 'search_identity']
    parity = {label: float(np.max(np.abs(value.detach().numpy() - real))) for label, value, real in zip(labels, reference, actual)}
    native = {
        'prediction': float((native_pose - reference[0]).abs().max()),
        'hidden': float((native_hidden - reference[1]).abs().max()),
    }
    for name, value in native_head.items():
        expected = reference[2 + ['heat', 'offset', 'presence', 'evidence', 'identity'].index(name)]
        if name == 'presence':
            value = value.reshape(1, 1)
        native[name] = float((value - expected).abs().max())
    if max(parity.values()) > 1e-4 or max(native.values()) > 1e-4:
        raise SystemExit(f'Export parity failed: {parity} {native}')

    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    result = {
        'model': target.name,
        'model_sha256': digest,
        'model_bytes': target.stat().st_size,
        'search_checkpoint_sha256': sh.get('checkpoint_sha256', hashlib.sha256((STUDENT / 'search_best.pt').read_bytes()).hexdigest()),
        'base_pose_sha256': hashlib.sha256((STUDENT / 'base/pose.pt').read_bytes()).hexdigest(),
        'outputs': {label: list(value.shape) for label, value in zip(labels, reference)},
        'export_parity': parity,
        'native_parity': native,
        'status': 'staged',
    }
    (out / 'export.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
