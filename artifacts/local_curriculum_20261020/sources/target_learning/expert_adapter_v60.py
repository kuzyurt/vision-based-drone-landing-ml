"""Teacher adapter v60 — one selection authority for planning and pad seeding.

Differences from ``expert_adapter_windows_v1`` (which stays frozen and is kept as
the negative reference):

* the planner is ``protocol_priority_v60.SearchProtocolV60`` (evidence priority,
  no mandatory survey over a visible opportunity, explicit preemption);
* candidates are built with observable evidence the planner needs: visible
  extent, own-calibrated focal length, implied physical length from the object's
  own bearing-plane range interval, peak target evidence over the recogniser
  window, and target vote count;
* the pad localiser seed is derived from the *same* authority as the planner:
  the confirmed object's alias set when identity is confirmed, otherwise the
  best target-class track.  It is never seeded from a buoy/weak blob;
* a descent permission that does not belong to the confirmed object is blocked
  and logged (invariant, not a comment);
* identity survives track aliasing through a world-point + appearance anchor;
  pad geometry is still re-measured every frame.

RGB/own telemetry/encoders/declared static priors only.  No simulator truth.
"""

from collections import deque
from dataclasses import asdict, replace
from pathlib import Path
import copy, importlib, json, math, sys, types

import numpy as np
import torch

from .protocol import PublicState, wrap
from .protocol_priority_v60 import (CandidateV60, SearchProtocolV60, C_NONE, WEAK, BOAT, TARGET,
                                    TARGET_CONFIRMED, PLAUSIBLE_BOAT_LENGTH_M)
from .camera_axis_continuity import install as install_camera_continuity
from .tracks_shape_v42 import TrackBank
from .own_cad_occlusion_v2 import OwnCadOcclusion
from .metric_candidate_continuity import compatible as metric_candidate_compatible
from .local_downlook_v22 import camera_only_downlook
from .inspection_feedback_v51 import InspectionFeedback


def load_parent(bundle, name):
    pkg = types.ModuleType(name)
    pkg.__path__ = [str(Path(bundle) / "code/landing_training")]
    sys.modules[name] = pkg
    return importlib.import_module(name + ".radio_robust_20261015.runtime")


