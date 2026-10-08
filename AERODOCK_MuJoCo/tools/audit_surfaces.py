"""Audit identical-facing planar CAD surfaces with positive overlap area."""
import json
import time
from collections import defaultdict
from pathlib import Path
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parents[1]

def audit(doc):
    planes=defaultdict(list)
    for obj in doc.Objects:
        if obj.TypeId!='Part::Feature' or obj.Name=='UAVEnvelope' or obj.Shape.isNull(): continue
        for index,face in enumerate(obj.Shape.Faces):
            if not isinstance(face.Surface,Part.Plane): continue
            u0,u1,v0,v1=face.ParameterRange
            n=face.normalAt((u0+u1)/2,(v0+v1)/2)
            p=face.valueAt((u0+u1)/2,(v0+v1)/2)
            # Same-facing duplicates are a visible-surface risk. Opposite-facing
            # touching interfaces are covered separately by contact-face export.
            key=tuple(round(v,5) for v in (n.x,n.y,n.z,n.dot(p)))
            planes[key].append((obj.Name,index,face))
    overlaps=[]; tested=0
    for key,items in planes.items():
        for i,(name,index,face) in enumerate(items):
            a=face.BoundBox
            for other,fi,bface in items[i+1:]:
                b=bface.BoundBox
                if not a.intersect(b): continue
                tested+=1
                area=face.common(bface).Area
                if area>.1:
                    overlaps.append({'a':name,'a_face':index,'b':other,'b_face':fi,'area_mm2':round(area,5),'plane':key})
    return {'candidate_pairs':tested,'same_facing_overlaps':overlaps}

if __name__=='__main__':
    t=time.perf_counter()
    doc=App.openDocument(str(ROOT/'cad/AERODOCK_RAISED_TRIM.FCStd'))
    result=audit(doc)
    result['seconds']=round(time.perf_counter()-t,2)
    (ROOT/'reports/surface_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
