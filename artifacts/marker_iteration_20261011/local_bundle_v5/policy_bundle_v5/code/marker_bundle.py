"""Load an immutable learned marker-policy bundle without altering legacy checkpoints."""
import json
from pathlib import Path
from .gate import file_hash
from .marker_policy import MarkerPosePolicy

def read_bundle(path,verify_source=True):
    path=Path(path).resolve();configuration=json.loads(path.read_text())
    if configuration.get('schema')!='aerodock.landing.marker_policy.v1':raise ValueError('Unknown marker policy bundle schema')
    checkpoint=(path.parent/configuration['checkpoint']).resolve()
    if not checkpoint.is_relative_to(path.parent):raise ValueError('Checkpoint must stay inside the policy bundle')
    if file_hash(checkpoint)!=configuration['checkpoint_sha256']:raise ValueError('Marker checkpoint checksum mismatch')
    if verify_source:
        root=Path(__file__).resolve().parent
        for name,digest in configuration['source_files_sha256'].items():
            source=(root/name).resolve()
            if not source.is_relative_to(root) or source.suffix!='.py':raise ValueError('Invalid bundled source reference')
            if file_hash(source)!=digest:raise ValueError('Marker policy source changed: '+name)
    return configuration,checkpoint

def load_bundle(path,device='cuda'):
    configuration,checkpoint=read_bundle(path)
    policy=MarkerPosePolicy(checkpoint,configuration['calibration'],configuration['slew_limits'],device)
    if policy.metadata['dataset_sha256']!=configuration['dataset_sha256']:raise ValueError('Bundle and checkpoint refer to different datasets')
    policy.metadata.update(policy_kind='learned_pose_and_metric_rgb',bundle_sha256=file_hash(path),pose_checkpoint_sha256=file_hash(checkpoint))
    return policy
