"""Load the radio-first search student over the frozen R15 base."""
import copy
import importlib
import sys
import types
from .common import REPO, ROOT, read, sha, write

RUN = ROOT / 'policies/student_radio'
BUNDLE = ROOT / 'policies/student/output_optimized'
BASE = 'r15-archived-export-67a80a63'


def policy():
    manifest = read(BUNDLE / 'policy.json')
    checkpoint = sha(BUNDLE / manifest['checkpoint'])
    if checkpoint != manifest['checkpoint_sha256']:
        raise ValueError('Search checkpoint checksum mismatch')
    canonical = read(RUN / 'identity.json')
    identity = canonical['identity']
    if checkpoint != identity['checkpoint_sha256']:
        raise ValueError('Radio search identity checkpoint mismatch')
    p = copy.deepcopy(read(ROOT / 'policies' / BASE / 'model.json'))
    if p['identity_sha256'] != identity['base_identity_sha256']:
        raise ValueError('Radio search identity base mismatch')
    p.update(id='fresh-search-radio-' + checkpoint[:8],
             label='Radio-first search student / frozen R15',
             identity_sha256=canonical['identity_sha256'],
             role='unprivileged learned search policy with radio-first guidance',
             fresh_search_identity=identity, radio_search=True)
    return p


def install(runner, selected, output):
    """Stage unchanged calibration/helpers; the actor is RadioSearchRuntime."""
    import torch
    torch.set_num_threads(1)
    local = REPO / 'artifacts/local_curriculum_20261020'
    if str(local) not in sys.path:
        sys.path.insert(0, str(local))
    sys.path.insert(0, str(RUN))
    sys.path.insert(0, str(ROOT / 'policies/student'))
    from radio_runtime import RadioSearchRuntime
    from common import no_radio_observation
    raw = RadioSearchRuntime(BUNDLE, selected.get('device', 'cpu'))

    class DeclaredInputActor:
        def reset(self):
            raw.reset()

        def __getattr__(self, name):
            return getattr(raw, name)

        def act(self, rgb, observation):
            sensor = no_radio_observation(
                observation['px4'], observation['gimbal_rad'],
                observation['previous_executed_action'],
                observation['image_capture_time_s'],
                observation['mission']['elapsed_s'],
                observation['mission']['budget_s'])
            for key in ('image_delivery_time_s', 'image_age_s', 'image_valid',
                        'decision_dt_s'):
                sensor[key] = observation[key]
            if 'recovery_clearance' in observation['mission']:
                sensor['mission']['recovery_clearance'] = observation['mission']['recovery_clearance']
            # The only additional input is the declared boat packet.  It is
            # copied, never merged from a teacher or environment object.
            if 'beacon' in observation:
                sensor['beacon'] = copy.deepcopy(observation['beacon'])
            return raw.act(rgb, sensor)

    actor = DeclaredInputActor()
    reference = read(ROOT / 'policies' / BASE / 'model.json')
    stage = runner.stage
    preflight = runner.preflight
    real_import = importlib.import_module
    runner.stage = lambda p, folder: stage(reference, folder)
    runner.preflight = lambda p: preflight(reference)

    def load(name, *args, **kwargs):
        if name == 'benchmark_actor.radio_robust_20261015.runtime':
            def construct(*a, **kw):
                from pathlib import Path
                write(Path(output) / 'student_actor.json',
                      dict(actual_class='radio_runtime.RadioSearchRuntime',
                           identity=selected['fresh_search_identity'],
                           boat_radio=True, radio_first=True, oracle_used=False))
                return actor
            return types.SimpleNamespace(RadioRobustRuntime=construct)
        return real_import(name, *args, **kwargs)

    runner.importlib = types.SimpleNamespace(import_module=load, util=importlib.util)
