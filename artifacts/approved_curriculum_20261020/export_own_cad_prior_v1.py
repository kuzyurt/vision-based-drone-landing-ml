"""Declared fixed OWN aircraft visual CAD only, never world/target geometry."""
from pathlib import Path
import hashlib,json,sys
import mujoco,numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'own_cad_prior_v1';sys.path.insert(0,'/home/hxhshsh7gyg/vision-based-drone-landing-ml')
from landing_training import paths,environment
def main():
    OUT.mkdir(exist_ok=False);proof=json.loads((ROOT/'world_contract_v1/proof.json').read_text());cache=proof['models']['hard'];assert hashlib.sha256(Path(cache['mjb']).read_bytes()).hexdigest()==cache['sha256'];m=mujoco.MjModel.from_binary_path(cache['mjb']);d=mujoco.MjData(m);mujoco.mj_forward(m,d);root=m.body('drone_base_link').id;origin=d.xpos[root];rotation=d.xmat[root].reshape(3,3);v0=[];e1=[];e2=[];lo=[];hi=[];offsets=[0];records=[]
    for g in range(m.ngeom):
        if m.geom_group[g]>2 or int(m.geom_type[g])!=int(mujoco.mjtGeom.mjGEOM_MESH)or m.geom_rgba[g,3]<.99:continue
        body=int(m.geom_bodyid[g]);fixed=True;inside=False
        while body:
            if body==root:inside=True;break
            if m.body_jntnum[body]>0:fixed=False
            body=int(m.body_parentid[body])
        if not inside or not fixed:continue
        mesh=int(m.geom_dataid[g]);verts=m.mesh_vert[m.mesh_vertadr[mesh]:m.mesh_vertadr[mesh]+m.mesh_vertnum[mesh]].astype(float);faces=m.mesh_face[m.mesh_faceadr[mesh]:m.mesh_faceadr[mesh]+m.mesh_facenum[mesh]]
        vertices=(verts@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g]-origin)@rotation;tri=vertices[faces];v0.append(tri[:,0]);e1.append(tri[:,1]-tri[:,0]);e2.append(tri[:,2]-tri[:,0]);lo.append(vertices.min(0));hi.append(vertices.max(0));offsets.append(offsets[-1]+len(tri));records.append(dict(geom_name=m.geom(g).name,body_name=m.body(int(m.geom_bodyid[g])).name,triangles=len(tri),bounds=[vertices.min(0).tolist(),vertices.max(0).tolist()]))
    assert records and offsets[-1]>100;np.savez_compressed(OUT/'fixed_own_aircraft.npz',v0=np.concatenate(v0).astype('float64'),e1=np.concatenate(e1).astype('float64'),e2=np.concatenate(e2).astype('float64'),lo=np.array(lo),hi=np.array(hi),offsets=np.array(offsets))
    receipt=dict(schema='declared.static.own-aircraft-cad.v1',source_model_sha256=cache['sha256'],source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),mesh_sha256=hashlib.sha256((OUT/'fixed_own_aircraft.npz').read_bytes()).hexdigest(),coordinate_frame='Own drone_base_link CAD axes, identical to camera_body_transform calibration output',fixed_geometry_only=True,excludes_rotors_and_gimbal_joints=True,world_target_or_distractor_geometry=False,records=records,triangles=offsets[-1]);(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(dict(status='exported_static_own_cad',geoms=len(records),triangles=offsets[-1],bytes=(OUT/'fixed_own_aircraft.npz').stat().st_size)),flush=True)
if __name__=='__main__':main()
