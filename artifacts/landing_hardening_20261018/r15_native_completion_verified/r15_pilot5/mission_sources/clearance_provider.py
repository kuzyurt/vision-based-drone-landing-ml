"""Evaluation's declared static map; dynamic vehicles are explicitly excluded."""
import hashlib,json
from pathlib import Path
import numpy as np
from recovery_clearance import column_clearance

class StaticRecoveryPrior:
    def __init__(self,env,directory):
        m,d=env.model,env.data;boxes=[]
        for i in range(m.ngeom):
            if not (m.geom_contype[i] or m.geom_conaffinity[i]):continue
            body=int(m.geom_bodyid[i]);static=True
            while body:
                if m.body_jntnum[body] or m.body_mocapid[body]>=0:static=False;break
                body=int(m.body_parentid[body])
            if not static:continue
            # Upward-facing ground plane is a floor, not an overhead obstacle.
            if int(m.geom_type[i])==0:
                normal=d.geom_xmat[i].reshape(3,3)[:,2]
                if normal[2]>.99:continue
            center=m.geom_aabb[i,:3];half=m.geom_aabb[i,3:];points=[]
            for signs in np.ndindex(2,2,2):
                local=center+(2*np.asarray(signs)-1)*half
                points.append(d.geom_xpos[i]+d.geom_xmat[i].reshape(3,3)@local)
            points=np.asarray(points)
            boxes.append(dict(name=m.geom(i).name,min=points.min(0).tolist(),max=points.max(0).tolist()))
        self.boxes=boxes
        value=dict(scope='declared static collision map, ascent veto only',dynamic_vehicles_excluded=True,boxes=boxes)
        data=json.dumps(value,sort_keys=True,separators=(',',':')).encode();self.sha=hashlib.sha256(data).hexdigest()
        p=Path(directory)/'static_recovery_prior.json'
        with p.open('xb') as f:f.write(data)
    def certify(self,px4):
        return column_clearance(self.boxes,px4.get('position_enu_m',[]),px4.get('velocity_enu_m_s',[]),map_sha256=self.sha,known_coverage=bool(px4.get('valid')),ceiling_m=10.5)
