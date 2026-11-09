"""Explicit user review bound to artifact, scenario and source fingerprints."""
import hashlib
import json
import os
from pathlib import Path
from .scene import REPO,ROOT

# Exact, audited crash-only correction. Legacy fingerprints are recomputed
# with this one file's old hash; every other runtime input still has to match.
SCENERY_RENDERER_PATH='AERODOCK_MuJoCo/usv/world_render.py'
SCENERY_RENDERER_BEFORE='bb40bb809fa5c15bc8003bfe62b80acf7004712bb5037b339b8569ddbc47e689'
SCENERY_RENDERER_FIXED='d4fb2c6343b20dfea73fd0fbe66f6b162d5a41dc35c67c8f89311ebb079b696e'

def safe_review_outcome(summary):
    if summary.get('failure'):return False
    if summary.get('outcome')=='landed':return True
    scenario=summary.get('scenario',{})
    fault=any(scenario.get(name,0)>0 for name in
              ('camera_blind_seconds','beacon_dropout_duration_s','dock_unavailable_seconds'))
    return fault and summary.get('outcome') in ('abort','timeout','contact_only')

def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def source_fingerprint(runtime_only=False,include_rendering=True):
    return _source_fingerprint(runtime_only,include_rendering)

def _source_fingerprint(runtime_only,include_rendering,*,legacy_scenery=False):
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
        relative=str(path.relative_to(REPO));actual=file_hash(path)
        if legacy_scenery and relative==SCENERY_RENDERER_PATH:
            if actual!=SCENERY_RENDERER_FIXED:
                raise PermissionError('Scenery compatibility requires the exact audited renderer correction')
            actual=SCENERY_RENDERER_BEFORE
        digest.update(relative.encode());digest.update(actual.encode())
    return digest.hexdigest()

def compatible_runtime_fingerprints(runtime=None):
    """Current runtime plus the exact predecessor of the short-rock-tile fix.

    This does not approve a bundle or enable reuse: callers must still verify
    user approval, artifacts and the plan, and explicitly request runtime reuse.
    The old renderer failed before producing an image in the corrected branch;
    all successful chunks retain identical geometry and random draws.
    """
    accepted={runtime or source_fingerprint(runtime_only=True)}
    renderer=REPO/SCENERY_RENDERER_PATH
    if renderer.is_file() and file_hash(renderer)==SCENERY_RENDERER_FIXED:
        accepted.add(_source_fingerprint(True,True,legacy_scenery=True))
    return frozenset(accepted)

def require_approval(bundle):
    bundle=Path(bundle).resolve();approval=bundle/'approval.json';manifest=bundle/'manifest.json'
    if not approval.exists() or not manifest.exists():raise PermissionError('User verification pending: review all videos, observations and qualification report, then explicitly approve this bundle')
    decision=json.loads(approval.read_text());review=json.loads(manifest.read_text())
    if decision.get('status')!='approved' or not decision.get('reviewer'):raise PermissionError('Review package has not been approved by the user')
    if decision.get('manifest_sha256')!=file_hash(manifest):raise PermissionError('Approval does not match current review manifest')
    if decision.get('reviewed_episodes')!=sorted(e['name'] for e in review['episodes']):raise PermissionError('Approval must cover every review episode')
    if len(review['episodes'])<10:raise PermissionError('At least ten review videos are required')
    if not review.get('qualification_passed'):raise PermissionError('Environment qualification did not pass')
    source_matches=review['source_sha256']==source_fingerprint()
    if not source_matches and os.environ.get('LANDING_REUSE_APPROVED_RUNTIME')!='1':
        raise PermissionError('Source/assets changed after review; regenerate and review the package')
    for relative,expected in review['artifacts'].items():
        path=(bundle/relative).resolve()
        if not path.is_relative_to(bundle) or not path.is_file() or file_hash(path)!=expected:raise PermissionError('Reviewed artifact missing or changed: '+relative)
    if not source_matches:
        # Explicit reuse of an already user-approved recording; never rewrite
        # its approval/manifest. Reviewed successful frames stay identical;
        # only the exact short-rock-tile crash correction can differ. Physics,
        # assets, dependencies, PX4, evidence and the plan remain fingerprinted.
        runtime=source_fingerprint(runtime_only=True)
        if 'qualification.json' not in review['artifacts']:
            raise PermissionError('Approved review has no fingerprinted qualification evidence')
        qualification=json.loads((bundle/'qualification.json').read_text())
        if not qualification.get('passed'):
            raise PermissionError('Approved qualification evidence did not pass')
        qualified_runtime=qualification.get('runtime_source_sha256')
        if not qualified_runtime:
            raise PermissionError('This older qualification report has no runtime fingerprint; its approval cannot establish compatibility with the current simulation')
        if qualified_runtime not in compatible_runtime_fingerprints(runtime):
            raise PermissionError('Approved simulation runtime changed; existing videos cannot be reused '
                                  f'(reviewed {qualified_runtime[:12]}, current {runtime[:12]})')
        for episode in review['episodes']:
            relative=episode['name']+'/summary.json'
            if relative not in review['artifacts']:
                raise PermissionError('Approved episode has no fingerprinted runtime evidence')
            summary=json.loads((bundle/relative).read_text())
            if summary.get('runtime_source_sha256')!=qualified_runtime or not safe_review_outcome(summary):
                raise PermissionError('Approved episode runtime/outcome is incompatible: '+episode['name'])
        from .collect import planned_scenarios
        if review.get('collection_plan')!=planned_scenarios():
            raise PermissionError('Collection scenarios changed since the approved review')
    return review
