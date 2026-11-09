"""Read-only cached model dynamics comparison; no simulation, actor or training."""
from pathlib import Path
import hashlib,json
import mujoco,numpy as np
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def records(model):
    roots={'boat','drone_base_link'};bodies={}
    for i in range(model.nbody):
        p=i
        while p:
            if model.body(p).name in roots:break
            p=int(model.body_parentid[p])
        if p:bodies[i]=model.body(i).name
    result={}
    for i,name in bodies.items():
        result['body:'+name]={k:np.asarray(getattr(model,k)[i]).tolist()for k in['body_mass','body_inertia','body_ipos','body_iquat','body_pos','body_quat']}
    for i in range(model.njnt):
        if int(model.jnt_bodyid[i])not in bodies:continue
        j=model.joint(i);d=int(model.jnt_dofadr[i]);next_d=int(model.jnt_dofadr[i+1])if i+1<model.njnt else model.nv
        result['joint:'+j.name]={k:np.asarray(getattr(model,k)[i]).tolist()for k in['jnt_type','jnt_axis','jnt_pos','jnt_range','jnt_limited']}
        result['joint:'+j.name]['damping']=np.asarray(model.dof_damping[d:next_d]).tolist()
    for i in range(model.ngeom):
        if int(model.geom_bodyid[i])not in bodies:continue
        local_index=i-int(model.body_geomadr[int(model.geom_bodyid[i])])
        key='geom:'+bodies[int(model.geom_bodyid[i])]+':'+(model.geom(i).name or str(local_index))
        assert key not in result,'Geometry entries must never collapse'
        result[key]={k:np.asarray(getattr(model,k)[i]).tolist()for k in[
            'geom_type','geom_size','geom_pos','geom_quat','geom_friction','geom_contype','geom_conaffinity','geom_solref','geom_solimp','geom_margin','geom_gap']}
        if int(model.geom_type[i])==int(mujoco.mjtGeom.mjGEOM_MESH):
            mesh=int(model.geom_dataid[i]);v=int(model.mesh_vertadr[mesh]);n=int(model.mesh_vertnum[mesh])
            f=int(model.mesh_faceadr[mesh]);nf=int(model.mesh_facenum[mesh])
            result[key]['mesh_collision_content_sha256']=hashlib.sha256(model.mesh_vert[v:v+n].tobytes()+model.mesh_face[f:f+nf].tobytes()).hexdigest()
    return result

index=json.loads((ROOT/'scene_cache_v2/index.json').read_text())['entries']['850000']
base_path=Path(index['mjb']);hard_path=ROOT/'hard_scene_probe_v3/hard_scene.mjb'
assert sha(base_path)==index['sha256']
baseline=mujoco.MjModel.from_binary_path(str(base_path));hard=mujoco.MjModel.from_binary_path(str(hard_path))
left,right=records(baseline),records(hard)
assert {'body:boat','body:drone_base_link'}<=left.keys()and {'body:boat','body:drone_base_link'}<=right.keys(),'Both actual target and aircraft roots must be compared'
differences=[]
for key in sorted(set(left)|set(right)):
    if left.get(key)!=right.get(key):differences.append(dict(component=key,base=left.get(key),hard=right.get(key)))
options={k:[np.asarray(getattr(baseline.opt,k)).tolist(),np.asarray(getattr(hard.opt,k)).tolist()]for k in[
    'timestep','gravity','integrator','solver','iterations','tolerance','cone','impratio']}
option_mismatches={k:v for k,v in options.items()if v[0]!=v[1]}
report=dict(status='cached_core_physics_identical'if not differences and not option_mismatches else'needs_actual_difference_review',
    baseline_model_sha256=sha(base_path),hard_model_sha256=sha(hard_path),components_compared=len(left),
    differences=differences,option_mismatches=option_mismatches,
    scope='Cached basic versus hard target/drone physical parameters, not full environment qualification',
    annotation_only=True,training_eligibility_granted=False)
(ROOT/'environment_cached_dynamics_comparison_v1.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
