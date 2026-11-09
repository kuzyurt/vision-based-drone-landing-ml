"""Create an auditable standalone renderer revision without editing V5 sources."""
from pathlib import Path
root=Path(__file__).resolve().parent
source=(root/'generate_hard_v5.py').read_text()
source=source.replace("out=ROOT/'perception_hard_dataset_v5'","out=ROOT/'perception_context_dataset_v8'")
source=source.replace("marker_ids={name:","context_ids={name:{part:[g for g in ids if model.geom(g).name.removeprefix('hard_clone_') in names] for part,names in {'frame':['FrameLoadPaths_plain','LidRails_textured','BayCoaming_plain'], 'aft':['obstacle_AftSlidingLid_textured'], 'fore':['obstacle_ForeSlidingLid_textured']}.items()} for name,ids in groups.items()}\n    marker_ids={name:")
old="""                context=len(xx)>=128 and max(w,hh)>=24 and not clipped
                marker="""
new="""                context=len(xx)>=128 and max(w,hh)>=24
                parts={part:int((np.isin(seg[...,0],gids)&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))).sum()) for part,gids in context_ids[name].items()}
                if name in ['target','decoy_blank_clone']:
                    # Visible hull/frame plus a lid or both lids distinguish
                    # structural context from a shared marker-only crop. A
                    # one-pixel frame-edge clipping is NOT identity blindness.
                    context=context and sum(n>=16 for n in parts.values())>=2 and sum(parts.values())>=128
                else:
                    # Do not claim that a cropped piece of a printed board or
                    # another hull establishes that whole object's identity.
                    context=context and not clipped
                marker="""
assert old in source;source=source.replace(old,new)
source=source.replace("identity_support=float(support),marker_visible_pixels=marker_pixels,pad_pixel=pad,", "identity_support=float(support),marker_visible_pixels=marker_pixels,pad_pixel=pad,visible_context_parts=parts,pad_label_available=name not in ['decoy_false_cross_boat','decoy_false_cross_board'],")
source=source.replace("            rgb_store[i]=rgb;rows[i]=json.dumps", """            # Re-render only to obtain visibility annotations that were not
            # preserved in V5. Verify exact RGB correspondence before reusing
            # any frozen V5 feature cache for these new labels.
            with h5py.File(ROOT/'perception_hard_dataset_v5'/job['name']/'samples.h5','r')as prior:
                assert np.array_equal(rgb,prior['rgb'][i]), 'RGB changed; feature cache cannot be reused'
            rgb_store[i]=rgb;rows[i]=json.dumps""")
source=source.replace("camera_position_annotation_only=env.data.cam_xpos[cid].tolist()", "camera_position_annotation_only=env.data.cam_xpos[cid].tolist(),camera_rotation_annotation_only=env.data.cam_xmat[cid].tolist(),gimbal_annotation_only=env.data.qpos[env.drone.camera_qpos].tolist()")
source=source.replace("    print(json.dumps({k:v for k,v in value.items()if k!='entries'}),flush=True)","    print(json.dumps({k:v for k,v in value.items()if k!='entries'},default=lambda v:v.item()),flush=True)")
dest=root/'generate_context_v8.py';assert not dest.exists();dest.write_text(source)
print(dest)
