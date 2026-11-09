"""Confidence-aware radio fusion and an unrestricted visual pose branch."""
import torch
from torch import nn
from ..pose_model import PoseModel
from ..policy import policy_observation


class RadioRobustPoseModel(nn.Module):
    def __init__(self, source=None):
        super().__init__()
        original = PoseModel()
        if source is not None:
            original.load_state_dict(source['model'], strict=True)
        self.backbone = original.backbone
        self.visual_absolute = nn.Linear(128, 6)
        # Preserve the learned heads; start the new branch from their learned
        # pose corrections, then learn absolute positions without a +/-5 m cap.
        with torch.no_grad():
            self.visual_absolute.weight.copy_(self.backbone.auxiliary.weight[1:7])
            self.visual_absolute.bias.copy_(self.backbone.auxiliary.bias[1:7])
        self.quality = nn.Linear(2, 64)
        nn.init.zeros_(self.quality.weight)
        nn.init.zeros_(self.quality.bias)

    def forward_features(self, features, numeric, hidden=None, uncertainty=None):
        if uncertainty is None:
            uncertainty = numeric.new_tensor([.25, .025]).expand(*numeric.shape[:-1], 2)
        if numeric.shape[-1] != 32 or uncertainty.shape[-1] != 2:
            raise ValueError('Expected the original 32 sensors and two uncertainty values')
        valid = (numeric[..., 21] > .5) & (numeric[..., 19] < 3.)
        valid &= torch.isfinite(numeric[..., 11:17]).all(-1)
        numeric = numeric.clone()
        numeric[..., 21] = valid.to(numeric.dtype)
        # A missing field is neutral AFTER normalization; the validity bit and
        # uncertainty carry missingness. Zero metres is never a fake target.
        represented = policy_observation(numeric, self.backbone.observation_mode)
        represented[..., 11:17] = torch.where(
            valid[..., None], represented[..., 11:17], self.backbone.observation_mean[11:17])
        normalized = (represented - self.backbone.observation_mean) / self.backbone.observation_std
        # Original recordings are almost always valid. Their tiny validity
        # standard deviation must not turn a missing packet into a -1000 input.
        normalized[..., 21] = valid.to(numeric.dtype) - 1.
        normalized[..., 19] = normalized[..., 19].clamp(-10., 10.)
        state = self.backbone.telemetry(normalized)
        baseline = uncertainty.new_tensor([.25, .025])
        state = state + self.quality(torch.log1p(uncertainty) - torch.log1p(baseline))
        recurrent, hidden = self.backbone.gru(
            torch.cat((self.backbone.visual(features), state), -1), hidden)
        raw = self.backbone.auxiliary(recurrent)
        absolute = self.visual_absolute(recurrent)
        position_visual = absolute[..., :3]
        velocity_visual = absolute[..., 3:6] - numeric[..., :3]
        age_weight = torch.exp(-(numeric[..., 19] - 1.).clamp_min(0.))
        pos_weight = valid * age_weight * torch.exp(-((uncertainty[..., 0] - .25).clamp_min(0.) / 1.5).square())
        vel_weight = valid * age_weight * torch.exp(-((uncertainty[..., 1] - .025).clamp_min(0.) / .2).square())
        radio = torch.nan_to_num(numeric[..., 11:17])
        position = (pos_weight[..., None] * (radio[..., :3] + raw[..., 1:4].clamp(-5., 5.))
                    + (1 - pos_weight[..., None]) * position_visual)
        velocity = (vel_weight[..., None] * (radio[..., 3:6] - numeric[..., :3] + raw[..., 4:7].clamp(-1., 1.))
                    + (1 - vel_weight[..., None]) * velocity_visual)
        vx, vy = radio[..., 3], radio[..., 4]
        speed_squared = vx.square() + vy.square()
        course = torch.stack((-2 * vx * vy, vx.square() - vy.square()), -1) / speed_squared.clamp_min(1e-6)[..., None]
        course_reliable = valid & (speed_squared > torch.maximum(3 * uncertainty[..., 1], uncertainty.new_tensor(.15)).square())
        course = course * (vel_weight * course_reliable)[..., None]
        heading = nn.functional.normalize(raw[..., 7:9] + course, dim=-1, eps=1e-6)
        normal = nn.functional.normalize(raw[..., 9:12] + raw.new_tensor([0., 0., -1.]), dim=-1, eps=1e-6)
        prediction = torch.cat((raw[..., :1], position, velocity, heading, normal, raw[..., 12:15]), -1)
        visual_pose = torch.cat((position_visual, velocity_visual), -1)
        return prediction, visual_pose, hidden

    def forward(self, images, numeric, hidden=None, uncertainty=None):
        return self.forward_features(self.backbone.encode_images(images), numeric, hidden, uncertainty)
