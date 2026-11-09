"""Read-only source discovery plus content-addressed copies. Never unpickles weights."""
import ast
import hashlib
import io
from datetime import datetime, timezone
import os
from pathlib import Path
import pickletools
import re
import shutil
import tarfile
import zipfile
from .common import REPO, ROOT, fingerprint, read, sha, utc, write

SKIP = {'.git', 'node_modules', '.venv', 'venv', 'policy-export-venv', '__pycache__', '.vendor', 'benchmark'}
WEIGHTS = {'.pt', '.pth', '.onnx', '.ckpt', '.safetensors'}
SOURCE_EXT = {'.py', '.cpp', '.h', '.hpp', '.so', '.dll', '.json', '.npz'}
ARCHITECTURES = {
    'privileged_teacher': {'name': 'Simulator-assisted teacher reference; no neural network',
        'vision': 'Exact currently visible instance pixels, range/resolution gates and sustained evidence',
        'control': 'Visible-target privileged deck pose → platform-aligned smooth controller → PX4',
        'note': 'A privileged reference, not an unaided learned policy.'},
    'radio_pose': {'name': 'Recurrent radio/visual pose checkpoint',
                   'note': 'This schema spans multiple fusion architectures. The full policy architecture receipt and source, not the schema alone, identify the exact network.'},
    'radio_conditioned': {
        'name': 'Quality-conditioned recurrent radio/visual pose + geometric control',
        'vision': 'MobileNetV3-Small spatial summary → 256 visual features',
        'telemetry': '32 → 64 → 64, plus uncertainty Linear(2,64)',
        'memory': 'GRU(320,128); absolute visual Linear(128,6) and inherited pose heads',
        'radio': 'Validity/age/uncertainty-aware recurrent input; this predates independent visual recurrence and bounded fusion gates',
        'control': 'Learned pose estimates, marker registration, explicit controller and PX4',
    },
    'radio_robust': {
        'name': 'Recurrent visual pose + bounded radio fusion + geometric control',
        'vision': 'MobileNetV3-Small; spatial feature summaries; visual projection 1728 → 256',
        'telemetry': '32 → 64 → 64; visual and telemetry concatenation 320',
        'memory': 'GRU(320, 128)',
        'state': '15 pose/contact values; inherited six-action head is not the executed control path',
        'radio': 'Separate 13 → 48 → 2 fusion MLP; position/velocity blend bounded to 0.35',
        'control': 'Marker registration, explicit guarded velocity/yaw/gimbal control, real PX4',
        'note': 'Spatial and acquisition heads differ by revision. Per-model frozen source receipts are authoritative.',
    },
    'recognizer': {
        'name': 'Dense boat discriminator + RGB object verifier',
        'input': 'MobileNet fine/context features plus candidate RGB crops (96 × 96)',
        'rgb_verifier': 'Stride-2 CNN widths 16,32,64,64 → pool 3×3 → 576→128→64',
        'output': 'Target / wrong design / unknown logits; marker confidence',
        'note': 'A recognition checkpoint alone is not a flight policy. rgb_only/residual is checkpoint metadata.',
    },
    'marker': {'name': 'Historical learned pose + marker geometry controller',
               'note': 'Original pose schema; retained as inventory. Runtime source is incomplete locally for this bundle.'},
    'spatial': {'name': 'Image-only spatial boat/pad acquisition head',
                'fine_context': '24-channel fine and 48-channel context maps → separate 1×1 Conv to 24 channels each',
                'merge': 'Concatenate 48 channels → two 3×3 Conv(48,48) blocks; heatmap, subcell offset, presence heads',
                'note': 'Component only, no standalone flight controller.'},
    'acquisition': {'name': 'Global-feature acquisition MLP',
                    'network': 'Normalized/clamped 1728 features → 256 → 128 → 3; ReLU and dropout 0.1',
                    'note': 'Visibility and image-centre acquisition component; distinct from the spatial CNN head.'},
    'action': {'name': 'Historical recurrent action policy',
               'network': 'MobileNetV3-Small + 32→64→64 telemetry + GRU(320,128) → 6 actions / 10 auxiliaries'},
    'onnx': {'name': 'Exported pose inference graph',
             'note': 'Browser inference component. Export does not include the complete controller/search/PX4 stack.'},
}


