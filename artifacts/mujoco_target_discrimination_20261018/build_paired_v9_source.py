"""Create standalone paired renderer; retain every earlier attempt."""
from pathlib import Path
root=Path(__file__).resolve().parent;s=(root/'generate_context_v8.py').read_text()
s=s.replace("out=ROOT/'perception_context_dataset_v8'","out=ROOT/'perception_paired_dataset_v9'")
s=s.replace("rgb_store=h.create_dataset('rgb',(job['frames'],", "rgb_store=h.create_dataset('rgb',(job['frames']*2,")
s=s.replace("rows=h.create_dataset('labels',(job['frames'],)", "rows=h.create_dataset('labels',(job['frames']*2,)")
s=s.replace("            glare=None", """            paint=model.geom('LandingTarget_plain').id;paint_group=int(model.geom_group[paint])
            model.geom_group[paint]=3;blank=r.onboard_image();model.geom_group[paint]=paint_group
            glare=None""")
old="""            if i%3!=1:rgb,glare=sun_glints(rgb,water_mask_for_scene(r,env)(seg),env,sun_direction=sun,roughness=rng.uniform(.07,.20),strength=rng.uniform(.2,1.3))"""
new="""            if i%3!=1:
                roughness=rng.uniform(.07,.20);strength=rng.uniform(.2,1.3);water_pixels=water_mask_for_scene(r,env)(seg)
                rgb,glare=sun_glints(rgb,water_pixels,env,sun_direction=sun,roughness=roughness,strength=strength)
                blank,_=sun_glints(blank,water_pixels,env,sun_direction=sun,roughness=roughness,strength=strength)"""
assert old in s;s=s.replace(old,new)
start=s.index("            rgb_store[i]=rgb;rows[i]=json.dumps")
end=s.index("    r.close();result=",start)
s=s[:start]+"""            import copy
            changed=np.max(np.abs(rgb.astype(int)-blank.astype(int)),axis=2)
            contrast_pixels=int((changed>20).sum())
            for variant,image in enumerate([rgb,blank]):
                labelled=copy.deepcopy(instances)
                for inst in labelled:
                    if inst['annotation_instance']=='target':
                        context_parts=inst['visible_context_parts']
                        context_visible=(sum(v>=16 for v in context_parts.values())>=2 and sum(context_parts.values())>=128)
                        supported=context_visible and contrast_pixels>=32
                        inst['identity']=(1 if variant==0 else 0)if supported else -1
                        inst['identity_support']=float(supported)
                        inst['marker_contrast_pixels_annotation_only']=contrast_pixels
                        if variant:
                            inst['annotation_instance']='counterfactual_unmarked_full_cad'
                            inst['pad_pixel']=None;inst['pad_label_available']=False
                index=i*2+variant;rgb_store[index]=image
                rows[index]=json.dumps(dict(index=index,source_view_index=i,variant='original'if variant==0 else'marker_paint_hidden',
                    role=job['role'],world_seed=job['seed'],instances=labelled,target_hidden=bool(hidden),glare=glare,
                    marker_contrast_pixels_annotation_only=contrast_pixels,
                    camera_position_annotation_only=env.data.cam_xpos[cid].tolist(),camera_rotation_annotation_only=env.data.cam_xmat[cid].tolist(),
                    own_body_qpos_annotation_only=env.data.qpos[env.drone.free_qadr:env.drone.free_qadr+7].tolist(),gimbal_annotation_only=env.data.qpos[env.drone.camera_qpos].tolist()))
"""+s[end:]
s=s.replace("world_seed=job['seed'],frames=job['frames'],wall_s=", "world_seed=job['seed'],frames=job['frames']*2,source_views=job['frames'],wall_s=")
s=s.replace("identity_counts=counts)", "identity_counts_first_variant_before_contrast_rule=counts,paired_exact_cad=True,only_counterfactual_mutation='marker paint visibility')")
s=s.replace("original_heldout_unused=True,no_tidewater=True", "original_heldout_unused=True,no_tidewater=True,paired_exact_cad=True,observable_identity_rule='>=32 changed RGB pixels above20levels and two visible structural groups; otherwise both identities unknown'")
dest=root/'generate_paired_v9.py';assert not dest.exists();dest.write_text(s);print(dest)
