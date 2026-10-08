"""Compose the existing CAD models without duplicating their mass or physics."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
DRONE=REPO/'px4-mujoco-drone-simulation'
BOAT=REPO/'AERODOCK_MuJoCo'
FEET=('LinkGroup005__Solid006','LinkGroup005__Link','LinkGroup005__Link010','LinkGroup005__Link011')
REFERENCES={'joint','joint1','joint2','body','site','mesh','material','texture','geom','camera','actuator','tendon','target','refsite','objname','class','childclass'}

def absolute_assets(root,source):
    compiler=root.find('compiler')
    for element in root.iter():
        if 'file' in element.attrib:
            folder=compiler.get('meshdir','') if element.tag=='mesh' else compiler.get('texturedir','') if element.tag=='texture' else ''
            element.set('file',str((source.parent/folder/element.get('file')).resolve()))
    for key in ('meshdir','texturedir'):compiler.attrib.pop(key,None)

def compile_scene(timestep=.001):
    boat_file=BOAT/'models/boat.xml';drone_file=DRONE/'models/flight.xml'
    boat=ET.parse(boat_file).getroot();drone=ET.parse(drone_file).getroot()
    absolute_assets(boat,boat_file);absolute_assets(drone,drone_file)
    names={e.get('name') for e in drone.iter() if e.get('name')}
    for element in drone.iter():
        if element.get('name'):element.set('name','drone_'+element.get('name'))
        for key in REFERENCES:
            if element.get(key) in names:element.set(key,'drone_'+element.get(key))
        if element.tag=='geom' and element.get('contype')=='2':element.set('conaffinity','8')
    world=boat.find('worldbody');world.append(deepcopy(drone.find("worldbody/body[@name='drone_base_link']")))
    # Static world geometry must be positioned before compilation: MuJoCo
    # caches world-body geom transforms rather than recomputing them each step.
    world.find("geom[@name='water_surface']").set('pos','0 0 -.2')
    for tag in ('asset','actuator','sensor'):
        target=boat.find(tag)
        if target is None:target=ET.SubElement(boat,tag)
        for element in drone.find(tag):target.append(deepcopy(element))
    boat.find('compiler').set('inertiafromgeom','false')
    boat.find('option').attrib.update(timestep=str(timestep),gravity='0 0 -9.80665',integrator='implicitfast',iterations='80',cone='elliptic')
    platform=boat.find(".//body[@name='platform']")
    ET.SubElement(platform,'geom',name='landing_contact',type='box',pos='0 0 -.004',size='.3 .3 .004',contype='8',conaffinity='2',density='0',group='5',friction='.8 .005 .0001',solref='.01 1')
    ET.SubElement(platform,'site',name='landing_center',pos='0 0 0',size='.002',rgba='0 0 0 0')
    hull=boat.find(".//geom[@name='hull_contact']");hull.set('contype','1');hull.set('conaffinity','4')
    # Convex collision hulls must not span the open docking bay. Clip the actual
    # deck into four surrounding pieces; coaming rails are exact CAD boxes.
    from .collision_pieces import clipped_deck
    deck_source=boat.find("asset/mesh[@name='MainDeck_plain']").get('file')
    boat_body=world.find("body[@name='boat']")
    for name,file in clipped_deck(deck_source,ROOT/'build/deck_collision').items():
        mesh='deck_collision_'+name
        ET.SubElement(boat.find('asset'),'mesh',name=mesh,file=str(file),inertia='shell',maxhullvert='64')
        ET.SubElement(boat_body,'geom',name=mesh,type='mesh',mesh=mesh,density='0',group='5',contype='8',conaffinity='2',rgba='0 0 0 0')
    for name,position,size in (('port','-.04 .405 .61','.42 .015 .01'),('starboard','-.04 -.405 .61','.42 .015 .01'),('aft','-.445 0 .61','.015 .39 .01'),('fore','.365 0 .61','.015 .39 .01')):
        ET.SubElement(boat_body,'geom',name='coaming_collision_'+name,type='box',pos=position,size=size,density='0',group='5',contype='8',conaffinity='2',rgba='0 0 0 0')
    # Separate CAD part hulls keep the bay cavity open; coarse outer hull is
    # reserved for shore contacts, never used as the UAV landing surface.
    for body in list(boat.iter('body')):
        for geom in list(body.findall('geom')):
            name=geom.get('name','')
            if (name.endswith('_plain') and (name.startswith(('LiftTopSupport','Guide')) and ('Rod' in name or 'FixedSupports' in name or 'TopSupport' in name) or name.startswith('Mast'))) or name in ('AftSlidingLid_textured','ForeSlidingLid_textured'):
                collision=deepcopy(geom);collision.attrib.update(name='obstacle_'+name,contype='8',conaffinity='2',density='0',group='5',rgba='0 0 0 0')
                collision.attrib.pop('material',None);body.append(collision)
    # Model the dock's engaged mechanism brakes, not a kinematic boat. Joint
    # constraints transfer platform loads through the articulated boat body.
    equality=boat.find('equality')
    for name,value in (('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)):
        ET.SubElement(equality,'joint',name='prepared_'+name,joint1=name,polycoef=f'{value} 0 0 0 0',solref='.002 1')
    # Launch pad stays fixed in world coordinates after setup.
    launch=ET.SubElement(world,'body',name='launch_pad',mocap='true',pos='0 0 2')
    ET.SubElement(launch,'geom',name='launch_contact',type='box',size='.7 .7 .05',rgba='.22 .24 .29 1',contype='8',conaffinity='2',group='0')
    metadata=json.loads((DRONE/'models/metadata/export.json').read_text())
    datum=np.array(json.loads((DRONE/'models/metadata/mass_model.json').read_text())['datum_source_m'])
    base=world.find("body[@name='drone_base_link']")
    for i,name in enumerate(FEET):
        part=next(p for p in metadata['parts'] if p['part']==name)
        bounds=np.array(part['world_bbox_mm'])*.001
        point=np.r_[(bounds[:2]+bounds[3:5])/2,bounds[2]]-datum
        ET.SubElement(base,'site',name=f'drone_foot_{i}',pos=' '.join(map(str,point)),size='.002',rgba='0 0 0 0')
    visual=boat.find('visual')
    if visual is None:visual=ET.SubElement(boat,'visual')
    global_visual=visual.find('global')
    if global_visual is None:global_visual=ET.SubElement(visual,'global')
    global_visual.attrib.update(offwidth='1280',offheight='720')
    # A render-only mesh buffer. The physics always uses analytical water;
    # this mesh is updated around the observer, never centred on the target.
    build=ROOT/'build';build.mkdir(exist_ok=True)
    wave_file=build/'wave_buffer.obj'
    if not wave_file.exists():
        size=101;lines=[]
        for y in range(size):
            for x in range(size):
                z=.01 if (x,y)==(0,0) else 0.
                lines.append(f'v {x*2-100} {y*2-100} {z}')
        lines.extend('vt 0 0' for _ in range(size*size));lines.extend('vn 0 0 1' for _ in range(size*size))
        for y in range(size-1):
            for x in range(size-1):
                a=y*size+x+1;b=a+1;c=a+size;d=c+1
                for triangle in ((a,b,d),(a,d,c)):lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in triangle))
        wave_file.write_text('\n'.join(lines)+'\n')
    ET.SubElement(boat.find('asset'),'mesh',name='observer_water_mesh',file=str(wave_file),inertia='shell',maxhullvert='32')
    ET.SubElement(world,'geom',name='observer_water_buffer',type='mesh',mesh='observer_water_mesh',group='5',contype='0',conaffinity='0',density='0',rgba='0 0 0 0')
    from .visual_lod import visual_lods
    visual_lods(boat,ROOT/'build')
    payload=ET.tostring(boat,encoding='unicode')
    build=ROOT/'build';build.mkdir(exist_ok=True)
    stem=f'combined_{round(timestep*1e6)}us'
    path=build/(stem+'.xml');path.write_text(payload)
    # Contents of mesh/texture assets are covered by the review provenance.
    digest_builder=hashlib.sha256(payload.encode())
    for asset in boat.find('asset'):
        if asset.get('file'):
            with Path(asset.get('file')).open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):digest_builder.update(block)
    digest=digest_builder.hexdigest()
    cache=build/(stem+'.mjb');stamp=build/(stem+'.sha256')
    if cache.exists() and stamp.exists() and stamp.read_text()==digest:
        model=mujoco.MjModel.from_binary_path(str(cache))
    else:
        model=mujoco.MjModel.from_xml_path(str(path));mujoco.mj_saveModel(model,str(cache));stamp.write_text(digest)
    model.vis.map.znear=.001/model.stat.extent
    model.vis.map.zfar=6000/model.stat.extent
    return model
