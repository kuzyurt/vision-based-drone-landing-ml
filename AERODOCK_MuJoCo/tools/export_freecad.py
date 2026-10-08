"""Run with FreeCAD's bundled Python. Rebuilds CAD and exports EVERY shape.
No FreeCAD dependency is needed to run the delivered MuJoCo package.
"""
import json
import math
import hashlib
import pathlib
import shutil
import re
import xml.etree.ElementTree as ET
import FreeCAD as App
import Part
import MeshPart

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT/'cad/freecad_macro.py'
ORIGIN = (1200., 0., 0.)


def vec(values):
    return ' '.join('%.9g' % float(v) for v in values)


def local(point, origin=ORIGIN):
    return [(point[i] - origin[i]) / 1000. for i in range(3)]


def write_obj(path, triangles, tile=.25):
    """Per-triangle metric UVs; no stretched bounding-box UV coordinates."""
    vertices=[]; lookup={}; uvs=[]; uv_lookup={}; faces=[]
    for tri in triangles:
        a,b,c=[App.Vector(*p) for p in tri]
        n=(b-a).cross(c-a)
        axis=max(range(3),key=lambda i:abs(tuple(n)[i]))
        plane=[i for i in range(3) if i!=axis]
        refs=[]
        for p in tri:
            key=tuple(round(q,9) for q in p)
            if key not in lookup:
                lookup[key]=len(vertices)+1; vertices.append(p)
            uv=tuple(round(p[i]/tile,9) for i in plane)
            if uv not in uv_lookup:
                uv_lookup[uv]=len(uvs)+1; uvs.append(uv)
            refs.append((lookup[key],uv_lookup[uv]))
        faces.append(refs)
    with path.open('w', encoding='ascii') as f:
        for p in vertices: f.write('v '+vec(p)+'\n')
        for uv in uvs: f.write('vt '+vec(uv)+'\n')
        for refs in faces: f.write('f '+' '.join('%d/%d'%ref for ref in refs)+'\n')


def surface_kind(name):
    if name=='HullShell' or name.endswith('SlidingLid') or name.endswith('ServiceHatch'):
        return 'paint'
    if name=='MainDeck' or 'Grip' in name or name=='LandingPlatform':
        return 'grip'
    if name.endswith('RubRail'): return 'rubber'
    if name in ('CameraMast','NavigationCameraMount','LidRails'): return 'metal'
    if name.endswith('Housing') and 'Camera' in name: return 'paint'
    return None


