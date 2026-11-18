"""Fly the current Tidewater student stack inside the benchmark.

Same network (student.onnx, run with onnxruntime) and the same Python
controller (tidewater-game/app/public/policy/reference/student_api.py) that the
browser game runs.  Nothing is re-implemented except the two small JavaScript
helpers that turn the raw search-head tensors into proposals (decode, weak
peaks); they are literal ports of StudentSearch.js.

Known differences from the browser, kept explicit:
- no solar ephemeris is supplied (MuJoCo has no sun glare), so the glare logic
  stays inactive;
- the marker kernel is the Python reference instead of marker_kernel.wasm;
- the mission clock budget is the scenario's, not the game's fixed 180 s.

This module does not touch the pinned harness files; run.py selects it only
through harness/tidewater_run.py.
"""
import copy
import hashlib
import importlib
import json
import math
import subprocess
import sys
import types
from pathlib import Path

import numpy as np

from .common import REPO, ROOT, read, sha, write
from . import student as student_base

POLICY_DIR = REPO / 'tidewater-game/app/public/policy'
REFERENCE_DIR = POLICY_DIR / 'reference'
STUDENT_DIR = ROOT / 'policies/student'
BASE = 'r15-archived-export-67a80a63'

HEIGHT, WIDTH = 45, 80
EVIDENCE = ('unknown_boat', 'target_or_similar', 'different_boat', 'target_boat')
THRESHOLD, MAX_OBJECTS = 0.36, 7
EVIDENCE_T, IDENTITY_T, TARGET_LIKE_T, TARGET_ID_T = 0.8, 0.98, 0.6, 0.85


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=np.float64)))


def _local_max(values, radius=2):
    """True where no cell inside the (2r+1)^2 window is strictly larger."""
    padded = np.pad(values, radius, constant_values=-np.inf)
    best = np.full(values.shape, -np.inf)
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            best = np.maximum(best, padded[dy:dy + values.shape[0], dx:dx + values.shape[1]])
    return values >= best


def decode_search(heat, offset, evidence, identity):
    """Port of StudentSearch.js::decodeStudentSearch."""
    heat = _sigmoid(heat.reshape(HEIGHT, WIDTH))
    offset = offset.reshape(2, HEIGHT, WIDTH)
    evidence = evidence.reshape(4, HEIGHT, WIDTH)
    identity = identity.reshape(2, HEIGHT, WIDTH)
    keep = _local_max(heat) & (heat >= THRESHOLD)
    scores = np.where(keep, heat, 0.0).astype(np.float32).ravel()
    order = [i for i in np.flatnonzero(scores >= THRESHOLD)]
    order.sort(key=lambda i: (-float(scores[i]), -int(i)))
    items = []
    for index in order[:MAX_OBJECTS * 2]:
        row, col = divmod(int(index), WIDTH)
        px = float((col + 0.5 + offset[0, row, col]) * 640 / WIDTH)
        py = float((row + 0.5 + offset[1, row, col]) * 360 / HEIGHT)
        if any((px - it['pixel'][0]) ** 2 + (py - it['pixel'][1]) ** 2 < 28 ** 2 for it in items):
            continue
        ev = np.exp(evidence[:, row, col] - evidence[:, row, col].max())
        ev /= ev.sum()
        ident = np.exp(identity[:, row, col] - identity[:, row, col].max())
        ident /= ident.sum()
        k = int(ev.argmax())
        label = EVIDENCE[k]
        if ev[k] < EVIDENCE_T:
            if ev[1] + ev[3] >= TARGET_LIKE_T:
                label = 'target_boat' if (ev[3] >= 0.42 and ident[1] >= 0.82) else 'target_or_similar'
            else:
                label = 'unknown_boat'
        if label == 'target_boat' and ident[1] < min(IDENTITY_T, TARGET_ID_T):
            label = 'target_or_similar'
        if label == 'different_boat' and ident[0] < IDENTITY_T:
            label = 'unknown_boat'
        items.append(dict(pixel=[px, py], confidence=float(scores[index]), evidence=label,
                          identity_target_probability=float(ident[1])))
        if len(items) >= MAX_OBJECTS:
            break
    return items