class IdentityExpertV60:
    def __init__(self, bundle, checkpoint, *, device="cuda", package_name="observable_identity_expert_v60",
                 review_only=False):
        self.bundle = Path(bundle)
        self.config = json.loads((self.bundle / "policy.json").read_text())
        saved = torch.load(checkpoint, map_location=device, weights_only=False)
        if saved["schema"] not in ["mujoco.target_discriminator.v1", "mujoco.target_discriminator.v5",
                                   "mujoco.target_discriminator.v7", "mujoco.target_discriminator.v10",
                                   "mujoco.target_discriminator.v11", "mujoco.target_discriminator.v12"]:
            raise ValueError("Wrong recognizer schema")
        gate = saved["validation"]
        self.review_only = bool(review_only)
        if not gate["expert_gate_passed"]:
            if not self.review_only:
                raise PermissionError("Recognition qualification gate not passed")
            point = gate.get("selected_operating_point")
            if point is None or point["identity"] < .98 or point["target_recall"] < .4 or gate["object_recall"] < .65:
                raise PermissionError("No conservative development-review operating point")
            if any(point[k] != 0 for k in ["wrong_object_acceptances", "ambiguous_acceptances",
                                           "background_acceptances"]):
                raise PermissionError("Review pilot cannot admit known false target assertions")
        self.qualification_gate_passed = bool(gate["expert_gate_passed"])
        op = gate["selected_operating_point"]
        self.support_threshold = float(op.get("support", 0.))
        self.presence_threshold = float(op.get("heat", .7))
        self.threshold = float(op.get("identity", op.get("threshold", .98)))
        self.marker_threshold = float(gate.get("selected_marker_operating_point", {}).get("threshold", .8))
        if saved["schema"] in ["mujoco.target_discriminator.v5", "mujoco.target_discriminator.v7",
                               "mujoco.target_discriminator.v10", "mujoco.target_discriminator.v11",
                               "mujoco.target_discriminator.v12"]:
            from .discriminator_v5 import Discriminator, decode
        else:
            from .discriminator import Discriminator, decode
        self.decode_candidates = decode
        self.parent = load_parent(bundle, package_name)
        self.runtime = self.parent.RadioRobustRuntime(self.bundle / "pose.pt", self.config["calibration"],
                                                      self.config["slew_limits"], device, allow_visual_landing=True)
        self.pad_head = self.runtime.acquisition
        self.pad_decoder = self.runtime.decode_spatial
        self.head = Discriminator().to(device)
        self.head.load_state_dict(saved["model"], strict=True)
        self.head.eval()
        self.verifier = None
        self.verify_candidates = None
        if saved["schema"] == "mujoco.target_discriminator.v7":
            from .object_verifier import ObjectVerifier, verify
            self.verifier = ObjectVerifier().to(device); self.verifier.load_state_dict(saved["verifier"], strict=True); self.verifier.eval()
            self.verify_candidates = verify
        elif saved["schema"] == "mujoco.target_discriminator.v10":
            from .object_verifier_v10 import ObjectVerifier, verify
            self.verifier = ObjectVerifier().to(device); self.verifier.load_state_dict(saved["verifier"], strict=True); self.verifier.eval()
            self.verify_candidates = verify
        elif saved["schema"] == "mujoco.target_discriminator.v11":
            from .object_verifier_v11 import ObjectVerifier, verify
            self.verifier = ObjectVerifier().to(device); self.verifier.load_state_dict(saved["verifier"], strict=True); self.verifier.eval()
            self.verify_candidates = verify
        elif saved["schema"] == "mujoco.target_discriminator.v12":
            from .object_verifier_v12 import ObjectVerifier, verify
            self.verifier = ObjectVerifier(mode=saved["verifier_mode"]).to(device)
            self.verifier.load_state_dict(saved["verifier"], strict=True); self.verifier.eval()
            self.verify_candidates = verify
        self.raw_rgb_verifier = saved["schema"] in ["mujoco.target_discriminator.v11", "mujoco.target_discriminator.v12"]
        self.camera_geometry = importlib.import_module(self.parent.__package__ + ".controller.visual_acquisition").camera_geometry
        guard = importlib.import_module(self.parent.__package__ + ".controller.action_guard")
        self.final_guard = guard.ActionGuard(guard.GuardConfig(slew_limits=tuple(self.config["slew_limits"])))
        self.supervise = importlib.import_module(self.parent.__package__ + ".controller.supervision").supervise_action
        owner = self

        class RecognizerProxy(torch.nn.Module):
            def forward(self, fine, context):
                output = owner.head(fine, context)
                if owner.verifier is not None:
                    output.update(_fine=fine, _context=context)
                pad_heat, pad_offset, pad_presence = owner.pad_head(fine, context)
                output.update(_pad_heat=pad_heat, _pad_offset=pad_offset, _pad_presence=pad_presence)
                return output

        self.runtime.acquisition = RecognizerProxy()
        self.runtime.decode_spatial = self._decode
        body_camera = importlib.import_module(self.parent.__package__ + ".controller.camera_geometry").camera_body_transform
        self.own_cad = OwnCadOcclusion(Path(__file__).with_name("fixed_own_aircraft.npz"),
                                       "d93557fde455fe08969496a416416d4e016afeb91cf6b30e181e812ef7a2440a", body_camera)
        self.own_cad_radius = float(max(np.linalg.norm(self.own_cad.v0, axis=1).max(),
                                        np.linalg.norm(self.own_cad.v0 + self.own_cad.e1, axis=1).max(),
                                        np.linalg.norm(self.own_cad.v0 + self.own_cad.e2, axis=1).max()))
        self.own_cad_drops = 0
        self._focal_px = 552.0
        self.track_peak = {}
        self.reset()
        self.camera_fix_state = install_camera_continuity(self.runtime.controller)

    def reset(self):
        if hasattr(self, "camera_fix_state"):
            for key in self.camera_fix_state:
                self.camera_fix_state[key] = None
        self.runtime.reset(); self.final_guard.reset()
        self.protocol = SearchProtocolV60(candidate_presence_threshold=self.presence_threshold)
        self.bank = TrackBank(target_threshold=self.threshold, support_threshold=self.support_threshold,
                              presence_threshold=self.presence_threshold)
        self.history = deque(maxlen=64)
        self.last_seed = None
        self.current_candidates = []
        self.inspection_feedback = InspectionFeedback()
        self.capture_error = None
        self.observation = None
        self.current_camera_world = None
        self.start = None
        self.last_near = None
        self.pad_diagnostics = {}
        self.track_peak = {}
        self.selection_log = []

    # ---------------------------------------------------------------- helpers
    def _mission(self, o):
        m = o.get("mission", {}).get("target_discrimination")
        required = ["search_height_enu_m", "maximum_height_enu_m", "nominal_boat_plane_enu_m",
                    "plane_uncertainty_m", "static_prior_no_dynamic_boat_state",
                    "search_corridor_valid", "upward_corridor_valid"]
        if not isinstance(m, dict) or not all(k in m for k in required):
            raise ValueError("Missing declared search mission prior")
        if not m["static_prior_no_dynamic_boat_state"]:
            raise PermissionError("Dynamic truth in search prior")
        if self.protocol.min_structure_m is None and "nominal_structure_bound_m" in m:
            self.protocol.min_structure_m = float(m["nominal_structure_bound_m"])
            self.protocol.plausible_length_m = max(PLAUSIBLE_BOAT_LENGTH_M,
                                                   0.28 * float(m["nominal_structure_bound_m"]))
        self.protocol.plane_height_m = float(m["nominal_boat_plane_enu_m"])
        return m

    @staticmethod
    def _heading(yaw):
        c, s = math.cos(yaw), math.sin(yaw)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])

    def _peak(self, track_id, capture_s, probability):
        """Peak target probability for this track inside the recogniser window."""
        peaks = self.track_peak.setdefault(track_id, [])
        peaks.append((capture_s, float(probability)))
        self.track_peak[track_id] = [p for p in peaks if capture_s - p[0] <= 0.8]
        return max(p[1] for p in self.track_peak[track_id])

    def _candidates(self, now_s, camera_world, camera_to_world=None):
        output = []
        own = np.asarray(camera_world, dtype=float)
        for track in self.bank.tracks.values():
            if track.confirmations >= 3:
                self.bank.objectness_confirmed.add(track.index)
            if track.index not in self.bank.objectness_confirmed:
                continue
            age = now_s - track.measured_s
            if age < 0 or age > self.bank.max_age_s:
                continue
            vector = track.ray_world if track.point_world is None else track.point_world - own
            if np.linalg.norm(vector[:2]) < 1e-6:
                continue
            detection = track.detection
            extent = float(max(detection.get("size_px", [0, 0])))
            interval = track.range_interval
            implied = None
            if interval is not None and self._focal_px:
                # Range intervals are horizontal (bearing x plane).  Implied
                # physical size needs the slant distance, which is the same
                # quantity at stand-off and the vertical drop when the camera
                # is near nadir (horizontal range -> 0 there).
                horizontal_norm = float(np.linalg.norm(np.asarray(track.ray_world, float)[:2]))
                if horizontal_norm > 0.08:
                    slant = float(interval[0]) / horizontal_norm
                else:
                    slant = max(float(own[2]) - float(self.protocol.plane_height_m), 0.3)
                implied = float(extent / float(self._focal_px) * slant)
            votes = 0
            if getattr(track, "identity_votes", None):
                votes = sum(1 for stamp, value in track.identity_votes if value == 1)
            def number(*keys, default=0.0):
                """First present probability, clamped to [0, 1].

                A softmax triple sums to 1 + 1e-8 in float32, so p(target)+p(wrong)
                can exceed 1 by a few ulp; the protocol rightly rejects that.  The
                clamp is numeric hygiene, not a reinterpretation of the evidence.
                """
                for key in keys:
                    value = detection.get(key)
                    if value is not None:
                        return min(1.0, max(0.0, float(value)))
                return min(1.0, max(0.0, float(default)))

            output.append(CandidateV60(
                track_id=track.index,
                bearing_world_rad=math.atan2(vector[1], vector[0]),
                boat_probability=number("presence"),
                target_probability=number("target_probability"),
                evidence_peak=self._peak(track.index, track.measured_s, detection["target_probability"]),
                wrong_boat_probability=number("wrong_object_probability",
                                              default=1. - number("target_probability")),
                identity_support=number("identity_support_probability", default=1.0),
                identity_observable=self.bank._identity(detection) >= 0,
                target_votes=votes,
                distinct_confirmations=int(track.confirmations),
                age_s=float(age),
                range_interval_m=None if interval is None else tuple(interval),
                marker_probability=number("marker_probability", "pad_visibility_probability"),
                extent_px=extent,
                focal_px=float(self._focal_px),
                implied_length_m=implied,
                point_world=None if track.point_world is None else tuple(float(v) for v in track.point_world),
                appearance=None if not detection.get("appearance_descriptor") else tuple(
                    float(v) for v in detection["appearance_descriptor"]),
            ))
        return output

    def _code_to_class(self, candidate):
        return self.protocol.classify(candidate)

    # ------------------------------------------------------------------ decode
    def _decode(self, output):
        self.pad_diagnostics = {}
        o = self.observation
        m = self._mission(o)
        now = float(o["image_delivery_time_s"])
        capture_time = float(o["image_capture_time_s"])
        stamp, capture = min(self.history, key=lambda t: abs(t[0] - capture_time))
        self.capture_error = abs(stamp - capture_time)
        pixel = [320., 180.]
        probability = 1e-5
        yaw = math.pi / 2 - o["px4"]["attitude_ned_rad"][2]
        R = self._heading(yaw)
        D = np.diag([1., -1., -1.])
        self.current_camera_world = np.array(o["px4"]["position_enu_m"], dtype=float)
        if self.capture_error <= .021 and o["image_valid"] and o["image_age_s"] <= .25:
            rotation, origin, focal, _ = self.camera_geometry(capture, self.config["calibration"])
            self._focal_px = float(focal)
            Rc = self._heading(math.pi / 2 - capture["px4"]["attitude_ned_rad"][2])
            camera_world = np.asarray(capture["px4"]["position_enu_m"]) + Rc @ D @ origin
            self.current_camera_world = np.asarray(o["px4"]["position_enu_m"]) + R @ D @ origin
            decode_args = dict(minimum_presence=self.presence_threshold)
            if self.verifier is not None:
                decode_args["topk"] = 24
            frames = self.decode_candidates({k: v.detach().cpu() for k, v in output.items() if not k.startswith("_")}, **decode_args)
            if self.verifier is not None:
                frames = self.verify_candidates(self.verifier, output["_fine"], output["_context"], frames,
                                                *([self.current_rgb] if self.raw_rgb_verifier else []))
            detections = frames[0]
            self.own_cad_drops = 0
            if self.protocol.confirmed is None and float(capture["px4"]["position_enu_m"][2]) - self.own_cad_radius > float(m.get("nominal_structure_bound_m", math.inf)) + .1:
                kept = []
                for detection in detections:
                    if self.own_cad.occluded(detection["pixel"], capture["gimbal_rad"], self.config["calibration"]):
                        self.own_cad_drops += 1
                    else:
                        kept.append(detection)
                detections = kept
            for detection in detections:
                center = np.asarray(detection["pixel"])
                half = .4 * np.asarray(detection["size_px"])
                xs = np.clip(np.linspace(center[0] - half[0], center[0] + half[0], 4).round().astype(int), 0, 639)
                ys = np.clip(np.linspace(center[1] - half[1], center[1] + half[1], 4).round().astype(int), 0, 359)
                detection["appearance_descriptor"] = (self.current_rgb[ys[:, None], xs[None, :], :] // 8).reshape(-1).tolist()
            self.bank.observe(detections, capture_s=capture_time, frame_token=int(round(capture_time * 1e6)),
                              camera_world=camera_world, camera_to_world=Rc @ D @ rotation, focal_px=focal,
                              plane_height_enu_m=float(m["nominal_boat_plane_enu_m"]),
                              plane_uncertainty_m=float(m["plane_uncertainty_m"]))
            self.current_candidates = self._candidates(now, self.current_camera_world)

            # --- single selection authority ---------------------------------
            confirmed = self.protocol.confirmed
            aliases = set() if self.protocol.anchor is None else set(self.protocol.anchor["aliases"])
            fresh = {c.track_id: c for c in self.current_candidates if c.age_s <= .25}
            target_class = [c for c in fresh.values()
                            if self.protocol.classify(c) >= TARGET]
            if confirmed is not None:
                # Identity is fixed to the confirmed object. Only an alias of it
                # may seed pad geometry; a different object never may.
                selected_candidate = next((c for c in target_class if c.track_id in aliases), None)
                authority = "confirmed_target_alias"
            else:
                selected_candidate = max(target_class, key=lambda c: (c.evidence_peak, c.extent_px)) if target_class else None
                authority = "best_target_class_track"
            track = None if selected_candidate is None else self.bank.tracks.get(selected_candidate.track_id)
            metric_time = self.runtime.controller.metric_time
            live_metric = bool(metric_time is not None and now - metric_time <= .5
                               and (self.last_seed in aliases if confirmed is not None
                                    else self.last_seed == self.protocol.confirmed))
            if track is not None:
                d = track.detection
                heat = output["_pad_heat"]
                _, height, width = heat.shape
                yy, xx = torch.meshgrid(torch.arange(height, device=heat.device), torch.arange(width, device=heat.device), indexing="ij")
                cell_x = (xx + .5) * 640 / width
                cell_y = (yy + .5) * 360 / height
                center = np.asarray(d["pixel"])
                half = .5 * np.asarray(d["size_px"])
                box_mask = (cell_x >= center[0] - half[0]) & (cell_x <= center[0] + half[0]) & (cell_y >= center[1] - half[1]) & (cell_y <= center[1] + half[1])
                if bool(box_mask.any()):
                    masked = heat.masked_fill(~box_mask[None], -1e9)
                    presence, pad = self.pad_decoder((masked, output["_pad_offset"], output["_pad_presence"]))
                    proposed = pad[0].detach().cpu().numpy()
                    inside = bool(np.all(proposed >= center - half) and np.all(proposed <= center + half))
                    if inside:
                        pixel = proposed.tolist()
                        probability = float(presence[0].sigmoid().detach().cpu()) * d["target_probability"] * d.get("identity_support_probability", 1.)
                    self.pad_diagnostics = dict(
                        source="preserved b432 image marker localizer, masked to the recognised object box",
                        inside_predicted_identity_box=inside, pixel=proposed.tolist(),
                        global_presence=float(presence[0].sigmoid().detach().cpu()),
                        track_id=selected_candidate.track_id, authority=authority)
                same_object = bool(selected_candidate.track_id == self.last_seed or
                                   (confirmed is not None and selected_candidate.track_id in aliases))
                changed = self.last_seed is not None and not same_object
                compatible = False
                if changed and not live_metric:
                    compatible = metric_candidate_compatible(
                        self.runtime.controller.visual_memory.estimate(o), d,
                        camera_world=camera_world, camera_to_world=Rc @ D @ rotation,
                        focal_px=focal, image_age_s=now - capture_time)
                    if not compatible:
                        self.runtime.controller.reset()
                        self.runtime.hidden = None
                        for key in self.camera_fix_state:
                            self.camera_fix_state[key] = None
                self.pad_diagnostics.update(proposal_changed=changed, metric_alias_compatible=compatible,
                                            destructive_metric_reset=bool(changed and not live_metric and not compatible))
                if not live_metric:
                    self.last_seed = selected_candidate.track_id
            else:
                self.last_seed = None
            self.pad_diagnostics["metric_live"] = live_metric
            self.pad_diagnostics["confirmed"] = confirmed
        else:
            self.current_candidates = self._candidates(now, self.current_camera_world)
        device = output["heat"].device
        p = torch.tensor([probability], device=device).clamp(1e-5, 1 - 1e-5)
        return torch.logit(p), torch.tensor([pixel], dtype=torch.float32, device=device)

    # ------------------------------------------------------------------ state
    @property
    def controller(self):
        return self.runtime.controller

    def _public_state(self, o, diag):
        m = self._mission(o)
        p = o["px4"]
        now = float(o["image_delivery_time_s"])
        position = np.asarray(p["position_enu_m"])
        velocity = np.asarray(p["velocity_enu_m_s"])
        age = diag.get("metric_age_s")
        sigma = diag.get("metric_uncertainty_m")
        clearance = diag.get("estimated_clearance_m")
        geometry = bool(diag.get("metric_confirmed") and age is not None and age <= .16 and sigma is not None and sigma <= .15)
        if geometry and clearance is not None and clearance < 1.:
            self.last_near = now
        near = self.last_near is not None and now - self.last_near < 1.5
        aliases = set() if self.protocol.anchor is None else set(self.protocol.anchor["aliases"])
        identity_associated = bool(self.last_seed in aliases and diag.get("metric_confirmed")
                                   and diag.get("metric_acceptance") == "tracked")
        return PublicState(now, int(round(float(o["image_capture_time_s"]) * 1e6)),
                           math.pi / 2 - p["attitude_ned_rad"][2],
                           float(position[2]), float(velocity[2]), *map(float, o["gimbal_rad"]),
                           bool(o["image_valid"] and o["image_age_s"] <= .25 and self.capture_error <= .021),
                           bool(p.get("valid") and p.get("position_age_s", 99) <= .25 and p.get("attitude_age_s", 99) <= .25),
                           bool(p.get("armed") and not p.get("landed")), bool(p.get("landed")),
                           bool(m["upward_corridor_valid"] or (self.protocol.confirmed is not None and diag.get("control_phase") == "recovery_climb" and diag.get("recovery_static_clearance_prior"))),
                           bool(m["search_corridor_valid"]),
                           float(m["search_height_enu_m"]), float(m["maximum_height_enu_m"]), geometry, sigma, near,
                           bool(np.linalg.norm(velocity) < .3), identity_associated,
                           bool(diag.get("control_phase") == "touchdown_commit" and self.last_seed in aliases),
                           tuple(float(v) for v in position[:2]))

    @torch.inference_mode()
    def act(self, rgb, observation):
        o = copy.deepcopy(observation)
        self._mission(o)
        # Pass the received SX1262 fix through.  The review harness used to hand
        # every flight an invalid beacon; when it does, this keeps that exact
        # radio-off behaviour.  A radio-on flight now reaches fusion.
        if o.get("beacon") is None:
            o["beacon"] = dict(valid=False, age_s=3.1, sequence=0,
                               dock_ready=False, dock_status_valid=False)
        if np.asarray(rgb).shape != (360, 640, 3):
            raise ValueError("Exact deployed image input required")
        self.current_rgb = np.asarray(rgb)
        now = float(o["image_delivery_time_s"])
        if self.start is None:
            self.start = now
        self.history.append((now, copy.deepcopy(o)))
        self.observation = o
        action, diag = self.runtime.act(rgb, o)
        s = self._public_state(o, diag)

        remembered = self.bank.tracks.get(self.protocol.selected)
        rotation, origin, focal, _ = self.camera_geometry(o, self.config["calibration"])
        self._focal_px = float(focal)
        R = self._heading(s.yaw_world_rad)
        D = np.diag([1., -1., -1.])
        feedback = self.inspection_feedback.observe(
            self.protocol, s, self.current_candidates,
            point_world=None if remembered is None else remembered.point_world,
            camera_world=np.asarray(o["px4"]["position_enu_m"]) + R @ D @ origin,
            camera_to_world=R @ D @ rotation, focal_px=focal,
            own_xy=np.asarray(o["px4"]["position_enu_m"])[:2],
            fresh_detections=[t.detection for t in self.bank.tracks.values() if s.time_s - t.measured_s <= .25],
            own_angular_speed_rad_s=float(np.linalg.norm(o["px4"]["angular_rate_frd_rad_s"])))
        diag["inspection_feedback"] = feedback
        if feedback.get("retired") and self.protocol.confirmed is None:
            if self.protocol.scan_mode != "scan_1" or not self.protocol.survey_active:
                self.protocol._restart_strict_survey("scan_1_after_negative_visual_inspection")

        intent = self.protocol.step(s, self.current_candidates)

        # --- invariant: descent only for the confirmed object ----------------
        if intent.allow_descent and self.protocol.confirmed is not None:
            aliases = set() if self.protocol.anchor is None else set(self.protocol.anchor["aliases"])
            if intent.selected_track not in aliases:
                self.protocol.invariant_violations.append(dict(
                    t=round(s.time_s, 3), kind="descent_for_unconfirmed_selection",
                    selected=intent.selected_track, confirmed=self.protocol.confirmed,
                    aliases=sorted(aliases)))
                intent = replace(intent, allow_descent=False,
                                 reason=intent.reason + "+descent_blocked_selection_not_confirmed")
        if intent.allow_descent and self.protocol.confirmed is not None and not s.pad_geometry_fresh:
            self.protocol.invariant_violations.append(dict(
                t=round(s.time_s, 3), kind="descent_without_fresh_geometry",
                selected=intent.selected_track))
            intent = replace(intent, allow_descent=False,
                             reason=intent.reason + "+descent_blocked_no_fresh_geometry")

        if intent.phase in ["target_align", "target_contact_confirmation"]:
            pass
        elif intent.phase in ["local_downlook", "recovery_climb", "recovery_downlook"]:
            if diag.get("recovery_active"):
                diag["expert_recovery_driver"] = "existing R15 visibility recovery, current guards unchanged"
            else:
                persistent = importlib.import_module(self.parent.__package__ + ".controller.persistent_target")
                own = persistent.own_state(o)
                memory = self.runtime.controller.visual_memory.estimate(o)
                action = np.zeros(6)
                if own is not None:
                    aimed = self.runtime.controller.visibility_recovery._camera(self.runtime.controller, o, own, memory, now)
                    action[3:] = aimed[3:]
                    if (memory is None or not memory.get("local_aim_valid", False)) and intent.look_down:
                        pan, tilt = o["gimbal_rad"]
                        action[3] = 0.
                        action[4] = float(np.clip(-3. * wrap(pan), -math.radians(50), math.radians(50)))
                        action[5] = float(np.clip(3. * (math.radians(80) - tilt), -math.radians(40), math.radians(40)))
                        diag["expert_expired_memory_downlook"] = True
                action, extra = self.final_guard.apply(action, o, dict(control_phase="local_downlook", pad_visibility_probability=0.))
                action[2] = 0.
                diag["expert_override_guard"] = extra
                diag["parent_control_phase"] = diag["control_phase"]
                diag["control_phase"] = "local_downlook"
                diag["expert_recovery_driver"] = "memory camera only; no unguarded protocol ascent"
            action[2] = min(action[2], 0.)
            aim_memory = self.runtime.controller.visual_memory.estimate(o)
            action, downlook_applied = camera_only_downlook(action, o, aim_memory, intent.look_down)
            if downlook_applied:
                diag["expert_expired_memory_downlook"] = True
        elif intent.phase == "ground_hold":
            if not o["px4"].get("armed"):
                action[:4] = 0.
        else:
            p = o["px4"]
            yaw = s.yaw_world_rad
            R = self._heading(yaw)
            D = np.diag([1., -1., -1.])
            own_velocity = np.asarray(p["velocity_enu_m_s"], float)
            velocity = -.5 * own_velocity
            goal = intent.height_goal_enu_m if intent.height_goal_enu_m is not None else s.own_height_enu_m
            velocity[2] = np.clip(.6 * (goal - s.own_height_enu_m) - .3 * own_velocity[2], -.2, .4)
            action = np.zeros(6)
            action[3] = intent.yaw_rate_rad_s
            pan, tilt = o["gimbal_rad"]
            desired_tilt = math.radians(self.protocol.SCAN_TILT_BANDS_DEG[self.protocol.scan_band])
            chosen = next((c for c in self.current_candidates if c.track_id == intent.selected_track), None) \
                if intent.phase in ["inspect_candidate", "reorient_candidate", "target_inspect", "reject_overflight"] else None
            if chosen is not None:
                error = wrap(chosen.bearing_world_rad - yaw)
                action[3] = -float(np.clip(.8 * error, -.35, .35))
                desired_tilt = math.radians(35.)
                if chosen.point_world is not None:
                    vector = np.asarray(chosen.point_world) - self.current_camera_world
                    desired_tilt = math.atan2(-vector[2], np.linalg.norm(vector[:2]))
                if intent.allow_approach and chosen.age_s <= .25 and abs(error) < math.radians(20):
                    if intent.phase == "reject_overflight" and chosen.range_interval_m:
                        speed = min(.5, .5 * chosen.range_interval_m[0])
                    elif chosen.range_interval_m:
                        lower = chosen.range_interval_m[0]
                        stop_room = max(0., lower - 1. - 2. * float(o["image_age_s"]))
                        speed = min(2., math.sqrt(stop_room), max(0., lower - .7) * .6)
                    else:
                        speed = .4
                    velocity[:2] = speed * np.array([math.cos(chosen.bearing_world_rad), math.sin(chosen.bearing_world_rad)])
            elif (intent.phase == "reorient_candidate"
                  and intent.target_bearing_world is not None):
                # The track can leave the current candidate list between the
                # protocol decision and this action.  Aim at the remembered
                # bearing/point instead of silently commanding zero yaw.
                error = wrap(intent.target_bearing_world - yaw)
                action[3] = -float(np.clip(.8 * error, -.35, .35))
                if intent.target_point_world is not None:
                    vector = np.asarray(intent.target_point_world) - self.current_camera_world
                    desired_tilt = math.atan2(-vector[2], np.linalg.norm(vector[:2]))
            if intent.look_down:
                desired_tilt = math.radians(75.)
            action[:3] = D @ R.T @ velocity
            aim = (chosen.bearing_world_rad if chosen is not None
                   else intent.target_bearing_world)
            action[4] = 3 * wrap((wrap(aim - yaw) if aim is not None else 0.) - pan) + float(p["angular_rate_frd_rad_s"][2])
            action[5] = 3 * (np.clip(desired_tilt, math.radians(-10), math.pi / 2) - tilt)
            action[2] = min(action[2], 0.)
            norm = np.linalg.norm(action[:2])
            if norm > 2:
                action[:2] *= 2 / norm
            action[2] = np.clip(action[2], -1., .7)
            action[3] = np.clip(action[3], -.5, .5)
            action, extra = self.final_guard.apply(action, o, dict(control_phase=intent.phase,
                                                                  pad_visibility_probability=diag.get("image_head_visibility", 0)))
            diag["expert_override_guard"] = extra
            if not intent.allow_descent:
                action[2] = min(action[2], 0.)
            diag["parent_control_phase"] = diag["control_phase"]
            diag["control_phase"] = intent.phase

        action, intervention = self.supervise(action, o, now - self.start, float(o["mission"]["budget_s"]))
        protocol_state = self.protocol.diagnostics()
        self.selection_log.append(dict(t=round(s.time_s, 3), phase=intent.phase, selected=intent.selected_track,
                                       confirmed=self.protocol.confirmed, reason=intent.reason,
                                       evidence_class=intent.evidence_class))
        if len(self.selection_log) > 600:
            del self.selection_log[:-600]
        diag.update(
            expert_scan_mode=self.protocol.scan_mode,
            expert_static_own_body_rejections=self.own_cad_drops,
            expert_static_own_cad_sha256=self.own_cad.source_sha256,
            expert_scan_band=self.protocol.scan_band,
            expert_scan_tilt_goal_deg=self.protocol.SCAN_TILT_BANDS_DEG[self.protocol.scan_band],
            expert_inspected_view_count=len(self.protocol.inspected_views),
            expert_visit_events=self.protocol.events[-4:],
            expert_search_exhausted=self.protocol.search_exhausted,
            expert_survey_epoch=self.protocol.survey_epoch,
            expert_scan_coverage_rad=self.protocol.scan_coverage,
            expert_empty_surveys=self.protocol.empty_surveys,
            expert_intent=asdict(intent),
            expert_visual_tracks=self.bank.diagnostics(),
            expert_source="RGB/own telemetry/encoders/declared static priors only",
            expert_intervention=intervention,
            expert_capture_history_error_s=self.capture_error,
            expert_observable_target_confirmed=self.protocol.confirmed is not None,
            expert_actual_flight_validated=False,
            expert_review_only=self.review_only,
            expert_recognition_qualification_passed=self.qualification_gate_passed,
            expert_marker_localizer=self.pad_diagnostics,
            expert_protocol_v60=protocol_state,
            expert_selection_authority=dict(selected=self.protocol.selected, confirmed=self.protocol.confirmed,
                                            anchor_age_s=protocol_state.get("anchor", {}).get("age_s")
                                            if protocol_state.get("anchor") else None,
                                            plausibility_m=self.protocol.plausible_length_m),
            expert_invariant_violations=protocol_state.get("invariant_violations", []),
        )
        return action, diag
