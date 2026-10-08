"""Low-poly scenery cache; only a local radius is submitted to the renderer.

Terrain patches are tiled in metres, not stretched over a kilometre. Distant
objects use one silhouette. Shadows/reflections and terrain simulation are off.
"""
from collections import OrderedDict
import math
import numpy as np
import mujoco

I=np.eye(3).ravel()


class WorldRenderer:
    def __init__(self, model, radius=380):
        self.model=model; self.radius=float(radius);self.cache=OrderedDict();self.world=None
        self.material={name:model.material('terrain_'+name).id for name in (
            'sand','wet_sand','grass','grass_macro','gravel','rock','concrete','facade','asphalt',
            'foliage','roof','pavers','quay','facade_brick','facade_modern',
            'rock_cliff','rock_wet','rock_boulder')}
        self.facade_mats={self.material[name] for name in ('facade','facade_brick','facade_modern')}
        self.count=0;self.chunk_count=0;self.truncated=False
        self.slots={};self.free_slots=[];self.gpu_owner=None

    def available_slots(self,renderer):
        slots=list(range(256))
        if renderer is None:return slots
        context=renderer._mjr_context
        # A missing final convex-hull display list can be reused by OpenGL for
        # built-in shapes. Re-uploading that final mesh deletes the sphere list.
        # Never upload a slot whose surface/hull pair overlaps built-in lists.
        return [i for i in slots if context.baseMesh+2*self.model.mesh(f'scenery_buffer_{i}').id+1<context.baseBuiltin]

    def upload_patch(self,renderer,key,triangles):
        if key in self.slots:return self.slots[key]
        slot=self.free_slots.pop();mesh=self.model.mesh(f'scenery_buffer_{slot}').id
        va=int(self.model.mesh_vertadr[mesh]);nv=int(self.model.mesh_vertnum[mesh])
        na=int(self.model.mesh_normaladr[mesh]);nn=int(self.model.mesh_normalnum[mesh])
        fa=int(self.model.mesh_faceadr[mesh]);nf=int(self.model.mesh_facenum[mesh])
        ta=int(self.model.mesh_texcoordadr[mesh]);nt=int(self.model.mesh_texcoordnum[mesh])
        if len(triangles)>nf or min(nv,nn,nt)<3*len(triangles):raise ValueError('Scenery patch buffer too small')
        vertices=[];normals=[]
        for _,size,pos,mat,_,_ in triangles:
            basis=mat.reshape(3,3)
            vertices.extend([pos,pos+basis[:,0]*size[0],pos+basis[:,1]*size[1]])
            normals.extend([basis[:,2]]*3)
        vertices=np.array(vertices);origin=vertices.mean(axis=0)
        self.model.mesh_vert[va:va+nv]=0
        self.model.mesh_normal[na:na+nn]=[0,0,1]
        self.model.mesh_texcoord[ta:ta+nt]=0
        n=len(vertices)
        self.model.mesh_vert[va:va+n]=vertices-origin
        self.model.mesh_normal[na:na+n]=normals
        uv=vertices[:,:2]*.5
        if key[2] in self.facade_mats or key[2]==self.material['quay']:
            normals=np.asarray(normals)
            scale=1/12 if key[2] in self.facade_mats else .25
            uv[:,0]=np.where(np.abs(normals[:,1])>np.abs(normals[:,0]),vertices[:,0],vertices[:,1])*scale
            uv[:,1]=(vertices[:,2]-(2 if key[2] in self.facade_mats else 0))*scale
        elif key[2] in (self.material['grass'],self.material['grass_macro']):uv=vertices[:,:2]/35
        elif key[2]==self.material['roof']:uv=vertices[:,:2]*.25
        elif key[2] in (self.material['rock_cliff'],self.material['rock_wet'],self.material['rock_boulder']):
            # Dominant-face projection gives vertical cliffs real vertical UVs,
            # instead of stretching a horizontal ground texture up the face.
            normal=np.asarray(normals);axis=np.argmax(np.abs(normal),axis=1)
            scale=1/8 if key[2]==self.material['rock_cliff'] else 1/4
            uv[:,0]=np.where(axis==0,vertices[:,1],vertices[:,0])*scale
            uv[:,1]=np.where(axis==2,vertices[:,1],vertices[:,2])*scale
        self.model.mesh_texcoord[ta:ta+n]=uv
        face=np.arange(nf*3).reshape(nf,3)
        self.model.mesh_face[fa:fa+nf]=face
        self.model.mesh_facenormal[fa:fa+nf]=face
        self.model.mesh_facetexcoord[fa:fa+nf]=face
        renderer._gl_context.make_current()
        mujoco.mjr_uploadMesh(self.model,renderer._mjr_context,mesh)
        self.slots[key]=(slot,mesh,origin)
        return self.slots[key]

    def triangle(self, a, b, c, material, tint=1.):
        ab=b-a;ac=c-a
        la=np.linalg.norm(ab);lc=np.linalg.norm(ac);normal=np.cross(ab,ac);ln=np.linalg.norm(normal)
        if min(la,lc,ln)<1e-7:return None
        # mjGEOM_TRIANGLE's two local edges become arbitrary world-space edges.
        # Normalized edge lengths keep the material frequency in metric units.
        mat=np.column_stack((ab/la,ac/lc,normal/ln)).ravel()
        return (mujoco.mjtGeom.mjGEOM_TRIANGLE,np.array([la,lc,.001]),a,mat,np.array([tint,tint,tint,1.],dtype=np.float32),self.material[material])

    def primitive(self,kind,size,pos,color,material=None,yaw=0.):
        co,si=math.cos(yaw),math.sin(yaw)
        mat=np.array([co,-si,0,si,co,0,0,0,1])
        return (kind,np.asarray(size),np.asarray(pos),mat,np.asarray(color,dtype=np.float32),self.material[material] if material else -1)

    def ground_z(self,w,inland,s):
        if w.kind=='city':return 2.0 if inland>=0 else -2.5
        if w.kind=='rock':
            if inland<0:return -.8
            toe=3.5+1.0*np.sin(s/23+w.phase[0])+.35*np.sin(s/9+w.phase[3])
            cliff=7.5+.26*w.height*(.7+.3*np.sin(s/42+w.phase[2]))+2.4*np.sin(s/17+w.phase[1])+1.1*np.sin(s/7+w.phase[3])
            base=.04+toe*.11
            if inland<toe:return .04+inland*.11
            if inland<toe+2:return base+cliff*(inland-toe)/2
            d=inland-toe-2
            return base+cliff+(w.height-cliff)*(1-np.exp(-d/110))+(1.3*np.sin(s/19+w.phase[1])*np.sin(d/12)+.8*np.sin(s/97+w.phase[1]))*min(d/10,1)
        shore=.035 if inland>=0 else -.8
        if inland<0:return shore
        if inland<w.beach_width:return shore+inland*(.045 if w.kind in ('island','beach') else .085)
        t=inland-w.beach_width
        hill=w.height*(1-np.exp(-t/95))
        return shore+w.beach_width*.055+hill*(.8+.2*np.sin(s/83+w.phase[3]))

    def chunk(self,w,index,lod):
        key=(index,lod)
        if key in self.cache:
            self.cache.move_to_end(key);return self.cache[key]
        rng=np.random.default_rng(np.random.SeedSequence([w.seed,index,1 if lod else 0]))
        start=index*40;end=min(start+40,w.coast_length)
        # Ground tessellation is already tiny. Keep it identical across LOD so
        # tree roots stay planted and never pop vertically as a chunk changes.
        ss=np.linspace(start,end,9 if w.kind=='rock' else 5)
        rows=([-3.,0.,2.,4.,6.,12.,35.,85.,200.,380.,1800.] if w.kind=='rock' else
              [0.,12.,24.,40.,68.,84.,110.,240.,1800.] if w.kind=='city' else
              [-3.,0.,1.5,w.beach_width,w.beach_width+42.,w.beach_width+120.,
              280.] if w.kind=='island' else
              [-3.,0.,1.5,w.beach_width,w.beach_width+42.,w.beach_width+120.,380.,1800.])
        geoms=[]
        def point(s,d):
            p,n,_=w.sample(s)
            if w.kind=='island':
                # Concentric inland rings avoid intersecting normal offsets and
                # finish in the green middle, not a narrow hollow ring.
                scale=max(0,1-d/np.linalg.norm(p))
                xy=p*scale
                actual=(1-scale)*np.linalg.norm(p)
            else:
                # Keep x monotone so inland bands never fold in concave bays.
                xy=p+[0,d];actual=d
            return np.r_[xy,self.ground_z(w,actual,s)]
        vertices=[[point(s,d) for d in rows] for s in ss]
        for i in range(len(ss)-1):
            for j in range(len(rows)-1):
                if w.kind=='city':
                    material=['pavers','asphalt','pavers','grass','asphalt','grass','grass_macro','grass_macro'][j]
                elif w.kind in ('island','beach'):
                    material='wet_sand' if j<2 else 'sand' if j==2 else 'grass' if j==3 else 'grass_macro'
                elif w.kind=='rock':
                    material='rock_wet' if j<3 else 'rock_cliff' if j<7 else 'grass_macro'
                else:
                    material='gravel' if j<3 and w.kind=='gravel' else 'rock' if w.kind=='rock' else 'grass' if j==3 else 'grass_macro'
                tint=float(rng.uniform(.92,1.04))
                a,b=vertices[i][j],vertices[i+1][j]
                c,d=vertices[i+1][j+1],vertices[i][j+1]
                for tri in (self.triangle(a,b,c,material,tint),self.triangle(a,c,d,material,tint)):
                    if tri:geoms.append(tri)
        if w.kind=='island':
            # Fill the remaining core with green triangles meeting at the center.
            center=np.array([0.,0.,self.ground_z(w,w.radius,0)])
            for i in range(len(ss)-1):
                tri=self.triangle(vertices[i][-1],vertices[i+1][-1],center,'grass')
                if tri:geoms.append(tri)
        # Plant objects on the rendered triangle surface, rather than on the
        # smooth height function (which can float above a coarse terrain mesh).
        bases=np.array([spec[2] for spec in geoms])
        edges_a=np.array([spec[3].reshape(3,3)[:,0]*spec[1][0] for spec in geoms])
        edges_b=np.array([spec[3].reshape(3,3)[:,1]*spec[1][1] for spec in geoms])
        det=edges_a[:,0]*edges_b[:,1]-edges_a[:,1]*edges_b[:,0]
        def grounded(p):
            p=p.copy();delta=p[:2]-bases[:,:2];safe=np.where(np.abs(det)>1e-9,det,np.inf)
            u=(delta[:,0]*edges_b[:,1]-delta[:,1]*edges_b[:,0])/safe
            v=(edges_a[:,0]*delta[:,1]-edges_a[:,1]*delta[:,0])/safe
            valid=np.flatnonzero((np.abs(det)>1e-9)&(u>=-1e-5)&(v>=-1e-5)&(u+v<=1+1e-5))
            if len(valid):
                k=valid[0];p[2]=bases[k,2]+u[k]*edges_a[k,2]+v[k]*edges_b[k,2]
            return p
        # Object placement has its own random stream. LOD changes appearance,
        # never world coordinates, heights or the identity of an object.
        rng=np.random.default_rng(np.random.SeedSequence([w.seed,index,77]))
        if w.kind=='city':
            # Weathered vertical quay, instead of a diagonal concrete beach.
            for i in range(len(ss)-1):
                a=point(ss[i],0);b=point(ss[i+1],0)
                aa=a.copy();bb=b.copy();aa[2]=bb[2]=-2.5
                geoms.extend([self.triangle(aa,bb,b,'quay'),self.triangle(aa,b,a,'quay')])

            def building(s,inland,width,depth,floors,style,gable=True):
                p=point(s,inland);h=floors*3.0
                _,_,t=w.sample(s);yaw=math.atan2(t[1],t[0])
                rot=np.array([[math.cos(yaw),-math.sin(yaw)],[math.sin(yaw),math.cos(yaw)]])
                corners=[p+np.r_[rot@offset,0] for offset in ([-width,-depth],[width,-depth],[width,depth],[-width,depth])]
                for k in range(4):
                    a=corners[k];b=corners[(k+1)%4];c=b+[0,0,h];d=a+[0,0,h]
                    geoms.extend([self.triangle(a,b,c,style),self.triangle(a,c,d,style)])
                if gable:
                    a,b,c,d=[q+[0,0,h] for q in corners];peak=float(rng.uniform(1.8,3.0))
                    front=(a+b)/2+[0,0,peak];back=(c+d)/2+[0,0,peak]
                    for aa,bb,cc in ((a,front,back),(a,back,d),(front,b,c),(front,c,back),(a,b,front),(d,back,c)):
                        geoms.append(self.triangle(aa,bb,cc,'roof'))
                else:geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_BOX,[width+.1,depth+.1,.18],p+[0,0,h+.18],[.58,.61,.59,1],yaw=yaw))
            # Human-scale frontage with alleys and periodic little parks.
            for j,s in enumerate((start+10,start+30)):
                width=float(rng.uniform(6,8));depth=float(rng.uniform(5,7));floors=int(rng.integers(2,5))
                style='facade' if (index+j)%3 else 'facade_brick'
                if index%7!=3:building(s,36,width,depth,floors,style,True)
            # Staggered back row; sparse taller office buildings, not a wall of
            # identical skyscrapers immediately next to the water.
            modern=index%5==0
            building(start+20,103,float(rng.uniform(8,11)),8,int(rng.integers(5,9) if modern else rng.integers(3,6)),
                     'facade_modern' if modern else 'facade_brick',not modern)
            for s in (start+10,start+30):
                p=grounded(point(s,53));p[2]-=.04;h=7.2
                geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_CYLINDER,[.23,h*.4,0],p+[0,0,h*.4],[.3,.24,.17,1]))
                geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_ELLIPSOID,[2.5,2.1,3.3],p+[0,0,6.1],[1,.98,.94,1],'foliage'))
            # Promenade fixtures only in nearby chunks. Lane markings are a
            # few raised paint strips, with a real separation from the road.
            if not lod:
                for s in (start+8,start+28):
                    p=point(s,5);_,_,t=w.sample(s);yaw=math.atan2(t[1],t[0])
                    geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_CYLINDER,[.07,2.1,0],p+[0,0,2.1],[.22,.26,.26,1]))
                    geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_BOX,[.4,.23,.13],p+[0,0,4.2],[.65,.64,.52,1],yaw=yaw))
                    q=point(s+4,7)
                    geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_BOX,[1.05,.32,.18],q+[0,0,.52],[.39,.29,.18,1],yaw=yaw))
                    for offset in (-.75,.75):
                        geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_BOX,[.055,.26,.26],q+[t[0]*offset,t[1]*offset,.26],[.22,.25,.25,1],yaw=yaw))
                for s in (start+5,start+15,start+25,start+35):
                    p=point(s,18);_,_,t=w.sample(s);yaw=math.atan2(t[1],t[0])
                    geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_BOX,[1.8,.07,.012],p+[0,0,.018],[.79,.78,.67,1],yaw=yaw))
                for s in (start+12,start+32):
                    p=point(s,0)
                    geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_ELLIPSOID,[.16,.3,.18],p+[0,-.02,.15],[.29,.33,.33,1]))
        elif w.kind in ('island','beach','gravel'):
            for tree_index in range(6):
                s=float(rng.uniform(start,end));inland=float(rng.uniform(w.beach_width+12,260 if w.kind=='island' else 155))
                p=grounded(point(s,inland));p[2]-=.04;h=float(rng.uniform(5,13));r=float(rng.uniform(2,4))
                green=.30+float(rng.uniform(0,.13))
                if lod and tree_index%2:continue
                geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_CYLINDER,[.18+.008*h,h*.38,0],p+[0,0,h*.38],[.3,.23,.15,1]))
                geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_ELLIPSOID,[r,r*.85,h*.35],p+[0,0,h*.68],[1,1,.93,1],'foliage'))
                if not lod:geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_ELLIPSOID,[r*.75,r*.65,h*.30],p+[r*.36,0,h*.86],[.94,1,.92,1],'foliage'))
            if w.kind=='gravel' and not lod:
                for _ in range(5):
                    p=grounded(point(float(rng.uniform(start,end)),float(rng.uniform(2,w.beach_width))))
                    r=float(rng.uniform(.3,1.1));geoms.append(self.primitive(mujoco.mjtGeom.mjGEOM_ELLIPSOID,[r,r*.7,r*.5],p+[0,0,r*.2],[.64,.62,.56,1],'gravel'))
        else:
            for rock_index in range(9):
                s=float(rng.uniform(start+2,end-2))
                inland=float(rng.uniform(1.2,2.2) if rock_index<3 else rng.uniform(9,30))
                p=grounded(point(s,inland))
                r=float(rng.uniform(.35,.7) if rock_index<3 else rng.uniform(1.1,2.6))
                yaw=float(rng.uniform(0,6.28));co,si=np.cos(yaw),np.sin(yaw)
                rot=np.array([[co,-si],[si,co]])
                widths=rng.uniform(.65,1.15,(4,2));top=rng.uniform(.58,.85,4)
                corners=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])*widths*r
                lower=[p+np.r_[rot@q,-r*.45] for q in corners]
                upper=[p+np.r_[rot@(q*.72),r*t] for q,t in zip(corners,top)]
                peak=p+[r*.1,0,r*1.15]
                if lod and rock_index%2:continue
                # Four fractured side panels plus a faceted cap; the hidden
                # bottom remains embedded in the ground, not a floating ball.
                for k in range(4):
                    a=lower[k];b=lower[(k+1)%4];c=upper[(k+1)%4];d=upper[k]
                    geoms.extend([self.triangle(a,b,c,'rock_boulder'),self.triangle(a,c,d,'rock_boulder'),
                                  self.triangle(d,c,peak,'rock_boulder')])
                geoms.extend([self.triangle(lower[0],lower[2],lower[1],'rock_boulder'),
                              self.triangle(lower[0],lower[3],lower[2],'rock_boulder')])
        self.cache[key]=geoms
        while len(self.cache)>64:self.cache.popitem(last=False)
        return geoms

    def append(self,scene,world,position,route_overlay=False,renderer=None):
        if world is None:self.count=self.chunk_count=0;return
        if world is not self.world or (renderer is not None and renderer is not self.gpu_owner):
            self.world=world;self.cache.clear();self.slots.clear();self.free_slots=self.available_slots(renderer);self.gpu_owner=renderer
        indices=np.arange(int(math.ceil(world.coast_length/40)))
        centers,_,_=world.sample(np.minimum(indices*40+20,world.coast_length))
        distances=np.linalg.norm(centers-np.asarray(position)[:2],axis=1)
        visible=np.flatnonzero(distances<self.radius+20)
        self.chunk_count=len(visible);initial=scene.ngeom;self.truncated=False
        active=[]
        for j in visible[np.argsort(distances[visible])]:
            lod=bool(distances[j]>200);specs=self.chunk(world,int(j),lod)
            groups={}
            for spec in specs:
                if spec[0]==mujoco.mjtGeom.mjGEOM_TRIANGLE:groups.setdefault(spec[5],[]).append(spec)
            active.append((int(j),lod,specs,groups))
        needed={(j,lod,material) for j,lod,_,groups in active for material in groups}
        for key in list(self.slots):
            if key not in needed:self.free_slots.append(self.slots.pop(key)[0])
        for j,lod,specs,groups in active:
            if renderer is not None:
                for material,triangles in groups.items():
                    if scene.ngeom>=scene.maxgeom:self.truncated=True;break
                    _,mesh,origin=self.upload_patch(renderer,(j,lod,material),triangles)
                    g=scene.geoms[scene.ngeom]
                    mujoco.mjv_initGeom(g,mujoco.mjtGeom.mjGEOM_MESH,np.ones(3),origin,I,np.ones(4,dtype=np.float32))
                    # MuJoCo keeps two display lists per mesh (surface/hull).
                    g.dataid=2*mesh;g.matid=material;g.texcoord=1;g.category=mujoco.mjtCatBit.mjCAT_DECOR;g.specular=.03
                    scene.ngeom+=1
            for spec in specs:
                if renderer is not None and spec[0]==mujoco.mjtGeom.mjGEOM_TRIANGLE:continue
                if scene.ngeom>=scene.maxgeom:self.truncated=True;break
                kind,size,pos,mat,color,material=spec
                g=scene.geoms[scene.ngeom]
                if kind=='connector':
                    mujoco.mjv_initGeom(g,mujoco.mjtGeom.mjGEOM_CAPSULE,np.zeros(3),np.zeros(3),I,color)
                    mujoco.mjv_connector(g,mujoco.mjtGeom.mjGEOM_CAPSULE,size,pos,mat)
                else:mujoco.mjv_initGeom(g,kind,size,pos,mat,color)
                g.matid=material;g.category=mujoco.mjtCatBit.mjCAT_DECOR;g.specular=.03;g.shininess=.05
                scene.ngeom+=1
        if route_overlay and world.route:
            points=world.route.points
            for i in range(0,len(points)-1,2):
                if np.linalg.norm(points[i]-position[:2])>min(self.radius,180):continue
                if scene.ngeom>=scene.maxgeom:break
                g=scene.geoms[scene.ngeom]
                mujoco.mjv_initGeom(g,mujoco.mjtGeom.mjGEOM_LINE,np.zeros(3),np.zeros(3),I,np.array([.2,.9,.75,1],np.float32))
                mujoco.mjv_connector(g,mujoco.mjtGeom.mjGEOM_LINE,2,np.r_[points[i],.16],np.r_[points[min(i+2,len(points)-1)],.16])
                scene.ngeom+=1
        self.count=scene.ngeom-initial

    def status(self):
        return {'scenery_geoms':self.count,'visible_chunks':self.chunk_count,
                'render_radius_m':self.radius,'scenery_budget_exceeded':self.truncated}