def files():
    found = []
    for directory, dirs, names in os.walk(REPO):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        found.extend(Path(directory) / n for n in sorted(names))
    return found


def receipt(path):
    return dict(path=path.relative_to(REPO).as_posix(), sha256=sha(path), bytes=path.stat().st_size,
                file_modified_utc=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())


def pickle_schema(path):
    # pickletools parses opcodes without importing modules or executing reducers.
    try:
        with zipfile.ZipFile(path) as archive:
            member = next(n for n in archive.namelist() if n.endswith('/data.pkl'))
            if archive.getinfo(member).file_size > 32 * 1024 * 1024:
                return None
            strings = [arg for op, arg, _ in pickletools.genops(archive.read(member))
                       if op.name in ('BINUNICODE', 'SHORT_BINUNICODE', 'BINUNICODE8')]
        return next((s for s in strings if s.startswith(('aerodock.', 'mujoco.'))), None)
    except (ValueError, StopIteration, zipfile.BadZipFile):
        return None


def tree_receipts(folder):
    return [receipt(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and p.suffix in SOURCE_EXT and '__pycache__' not in p.parts]


def family_for(path, schema):
    schema = schema or ''
    return ('onnx' if Path(path).suffix == '.onnx' else 'recognizer' if 'discriminator' in schema
            else 'radio_pose' if 'radio_robust_pose' in schema else 'marker' if 'pose.v1' in schema
            else 'action' if 'checkpoint.v1' in schema else 'acquisition' if Path(path).name=='acquisition.pt' else 'spatial')


def archive_members(path):
    """Read only named checkpoint bytes. Never extract executable/archive paths."""
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                if Path(item.filename).suffix in WEIGHTS:
                    yield dict(path=item.filename, bytes=item.file_size, crc32=f'{item.CRC:08x}',
                               archive_timestamp=list(item.date_time),
                               timestamp_basis='ZIP entry time; timezone unspecified, not a verified training time'), archive.read(item)
    else:
        with tarfile.open(path, 'r:*') as archive:
            for item in archive:
                if item.isfile() and Path(item.name).suffix in WEIGHTS:
                    with archive.extractfile(item) as stream:
                        blob = stream.read()
                    stamp = datetime.fromtimestamp(item.mtime, timezone.utc)
                    yield dict(path=item.name, bytes=item.size, archive_timestamp=[stamp.year,stamp.month,stamp.day,stamp.hour,stamp.minute,stamp.second],
                               timestamp_basis='TAR entry modification time (UTC), not a verified training time'), blob


def register_privileged_teacher(policies):
    manifest = ROOT / 'teacher_policy.json'
    sources = [receipt(REPO / 'landing_training' / n) for n in
               ['privileged_teacher.py', 'smooth_landing.py', 'expert.py']]
    config = read(manifest)
    identity = fingerprint(dict(config=config, source_files=[(r['path'],r['sha256']) for r in sources]))
    identifier = 'privileged-teacher-platform-aligned-' + identity[:8]
    row = dict(id=identifier, label=config['label'], identity_sha256=identity,
        manifest=receipt(manifest), aliases=[], source_root='landing_training', source_files=sources,
        actor='privileged_teacher', actor_source_root=None, actor_source_files=[], weights={},
        architecture='privileged_teacher', architecture_base='privileged_teacher', available=True,
        missing=[], role='privileged teacher', benchmark_status='not_run', captured_utc=utc(),
        file_modified_utc=receipt(manifest)['file_modified_utc'],
        timestamp_basis='Source snapshot time; no trained weights.',
        historical_qualification='Reference only; independently scored against the same physical environment.')
    folder = ROOT / 'models' / identifier
    write(folder/'policy.json', config)
    write(folder/'architecture.json', dict(ARCHITECTURES['privileged_teacher'], source_files=sources))
    write(folder/'weights.json', {})
    write(folder/'model.json', row)
    policies.append(row)
    return row


def build():
    discovered = files()
    weights = []
    for path in discovered:
        if path.suffix.lower() not in WEIGHTS:
            continue
        row = receipt(path)
        row['checkpoint_schema'] = pickle_schema(path) if path.suffix == '.pt' else None
        family = family_for(path, row['checkpoint_schema'])
        row['architecture'] = family
        row['date_hint'] = next(iter(re.findall(r'20\d{6}', row['path'])), None)
        row['timestamp_basis'] = 'Filesystem modification time; path date is lineage only, not a claimed training time.'
        destination = ROOT / 'models' / 'weights' / (row['sha256'] + path.suffix)
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        if sha(destination) != row['sha256']:
            raise ValueError('Weight copy differs: ' + str(destination))
        row['stored_path'] = destination.relative_to(ROOT).as_posix()
        weights.append(row)

    by_hash = {}
    for weight in weights:
        by_hash.setdefault(weight['sha256'], weight)
    by_path = {w['path']: w for w in weights}
    policies = []

    def register(manifest, *, actor=None, recognizer=None, sources=None, label=None):
        config = read(manifest)
        base = manifest.parent
        source_root = base / 'code' / 'landing_training'
        code = tree_receipts(source_root) if source_root.exists() else []
        extra = tree_receipts(sources) if sources else []
        needed = {'pose.pt': config.get('checkpoint_sha256')}
        for filename, key in [('acquisition.pt', 'acquisition'), ('spatial_acquisition.pt', 'spatial_acquisition')]:
            if (base / filename).exists():
                needed[filename] = sha(base / filename)
            elif config.get('acquisition_checkpoint_sha256' if filename=='acquisition.pt' else 'spatial_checkpoint_sha256'):
                needed[filename] = config['acquisition_checkpoint_sha256' if filename=='acquisition.pt' else 'spatial_checkpoint_sha256']
            elif isinstance(config.get(key), dict) and config[key].get('checkpoint_sha256'):
                needed[filename] = config[key]['checkpoint_sha256']
        weight_refs = {}
        missing = []
        for filename, digest in needed.items():
            ref = by_path.get((base / filename).relative_to(REPO).as_posix()) or by_hash.get(digest)
            if ref and (not digest or ref['sha256'] == digest):
                weight_refs[filename] = dict(sha256=ref['sha256'], path=ref['stored_path'])
            else:
                missing.append(filename)
        if recognizer:
            ref = by_path[recognizer.relative_to(REPO).as_posix()]
            weight_refs['recognizer.pt'] = dict(sha256=ref['sha256'], path=ref['stored_path'])
        runtime = source_root / 'radio_robust_20261015' / 'runtime.py'
        family = 'marker'
        if 'radio_robust_policy' in config.get('schema', ''):
            model_source = source_root / 'radio_robust_20261015/model.py'
            family = ('radio_robust' if 'fusion_gate' in model_source.read_text(encoding='utf-8') else 'radio_conditioned') if model_source.exists() else 'radio_pose'
        if runtime.exists() and 'spatial_acquisition.pt' in runtime.read_text(encoding='utf-8') and 'spatial_acquisition.pt' not in weight_refs:
            missing.append('spatial_acquisition.pt')
        if not runtime.exists():
            missing.append('complete runtime source')
        identity = fingerprint(dict(manifest=sha(manifest), code=[(x['sha256'], x['path'].split('/code/')[-1]) for x in code],
                                    actor=actor, extra=[(x['path'].split('/target_learning/')[-1], x['sha256']) for x in extra],
                                    weights=weight_refs))
        alias = manifest.relative_to(REPO).as_posix()
        duplicate = next((p for p in policies if p['identity_sha256'] == identity), None)
        if duplicate:
            duplicate['aliases'].append(alias)
            return
        name = label or base.name
        identifier = re.sub('[^a-z0-9]+', '-', name.lower()).strip('-') + '-' + identity[:8]
        row = dict(id=identifier, label=name, identity_sha256=identity, manifest=receipt(manifest),
                   aliases=[alias], source_root=source_root.relative_to(REPO).as_posix(), source_files=code,
                   actor=actor or 'radio_robust', actor_source_root=sources.relative_to(REPO).as_posix() if sources else None,
                   actor_source_files=extra, weights=weight_refs, architecture='recognizer' if actor else family,
                   architecture_base=family, available=not missing, missing=missing,
                   role='observable teacher' if actor else 'flight policy', benchmark_status='not_run',
                   captured_utc=utc(), file_modified_utc=receipt(manifest)['file_modified_utc'],
                   timestamp_basis='Preserved manifest file modification time; capture timestamp is inventory time.',
                   historical_qualification='See original bundle. No historical success rate is imported into this suite.')
        folder = ROOT / 'models' / identifier
        write(folder / 'policy.json', config)
        write(folder / 'architecture.json', dict(ARCHITECTURES[family],
              recognition=ARCHITECTURES['recognizer'] if actor else None,
              implementation=actor or config.get('policy_class'), source_files=code + extra))
        write(folder / 'weights.json', weight_refs)
        write(folder / 'model.json', row)
        policies.append(row)

    for manifest in discovered:
        if manifest.name != 'policy.json':
            continue
        config = read(manifest)
        if config.get('policy_class'):
            label = manifest.parent.name
            if label in ('candidate', 'baseline_bundle', 'policy_bundle'):
                label = manifest.relative_to(REPO).parts[1] + ' / ' + label
            if label == 'base_r15':
                label = 'R15 / archived export'
            if label == 'candidate_r15' and 'r15_native_completion_verified' in manifest.parts:
                label = 'R15 / verification snapshot'
            register(manifest, label=label)

    # Observable actors run independently: no DAgger and no expert rescue of a learner.
    exports = REPO / 'artifacts/approved_curriculum_20261020/candidate_exports'
    for version, folder in [('39', 'experimental_v39'), ('46', 'experimental_v46'), ('48', 'experimental_v48_local_recovery')]:
        package = exports / folder / 'package'
        adapter = package / f'sources/target_learning/expert_adapter_v{version}.py'
        if adapter.exists():
            classes = [n.name for n in ast.parse(adapter.read_text()).body if isinstance(n, ast.ClassDef)]
            register(package / 'base_r15/policy.json', actor=f'target_learning.expert_adapter_v{version}.{classes[-1]}',
                     recognizer=package / 'checkpoints/recognizer_best.pt', sources=package / 'sources/target_learning',
                     label=f'Observable teacher v{version}')
    local = REPO / 'artifacts/local_curriculum_20261020'
    base = exports / 'experimental_v48_local_recovery/package/base_r15/policy.json'
    if base.exists():
        register(base, actor='target_learning.expert_adapter_v60.IdentityExpertV60',
                 recognizer=local / 'models/perception_v61/best.pt', sources=local / 'sources/target_learning',
                 label='Observable teacher v60 + v61 recognition')

    register_privileged_teacher(policies)
    for policy in policies:
        write(ROOT/'models'/policy['id']/'model.json', policy)
    inventory = dict(schema='aerodock.benchmark.inventory.v1', captured_utc=utc(),
                     weights=weights, unique_weight_count=len(by_hash), policies=policies,
                     architectures=ARCHITECTURES,
                     unweighted_architectures=[dict(path='landing_training/policy.py', sha256=sha(REPO / 'landing_training/policy.py'),
                         name='Historical action policy: MobileNetV3-Small + 32→64→64 telemetry + GRU(320,128) → 6 actions / 10 auxiliaries',
                         status='Source present; no matching aerodock.landing.checkpoint.v1 weights found locally')],
                     exclusions=sorted(SKIP), archives='Archived checkpoint bytes are deduplicated and inspected without loading a model; full archived flight pipelines are not automatically promoted.')
    archives = []
    for archive in discovered:
        if archive.suffix == '.zip' or archive.name.endswith(('.tar', '.tar.gz', '.tgz')):
            try:
                members = []
                for metadata, blob in archive_members(archive):
                    suffix = Path(metadata['path']).suffix
                    digest = hashlib.sha256(blob).hexdigest()
                    schema = pickle_schema(io.BytesIO(blob)) if suffix == '.pt' else None
                    destination = ROOT/'models/weights'/(digest+suffix)
                    if not destination.exists():
                        destination.write_bytes(blob)
                    if sha(destination) != digest:
                        raise ValueError('Archived weight copy differs')
                    members.append(dict(metadata, sha256=digest, checkpoint_schema=schema,
                        architecture=family_for(metadata['path'],schema), stored_path=destination.relative_to(ROOT).as_posix()))
                if members:
                    archives.append(dict(**receipt(archive), members=members))
            except (zipfile.BadZipFile, tarfile.ReadError):
                continue
    inventory['weight_archives'] = archives
    inventory['unique_weight_count_including_archives'] = len({w['sha256'] for w in weights} | {m['sha256'] for a in archives for m in a['members']})
    write(ROOT / 'models/inventory.json', inventory)
    lines = ['# Local policy and weight inventory', '', f"Captured {inventory['captured_utc']}.", '',
             f"{len(weights)} loose weight files, {len(by_hash)} unique weight hashes, {len(policies)} distinct full-policy configurations.",
             f"Including {sum(len(a['members']) for a in archives)} archived checkpoint entries: {inventory['unique_weight_count_including_archives']} unique weight hashes in total, stored in weights/.",
             '', 'File times below are filesystem modification times, **not verified training timestamps**. Path dates are lineage hints.',
             'Equal weights do not imply equal policies: controller, search code and calibration are part of model identity.', '',
             '| Policy | Role | Locally complete | File modified (UTC) |', '|---|---|---|---|']
    lines += [f"| [{p['label']}]({p['id']}/model.json) | {p['role']} | {'yes' if p['available'] else ', '.join(p['missing'])} | {p['file_modified_utc']} |" for p in policies]
    lines += ['', '## Every loose weight', '', '| Path | Architecture | SHA-256 | File modified (UTC) |', '|---|---|---|---|']
    lines += [f"| `{w['path']}` | {w['architecture']} | `{w['sha256']}` | {w['file_modified_utc']} |" for w in weights]
    lines += ['', '## Archived weights', '']
    for archive in archives:
        lines += [f"### {archive['path']}", '', '| Member | Architecture | SHA-256 | Archive entry time (ZIP: timezone unspecified; TAR: UTC) |', '|---|---|---|---|']
        lines += [f"| `{m['path']}` | {m['architecture']} ({m['checkpoint_schema'] or 'no schema recorded'}) | `{m['sha256']}` | {'-'.join(map(str,m['archive_timestamp'][:3]))} {'-'.join(map(str,m['archive_timestamp'][3:]))} |" for m in archive['members']]
        lines += ['']
    lines += ['', '## Architecture without local trained weights', '', inventory['unweighted_architectures'][0]['name'],
              '', inventory['unweighted_architectures'][0]['status'], '']
    (ROOT / 'models/INVENTORY.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f"Inventoried {len(weights)} loose files / {len(by_hash)} unique loose weights / {inventory['unique_weight_count_including_archives']} unique weights including archives / {len(policies)} policies. No inference or flights.",flush=True)
    return inventory


if __name__ == '__main__':
    build()
