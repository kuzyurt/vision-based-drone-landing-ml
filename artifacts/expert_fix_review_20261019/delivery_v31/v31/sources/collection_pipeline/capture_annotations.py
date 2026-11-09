"""Capture-bound offline labels. No actor, vehicle commands or dataset approval.

Use only AFTER final image effects. For delivery-time occluders, apply the same
explicit pixel-retention mask to the cached capture segmentation before writing
the new image hash. Never join a modified RGB image to unmodified visibility.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping,Tuple
import hashlib,json,math
import numpy as np


@dataclass(frozen=True)
class ObjectSpec:
    name:str
    design:str  # target / other / unverified; static annotation provenance only
    category:str  # boat / board / buoy / debris
    geom_ids:Tuple[int,...]
    context_parts:Mapping[str,Tuple[int,...]]
    marker_geom_ids:Tuple[int,...]
    marker_paint:str  # present / absent / unknown, independent of CAD design

    def validate(self):
        if not self.name or self.category not in ['boat','board','buoy','debris']:raise ValueError('Undeclared object category')
        if self.design not in ['target','other','unverified']:raise ValueError('Undeclared design semantics')
        if self.marker_paint not in ['present','absent','unknown']:raise ValueError('Undeclared marker paint availability')
        if not self.geom_ids or len(set(self.geom_ids))!=len(self.geom_ids):raise ValueError('Invalid object geometry mapping')
        ids=set(self.geom_ids)
        if not set(self.marker_geom_ids)<=ids or any(not set(v)<=ids for v in self.context_parts.values()):raise ValueError('Part outside its annotation instance')
        used=set()
        for part_ids in self.context_parts.values():
            if used.intersection(part_ids)or set(part_ids).intersection(self.marker_geom_ids):raise ValueError('Paint or duplicated geometry cannot supply multiple identity parts')
            used.update(part_ids)


def rgb_hash(rgb):
    a=np.asarray(rgb)
    if a.shape!=(360,640,3)or a.dtype!=np.uint8:raise ValueError('Exact deployed RGB contract required')
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def capture_key(capture_s,digest):
    if not math.isfinite(capture_s)or capture_s<0 or len(digest)!=64:raise ValueError('Invalid capture identity')
    return f'{round(capture_s*1e6):016d}:{digest}'


def instances_from_segmentation(seg,specs,*,geom_object_type,retained_pixels):
    seg=np.asarray(seg);retained=np.asarray(retained_pixels)
    if seg.shape!=(360,640,2)or retained.shape!=(360,640)or retained.dtype!=bool:raise ValueError('Exact segmentation and explicit visibility mask required')
    names=set();all_ids=set();instances=[]
    for spec in specs:
        spec.validate()
        if spec.name in names or all_ids.intersection(spec.geom_ids):raise ValueError('Annotation instances overlap in geometry identity')
        names.add(spec.name);all_ids.update(spec.geom_ids)
        geometry=(seg[...,1]==geom_object_type)&retained
        visible=np.isin(seg[...,0],spec.geom_ids)&geometry;yy,xx=np.nonzero(visible)
        if len(xx)<3:continue
        bbox=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
        width,height=bbox[2]-bbox[0],bbox[3]-bbox[1]
        clipped=bbox[0]<2 or bbox[1]<2 or bbox[2]>638 or bbox[3]>358
        parts={name:int((np.isin(seg[...,0],ids)&geometry).sum())for name,ids in spec.context_parts.items()}
        structural_pixels=int((visible&~np.isin(seg[...,0],spec.marker_geom_ids)).sum())
        resolved=len(xx)>=128 and max(width,height)>=24
        if spec.design in ['target','unverified']:
            context=resolved and sum(n>=16 for n in parts.values())>=2 and sum(parts.values())>=128
        else:context=resolved and not clipped and structural_pixels>=128
        # Hidden paint never turns the original CAD into a different design.
        identity=-2 if spec.design=='unverified'else(1 if spec.design=='target'else 0)if context else -1
        painted=int((np.isin(seg[...,0],spec.marker_geom_ids)&geometry).sum())
        marker_known=spec.marker_paint!='unknown'
        marker_visible=marker_known and spec.marker_paint=='present'and painted>=4
        instances.append(dict(annotation_instance=spec.name,object_category=spec.category,boat=spec.category=='boat',bbox=bbox,pixels=len(xx),identity=identity,
            identity_support=float(context)if spec.design!='unverified'else None,identity_loss_available=identity!=-2,
            marker_visibility_label=int(marker_visible)if marker_known else None,marker_label_available=marker_known,
            marker_geometry_pixels=painted,marker_visible_pixels=painted if spec.marker_paint=='present'else 0,visible_context_parts=parts,structural_pixels=structural_pixels,
            cold_marker_only_is_target_identity=False,clipped=clipped))
    return instances


def make_capture(rgb,seg,specs,*,capture_s,geom_object_type,retained_pixels,render_provenance_sha256,target_pad_center_px=None):
    specs=tuple(specs)
    if len(render_provenance_sha256)!=64 or any(c not in '0123456789abcdef'for c in render_provenance_sha256):raise ValueError('Missing frozen render provenance hash')
    digest=rgb_hash(rgb);key=capture_key(capture_s,digest)
    instances=instances_from_segmentation(seg,specs,geom_object_type=geom_object_type,retained_pixels=retained_pixels)
    for inst in instances:
        is_target=next(s.design=='target'for s in specs if s.name==inst['annotation_instance'])
        point=target_pad_center_px
        available=bool(is_target and inst['marker_visibility_label']==1 and point is not None and len(point)==2 and all(math.isfinite(float(v))for v in point)and 0<=point[0]<640 and 0<=point[1]<360)
        inst['pad_pixel']=list(map(float,point))if available else None
        inst['pad_label_available']=available
    return dict(schema='mujoco.capture_annotations.v1',capture_uid=key,capture_s=float(capture_s),rgb_sha256=digest,instances=instances,
        render_provenance_sha256=render_provenance_sha256,actor_input=False,annotations_grant_training_eligibility=False,
        identity_observability_rule='Conservative pixel/context heuristic; not a universal human recognition distance')


class CaptureSidecar:
    def __init__(self,path):
        self.path=Path(path);self.stream=self.path.open('x',encoding='utf-8');self.seen={};self.last_time=-math.inf;self.count=0
    def append(self,label):
        if label['actor_input']or label['annotations_grant_training_eligibility']:raise ValueError('Observer/control separation violated')
        if label['capture_uid']!=capture_key(label['capture_s'],label['rgb_sha256']):raise ValueError('Capture identity corrupted')
        encoded=json.dumps(label,separators=(',',':'),sort_keys=True,allow_nan=False)
        uid=label['capture_uid']
        if uid in self.seen:
            if self.seen[uid]!=hashlib.sha256(encoded.encode()).hexdigest():raise ValueError('Same capture has conflicting labels')
            return False
        if label['capture_s']<self.last_time:raise ValueError('Out-of-order annotation capture')
        self.last_time=label['capture_s'];self.seen[uid]=hashlib.sha256(encoded.encode()).hexdigest();self.stream.write(encoded+'\n');self.count+=1
        if self.count%100==0:self.stream.flush()
        return True
    def close(self):self.stream.close()


def load_capture_index(path):
    result={}
    for line in Path(path).open(encoding='utf-8'):
        label=json.loads(line);uid=label['capture_uid']
        if uid in result:raise ValueError('Duplicate persisted capture identity')
        result[uid]=label
    return result


def join_delivered_frame(observation,rgb,index):
    if not observation['image_valid']:return None
    key=capture_key(float(observation['image_capture_time_s']),rgb_hash(rgb))
    if key not in index:raise ValueError('No exact capture-time/image-hash annotation; never nearest-frame substitute')
    label=index[key]
    if abs(label['capture_s']-float(observation['image_capture_time_s']))>1e-6:raise ValueError('Capture timestamp mismatch')
    return label
