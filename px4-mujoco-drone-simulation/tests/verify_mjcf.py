"""Check MuJoCo rendered coordinates against the independent source inventory."""
import hashlib
import json
from pathlib import Path
import numpy as np
import mujoco
ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT/'models/metadata/export.json').read_text(encoding='utf-8'))
parts={p['part']:p for p in source['parts']}
m=mujoco.MjModel.from_xml_path(str(ROOT/'models/drone.xml'))
d=mujoco.MjData(m)
mujoco.mj_forward(m,d)
assert m.njnt==6
assert hashlib.sha256(Path(source['source']).read_bytes()).hexdigest()==source['sha256']
max_rest=0
samples={}
for i in range(m.ngeom):
    mesh=int(m.geom_dataid[i]); start=int(m.mesh_vertadr[mesh]); count=int(m.mesh_vertnum[mesh])
    verts=m.mesh_vert[start:start+count].astype(np.float64)
    world=verts @ d.geom_xmat[i].reshape(3,3).T+d.geom_xpos[i]
    bb=np.r_[world.min(axis=0),world.max(axis=0)]*1000
    error=float(np.max(np.abs(bb-parts[m.geom(i).name]['world_bbox_mm'])))
    max_rest=max(max_rest,error)
    assert error<.05,(m.geom(i).name,error)
    samples[i]=(verts[0],world[0]*1000)
origins={b['name']:np.array(b['origin']) for b in source['bodies']}
def rotate(p,o,axis,angle):
    x,y,z=p-o;c=np.cos(angle);s=np.sin(angle)
    return np.array([c*x-s*y,s*x+c*y,z] if axis=='Z' else [c*x+s*z,y,-s*x+c*z])+o
max_motion=0
for pan,tilt,prop in ((.7,-.4,1.57),(-1.2,.6,-2.1)):
    for i in range(m.njnt):
        name=m.joint(i).name
        d.qpos[m.jnt_qposadr[i]]=pan if name=='cam_x_pan' else tilt if name=='cam_y_tilt' else prop
    mujoco.mj_forward(m,d)
    for i,(local,rest) in samples.items():
        body=parts[m.geom(i).name]['body'];expected=rest
        if body=='cam_y_tilt':expected=rotate(expected,origins[body],'Y',tilt)
        if body in ('cam_x_pan','cam_y_tilt'):expected=rotate(expected,origins['cam_x_pan'],'Z',pan)
        if body.startswith('prop_'):expected=rotate(expected,origins[body],'Z',prop)
        actual=(d.geom_xmat[i].reshape(3,3) @ local+d.geom_xpos[i])*1000
        err=float(np.max(np.abs(actual-expected)))
        max_motion=max(max_motion,err)
        assert err<.00001,(m.geom(i).name,err)
    for i in range(m.njnt):
        name=m.joint(i).name
        if name.startswith('prop_'):assert np.max(np.abs(d.xanchor[i]*1000-origins[name]))<.00001
report={'passed':True,'mesh_instances':m.ngeom,'hinges':m.njnt,'max_rest_error_mm':max_rest,'max_motion_error_mm':max_motion,'source_unchanged':True}
(ROOT/'build/mujoco_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
