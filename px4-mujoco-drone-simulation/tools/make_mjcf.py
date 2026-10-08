"""Export corrected articulated geometry for MuJoCo inspection.

Base fixed for inspection; physical inertials come from the mass ledger.
Use flight.xml for the free aircraft and flight environment.
Visual meshes do not participate in collisions.
"""
import json
import math
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from make_viewer import unique_parts
ROOT = Path(__file__).resolve().parents[1]
export = json.loads((ROOT/'models/metadata/export.json').read_text(encoding='utf-8'))
materials = json.loads((ROOT/'models/metadata/materials.json').read_text(encoding='utf-8'))
masses = json.loads((ROOT/'models/metadata/mass_model.json').read_text(encoding='utf-8'))
if masses['source_sha256'] != export['sha256']:
    raise SystemExit('Mass properties must be regenerated for this CAD source.')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--limits',type=Path,help='Downloaded joint_limits.json from the viewer')
args=parser.parse_args()
if args.limits:
    limits=json.loads(args.limits.read_text(encoding='utf-8'))['joints']
    known={b['joint']['name'] for b in export['bodies'] if b['joint']}
    if set(limits)-known:raise SystemExit('Limits contain obsolete or unknown joints; download them from the corrected viewer.')
    for b in export['bodies']:
        j=b['joint']
        if not j or not j['limited'] or j['name'] not in limits:continue
        values=limits[j['name']]['range_rad']
        if not values or len(values)!=2 or not all(math.isfinite(v) for v in values) or values[0]>=values[1]:
            raise SystemExit('Invalid joint limits: '+j['name'])
        j['range']=values
def fmt(values):
    return ' '.join(f'{v:.12g}' for v in values)
model = ET.Element('mujoco',model='px4_mujoco_drone_simulation_corrected_inspection')
ET.SubElement(model,'compiler',angle='radian',meshdir='meshes',texturedir='textures')
ET.SubElement(model,'option',gravity='0 0 0')
asset = ET.SubElement(model,'asset')
world = ET.SubElement(model,'worldbody')
ET.SubElement(world,'light',pos='0 -1 2',dir='0 1 -2',directional='true')
texdir=ROOT/'models/textures'
texdir.mkdir(exist_ok=True)
from PIL import Image, ImageDraw
for name in ('carbon_weave','brushed_grey','grey_matte','battery_wrap'):
    im=Image.new('RGB',(128,128),(145,148,152) if name!='carbon_weave' else (24,26,29))
    draw=ImageDraw.Draw(im)
    if name=='carbon_weave':
        for y in range(8):
            for x in range(8):
                draw.rectangle((x*16,y*16,x*16+14,y*16+14),fill=(65,69,76) if (x+y)%4<2 else (33,36,40))
    elif name=='battery_wrap':
        for y in range(0,128,4):draw.line((0,y,127,y),fill=(43,68,98) if y%8 else (35,59,87))
        draw.rounded_rectangle((21,38,107,89),radius=5,fill=(220,229,238))
        draw.rectangle((21,38,107,45),fill=(36,73,111))
        draw.text((27,49),'4S LI-ION',fill=(23,50,79))
        draw.text((33,67),'12 000 mAh',fill=(65,82,101))
        draw.rectangle((28,94,100,97),fill=(236,175,59))
    else:
        for y in range(0,128,3):draw.line((0,y,127,y),fill=(138+y%13,141+y%13,145+y%13))
    im.save(texdir/(name+'.png'))
    ET.SubElement(asset,'texture',name=name,type='2d',file=name+'.png')
for key,mat in materials['palette'].items():
    attrs={'name':key,'rgba':fmt(mat['rgb']+[1]),'specular':str(mat['metallic']*.5),'shininess':str(1-mat['roughness'])}
    if mat['texture']:
        attrs['texture']=mat['texture'];attrs['texrepeat']='6 6' if mat['texture']=='carbon_weave' else '1 1' if mat['texture']=='battery_wrap' else '2 2';attrs['texuniform']='true'
    ET.SubElement(asset,'material',**attrs)
nodes={}
body_specs={b['name']:b for b in export['bodies']}
for b in export['bodies']:
    parent=body_specs.get(b['parent'])
    rel=[(v-(parent['origin'][i] if parent else 0))*.001 for i,v in enumerate(b['origin'])]
    node=ET.SubElement(nodes.get(b['parent'],world),'body',name=b['name'],pos=fmt(rel))
    nodes[b['name']]=node
    physical=masses['bodies'][b['name']]
    tensor=physical['inertia_kg_m2']
    center=[v-b['origin'][i]*.001 for i,v in enumerate(physical['center_source_m'])]
    ET.SubElement(node,'inertial',pos=fmt(center),mass=str(physical['mass_kg']),
                  fullinertia=fmt([tensor[0][0],tensor[1][1],tensor[2][2],tensor[0][1],tensor[0][2],tensor[1][2]]))
    if b['joint']:
        j=b['joint']
        attrs={'name':j['name'],'type':'hinge','axis':fmt(j['axis']),'pos':'0 0 0',
               'limited':'true' if j['limited'] else 'false','damping':str(j['damping']),'armature':str(j['armature'])}
        if j['limited']:attrs['range']=fmt(j['range'])
        ET.SubElement(node,'joint',**attrs)
for p in unique_parts(export['parts']):
    if not p['facets']:continue
    ET.SubElement(asset,'mesh',name=p['part'],file=p['part']+'.obj',scale='.001 .001 .001')
    ET.SubElement(nodes[p['body']],'geom',name=p['part'],type='mesh',mesh=p['part'],
                  material=materials['assignments'][p['part']]['material'],contype='0',conaffinity='0',density='0',group='2')
ET.indent(model)
path=ROOT/'models/drone.xml'
ET.ElementTree(model).write(path,encoding='utf-8',xml_declaration=True)
print(f'Wrote {path}')