def weak_peaks(heat, offset, proposals, minimum=0.07, maximum=0.36, count=5):
    """Port of StudentSearch.js::weakSearchPeaks."""
    value = _sigmoid(heat.reshape(HEIGHT, WIDTH))
    offset = offset.reshape(2, HEIGHT, WIDTH)
    peak = _local_max(value)
    out = []
    for row in range(1, HEIGHT - 1):
        for col in range(1, WIDTH - 1):
            v = float(value[row, col])
            if v < minimum or v >= maximum or not peak[row, col]:
                continue
            px = float((col + 0.5 + offset[0, row, col]) * 640 / WIDTH)
            py = float((row + 0.5 + offset[1, row, col]) * 360 / HEIGHT)
            if any((px - it['pixel'][0]) ** 2 + (py - it['pixel'][1]) ** 2 < 28 ** 2 for it in proposals):
                continue
            out.append(dict(pixel=[px, py], confidence=v, evidence='weak',
                            identity_target_probability=0, weak=True))
    out.sort(key=lambda it: -it['confidence'])
    return out[:count]


def _plain(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def _source_receipt():
    files = {p.name: sha(p) for p in sorted(REFERENCE_DIR.glob('*.py'))}
    files['student.onnx'] = sha(POLICY_DIR / 'student.onnx')
    files['manifest.json'] = sha(POLICY_DIR / 'manifest.json')
    try:
        commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, capture_output=True,
                                text=True, timeout=20).stdout.strip()
        dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--', 'tidewater-game/app/public/policy'],
                                    cwd=REPO, capture_output=True, text=True, timeout=20).stdout.strip())
    except Exception:
        commit, dirty = 'unknown', None
    return dict(files=files, git_commit=commit, policy_dir_dirty=dirty)


def policy():
    """Policy row with its own identity; the R15 base calibration is reused unchanged."""
    p = copy.deepcopy(read(ROOT / 'policies' / BASE / 'model.json'))
    receipt = _source_receipt()
    digest = hashlib.sha256(json.dumps(receipt['files'], sort_keys=True).encode()).hexdigest()
    p.update(id='tidewater-student-' + digest[:8],
             label='Tidewater student (current browser stack, native)',
             identity_sha256=digest,
             role='unprivileged learned search policy, Tidewater reference controller',
             fresh_search_identity=dict(receipt, checkpoint_sha256=sha(POLICY_DIR / 'student.onnx'),
                                        base_identity_sha256=p['identity_sha256']),
             tidewater_student=True)
    return p


def _use_python_marker_fit():
    """Run the marker fit without the browser's WASM kernel.

    marker_geometry.py redefines marker_pose three times; the last one needs
    `js.marker_kernel` (the WASM accelerator), which does not exist natively.
    The first definition is the frozen Python fit that the kernel reproduces
    (the file keeps it for parity tests), so we rebuild it from the file's own
    source above the first redefinition and use it with the paint-prior seed
    exactly as the file's ImportError fallback intends.
    """
    mg = importlib.import_module('reference.marker_geometry')
    if getattr(mg, '_native_python_fit', False):
        return
    source = (REFERENCE_DIR / 'marker_geometry.py').read_text(encoding='utf-8')
    cut = source.index('# Keep the frozen implementation callable')
    frozen = types.ModuleType('reference._marker_geometry_frozen')
    frozen.__package__ = 'reference'
    frozen.__file__ = str(REFERENCE_DIR / 'marker_geometry.py')
    exec(compile(source[:cut], frozen.__file__, 'exec'), frozen.__dict__)
    original = frozen.marker_pose

    def marker_pose(rgb, observation, calibration, estimate):
        if not observation['beacon'].get('valid', False) and not estimate.get('_tracked', False):
            from reference.visual_acquisition import paint_prior
            seed = paint_prior(rgb, observation, calibration, estimate)
            return None if seed is None else original(rgb, observation, calibration, seed)
        return original(rgb, observation, calibration, estimate)

    mg.marker_pose = marker_pose
    mg._native_python_fit = True
    policy_module = importlib.import_module('reference.marker_policy')
    policy_module.marker_pose = marker_pose