def main():
    (ROOT/'assets/meshes').mkdir(parents=True,exist_ok=True)
    (ROOT/'assets/textures').mkdir(parents=True,exist_ok=True)
    if SOURCE.resolve()!=(ROOT/'cad/freecad_macro.py').resolve():
        shutil.copyfile(SOURCE,ROOT/'cad/freecad_macro.py')
    prior_shapes={};prior_report={}
    if (ROOT/'cad/AERODOCK_RAISED_TRIM.FCStd').exists() and (ROOT/'reports/cad_validation.json').exists():
        prior_report=json.loads((ROOT/'reports/cad_validation.json').read_text())
        previous=App.openDocument(str(ROOT/'cad/AERODOCK_RAISED_TRIM.FCStd'))
        prior_shapes={o.Name:hashlib.sha256(o.Shape.exportBrepToString().encode()).hexdigest()
                      for o in previous.Objects if o.TypeId=='Part::Feature'}
        App.closeDocument(previous.Name)
    ns={'__name__':'__main__','__file__':str(SOURCE),'_cached_check':lambda label:False}
    raw_source=SOURCE.read_text(encoding='utf-8')
    source=raw_source.replace('BUILD_VALIDATION = True','BUILD_VALIDATION = False')
    for marker in ('# Real drilled feed-throughs', '# Machine actual seats', '# All motion updates'):
        source=source.replace(marker,"print('CAD stage: "+marker[2:]+"',flush=True)\n"+marker,1)
    source=source.replace("            else: checks.append(label)","            else:\n                checks.append(label)\n                if len(checks)%100==0: print('CAD check %d: '%len(checks)+label,flush=True)")
    source=source.replace('    def check(label,fun):\n        try:',
                          '    def check(label,fun):\n        if _cached_check(label):\n            checks.append(label)\n            return\n        try:')
    print('Rebuilding all CAD parts including raised trim...',flush=True)
    exec(compile(source,str(SOURCE),'exec'),ns)
    ns['set_geometry'](lid=0,lift=1)
    doc=ns['doc']; parts=ns['parts']; meta=ns['meta']
    current_hashes={n:hashlib.sha256(o.Shape.exportBrepToString().encode()).hexdigest() for n,o in parts.items()}
    unchanged={n for n,h in current_hashes.items() if prior_shapes.get(n)==h}
    failed_labels={x.split(':',1)[0] for x in prior_report.get('failures',[])}
    pattern=re.compile(r'(?<![A-Za-z0-9_])('+ '|'.join(re.escape(n) for n in sorted(parts,key=len,reverse=True))+r')(?![A-Za-z0-9_])')
    cache_hits=[0]
    motion_members=set(ns['moving_platform']+ns['moving_lids']['aft']+ns['moving_lids']['fore'])
    def cached(label):
        if not prior_report.get('motion_sweeps') or label in failed_labels:return False
        names=set(pattern.findall(label))
        if not names or not names<=unchanged:return False
        if ('containment' in label or 'internal portion' in label) and 'HullShell' not in unchanged:return False
        if ('sweep' in label or 'stored UAV' in label) and not motion_members<=unchanged:return False
        if label.startswith('camera ray') and not {'DockCameraHousing','NavigationCameraHousing'}<=unchanged:return False
        cache_hits[0]+=1;return True
    ns['_cached_check']=cached
    print('Rechecking changed geometry; %d / %d parts have identical BREP to previous checked CAD.'%(len(unchanged),len(parts)),flush=True)
    validation=ns['validate'](full_motion=True,verbose=True)
    validation['cached_unchanged_checks']=cache_hits[0]
    validation['changed_geometry_rechecked']=True
    (ROOT/'reports/cad_validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    doc.saveAs(str(ROOT/'cad/AERODOCK_RAISED_TRIM.FCStd'))
    if not validation['passed']:
        for issue in validation['failures']:print(issue,flush=True)
        raise RuntimeError('CAD validation failed; fix geometry before exporting meshes.')
    platform=ns['moving_platform']; lids=ns['moving_lids']
    owners={name:'boat' for name in parts}
    for name in platform: owners[name]='platform'
    for tag in ('aft','fore'):
        for name in lids[tag]: owners[name]=tag+'_lid'
    for i in range(1,5): owners['LiftScrew'+str(i)]='lift_screw_'+str(i)
    for tag in ('Aft','Fore'): owners[tag+'LidScrew']=tag.lower()+'_lid_screw'
    for tag in ('Port','Starboard'):
        for suffix in ('Propeller','PropShaft'):
            owners[tag+suffix]=tag.lower()+'_prop'
        for suffix in ('Coupling','UpperDriveShaft'):
            owners[tag+suffix]=tag.lower()+'_upper_drive'
        for suffix in ('DropShaft','UpperBevelGear','LowerBevelGear'):
            owners[tag+suffix]=tag.lower()+'_vertical_drive'
    owners['SpeedNeedle']='speed_needle'
    origins={'boat':ORIGIN,'platform':(1160.,0.,200.),'aft_lid':ORIGIN,'fore_lid':ORIGIN,
             'port_prop':(-158.,-205.,ns['PROP_Z']),'starboard_prop':(-158.,205.,ns['PROP_Z']),
             'port_upper_drive':(-37.,-205.,230.),'starboard_upper_drive':(-37.,205.,230.),
             'port_vertical_drive':(-55.,-205.,60.),'starboard_vertical_drive':(-55.,205.,60.),
             'speed_needle':(2055.,-210.,611.)}
    for i,(x,y) in enumerate(ns['screw_positions'],1): origins['lift_screw_'+str(i)]=(x,y,172.)
    origins['aft_lid_screw']=(255.,-475.,636.)
    origins['fore_lid_screw']=(1140.,475.,636.)
    outer_shell=Part.makeShell(ns['outer'].Faces)
    records=[]
    total_triangles=0
    for index,(name,obj) in enumerate(parts.items(),1):
        owner=owners[name]; origin=origins[owner]
        kind=surface_kind(name)
        buckets={'plain':[],'textured':[]}
        for face in obj.Shape.Faces:
            vertices,facets=MeshPart.meshFromShape(Shape=face,LinearDeflection=.65,AngularDeflection=.20,Relative=False).Topology
            is_textured=bool(kind)
            if kind:
                u0,u1,v0,v1=face.ParameterRange
                sample=face.valueAt((u0+u1)/2,(v0+v1)/2)
                normal=face.normalAt((u0+u1)/2,(v0+v1)/2)
                if name=='HullShell':
                    is_textured=Part.Vertex(sample).distToShape(outer_shell)[0]<.8
                elif name=='MainDeck' or name=='LandingPlatform' or 'Grip' in name:
                    is_textured=normal.z>.7
                elif name in ('LidRails','CameraMast','NavigationCameraMount'):
                    is_textured=sample.z>=600
                elif name.endswith('Housing') and 'Camera' in name:
                    camera=ns['CAMERAS'][name.removesuffix('Housing')]
                    center=App.Vector(*camera['lens'])-App.Vector(*camera['axis'])*21
                    is_textured=normal.dot(sample-center)>0
            target=buckets['textured' if is_textured else 'plain']
            for tri in facets:
                points=[local((vertices[j].x,vertices[j].y,vertices[j].z),origin) for j in tri]
                # Reject only zero-area tessellation artifacts, never a CAD part.
                a,b,c=[App.Vector(*p) for p in points]
                if (b-a).cross(c-a).Length>1e-14: target.append(points)
        if not any(buckets.values()): raise RuntimeError('No tessellation for '+name)
        group=4 if meta[name]['role']=='reference' else 0
        if name in ('HullShell','MainDeck','ElectronicsBoxLid') or name.endswith('ServiceHatch') or name.endswith('SlidingLid') or name.endswith('LidGraphics'):
            group=2
        if name.endswith('Lens') or name.endswith('Window'): group=3
        record={'name':name,'owner':owner,'group':group,'description':obj.Description,
                'material':obj.Material,'metadata':meta[name], 'meshes':[]}
        for bucket,triangles in buckets.items():
            if not triangles: continue
            asset=name+'_'+bucket
            write_obj(ROOT/'assets/meshes'/(asset+'.obj'),triangles)
            total_triangles+=len(triangles)
            record['meshes'].append({'name':asset,'file':asset+'.obj','triangles':len(triangles),
                                    'texture':kind if bucket=='textured' else None})
        records.append(record)
        if index%30==0: print('Exported %d / %d parts'%(index,len(parts)),flush=True)

    # Exterior displacement envelope, not the hollow material hull.
    verts,faces=ns['outer'].tessellate(2.)
    write_obj(ROOT/'assets/meshes/hull_collision.obj',[[local(tuple(verts[i])) for i in tri] for tri in faces])
    cells=[]
    nx,ny=24,12; dx=ns['LENGTH']/nx; dy=ns['BEAM']/ny
    for ix in range(nx):
        x=(ix+.5)*dx
        factor,keel=ns['station'](x); half=ns['BEAM']*factor/2
        height=600-keel
        profile=[(0.,keel),(.8*half,keel),(.89*half,keel+.18*height),
                 (.95*half,keel+.48*height),(.99*half,keel+.78*height),(half,600.)]
        for iy in range(ny):
            y=-ns['BEAM']/2+(iy+.5)*dy
            if abs(y)>=half: continue
            bottom=keel
            for (ya,za),(yb,zb) in zip(profile[:-1],profile[1:]):
                if ya<=abs(y)<=yb:
                    bottom=za+(zb-za)*(abs(y)-ya)/(yb-ya); break
            cells.append({'x':(x-1200)/1000,'y':y/1000,'bottom':bottom/1000,
                          'top':.6,'area':dx*dy/1e6})
    exact_volume=ns['outer'].Volume/1e9
    factor=exact_volume/sum(c['area']*(c['top']-c['bottom']) for c in cells)
    for c in cells: c['area']*=factor
    manifest={'source':str(SOURCE),'source_sha256':hashlib.sha256(raw_source.encode()).hexdigest(),'units':'meters','origin_mm':ORIGIN,
              'cad_part_count':len(parts),'exported_part_count':len(records),'triangle_count':total_triangles,
              'parts':records,'body_origins_mm':origins,'cameras':ns['CAMERAS'],
              'displacement_volume_m3':exact_volume,'buoyancy_cells':cells,
              'wiring_schedule':ns['wire_rows'],
              'documentation_objects':[{'name':o.Name,'type':o.TypeId} for o in doc.Objects if o.Name not in parts],
              'trim_note':'Raised 3 mm outside hull, bonded 0.2 mm inward; no coplanar hull surface.'}
    (ROOT/'models/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    build_mjcf(manifest)
    # Rebuilt CAD keeps the same procedural scenery buffers and materials.
    from tools.setup_world_assets import setup
    setup()
    print('COMPLETE: %d / %d parts, %d triangles, %d buoyancy cells'%(len(records),len(parts),total_triangles,len(cells)),flush=True)


def build_mjcf(manifest):
    root=ET.Element('mujoco',model='AERODOCK complete CAD boat')
    ET.SubElement(root,'compiler',angle='radian',meshdir='../assets/meshes',texturedir='../assets/textures',inertiafromgeom='false',autolimits='true')
    ET.SubElement(root,'option',timestep='.005',gravity='0 0 -9.81',integrator='implicitfast',density='0',viscosity='0',iterations='30')
    ET.SubElement(root,'statistic',extent='3',center='0 0 0')
    visual=ET.SubElement(root,'visual')
    ET.SubElement(visual,'global',offwidth='960',offheight='540')
    ET.SubElement(visual,'map',znear='.000166667',zfar='200',fogstart='90',fogend='160')
    ET.SubElement(visual,'quality',shadowsize='1024',offsamples='2')
    ET.SubElement(visual,'rgba',fog='.62 .75 .82 1')
    assets=ET.SubElement(root,'asset')
    ET.SubElement(assets,'texture',name='sky',type='skybox',builtin='gradient',rgb1='.32 .56 .76',rgb2='.86 .92 .94',width='512',height='3072')
    for kind in ('paint','grip','rubber','metal','water'):
        ET.SubElement(assets,'texture',name='tex_'+kind,type='2d',file=kind+'.png')
    ET.SubElement(assets,'texture',name='tex_wake',type='2d',file='wake.png',nchannel='4')
    ET.SubElement(assets,'material',name='wake_mat',texture='tex_wake',texuniform='false',rgba='1 1 1 .7',specular='0',shininess='0',emission='.15')
    ET.SubElement(assets,'material',name='water_mat',texture='tex_water',texuniform='true',texrepeat='.2 .2',rgba='.55 .7 .78 1',specular='.18',shininess='.6',reflectance='0')
    for record in manifest['parts']:
        color=record['metadata']['color']; alpha=0 if record['group']==4 else (.45 if record['name'].endswith('Window') else 1)
        for chunk in record['meshes']:
            ET.SubElement(assets,'mesh',name=chunk['name'],file=chunk['file'],smoothnormal='false',inertia='shell',maxhullvert='32')
            material=chunk['name']+'_mat'
            attrs={'name':material,'rgba':vec(color+[alpha] if isinstance(color,list) else list(color)+[alpha]),'specular':'.25','shininess':'.2'}
            if chunk['texture']:
                attrs.update(texture='tex_'+chunk['texture'],texrepeat='1 1',texuniform='false')
            ET.SubElement(assets,'material',**attrs)
    ET.SubElement(assets,'mesh',name='hull_collision',file='hull_collision.obj',maxhullvert='64')
    world=ET.SubElement(root,'worldbody')
    ET.SubElement(world,'light',name='sun',directional='true',pos='-4 -3 8',dir='.25 .2 -1',diffuse='.78 .8 .8',ambient='.3 .32 .35',castshadow='true')
    ET.SubElement(world,'light',name='fill',directional='true',pos='2 5 5',dir='-.2 -.4 -1',diffuse='.22 .26 .3',castshadow='false')
    ET.SubElement(world,'geom',name='water_surface',type='plane',pos='0 0 0',size='100 100 .01',material='water_mat',contype='0',conaffinity='0',group='1')
    ET.SubElement(world,'geom',name='seabed',type='plane',pos='0 0 -8',size='100 100 .1',rgba='.18 .24 .23 1',group='5')
    for tag in ('port','starboard'):
        wake=ET.SubElement(world,'body',name=tag+'_wake',mocap='true',pos='0 0 .001')
        ET.SubElement(wake,'geom',name=tag+'_wake_surface',type='box',size='.8 .18 .00008',material='wake_mat',rgba='1 1 1 0',contype='0',conaffinity='0',group='1')
    boat=ET.SubElement(world,'body',name='boat',pos='0 0 -.22')
    ET.SubElement(boat,'freejoint',name='boat_free')
    # Physical mass remains separate from geometry-envelope volume and added mass.
    ET.SubElement(boat,'inertial',pos='-.025 0 .32',mass='182.6',diaginertia='24.6 89 98')
    flood=ET.SubElement(boat,'body',name='cabin_water',pos='-.04 0 .134')
    ET.SubElement(flood,'inertial',pos='0 0 0',mass='.000001',diaginertia='.000000001 .000000001 .000000001')
    ET.SubElement(boat,'geom',name='hull_contact',type='mesh',mesh='hull_collision',rgba='0 0 0 0',group='5',friction='.4 .01 .001')
    bodies={'boat':boat}
    actuators=ET.SubElement(root,'actuator')
    equality=ET.SubElement(root,'equality')
    for name,origin in manifest['body_origins_mm'].items():
        if name=='boat': continue
        body=ET.SubElement(boat,'body',name=name,pos=vec(local(origin)))
        bodies[name]=body
        if name=='platform':
            ET.SubElement(body,'inertial',pos='0 0 .025',mass='22',diaginertia='.82 .82 1.35')
            ET.SubElement(body,'joint',name='platform_slide',type='slide',axis='0 0 1',range='0 .4',damping='80')
            ET.SubElement(actuators,'position',name='lift_position',joint='platform_slide',kp='18000',kv='1100',ctrlrange='0 .4',forcerange='-1600 1600')
        elif name in ('aft_lid','fore_lid'):
            ET.SubElement(body,'inertial',pos=vec(local((950 if name=='aft_lid' else 1370,0,630))),mass='4.5',diaginertia='.27 .075 .33')
            ET.SubElement(body,'joint',name=name+'_slide',type='slide',axis=('-1 0 0' if name=='aft_lid' else '1 0 0'),range='0 .46',damping='35')
            ET.SubElement(actuators,'position',name=name+'_position',joint=name+'_slide',kp='10000',kv='450',ctrlrange='0 .46',forcerange='-600 600')
        elif name.endswith('_prop'):
            ET.SubElement(body,'inertial',pos='.04 0 0',mass='1.0',diaginertia='.00055 .011 .011')
            ET.SubElement(body,'joint',name=name+'_spin',type='hinge',axis='1 0 0',damping='.001')
            ET.SubElement(actuators,'velocity',name=name+'_velocity',joint=name+'_spin',kv='.08',ctrlrange='-450 450',forcerange='-8 8')
        elif name.endswith('_drive'):
            vertical='vertical' in name
            ET.SubElement(body,'inertial',pos=('0 0 .085' if vertical else '.12 0 0'),mass='.35',diaginertia='.001 .001 .001')
            ET.SubElement(body,'joint',name=name+'_spin',type='hinge',axis=('0 0 1' if vertical else '1 0 0'),damping='.00001')
            parent_prop=name.split('_')[0]+'_prop_spin'
            ET.SubElement(equality,'joint',name=name+'_ratio',joint1=name+'_spin',joint2=parent_prop,polycoef='0 1 0 0 0',solref='.015 1')
        elif name=='speed_needle':
            ET.SubElement(body,'inertial',pos='0 .01 0',mass='.005',diaginertia='.000001 .000001 .000001')
            ET.SubElement(body,'joint',name='speed_needle_spin',type='hinge',axis='0 0 1',damping='.00001')
            ET.SubElement(actuators,'position',name='speed_needle_position',joint='speed_needle_spin',kp='.002',kv='.00008',ctrlrange='-3.2 3.2')
        else:
            lift=name.startswith('lift_screw')
            ET.SubElement(body,'inertial',pos=('0 0 .22' if lift else '.46 0 0'),mass=('.35' if lift else '.28'),diaginertia=('.006 .006 .000012' if lift else '.000006 .021 .021'))
            ET.SubElement(body,'joint',name=name+'_spin',type='hinge',axis=('0 0 1' if lift else '1 0 0'),damping='.00001')
            j2='platform_slide' if lift else name.replace('_screw','')+'_slide'
            sign=-1 if name=='aft_lid_screw' else 1
            ET.SubElement(equality,'joint',name=name+'_pitch',joint1=name+'_spin',joint2=j2,polycoef='0 '+str(sign*2*math.pi/.004)+' 0 0 0',solref='.015 1')
    for record in manifest['parts']:
        for chunk in record['meshes']:
            ET.SubElement(bodies[record['owner']],'geom',name=chunk['name'],type='mesh',mesh=chunk['name'],material=chunk['name']+'_mat',contype='0',conaffinity='0',group=str(record['group']))
    # Keep the exact reference mesh in the export; draw edges instead of its
    # translucent bottom face sharing the landing deck's plane.
    vertices=[(sx*.2,sy*.2,z) for z in (0,.35) for sy in (-1,1) for sx in (-1,1)]
    for i,a in enumerate(vertices):
        for j,b in enumerate(vertices[i+1:],i+1):
            if sum(abs(a[k]-b[k])>1e-8 for k in range(3))==1:
                ET.SubElement(bodies['platform'],'geom',name='UAVEnvelope_edge_%d_%d'%(i,j),type='capsule',
                              fromto=vec(a+b),size='.001',rgba='.02 .75 .7 .7',contype='0',conaffinity='0',group='4')
    for name,camera in manifest['cameras'].items():
        axis=App.Vector(*camera['axis']); right=axis.cross(App.Vector(0,0,1)); right.normalize(); up=right.cross(axis); up.normalize()
        ET.SubElement(boat,'camera',name=name,pos=vec(local(camera['lens'])),xyaxes=vec(tuple(right)+tuple(up)),fovy=str(camera['v']))
    ET.SubElement(boat,'site',name='port_thrust',pos=vec(local(manifest['body_origins_mm']['port_prop'])),size='.012',rgba='0 0 0 0',group='5')
    ET.SubElement(boat,'site',name='starboard_thrust',pos=vec(local(manifest['body_origins_mm']['starboard_prop'])),size='.012',rgba='0 0 0 0',group='5')
    ET.indent(root)
    ET.ElementTree(root).write(ROOT/'models/boat.xml',encoding='utf-8',xml_declaration=True)


if __name__=='__main__': main()
