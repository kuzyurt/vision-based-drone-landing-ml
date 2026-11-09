"""Isolated MuJoCo distractors. IDs are annotation-only, never actor inputs."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
import numpy as np
import mujoco


def add_boat(world,assets,name,position,colour,*,yaw=0.,cabin=True,mast=False,scale=(1.,1.,1.)):
    # Authored distractor, deliberately a different hull from the target CAD.
    vertices=[[-1.,-.36,-.12],[-1.,.36,-.12],[.72,-.36,-.12],[.72,.36,-.12],
              [1.15,0,-.06],[-.9,-.29,.18],[-.9,.29,.18],[.65,-.29,.18],[.65,.29,.18],[1.08,0,.18]]
    mesh=name+'_hull_mesh'
    vertices=(np.asarray(vertices)*np.asarray(scale)).tolist()
    ET.SubElement(assets,'mesh',name=mesh,vertex=' '.join(str(v)for p in vertices for v in p))
    b=ET.SubElement(world,'body',name=name,mocap='true',pos=' '.join(map(str,position)),euler=f'0 0 {yaw}')
    common=dict(contype='8',conaffinity='2',group='0')
    ET.SubElement(b,'geom',name=name+'_hull',type='mesh',mesh=mesh,rgba=' '.join(map(str,[*colour,1])),**common)
    ET.SubElement(b,'geom',name=name+'_deck',type='box',pos='-.12 0 .19',size='.68 .27 .035',rgba='.72 .72 .67 1',**common)
    if cabin:ET.SubElement(b,'geom',name=name+'_cabin',type='box',pos='.1 0 .42',size='.30 .23 .2',rgba='.88 .86 .8 1',**common)
    if mast:ET.SubElement(b,'geom',name=name+'_mast',type='cylinder',pos='.12 0 1.12',size='.025 .66',rgba='.23 .24 .25 1',**common)
    return b


def compile_variant(base_xml,out,*,seed=810100,sun=True,distractors=True):
    """Compile into new files. Never mutate original model, XML or checkpoints."""
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    root=ET.parse(base_xml).getroot();world=root.find('worldbody');assets=root.find('asset')
    # MuJoCo's scene convention is radians (verified via compiler setting).
    compiler=root.find('compiler')
    if compiler is not None and compiler.get('angle','degree')!='radian':
        raise ValueError('Distractor yaw requires verified radian scene convention')
    for light in world.findall('light'):world.remove(light)
    ET.SubElement(world,'light',name='discrimination_sun',directional='true',pos='0 0 20',
                  dir='-.75 .08 -.66' if sun else '.1 -.3 -1',ambient='.25 .25 .25',
                  diffuse='.8 .79 .75',specular='1 1 1' if sun else '.1 .1 .1',castshadow='false')
    if distractors:
        rng=np.random.default_rng(seed)
        for name,position,colour,cabin,mast in [
            ('decoy_red',[8,0,.03],[.72,.035,.025],True,False),
            ('decoy_similar',[5,5,.03],[.85,.86,.83],True,True),
            ('decoy_dark',[-8,-3,.03],[.05,.12,.2],False,False)]:
            add_boat(world,assets,name,position,colour,yaw=float(rng.uniform(-3.14,3.14)),
                     cabin=cabin,mast=mast,scale=rng.uniform([.75,.75,.85],[1.4,1.3,1.2]))
        buoy=ET.SubElement(world,'body',name='decoy_buoy',mocap='true',pos='-4 4 .12')
        ET.SubElement(buoy,'geom',name='decoy_buoy_shape',type='sphere',size='.22',rgba='1 .65 .05 1',contype='8',conaffinity='2')
        log=ET.SubElement(world,'body',name='decoy_debris',mocap='true',pos='-3 -5 .02')
        ET.SubElement(log,'geom',name='decoy_debris_shape',type='box',size='.8 .18 .08',rgba='.3 .22 .14 1',contype='8',conaffinity='2')
    payload=ET.tostring(root,encoding='unicode');xml=out/'scene.xml';xml.write_text(payload)
    model=mujoco.MjModel.from_xml_path(str(xml));mujoco.mj_saveModel(model,str(out/'scene.mjb'))
    (out/'source.json').write_text(json.dumps(dict(seed=seed,base_xml_sha256=hashlib.sha256(Path(base_xml).read_bytes()).hexdigest(),
        variant_xml_sha256=hashlib.sha256(payload.encode()).hexdigest(),sun=sun,distractors=distractors,
        distractor_note='Static physical obstacles; dynamics/moving variants pending review. Not another valid landing target.',
        glare='MuJoCo directional-light/specular-water approximation, not a Tidewater shader or image overlay.'),indent=2))
    return model


def annotation_groups(model):
    groups={}
    for gid in range(model.ngeom):
        body=int(model.geom_bodyid[gid]);ancestors=[]
        while body:
            ancestors.append(mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_BODY,body));body=int(model.body_parentid[body])
        key=next((n for n in ancestors if n and n.startswith('decoy_')),None)
        if key is None and 'boat' in ancestors:key='target'
        if key:groups.setdefault(key,[]).append(gid)
    return groups
