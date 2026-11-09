"""Observer-only bridge between an existing segmentation pass and final RGB.

This object belongs to the recording producer. Never pass it to a controller.
It adds annotations, not images or commands, and cannot approve a dataset.
"""
import hashlib,json
from pathlib import Path
import numpy as np
from .capture_annotations import ObjectSpec,CaptureSidecar,make_capture


def declared_specs(model,groups):
    parts={'frame':['FrameLoadPaths_plain','LidRails_textured','BayCoaming_plain'],
           'aft':['AftSlidingLid_textured','obstacle_AftSlidingLid_textured'],
           'fore':['ForeSlidingLid_textured','obstacle_ForeSlidingLid_textured'],
           'mast':['CameraMast_textured','DockCameraHousing_textured']}
    specs=[]
    for name,ids in groups.items():
        context={k:tuple(g for g in ids if model.geom(g).name.removeprefix('hard_clone_')in names)
                 for k,names in parts.items()}if name in ['target','decoy_blank_clone']else{}
        markers=tuple(g for g in ids if model.geom(g).name=='LandingTarget_plain'or 'copied_marker'in model.geom(g).name)
        design='target'if name=='target'else'unverified'if name=='decoy_blank_clone'else'other'
        category='board'if 'board'in name else'buoy'if 'buoy'in name else'debris'if 'debris'in name else'boat'
        spec=ObjectSpec(name,design,category,tuple(ids),context,markers,'present'if markers else'absent')
        spec.validate();specs.append(spec)
    return tuple(specs)


class ObserverCaptureBridge:
    def __init__(self,directory,specs,*,geom_object_type,provenance):
        self.directory=Path(directory);self.specs=tuple(specs);self.geom_object_type=geom_object_type
        self.provenance=provenance
        self.digest=hashlib.sha256(json.dumps(provenance,sort_keys=True,allow_nan=False).encode()).hexdigest()
        self.writer=CaptureSidecar(self.directory/'capture_annotations.jsonl');self.pending=None
        self.first_s=None;self.last_s=None;self.closed=False

    def cache_geometry(self,segmentation,*,capture_s,target_pad_center_px,retained_pixels):
        if self.pending is not None:raise RuntimeError('Previous geometry never joined final RGB')
        self.pending=dict(seg=np.array(segmentation,copy=True),capture_s=float(capture_s),
            target_pad_center_px=list(map(float,target_pad_center_px)),retained_pixels=np.array(retained_pixels,dtype=bool,copy=True))

    def bind_final_rgb(self,rgb,*,current_capture_s):
        if self.pending is None:raise RuntimeError('Final image has no same-capture geometry')
        pending=self.pending
        if abs(float(current_capture_s)-pending['capture_s'])>1e-8:raise RuntimeError('Physics advanced between geometry and final RGB')
        label=make_capture(rgb,pending['seg'],self.specs,capture_s=pending['capture_s'],
            geom_object_type=self.geom_object_type,retained_pixels=pending['retained_pixels'],
            render_provenance_sha256=self.digest,target_pad_center_px=pending['target_pad_center_px'])
        self.writer.append(label);self.pending=None
        if self.first_s is None:self.first_s=label['capture_s']
        self.last_s=label['capture_s']
        # No label result is returned to the caller's control path.

    def close(self):
        if self.closed:return
        pending=self.pending is not None;self.writer.close();self.closed=True
        receipt=dict(schema='mujoco.observer_bridge.v1',captures=self.writer.count,
            first_capture_s=self.first_s,last_capture_s=self.last_s,unbound_capture=pending,
            provenance=self.provenance,provenance_sha256=self.digest,
            actor_input=False,grants_training_eligibility=False,
            contract='exact final image after effects, before queue; cached same-capture segmentation')
        (self.directory/'capture_annotation_receipt.json').write_text(json.dumps(receipt,indent=2))
        if pending:raise RuntimeError('Unbound final capture; recording requires diagnosis')
