"""Build the browser manifest for the staged student policy bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / 'tidewater-game/app'
POLICY = APP / 'public/policy'
STAGED = POLICY / 'student'
STUDENT = ROOT / 'benchmark/policies/student/output_optimized'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    old = json.loads((POLICY / 'manifest.json').read_text(encoding='utf-8'))
    exported = json.loads((STAGED / 'export.json').read_text(encoding='utf-8'))
    policy = json.loads((STUDENT / 'policy.json').read_text(encoding='utf-8'))
    references = {}
    for path in sorted((POLICY / 'reference').glob('*')):
        if path.is_file():
            references[path.name] = sha(path)
    manifest = {
        'schema': 'aerodock.landing.search_student_policy.v1',
        'policy_class': 'reference.student_radio.RadioSearchRuntime',
        'checkpoint': 'search_best.pt',
        'checkpoint_sha256': policy['checkpoint_sha256'],
        'base': 'base/pose.pt',
        'base_checkpoint_sha256': old['checkpoint_sha256'],
        'source_policy_schema': policy['schema'],
        'source_policy_runtime': policy['runtime'],
        'source_fingerprint': policy['source_fingerprint'],
        'selected_epoch': None,
        'calibration': old['calibration'],
        'slew_limits': old['slew_limits'],
        'mission_budget_s': old['mission_budget_s'],
        'allow_visual_landing': True,
        'boat_radio': True,
        'unknown_dock_observation_mean': old['unknown_dock_observation_mean'],
        'algorithm_version': 'radio_search_student_v1',
        'browser_schema': 'tidewater.search_student.browser.v1',
        'model': exported['model'],
        'model_sha256': exported['model_sha256'],
        'model_bytes': exported['model_bytes'],
        'input_contract': {
            'image': [1, 1, 3, 360, 640],
            'numeric': [1, 1, 32],
            'hidden': [1, 1, 128],
            'prediction': [1, 1, 15],
            'numeric_fields': 'original 32-value sensor contract',
            'prediction_fields': 'fused pose[15]',
            'image_dtype': 'float32',
            'image_value_range': [0, 255],
        },
        'output_contract': {
            'search': {
                'heat': [1, 45, 80],
                'offset': [1, 2, 45, 80],
                'presence': [1, 1],
                'evidence': [1, 4, 45, 80],
                'identity': [1, 2, 45, 80],
            },
        },
        'search_thresholds': {
            'proposal_threshold': 0.5,
            'max_objects': 7,
            'evidence_threshold': 0.8,
            'identity_threshold': 0.98,
            'target_like_threshold': 0.6,
            'target_identity_threshold': 0.85,
        },
        'reference_entry': 'student_api.py',
        'reference_adapter_sha256': references,
        'runtime': old['runtime'],
        'marker_kernel': old['marker_kernel'],
        'marker_kernel_sha256': old['marker_kernel_sha256'],
        'marker_kernel_source_sha256': old['marker_kernel_source_sha256'],
        'marker_solver_source_sha256': old['marker_solver_source_sha256'],
        # Same values as tools/refresh-policy-manifest.py (run that after
        # editing public/policy/reference/).
        'pre360': {
            'tilt_deg': 75.0,
            'nadir_s': 2.5,
            'yaw_rate_rad_s': 0.5,
            'sweep_timeout_s': 45.0,
            'handoff_rule': 'normal_search_evidence',
            'handoff_note': 'pre360 ends as soon as the normal search would inspect (target_or_similar) or confirm (target_boat) a boat; same thresholds and 0.12 s stable support as the normal search',
        },
        'min_search_height_m': 5.0,
        'export_parity': exported['export_parity'],
        'native_parity': exported['native_parity'],
        'search_engine': {
            'input_proposals': 'decoded SearchHead proposals; no radio coordinates enter search/identity',
            'search_decision': 'benchmark/policies/student/revised_teacher.py SearchDecision',
            'radio_first': 'RadioSearchRuntime; fresh/plausible packet only until pre360/handoff',
            'base_landing': 'frozen R15 MarkerPosePolicy controller, radio-free observation',
        },
        'qualification': 'staged browser port; benchmark policy is not closed-loop qualified',
        'rollback': 'legacy vision-first manifest preserved in public/policy-legacy-vision-first',
        'staged_at': '2026-11-12',
    }
    target = STAGED / 'manifest.json'
    target.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(target)
    print('model', manifest['model_sha256'], 'references', len(references))


if __name__ == '__main__':
    main()
