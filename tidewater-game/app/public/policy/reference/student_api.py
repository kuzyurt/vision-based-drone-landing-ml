"""Pyodide boundary for the frozen student search/radio controller.

The combined ONNX graph executes pose + search head on WebGPU.  This module
receives the 15-value pose and the decoded search proposals, then runs the
sensor-only search state machine, radio-first approach, pre360 sweep and the
existing R15 landing controller without any simulator truth.
"""
import copy
import json
import math

import numpy as np

from .marker_policy import MarkerPosePolicy
from .recording import numeric_observation
from . import runtime_fixes
from .student_radio import RadioSearchRuntime

runtime = None
config = None


def initialize(configuration_json):
    global runtime, config
    config = json.loads(configuration_json)
    runtime_fixes.install(__package__)
    policy = MarkerPosePolicy(None, config['calibration'],
                              config['slew_limits'], 'browser')
    policy.reset()
    policy.controller.visual_search_started = None
    runtime = RadioSearchRuntime(config, policy)


def prepare(observation):
    observation = copy.deepcopy(observation)
    mission = observation.setdefault('mission', {})
    mission.setdefault('elapsed_s', float(observation.get('image_delivery_time_s', 0.0) or 0.0))
    mission.setdefault('budget_s', 180.0)
    beacon = observation.setdefault('beacon', {})
    beacon.setdefault('valid', False)
    beacon.setdefault('dock_ready', False)
    beacon.setdefault('age_s', 3.1)
    beacon.setdefault('relative_heading_m', [0.0, 0.0, 0.0])
    beacon.setdefault('velocity_heading_m_s', [0.0, 0.0, 0.0])
    if not beacon.get('valid', False):
        beacon.update(valid=False, age_s=3.1,
                      relative_heading_m=[0.0, 0.0, 0.0],
                      velocity_heading_m_s=[0.0, 0.0, 0.0])
    return observation


def numeric(observation_json):
    observation = prepare(json.loads(observation_json))
    values = numeric_observation({'observation': observation})
    if len(values) != 32:
        raise ValueError('Student policy requires the original 32-value sensor contract')
    if not np.isfinite(values).all():
        raise ValueError('Non-finite policy sensor input')
    return values.tolist()


def clean(value):
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _search_warning(diagnostics):
    if diagnostics.get('warning_code'):
        return str(diagnostics['warning_code'])
    passes = int(diagnostics.get('scan_passes_completed', 0) or 0)
    if passes >= 2 and not diagnostics.get('search_identity_confirmed', False):
        if passes >= 3:
            return 'boat_search_exhausted'
        return f'search_pass_{passes}_no_identity'
    return None


def step(rgb, prediction, proposals_json, observation_json, elapsed_s):
    observation = prepare(json.loads(observation_json))
    output = np.asarray(prediction, dtype=np.float32).reshape(-1)
    if output.size < 15 or not np.isfinite(output[:15]).all():
        raise ValueError('Student policy requires a finite 15-value pose prediction')
    proposals = json.loads(proposals_json) if proposals_json else []
    if not isinstance(proposals, list):
        raise ValueError('Student proposals must be a list')
    runtime.base.set_prediction(output[:15])
    runtime.set_proposals(proposals)
    if rgb is None:
        image = None
    else:
        buffer = np.frombuffer(rgb, dtype=np.uint8) if isinstance(rgb, (bytes, bytearray, memoryview)) else np.asarray(rgb, dtype=np.uint8)
        image = buffer.reshape(360, 640, 3)
    action, diagnostics = runtime.act(image, observation)
    diagnostics = dict(diagnostics)
    diagnostics.setdefault('boat_radio', False)
    diagnostics.setdefault('search_identity_confirmed',
                           bool(getattr(runtime.search, 'confirmed', False)))
    diagnostics['search_mode'] = getattr(runtime.search, 'mode', None)
    diagnostics['search_phase'] = getattr(runtime.search, 'phase', None)
    diagnostics['scan_passes_completed'] = int(
        getattr(runtime.search, 'scan_passes_completed', 0) or 0)
    diagnostics['search_selected'] = getattr(runtime, 'selected', None)
    diagnostics['search_proposals'] = [p for p in proposals if not p.get('weak')]
    summary = getattr(runtime, 'guidance_summary', None)
    if summary is not None:
        diagnostics['guidance'] = summary()
    diagnostics['pre360_done'] = bool(getattr(runtime, 'pre360_done', False))
    diagnostics['pre360_phase'] = getattr(runtime, 'pre360_phase', None)
    diagnostics['radio_active'] = bool(diagnostics.get('boat_radio', False))
    diagnostics['radio_age_s'] = float(diagnostics.get('radio_age_s', 0.0) or 0.0)
    warning = _search_warning(diagnostics)
    diagnostics['search_warning'] = warning
    diagnostics['policy_elapsed_s'] = float(elapsed_s)
    return json.dumps(clean({'action': action, 'diagnostics': diagnostics,
                             'intervention': diagnostics.get('intervention')}),
                      allow_nan=False)
