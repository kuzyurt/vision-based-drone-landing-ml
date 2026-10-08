"""Orthographic CAD-LOD silhouettes: union areas avoid overlapping part boxes.

This is a raster geometric reference area, not CFD or an identified Cd. Pressure
is represented by one force at each projected centroid. Shielding between the
separate articulated bodies and rotor inflow are not simulated.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]

def read_obj(path):
    vertices, faces = [], []
    with path.open() as stream:
        for line in stream:
            if line.startswith('v '): vertices.append([float(v) for v in line.split()[1:4]])
            elif line.startswith('f '): faces.append([int(v.split('/')[0])-1 for v in line.split()[1:4]])
    return np.asarray(vertices)*.001, np.asarray(faces, dtype=np.int32)

def main():
    export = json.loads((ROOT/'models/metadata/export.json').read_text())
    masses = json.loads((ROOT/'models/metadata/mass_model.json').read_text())
    active = {p['part'] for p in masses['parts'] if p['mass_kg'] > 0}
    body_origins = {b['name']: np.array(b['origin'])*.001 for b in export['bodies']}
    elements = []
    for body in ('base_link', 'camera_mount', 'cam_x_pan', 'cam_y_tilt'):
        meshes = [read_obj(ROOT/'models/flight_meshes'/f"{p['part']}.obj") for p in export['parts'] if p['body']==body and p['part'] in active and p['world_bbox_mm']]
        verts = np.vstack([v for v,f in meshes]); lower=verts.min(axis=0); upper=verts.max(axis=0)
        for axis in range(3):
            plane = [i for i in range(3) if i != axis]
            span = upper[plane]-lower[plane]
            pixel = max(span)/768
            image=Image.new('1', tuple((np.ceil(span/pixel)+3).astype(int)), 0); draw=ImageDraw.Draw(image)
            for vertices,faces in meshes:
                points=np.rint((vertices[:,plane]-lower[plane])/pixel+1).astype(int)
                for face in faces:
                    triangle=points[face]
                    draw.polygon([tuple(p) for p in triangle], fill=1)
            yy,xx=np.nonzero(np.asarray(image)); area=len(xx)*pixel**2
            center=(lower+upper)/2
            center[plane]=lower[plane]+np.array([xx.mean()-1,yy.mean()-1])*pixel
            # Exported OBJ coordinates are already body-local, except the base
            # which used source-world coordinates before the flight datum shift.
            if body=='base_link': center-=np.array(masses['datum_source_m'])
            elements.append({'body':body, 'axis':axis, 'area_m2':float(area), 'center_local_m':center.tolist(), 'coefficient':1., 'coefficient_evidence':'authored_unit_reference_coefficient_not_identified_for_airframe'})
        print(body, [round(e['area_m2'],5) for e in elements[-3:]], flush=True)
    out={'method':'768_pixel_union_silhouette_per_body_axis', 'source_sha256':export['sha256'], 'elements':elements,
         'rotors_excluded':True, 'limitations':['LOD/raster silhouette approximation','one pressure centroid per projected plane','no inter-body shielding, rotor inflow or CFD','drag coefficient 1 is a configurable reference scenario, not a measured X500 value']}
    (ROOT/'models/metadata/aerodynamics.json').write_text(json.dumps(out,indent=2))

if __name__=='__main__': main()
