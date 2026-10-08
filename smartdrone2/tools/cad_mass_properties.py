"""Read exact solid volume and normalized inertia. Run with FreeCAD Python.

No source recompute/save. Open shells and mesh-only objects are flagged; their
mass/inertia must be allocated explicitly rather than trusting BRep volume.
"""
import json
from pathlib import Path
import FreeCAD as App
ROOT=Path(__file__).resolve().parents[1]
exp=json.loads((ROOT/'models/metadata/export.json').read_text())
doc=App.openDocument(str(ROOT/'cad/drone+camera+other-things.FCStd'))
out={}
cache={}
for p in exp['parts']:
    obj=doc.getObject(p['source_object'])
    world=App.Placement(App.Vector(*p['placement_mm']),App.Rotation(*p['quaternion_xyzw']))
    outer=world.multiply(obj.Placement.inverse())
    row={'solid':False,'volume_mm3':0}
    if hasattr(obj,'Shape') and not obj.Shape.isNull():
        s=obj.Shape
        row['solid']=bool(s.Solids) and all(x.isClosed() for x in s.Solids)
        if row['solid'] and s.Volume>0:
            if obj.Name not in cache:
                solids=[x for x in s.Solids if x.Volume>0]
                volume=sum(x.Volume for x in solids)
                center=sum((x.CenterOfMass*x.Volume for x in solids),App.Vector())/volume
                mat=[[0. for j in range(3)] for i in range(3)]
                for solid in solids:
                    m=solid.MatrixOfInertia
                    d=solid.CenterOfMass-center
                    for i in range(3):
                        for j in range(3):
                            mat[i][j]+=(getattr(m,'A'+str(i+1)+str(j+1))+solid.Volume*((d.Length**2 if i==j else 0)-d[i]*d[j]))/volume*1e-6
                cache[obj.Name]=(volume,center,mat)
            volume,center,mat=cache[obj.Name]
            row['volume_mm3']=volume
            row['center_mm']=list(outer.multVec(center))
            # Rotate the central tensor, never translate it. Shape inertia is
            # already in its shape-placement axes; only outer remains.
            r=outer.Rotation.toMatrix()
            rot=[[getattr(r,'A'+str(i+1)+str(j+1)) for j in range(3)] for i in range(3)]
            row['unit_inertia_m2']=[[sum(rot[i][k]*mat[k][l]*rot[j][l] for k in range(3) for l in range(3)) for j in range(3)] for i in range(3)]
    out[p['part']]=row
    if len(out)%50==0:print('Read',len(out),'instances',flush=True)
(ROOT/'models/metadata/cad_mass_properties.json').write_text(json.dumps(out,indent=2))
print('Solid properties:',sum(p['solid'] for p in out.values()),'/',len(out))
