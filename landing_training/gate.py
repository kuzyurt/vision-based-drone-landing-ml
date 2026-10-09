"""Explicit user review bound to artifact, scenario and source fingerprints."""
import hashlib
import json
from pathlib import Path
from .scene import REPO,ROOT

def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def source_fingerprint(runtime_only=False,include_rendering=True):
    # Runtime caches, videos, approval files and timestamps are excluded.
    if runtime_only:
        paths=[ROOT/name for name in ('config.py','environment.py','expert.py','supervision.py','scene.py','collision_pieces.py','visual_lod.py','px4.py','px4_wsl.sh','rendering.py','recording.py','run_episode.py','paths.py','runtime.py','execution.py')]
        if not include_rendering:paths=[p for p in paths if p.name!='rendering.py']
    else:paths=list(ROOT.glob('*.py'))+list(ROOT.glob('*.sh'))+list(ROOT.glob('*.json'))+list(ROOT.glob('*.txt'))
    for folder in ('AERODOCK_MuJoCo/usv','px4-mujoco-drone-simulation/sim'):
        paths+=list((REPO/folder).glob('*.py'))+list((REPO/folder).glob('*.sh'))
    for folder in ('AERODOCK_MuJoCo/models','px4-mujoco-drone-simulation/models'):
        paths+=[p for p in (REPO/folder).rglob('*') if p.is_file() and p.suffix in ('.xml','.json','.obj','.png')]
    paths.append(REPO/'AERODOCK_MuJoCo/config.json')
    paths+=[p for p in (REPO/'AERODOCK_MuJoCo/assets').rglob('*') if p.is_file() and p.suffix in ('.obj','.png','.jpg','.json')]
    binary=ROOT/'.vendor/PX4-Autopilot/build/px4_sitl_landing/bin/px4'
    if binary.exists():paths.append(binary)
    digest=hashlib.sha256()
    from .runtime import WINDOWS,check_px4,wsl
    if WINDOWS:
        digest.update(('WSL-PX4='+wsl('sha256sum',check_px4()).split()[0]).encode())
    from importlib.metadata import version
    for package in ('mujoco','numpy','scipy','Pillow','pymavlink','h5py','fast-simplification','torch','torchvision'):
        digest.update((package+'='+version(package)).encode())
    for path in sorted(set(paths)):
        digest.update(str(path.relative_to(REPO)).encode());digest.update(file_hash(path).encode())
    return digest.hexdigest()

def require_approval(bundle):
    bundle=Path(bundle).resolve();approval=bundle/'approval.json';manifest=bundle/'manifest.json'
    if not approval.exists() or not manifest.exists():raise PermissionError('User verification pending: review all videos, observations and qualification report, then explicitly approve this bundle')
    decision=json.loads(approval.read_text());review=json.loads(manifest.read_text())
    if decision.get('status')!='approved' or not decision.get('reviewer'):raise PermissionError('Review package has not been approved by the user')
    if decision.get('manifest_sha256')!=file_hash(manifest):raise PermissionError('Approval does not match current review manifest')
    if decision.get('reviewed_episodes')!=sorted(e['name'] for e in review['episodes']):raise PermissionError('Approval must cover every review episode')
    if len(review['episodes'])<10:raise PermissionError('At least ten review videos are required')
    if not review.get('qualification_passed'):raise PermissionError('Environment qualification did not pass')
    if review['source_sha256']!=source_fingerprint():raise PermissionError('Source/assets changed after review; regenerate and review the package')
    for relative,expected in review['artifacts'].items():
        path=(bundle/relative).resolve()
        if not path.is_relative_to(bundle) or not path.is_file() or file_hash(path)!=expected:raise PermissionError('Reviewed artifact missing or changed: '+relative)
    return review
