"""Fix measured missing palette coverage, add hidden-marker views; new files."""
from pathlib import Path
p=Path(__file__).parent
s=(p/'render_static_repair_v37.py').read_text().replace("ROOT/'static_repair_v37'","ROOT/'static_repair_v38'")
s=s.replace("rgb=renderer.onboard_image();renderer.onboard.enable_segmentation_rendering()","hide_marker=bool(i%4==2)\n                for gid in groups['target']:\n                    if env.model.geom(gid).name=='LandingTarget_plain':env.model.geom_group[gid]=5 if hide_marker else 0\n                rgb=renderer.onboard_image();renderer.onboard.enable_segmentation_rendering()")
s=s.replace("image_effects=effect)","image_effects=effect,marker_hidden_render_only=hide_marker,palette=job['palette'])")
(p/'render_static_repair_v38.py').write_text(s)
s=(p/'queue_static_repair_v37.py').read_text().replace('static_repair_v37','static_repair_v38')
a="    for i,w in enumerate(proof['worlds']):jobs.append(dict(**w,name=f\"{w['role']}_{w['kind']}\",frames=96 if w['role']=='training'else 48,seed=w['world_seed']+50000,rotation=[0.,37.,89.,153.,225.][i//2]))\n    assert len(jobs)==10 and sum(j['frames']for j in jobs)==720"
b="""    for i,w in enumerate(proof['worlds']):
        for palette in (range(5)if w['role']=='training'else[(i//2)%5,(i//2+2)%5]):
            jobs.append(dict(**w,name=f\"{w['role']}_{w['kind']}_palette{palette}\",frames=96 if w['role']=='training'else 80,seed=w['world_seed']+100000+palette,palette=palette,rotation=[0.,37.,89.,153.,225.][i//2]))
    assert len(jobs)==35 and sum(j['frames']for j in jobs)==3200
    assert {j['seed']%5 for j in jobs if j['role']=='training'}==set(range(5))"""
assert a in s;s=s.replace(a,b);(p/'queue_static_repair_v38.py').write_text(s)
(p/'launch_static_repair_v38.py').write_text((p/'launch_static_repair_v37.py').read_text().replace('static_repair_v37','static_repair_v38'))
s=(p/'train_static_verifier_v37.py').read_text().replace('static_repair_v37','static_repair_v38').replace('static_v37','static_v38').replace('perception_training_v37','perception_training_v38').replace("manifest['frames']==720","manifest['frames']==3200")
# Actual repair of the selection defect, not relaxation: ALL non-target types
# must remain at or below the parent's observed validation count.
s=s.replace("and metrics['selected_operating_point']['background_acceptances']<=baseline['selected_operating_point']['background_acceptances']:","and metrics['selected_operating_point']['background_acceptances']<=baseline['selected_operating_point']['background_acceptances']and metrics['selected_operating_point']['ambiguous_acceptances']<=baseline['selected_operating_point']['ambiguous_acceptances']:")
(p/'train_static_verifier_v38.py').write_text(s)
for name in ['queue_static_cache','launch_static_cache','launch_static_training']:
    s=(p/(name+'_v37.py')).read_text().replace('static_repair_v37','static_repair_v38').replace('static_v37','static_v38').replace('static_cache_v37','static_cache_v38').replace('static_training_v37','static_training_v38').replace('train_static_verifier_v37','train_static_verifier_v38').replace('queue_static_cache_v37','queue_static_cache_v38')
    (p/(name+'_v38.py')).write_text(s)
for f in p.glob('*v38.py'):compile(f.read_text(),str(f),'exec')
