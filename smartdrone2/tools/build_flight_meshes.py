"""Render-only CAD LOD. Mass/inertia use the original exact solids.

Assembly transforms, body hierarchy and joint anchors are unchanged. Bounds
must remain within 0.15 mm of the packed full-resolution meshes or that mesh
falls back to full resolution. Source and inspection OBJs are never edited.
"""
import base64
import json
from pathlib import Path
import fast_simplification
import numpy as np
from packed_geometry import read_packed_data
ROOT=Path(__file__).resolve().parents[1]
def main():
    data,blob=read_packed_data(ROOT)
    out=ROOT/'models/flight_meshes';out.mkdir(exist_ok=True)
    report=[]
    for p in data['parts']:
        vertices=np.frombuffer(blob,dtype='<u2',count=p['vertices']*3,offset=p['offset']).reshape(-1,3).astype(float)
        lo=np.array(p['lo']);hi=np.array(p['hi']);vertices=lo+vertices/65535*(hi-lo)
        faces=np.frombuffer(blob,dtype='<u4',count=p['triangles']*3,offset=p['offset']+p['pos_bytes']).reshape(-1,3).astype(np.int32)
        target=min(8000,max(600,int(len(faces)*.10)))
        v,f=vertices,faces;error=0.;fallback=False
        if len(faces)>target:
            while target<len(faces):
                vv,ff=fast_simplification.simplify(vertices,faces,target_count=target,agg=5)
                error=float(np.max(np.abs(np.concatenate((vv.min(axis=0),vv.max(axis=0)))-np.concatenate((vertices.min(axis=0),vertices.max(axis=0))))))
                if error<=.15:v,f=vv,ff;break
                target*=2
            else:fallback=True
        with (out/(p['name']+'.obj')).open('w',encoding='utf-8') as handle:
            handle.write('# Render LOD; unchanged CAD body-local coordinates in mm\n')
            np.savetxt(handle,v,fmt='v %.7f %.7f %.7f')
            np.savetxt(handle,f+1,fmt='f %d %d %d')
        report.append({'part':p['name'],'source_faces':len(faces),'flight_faces':len(f),'candidate_bbox_error_mm':error,'full_resolution_fallback':fallback})
        if len(report)%50==0:print('LOD',len(report),flush=True)
    (ROOT/'build/flight_mesh_verification.json').write_text(json.dumps({'max_accepted_bbox_deviation_mm':max(r['candidate_bbox_error_mm'] for r in report if not r['full_resolution_fallback']),'source_faces':sum(r['source_faces'] for r in report),'flight_faces':sum(r['flight_faces'] for r in report),'parts':report,'physics_uses_original_CAD_solids':True,'caution':'Bounds verification alone is not a full surface error metric; LOD is visual only.'},indent=2))
    print('Flight render faces:',sum(r['flight_faces'] for r in report),flush=True)
if __name__=='__main__':main()
