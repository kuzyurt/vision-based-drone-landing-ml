"""Independent retained-water reference from the unmodified CabinDrainage."""
import sys,json,math
from pathlib import Path
from types import SimpleNamespace
import numpy as np,mujoco
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'AERODOCK_MuJoCo'))
from usv.drainage import CabinDrainage
base=root/'tidewater-game/app/public/landing/physics'
c=json.loads((base/'configuration.json').read_text())
m=mujoco.MjModel.from_xml_path(str(base/'vehicles.xml'));d=mujoco.MjData(m);d.qpos[:]=c['qpos_initial'];d.qvel[:]=c['qvel_initial'];mujoco.mj_forward(m,d)
body=m.body('boat').id
s=SimpleNamespace(model=m,data=d,boat=body,gravity=c['boat']['gravity'],config=c['boat']['config'])
s._positions=lambda:np.array([d.qpos[c['boat']['qadr'][name]] for name in ('platform_slide','aft_lid_slide','fore_lid_slide')])
s.refresh_mass=lambda:None
s.status=lambda:{}
def speed(unit):
    v=np.zeros(6);mujoco.mj_objectVelocity(m,d,mujoco.mjtObj.mjOBJ_BODY,body,v,0);return np.linalg.norm(v[3:5])
s.get_speed=speed
waves=np.array(c['boat']['waves'])
s.waves=lambda xy:(np.cos(np.asarray(xy)@waves[:,:2].T-d.time*waves[:,3]+waves[:,4])@waves[:,2],None)
r=CabinDrainage(s);r.add(12);rows=[]
for i in range(120):
    r.rain=100 if i<40 else 0;r.failures=[i>=40,i>=80]
    angle=(0 if i<20 else 12 if i<60 else -15)*math.pi/180
    q=c['boat']['free_qadr'];d.qpos[q+3:q+7]=[math.cos(angle/2),math.sin(angle/2),0,0]
    d.qvel[c['boat']['free_vadr']]=2.5;d.time=(i+1)*.05;mujoco.mj_forward(m,d);r.step(.05)
    rows.append({'litres':r.litres,'pumped':r.total_pumped,'ingress':r.total_ingress,'flow':r.flow,'head':r.head,'mass':m.body_mass[r.body],'com':m.body_pos[r.body].tolist(),'time':d.time,'selected':r.selected})
(Path(__file__).parent/'drainage-reference.json').write_text(json.dumps(rows,separators=(',',':')))
