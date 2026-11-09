"""Register the wave-aware teacher without touching the frozen teacher row."""
from pathlib import Path

from benchmark.common import ROOT, read, write, sha, fingerprint, utc
from benchmark.inventory import ARCHITECTURES, receipt

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'teacher_policy_wave.json'
SOURCE_NAMES = (
    'landing_training/privileged_teacher.py',
    'landing_training/smooth_landing.py',
    'landing_training/expert.py',
    'landing_training/wave_teacher.py',
)


def register_policy():
    config = read(MANIFEST)
    sources = [receipt(ROOT.parent / name) for name in SOURCE_NAMES]
    identity = fingerprint(dict(
        config=config,
        source_files=[(item['path'], item['sha256']) for item in sources],
    ))
    identifier = 'privileged-teacher-wave-gate-' + identity[:8]
    manifest = receipt(MANIFEST)
    row = dict(
        id=identifier,
        label=config['label'],
        identity_sha256=identity,
        manifest=manifest,
        aliases=[],
        source_root='landing_training',
        source_files=sources,
        actor='privileged_teacher',
        actor_source_root=None,
        actor_source_files=[],
        weights={},
        architecture='privileged_teacher',
        architecture_base='privileged_teacher',
        available=True,
        missing=[],
        role='privileged teacher',
        benchmark_status='not_run',
        captured_utc=utc(),
        file_modified_utc=manifest['file_modified_utc'],
        timestamp_basis='Source snapshot time; no trained weights.',
        historical_qualification=(
            'Wave-aware variant of privileged-teacher-platform-aligned-7ac0a6ff; '
            'search and visibility rules are inherited unchanged.'
        ),
    )
    folder = ROOT / 'models' / identifier
    write(folder / 'policy.json', config)
    write(folder / 'architecture.json', dict(ARCHITECTURES['privileged_teacher'], source_files=sources))
    write(folder / 'weights.json', {})
    write(folder / 'model.json', row)

    inventory = read(ROOT / 'models/inventory.json')
    inventory['policies'] = [p for p in inventory['policies'] if p['id'] != identifier]
    inventory['policies'].append(row)
    write(ROOT / 'models/inventory.json', inventory)
    write(HERE / 'policy_id.json', dict(
        policy_id=identifier,
        identity_sha256=identity,
        manifest=manifest,
        source_files=sources,
        registered_utc=utc(),
    ))
    print('Registered', identifier, flush=True)
    return row

if __name__ == '__main__':
    register_policy()
