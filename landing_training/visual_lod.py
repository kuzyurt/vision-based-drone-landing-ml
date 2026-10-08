"""Decimate only render meshes. Original contact meshes and inertias survive."""
from copy import deepcopy
import hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import fast_simplification

def make_lod(source,destination):
    vertices=[];uv=[];faces=[];uv_by_vertex={}
    for line in source.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':vertices.append([float(v) for v in fields[1:4]])
        elif fields[0]=='vt':uv.append([float(v) for v in fields[1:3]])
        elif fields[0]=='f':
            corners=[]
            for field in fields[1:]:
                indices=field.split('/');index=int(indices[0]);index=index-1 if index>0 else len(vertices)+index;corners.append(index)
                if len(indices)>1 and indices[1]:
                    texture_index=int(indices[1]);texture_index=texture_index-1 if texture_index>0 else len(uv)+texture_index
                    uv_by_vertex[index]=uv[texture_index]
            for i in range(1,len(corners)-1):faces.append([corners[0],corners[i],corners[i+1]])
    if len(faces)<=1200:return False
    points=np.asarray(vertices,dtype=np.float64);triangles=np.asarray(faces,dtype=np.int32)
    points_new,faces_new=fast_simplification.simplify(points,triangles,target_count=400,agg=5.)
    if len(faces_new)<4:return False
    lines=['# Visual LOD only; collision asset remains original']
    lines.extend('v '+' '.join(f'{v:.10g}' for v in point) for point in points_new)
    if uv_by_vertex:
        closest=cKDTree(points).query(points_new)[1]
        lines.extend('vt '+' '.join(map(str,uv_by_vertex.get(int(index),[0.,0.]))) for index in closest)
        lines.extend('f '+' '.join(f'{int(index)+1}/{int(index)+1}' for index in face) for face in faces_new)
    else:lines.extend('f '+' '.join(str(int(index)+1) for index in face) for face in faces_new)
    destination.write_text('\n'.join(lines)+'\n');return True

def visual_lods(root,build):
    assets=root.find('asset');meshes={mesh.get('name'):mesh for mesh in assets.findall('mesh')}
    folder=build/'visual_lod';folder.mkdir(parents=True,exist_ok=True);created={}
    for geom in root.iter('geom'):
        mesh_name=geom.get('mesh')
        if not mesh_name or geom.get('contype','0')!='0' or geom.get('group','0') in ('4','5'):continue
        # Preserve the boat's original CAD visuals. Independent simplification
        # of neighbouring deck/overlay surfaces changes their boundaries and
        # produces gaps and overlapping faces. Only the drone uses visual LOD.
        if not mesh_name.startswith('drone_'):continue
        if any(token in mesh_name for token in ('LandingTarget','LandingGrip','LandingPlatform','scenery_buffer')):continue
        if mesh_name not in created:
            original=meshes[mesh_name];source=Path(original.get('file'))
            key=hashlib.sha256((str(source)+str(source.stat().st_size)+str(source.stat().st_mtime_ns)+'render400-v1').encode()).hexdigest()[:16]
            path=folder/(key+'.obj');skip=folder/(key+'.skip')
            if skip.exists():created[mesh_name]=None
            elif path.exists() or make_lod(source,path):
                mesh=deepcopy(original);mesh.attrib.update(name=mesh_name+'__render_lod',file=str(path));assets.append(mesh);created[mesh_name]=mesh.get('name')
            else:skip.touch();created[mesh_name]=None
        if created[mesh_name]:geom.set('mesh',created[mesh_name])
