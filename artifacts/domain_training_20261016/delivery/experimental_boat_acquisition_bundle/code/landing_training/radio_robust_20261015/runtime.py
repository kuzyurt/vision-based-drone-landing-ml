"""Camera/PX4-only fallback, trained pose estimates and preserved metric gates."""
import copy
import math
import numpy as np
import torch
from .model import RadioRobustPoseModel
from .controller.marker_policy import MarkerPosePolicy
from .controller.recording import numeric_observation
from .controller.supervision import supervise_action


class RadioRobustRuntime:
    def __init__(self, checkpoint, calibration, slew_limits, device='cuda', *, allow_visual_landing=False):
        from . import native_marker, runtime_fixes
        native_marker.install(__package__)
        runtime_fixes.install(__package__)
        saved = torch.load(checkpoint, map_location=device, weights_only=False)
        if saved.get('schema') != 'aerodock.landing.radio_robust_pose.v1':
            raise ValueError('Not a radio-robust pose checkpoint')
        self.device = device
        self.model = RadioRobustPoseModel().to(device)
        self.model.load_state_dict(saved['model'], strict=True)
        self.model.eval()
        from .acquisition import AcquisitionHead
        from pathlib import Path
        acquisition=torch.load(Path(checkpoint).with_name('acquisition.pt'),map_location=device,weights_only=False)
        self.acquisition=AcquisitionHead().to(device)
        self.acquisition.load_state_dict(acquisition['model'],strict=True);self.acquisition.eval()
        self.controller = MarkerPosePolicy(None, calibration, slew_limits, device)
        self.allow_visual_landing = bool(allow_visual_landing)
        self.metadata = {k: saved[k] for k in ['schema', 'epoch', 'source_checkpoint_sha256', 'dataset_sha256', 'training']}
        self.reset()

    def reset(self):
        self.hidden = None
        self.controller.reset()
        self.controller.controller.visual_search_started = None
        self.start_time = None

    @torch.inference_mode()
    def act(self, rgb, observation):
        observation = copy.deepcopy(observation)
        if observation.get('beacon') is None:
            observation['beacon'] = {}
        b = observation['beacon']
        b.setdefault('dock_ready', False)
        status_known = bool(b.get('dock_status_valid', b.get('valid', False)))
        dock_ready = bool(b.get('dock_ready', False))
        # These are reported uncertainty/calibrated defaults, never the actual
        # error against a hidden simulator position.
        sigma_p = float(b.get('position_sigma_m', 1.))
        sigma_v = float(b.get('velocity_sigma_m_s', .1))
        quality_known = all(math.isfinite(v) and v >= 0 for v in [sigma_p, sigma_v])
        sigma_p, sigma_v = (sigma_p, sigma_v) if quality_known else (100., 10.)
        available = bool(b.get('valid', False)) and float(b.get('age_s', math.inf)) < 3.
        available &= all(np.asarray(b.get(key, []), dtype=float).shape == (3,)
                         and np.isfinite(b[key]).all() for key in ['relative_heading_m', 'velocity_heading_m_s'])
        if not available:
            b.update(valid=False, relative_heading_m=[0., 0., 0.], velocity_heading_m_s=[0., 0., 0.],
                     age_s=3.1)
            sigma_p, sigma_v = 100., 10.
        image = torch.from_numpy(np.asarray(rgb).copy()).permute(2, 0, 1)[None, None].to(self.device)
        numeric = torch.from_numpy(numeric_observation({'observation': observation}))[None, None].to(self.device)
        if not status_known:
            # Unknown dock status is neutral to perception, not a fabricated
            # clearance or a large out-of-distribution normalized Boolean.
            numeric[..., 22] = self.model.backbone.observation_mean[22]
        uncertainty = numeric.new_tensor([sigma_p, sigma_v]).reshape(1, 1, 2)
        features=self.model.backbone.encode_images(image)
        prediction, _, self.hidden = self.model.forward_features(features,numeric,self.hidden,uncertainty)
        image_prediction=self.acquisition(features)
        metric_time=self.controller.metric_time
        acquisition_active=metric_time is None or float(observation['image_delivery_time_s'])-metric_time>.5
        if acquisition_active:
            prediction=prediction.clone()
            prediction[...,0]=image_prediction[...,0]
            prediction[...,12:14]=image_prediction[...,1:3]
        # Coarse radio must not bypass the model via range, velocity, heading
        # initialization or the camera/controller's direct radio fallback.
        reliable = available and quality_known and sigma_p <= 1.5 and sigma_v <= .2
        controlled = copy.deepcopy(observation)
        if not reliable:
            controlled['beacon'].update(valid=False, relative_heading_m=[0., 0., 0.],
                                         velocity_heading_m_s=[0., 0., 0.], age_s=3.1)
        action, diagnostics = self.controller.act(np.asarray(rgb), controlled,
                                                prediction[0, 0].cpu().numpy())
        now = float(observation['image_delivery_time_s'])
        if self.start_time is None:
            self.start_time = now
        action, intervention = supervise_action(action, controlled, now - self.start_time, float(observation['mission']['budget_s']))
        # Losing POSITION does not manufacture a dock-clearance signal. Search
        # remains available, but radio-free touchdown requires mission approval.
        if status_known and not dock_ready:
            action[:4] = 0.
            intervention = 'dock_not_ready'
        elif not status_known and not self.allow_visual_landing and action[2] > 0:
            action[2] = 0.
            intervention = 'visual_landing_authorization_required'
        diagnostics.update(radio_position_available=available, radio_controller_trusted=reliable,
                           radio_position_sigma_m=sigma_p, radio_velocity_sigma_m_s=sigma_v,
                           radio_fallback='visual' if not reliable else 'confidence_weighted',
                           intervention=intervention)
        diagnostics.update(acquisition_head_active=acquisition_active,acquisition_head_visibility=float(image_prediction[0,0,0].sigmoid().cpu()),acquisition_head_center_px=((image_prediction[0,0,1:3].cpu().numpy()+1)*[320.,180.]).tolist())
        return action, diagnostics
