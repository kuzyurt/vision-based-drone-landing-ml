"""Re-seal the browser policy after editing its Python decision logic.

The game only loads policy files whose SHA-256 matches public/policy/manifest.json
(PolicyInference.js refuses anything else). Run this after changing any file in
public/policy/reference/:

    python tidewater-game/app/tools/refresh-policy-manifest.py

It recomputes the reference checksums, checks that the network and marker-kernel
files still match, records the current decision-rule settings, and keeps the
manifest's formatting and line endings. Use --check to only verify.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
POLICY = APP / 'public/policy'

# Decision-rule settings recorded in the manifest (documentation for readers and
# tests; the Python files are the authority).
PRE360 = {
    'tilt_deg': 75.0,
    'nadir_s': 2.5,
    'yaw_rate_rad_s': 0.5,
    'sweep_timeout_s': 45.0,
    'handoff_rule': 'normal_search_evidence',
    'handoff_note': 'pre360 ends as soon as the normal search would inspect (target_or_similar) or confirm (target_boat) a boat; same thresholds and 0.12 s stable support as the normal search',
}
MIN_SEARCH_HEIGHT_M = 5.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='only verify, do not write')
    parser.add_argument('--policy', type=Path, default=POLICY)
    args = parser.parse_args()
    policy = args.policy.resolve()
    target = policy / 'manifest.json'
    raw = target.read_bytes()
    crlf = b'\r\n' in raw
    manifest = json.loads(raw.decode('utf-8'))
    problems = []
    for key, file_key in (('model_sha256', 'model'), ('marker_kernel_sha256', 'marker_kernel')):
        path = policy / manifest[file_key]
        if sha(path) != manifest[key]:
            problems.append(f'{path.name} does not match {key}; re-export the network instead')
    references = {path.name: sha(path) for path in sorted((policy / 'reference').iterdir()) if path.is_file()}
    changed = sorted(name for name, digest in references.items() if manifest['reference_adapter_sha256'].get(name) != digest)
    removed = sorted(set(manifest['reference_adapter_sha256']) - set(references))
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        return 2
    rules_changed = manifest.get('pre360') != PRE360 or manifest.get('min_search_height_m') != MIN_SEARCH_HEIGHT_M
    if args.check:
        if changed or removed:
            print('Out of date:', ', '.join(changed + removed), file=sys.stderr)
            return 1
        print('Policy manifest matches every policy file.')
        return 0
    manifest['reference_adapter_sha256'] = references
    manifest['pre360'] = PRE360
    manifest['min_search_height_m'] = MIN_SEARCH_HEIGHT_M
    text = json.dumps(manifest, indent=2) + '\n'
    if crlf:
        text = text.replace('\n', '\r\n')
    if text.encode('utf-8') != raw:
        target.write_bytes(text.encode('utf-8'))
    print('Updated checksums:', ', '.join(changed + removed) or 'none',
          '| rule settings', 'updated' if rules_changed else 'unchanged')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
