"""Split the actual deck mesh around its bay rather than filling the bay hull."""
import hashlib
from pathlib import Path
import numpy as np

def clipped_deck(source,directory):
    source=Path(source);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(source.read_bytes()+Path(__file__).read_bytes()).hexdigest()[:16]
    pieces={name:directory/f'deck_{name}_{digest}.obj' for name in ('port','starboard','aft','fore')}
    if all(p.exists() for p in pieces.values()):return pieces
    vertices=[];faces=[]
    for line in source.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':vertices.append([float(x) for x in fields[1:4]])
        elif fields[0]=='f':
            indices=[int(x.split('/')[0])-1 for x in fields[1:]]
            faces.extend((indices[0],indices[i],indices[i+1]) for i in range(1,len(indices)-1))
    vertices=np.array(vertices)
    # These boundaries are the original deck bay / coaming exterior vertices.
    planes={'port':[(1,1,.42)],'starboard':[(1,-1,-.42)],'aft':[(0,-1,-.46),(1,1,-.42),(1,-1,.42)],'fore':[(0,1,.38),(1,1,-.42),(1,-1,.42)]}
    for name,cuts in planes.items():
        points=[];triangles=[]
        for face in faces:
            polygon=list(vertices[list(face)])
            for axis,direction,bound in cuts:
                clipped=[]
                if not polygon:break
                for start,end in zip(polygon,polygon[1:]+polygon[:1]):
                    a=direction*(start[axis]-bound);b=direction*(end[axis]-bound)
                    if a>=-1e-10:clipped.append(start)
                    if (a<0)!=(b<0):clipped.append(start+(end-start)*(a/(a-b)))
                polygon=clipped
            if len(polygon)<3:continue
            offset=len(points)+1;points.extend(polygon)
            for i in range(1,len(polygon)-1):
                if np.linalg.norm(np.cross(polygon[i]-polygon[0],polygon[i+1]-polygon[0]))>1e-12:triangles.append((offset,offset+i,offset+i+1))
        if not triangles:raise ValueError('Deck clipping produced an empty piece: '+name)
        text=['v '+' '.join(f'{v:.10g}' for v in point) for point in points]
        text+=['f '+' '.join(map(str,face)) for face in triangles]
        pieces[name].write_text('\n'.join(text)+'\n')
    return pieces
