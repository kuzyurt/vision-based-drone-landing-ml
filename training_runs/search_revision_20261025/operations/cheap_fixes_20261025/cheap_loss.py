"""Same FP32 objective, with fixed-size reductions instead of GPU-driven Python branches."""
import torch
from torch.nn import functional as F


def macro_ce(logits, labels):
    losses = F.cross_entropy(logits, labels, ignore_index=-100, reduction='none')
    masks = [(labels == i) for i in range(logits.shape[1])]
    counts = torch.stack([m.sum() for m in masks])
    sums = torch.stack([(losses * m).sum() for m in masks])
    return (sums / counts.clamp_min(1)).sum() / (counts > 0).sum().clamp_min(1)


def loss(output, target):
    heat = target['heat']
    valid = ~target['ignore']
    p = output['heat'].sigmoid().clamp(1e-5, 1-1e-5)
    pos = heat == 1
    neg = (heat < 1) & valid
    positive_loss = -(p.log() * (1-p).square() * pos).sum()
    negative_loss = -((1-p).log() * p.square() * (1-heat).pow(4) * neg).sum()
    focal = (positive_loss + negative_loss) / pos.sum().clamp_min(1)
    mask = target['positive']
    errors = F.smooth_l1_loss(output['offset'], target['offset'], reduction='none')
    offset = (errors * mask[:, None]).sum() / (mask.sum() * 2).clamp_min(1)
    presence = F.binary_cross_entropy_with_logits(output['presence'], pos.flatten(1).any(1).float())
    evidence = macro_ce(output['evidence'], target['evidence'])
    identity = macro_ce(output['identity'], target['identity'])
    values = dict(heat=focal, offset=offset, presence=presence, evidence=evidence, identity=identity)
    return focal + offset + .1*presence + evidence + identity, values
