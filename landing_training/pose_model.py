"""Versioned pad-pose prediction and physically scaled supervised losses."""
import math
import torch
from torch import nn
from .policy import LandingPolicy


class PoseModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = LandingPolicy(freeze_encoder=True, observation_mode='periodic_no_action_v1')
        self.backbone.auxiliary = nn.Linear(128, 15)
        for parameter in self.backbone.actions.parameters():
            parameter.requires_grad = False

    def forward_features(self, features, numeric, hidden=None):
        _, raw, hidden = self.backbone.forward_features(features, numeric, hidden)
        return decode_pose(raw, numeric), raw, hidden

    def forward(self, images, numeric, hidden=None):
        return self.forward_features(self.backbone.encode_images(images), numeric, hidden)


def decode_pose(raw, numeric):
    position = numeric[..., 11:14] + raw[..., 1:4].clamp(-5., 5.)
    velocity = numeric[..., 14:17] - numeric[..., :3] + raw[..., 4:7].clamp(-1., 1.)
    vx, vy = numeric[..., 14], numeric[..., 15]
    speed_squared = vx * vx + vy * vy
    # Moving-boat course supplies an observable modulo-pi heading prior.
    # Right-positive FRD velocity corresponds to negative ENU heading.
    course = torch.stack((-2 * vx * vy, vx * vx - vy * vy), dim=-1) / speed_squared.clamp_min(1e-6)[..., None]
    prior = torch.where((speed_squared > .15 ** 2)[..., None], course, torch.zeros_like(course))
    heading = nn.functional.normalize(raw[..., 7:9] + prior, dim=-1, eps=1e-6)
    normal = nn.functional.normalize(raw[..., 9:12] + raw.new_tensor([0., 0., -1.]), dim=-1, eps=1e-6)
    return torch.cat((raw[..., :1], position, velocity, heading, normal, raw[..., 12:15]), dim=-1)


def pose_loss(prediction, target):
    visible = target[..., 0]
    xy = nn.functional.huber_loss(prediction[..., 1:3], target[..., 1:3], delta=.1, reduction='none').mean(-1)
    z = nn.functional.huber_loss(prediction[..., 3], target[..., 3], delta=.1, reduction='none')
    velocity = nn.functional.huber_loss(prediction[..., 4:7], target[..., 4:7], delta=.05, reduction='none').mean(-1)
    heading = ((prediction[..., 7:9] - target[..., 7:9]) ** 2).mean(-1)
    normal = ((prediction[..., 9:12] - target[..., 9:12]) ** 2).mean(-1)
    pixels = nn.functional.huber_loss(prediction[..., 12:14] * prediction.new_tensor([320., 180.]),
                                     target[..., 12:14] * target.new_tensor([320., 180.]),
                                     delta=2., reduction='none').mean(-1)
    near = (torch.linalg.vector_norm(target[..., 1:3], dim=-1) < 1.) & (target[..., 3].abs() < 2.5)
    weight = torch.where(near, 8., 1.) * visible
    regression = (8 * xy + 4 * z + 2 * velocity + .3 * heading + .3 * normal + .005 * pixels)
    regression = (regression * weight).sum() / weight.sum().clamp_min(1)
    visibility = nn.functional.binary_cross_entropy_with_logits(prediction[..., 0], visible)
    contact = nn.functional.binary_cross_entropy_with_logits(prediction[..., 14], target[..., 14])
    return regression + .1 * visibility + .05 * contact