class TidewaterActor:
    """The browser's PolicyInference.act, run natively."""

    def __init__(self, device='cpu'):
        import onnxruntime as ort
        if str(POLICY_DIR) not in sys.path:
            sys.path.insert(0, str(POLICY_DIR))
        for name in list(sys.modules):
            if name == 'reference' or name.startswith('reference.'):
                del sys.modules[name]
        self.api = importlib.import_module('reference.student_api')
        _use_python_marker_fit()
        self.manifest = (POLICY_DIR / 'manifest.json').read_text(encoding='utf-8')
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(POLICY_DIR / 'student.onnx'), options,
                                            providers=['CPUExecutionProvider'])
        self.reset()

    def reset(self):
        self.api.initialize(self.manifest)
        self.hidden = np.zeros((1, 1, 128), np.float32)

    @property
    def controller(self):
        # MissionSafety reads policy.controller.calibration.
        return self.api.runtime.base.controller

    def act(self, rgb, observation):
        sensor = _sensor(observation)
        observation_json = json.dumps(sensor, default=_plain, allow_nan=False)
        numeric = np.asarray(self.api.numeric(observation_json), np.float32).reshape(1, 1, 32)
        frame = np.ascontiguousarray(rgb, dtype=np.uint8).reshape(360, 640, 3)
        image = np.ascontiguousarray(frame.transpose(2, 0, 1)[None, None]).astype(np.float32)
        out = self.session.run(None, dict(image=image, numeric=numeric, hidden=self.hidden))
        names = [o.name for o in self.session.get_outputs()]
        result = dict(zip(names, out))
        self.hidden = result['next_hidden'].astype(np.float32)
        proposals = decode_search(result['search_heat'], result['search_offset'],
                                  result['search_evidence'], result['search_identity'])
        weak = weak_peaks(result['search_heat'], result['search_offset'], proposals)
        answer = json.loads(self.api.step(
            frame.tobytes(), result['prediction'].reshape(-1).astype(np.float32).tolist(),
            json.dumps(proposals + weak), observation_json, float(sensor['mission']['elapsed_s'])))
        action = np.asarray(answer['action'], dtype=float)
        diagnostics = dict(answer['diagnostics'])
        diagnostics['search_proposal_count'] = len(proposals)
        return action, diagnostics


def _sensor(observation):
    """Allow-list what the browser's PolicyTelemetry provides; radio only as the declared packet."""
    from common import no_radio_observation
    mission = observation['mission']
    sensor = no_radio_observation(
        observation['px4'], observation['gimbal_rad'], observation['previous_executed_action'],
        observation['image_capture_time_s'], mission['elapsed_s'], mission['budget_s'])
    for key in ('image_delivery_time_s', 'image_age_s', 'image_valid', 'decision_dt_s'):
        sensor[key] = observation[key]
    for key in ('recovery_clearance', 'water_datum_enu_m', 'nominal_deck_height_above_water_m',
                'coarse_height_uncertainty_m'):
        if key in mission:
            sensor['mission'][key] = copy.deepcopy(mission[key])
    if 'beacon' in observation:
        sensor['beacon'] = copy.deepcopy(observation['beacon'])
    return sensor


def install(runner, selected, output):
    """Same hook as student.install: stage the unchanged R15 helpers, swap in the actor."""
    sys.path.insert(0, str(STUDENT_DIR))
    actor = TidewaterActor(selected.get('device', 'cpu'))
    reference = read(ROOT / 'policies' / BASE / 'model.json')
    stage, preflight = runner.stage, runner.preflight
    real_import = importlib.import_module
    runner.stage = lambda p, folder: stage(reference, folder)
    runner.preflight = lambda p: preflight(reference)

    def load(name, *args, **kwargs):
        if name == 'benchmark_actor.radio_robust_20261015.runtime':
            def construct(*a, **kw):
                write(Path(output) / 'student_actor.json', dict(
                    actual_class='reference.student_api (Tidewater browser stack, native)',
                    identity=selected['fresh_search_identity'],
                    boat_radio='declared packet only; none in radio-off cases',
                    ephemeris=False, oracle_used=False))
                return actor
            return types.SimpleNamespace(RadioRobustRuntime=construct)
        return real_import(name, *args, **kwargs)

    runner.importlib = types.SimpleNamespace(import_module=load, util=importlib.util)
