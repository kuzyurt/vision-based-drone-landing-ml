"""Small safety-semantic check; no simulation, render, teacher rollout or training."""
from dataclasses import replace
from pathlib import Path
import json,tempfile,numpy as np
from collection_pipeline.capture_annotations import ObjectSpec,make_capture,CaptureSidecar,load_capture_index,join_delivered_frame
rgb=np.zeros((360,640,3),dtype=np.uint8);seg=np.full((360,640,2),-1,dtype=np.int32)
seg[100:120,200:220]=[1,5];seg[130:150,200:220]=[2,5];seg[120:130,205:215]=[3,5]
target=ObjectSpec('target','target','boat',(1,2,3),{'frame':(1,),'lid':(2,)},(3,),'present')
def capture(spec=target,visible=None,time=1.,image=rgb,segmentation=seg):
    return make_capture(image,segmentation,[spec],capture_s=time,geom_object_type=5,retained_pixels=np.ones((360,640),bool)if visible is None else visible,render_provenance_sha256='a'*64,target_pad_center_px=[210.,125.])
full=capture();assert full['instances'][0]['identity']==1 and full['instances'][0]['marker_visibility_label']==1
hidden=capture(replace(target,marker_paint='absent'));assert hidden['instances'][0]['identity']==1 and hidden['instances'][0]['marker_visibility_label']==0
wrong=capture(replace(target,name='other_boat',design='other'));assert wrong['instances'][0]['identity']==0 and wrong['instances'][0]['marker_visibility_label']==1 and wrong['instances'][0]['pad_pixel']is None
unknown_clone=capture(replace(target,name='reduced_clone',design='unverified'));assert unknown_clone['instances'][0]['identity']==-2 and not unknown_clone['instances'][0]['identity_loss_available']
retained=np.zeros((360,640),bool);retained[120:130,205:215]=True
marker_only=capture(visible=retained);assert marker_only['instances'][0]['identity']==-1 and marker_only['instances'][0]['marker_visibility_label']==1
wrong_marker_only=capture(replace(target,name='wrong_cross_only',design='other'),visible=retained)
assert wrong_marker_only['instances'][0]['identity']==-1,'The identical shared cross cannot establish either boat identity'
try:capture(replace(target,context_parts={'fake_part1':(3,),'fake_part2':(3,)}))
except ValueError:pass
else:raise AssertionError('One paint geom must not fabricate multiple structural parts')
with tempfile.TemporaryDirectory()as td:
    path=Path(td)/'sidecar.jsonl';writer=CaptureSidecar(path);assert writer.append(full)and not writer.append(full);writer.close();index=load_capture_index(path)
    delayed=dict(image_valid=True,image_capture_time_s=1.,image_delivery_time_s=4.)
    assert join_delivered_frame(delayed,rgb,index)['capture_uid']==full['capture_uid']
    assert join_delivered_frame(delayed,rgb,index)['capture_uid']==full['capture_uid']
    modified=rgb.copy();modified[0,0,0]=1
    try:join_delivered_frame(delayed,modified,index)
    except ValueError:pass
    else:raise AssertionError('Modified image must not inherit unmodified labels')
    assert join_delivered_frame(dict(delayed,image_valid=False),modified,index)is None
print(json.dumps(dict(status='passed',scope='Hidden paint preserves design; wrong copied cross rejected; reduced clone unscored; occluded marker-only unknown; capture hash/time join; delayed/repeat not fresh; invalid images skipped',physical_flight=False,teacher_collection=False,training=False)))
