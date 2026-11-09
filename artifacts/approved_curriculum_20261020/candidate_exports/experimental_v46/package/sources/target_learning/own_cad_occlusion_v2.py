"""Proposal self-occlusion from fixed OWN CAD + own camera encoders only."""
from pathlib import Path
import hashlib
import numpy as np
class OwnCadOcclusion:
    def __init__(self,path,expected_sha256,camera_body_transform):
        path=Path(path);assert hashlib.sha256(path.read_bytes()).hexdigest()==expected_sha256;self.source_sha256=expected_sha256;self.camera_body_transform=camera_body_transform
        with np.load(path)as a:
            for n in ['v0','e1','e2','lo','hi','offsets']:setattr(self,n,np.asarray(a[n]))
        assert self.v0.shape==self.e1.shape==self.e2.shape and self.v0.shape[1]==3 and len(self.offsets)==len(self.lo)+1
    def ray_hits(self,origin,direction):
        inv=np.divide(1.,direction,out=np.full(3,np.inf),where=np.abs(direction)>1e-12);a=(self.lo-origin)*inv;b=(self.hi-origin)*inv;near=np.maximum(np.minimum(a,b).max(1),.001);far=np.maximum(a,b).min(1);geoms=np.flatnonzero(far>=near)
        for g in geoms:
            sl=slice(self.offsets[g],self.offsets[g+1]);v=self.v0[sl];e1=self.e1[sl];e2=self.e2[sl];h=np.cross(np.broadcast_to(direction,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);valid=np.abs(det)>1e-10
            if not valid.any():continue
            e1=e1[valid];e2=e2[valid];v=v[valid];h=h[valid];invdet=1/det[valid];s=origin-v;u=np.einsum('ij,ij->i',s,h)*invdet;q=np.cross(s,e1);bary=np.einsum('j,ij->i',direction,q)*invdet;t=np.einsum('ij,ij->i',e2,q)*invdet
            if np.any((u>=0)&(bary>=0)&(u+bary<=1)&(t>.001)):return True
        return False
    def occluded(self,pixel,gimbal,calibration,*,erosion_px=2.):
        p=np.asarray(pixel,float)
        if p.shape!=(2,)or not np.isfinite(p).all()or np.any(p<[0,0])or np.any(p>=[640,360]):return False
        transform=self.camera_body_transform(calibration,gimbal);origin=transform[:3,3];rot=transform[:3,:3];focal=180/np.tan(np.deg2rad(calibration['camera_fovy_deg'])/2)
        for delta in [(0,0),(-erosion_px,0),(erosion_px,0),(0,-erosion_px),(0,erosion_px)]:
            x,y=p+delta;ray=rot@np.array([(x-320)/focal,-(y-180)/focal,-1.]);ray/=np.linalg.norm(ray)
            if not self.ray_hits(origin,ray):return False
        return True
