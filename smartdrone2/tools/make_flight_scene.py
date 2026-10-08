"""Add an explicit-mass free aircraft, physical actuators and flight environment."""
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
def fmt(x):return ' '.join(f'{v:.10g}' for v in x)
def main():
    masses=json.loads((ROOT/'models/metadata/mass_model.json').read_text())
    exp=json.loads((ROOT/'models/metadata/export.json').read_text())
    datum=np.array(masses['datum_source_m'])
    root=ET.parse(ROOT/'models/drone.xml').getroot()
    root.set('model','X500_V2_PX4_MuJoCo')
    root.find('option').attrib.update(gravity='0 0 -9.80665',timestep='.001',integrator='implicitfast',iterations='80',cone='elliptic')
    ET.SubElement(root,'size',njmax='3000',nconmax='1000')
    ET.SubElement(root,'visual')
    ET.SubElement(root.find('visual'),'global',offwidth='960',offheight='640')
    ET.SubElement(root.find('visual'),'headlight',ambient='.3 .3 .3',diffuse='.6 .6 .6',specular='.1 .1 .1')
    assets=root.find('asset'); world=root.find('worldbody')
    for light in world.findall('light'):light.set('castshadow','false')
    ET.SubElement(assets,'texture',name='sky',type='skybox',builtin='gradient',width='512',height='3072',rgb1='.12 .22 .34',rgb2='.56 .71 .83')
    root.find('compiler').set('meshdir','flight_meshes')
    root.find('compiler').set('inertiafromgeom','false')
    base=world.find("body[@name='base_link']")
    base.set('pos','0 0 .225')
    ET.SubElement(base,'freejoint',name='aircraft_free')
    origins={b['name']:np.array(b['origin'])*.001 for b in exp['bodies']}
    for node in base.iter('body'):
        name=node.get('name')
        inertial=node.find('inertial')
        if inertial is not None:node.remove(inertial)
        b=masses['bodies'][name]
        origin=datum if name=='base_link' else origins[name]
        I=np.array(b['inertia_kg_m2'])
        ET.SubElement(node,'inertial',mass=str(b['mass_kg']),pos=fmt(np.array(b['center_source_m'])-origin),fullinertia=fmt([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
        if name=='base_link':
            for geom in node.findall('geom'):geom.set('pos',fmt(-datum))
        else:
            spec=next(b for b in exp['bodies'] if b['name']==name)
            parent_origin=datum if spec['parent']=='base_link' else origins[spec['parent']]
            node.set('pos',fmt(origins[name]-parent_origin))
        joint=node.find('joint')
        if joint is not None:
            joint.set('armature','0');joint.set('damping','0.002' if name.startswith('cam_') else '0')
            if name=='cam_x_pan':joint.set('limited','false');joint.attrib.pop('range',None)
            if name=='cam_y_tilt':joint.set('range',fmt([math.radians(-61),math.radians(140)]))
        if name.startswith('prop_'):
            ET.SubElement(node,'site',name='hub_'+name,pos='0 0 0',size='.005',rgba='0 0 0 0')
    # Each CAD part gets its own convex collision hull, not one hull around
    # the open aircraft. Masks permit environment contacts and suppress
    # contacts between components of the same assembled drone.
    coverage=[]
    for node in base.iter('body'):
        if node.get('name','').startswith('prop_'):continue
        for visual in list(node.findall('geom')):
            if not visual.get('mesh'):continue
            attrs={key:value for key,value in visual.attrib.items() if key in ('mesh','pos','quat')}
            name='contact__'+visual.get('name')
            ET.SubElement(node,'geom',name=name,type='mesh',group='3',density='0',rgba='0 0 0 0',contype='2',conaffinity='1',friction='.8 .005 .0001',**attrs)
            coverage.append({'geom':name,'part':visual.get('name'),'body':node.get('name'),'method':'per_part_CAD_LOD_convex_hull'})
    for b in exp['bodies']:
        if not b['name'].startswith('prop_'):continue
        p=next(p for p in exp['parts'] if p['body']==b['name'] and p['world_bbox_mm'])
        lo=np.array(p['world_bbox_mm'][:3])*.001;hi=np.array(p['world_bbox_mm'][3:])*.001
        hub=origins[b['name']]
        xy=np.maximum(np.abs(lo[:2]-hub[:2]),np.abs(hi[:2]-hub[:2]))
        radius=float(np.linalg.norm(xy));half_height=float((hi[2]-lo[2])/2)
        center=hub.copy();center[2]=(lo[2]+hi[2])/2
        ET.SubElement(base,'geom',name='rotor_envelope_'+b['name'],type='cylinder',pos=fmt(center-datum),size=fmt([radius,half_height]),group='3',density='0',rgba='0 0 0 0',contype='2',conaffinity='1',friction='.4 .001 .0001')
        coverage.append({'geom':'rotor_envelope_'+b['name'],'part':p['part'],'body':'base_link','radius_m':radius,'half_height_m':half_height,'method':'conservative_nonspinning_rotor_swept_envelope'})
    aero=json.loads((ROOT/'models/metadata/aerodynamics.json').read_text())
    for i,element in enumerate(aero['elements']):
        node=base if element['body']=='base_link' else base.find(f".//body[@name='{element['body']}']")
        ET.SubElement(node,'site',name='aero_'+str(i),pos=fmt(element['center_local_m']),size='.001',rgba='0 0 0 0')
    # IMU location selected with the provisional physical FC proxy.
    ET.SubElement(base,'site',name='imu',pos='0 0 .015',size='.003',rgba='0 0 0 0')
    gps=next(r for r in masses['parts'] if r['group']=='GPS')
    ET.SubElement(base,'site',name='gps_antenna',pos=fmt(np.array(gps['center_source_m'])-datum),size='.003',rgba='0 0 0 0')
    tilt=base.find(".//body[@name='cam_y_tilt']")
    cover=next(p for p in exp['parts'] if p['part']=='Body004')
    bb=np.array(cover['world_bbox_mm'])*.001
    center=(bb[:3]+bb[3:])/2
    # Cover is a YZ face. +X is optical forward. Move 1 mm outside the front
    # face to avoid placing the lens inside opaque cover geometry.
    lens=center.copy();lens[0]=bb[3]+.001
    R=np.column_stack(([0,-1,0],[0,0,1],[-1,0,0]))
    q=Rotation.from_matrix(R).as_quat();quat=[q[3],*q[:3]]
    ET.SubElement(tilt,'camera',name='onboard',pos=fmt(lens-origins['cam_y_tilt']),quat=fmt(quat),fovy='36.1')
    ET.SubElement(tilt,'site',name='optical_center',pos=fmt(lens-origins['cam_y_tilt']),size='.002',rgba='0 0 0 0')
    ET.SubElement(assets,'texture',name='ground_tex',type='2d',builtin='checker',width='512',height='512',rgb1='.16 .21 .25',rgb2='.23 .29 .32')
    ET.SubElement(assets,'material',name='ground_mat',texture='ground_tex',texrepeat='12 12',reflectance='.04')
    ET.SubElement(world,'geom',name='ground',type='plane',size='30 30 .1',material='ground_mat',friction='.9 .005 .0001')
    ET.SubElement(world,'light',pos='2 -3 6',dir='-1 1 -2',diffuse='.9 .9 .9',castshadow='true')
    # An open arch and staggered landmarks give the onboard view depth without
    # putting a solid wall directly in front of the lens.
    for name,pos,size,color in [('red_gate','10 -1.8 1.5','.12 .12 1.5','.58 .25 .19 1'),('gate_right','10 1.8 1.5','.12 .12 1.5','.58 .25 .19 1'),('gate_top','10 0 3','.12 1.92 .12','.58 .25 .19 1'),('blue_block','5 3 .6','.55 .55 .6','.12 .35 .65 1'),('yellow_block','8 -4 .8','.7 .5 .8','.75 .55 .12 1'),('green_block','15 2 .5','.7 .7 .5','.16 .5 .3 1'),('far_marker','21 -3 1','.3 .3 1','.38 .46 .55 1'),('near_block','-3 3 .35','.5 .5 .35','.23 .39 .48 1')]:
        ET.SubElement(world,'geom',name=name,type='box',pos=pos,size=size,rgba=color)
    for geom in world.findall('geom'):
        geom.set('contype','1');geom.set('conaffinity','2')
    ET.SubElement(world,'camera',name='overview',pos='3 -4 2.5',xyaxes='.8 .6 0 -.25 .33 .91',fovy='52')
    actuator=ET.SubElement(root,'actuator')
    for name in ('prop_1','prop_2','prop_3','prop_4','cam_x_pan','cam_y_tilt'):
        ET.SubElement(actuator,'motor',name='drive_'+name,joint=name,gear='1',ctrllimited='true',ctrlrange='-3 3' if name.startswith('prop') else '-.8 .8')
    sensor=ET.SubElement(root,'sensor')
    ET.SubElement(sensor,'accelerometer',name='imu_accel_FLU',site='imu')
    ET.SubElement(sensor,'gyro',name='imu_gyro_FLU',site='imu')
    ET.SubElement(sensor,'framequat',name='attitude_FLU',objtype='body',objname='base_link')
    ET.indent(root);path=ROOT/'models/flight.xml';ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    (ROOT/'models/metadata/camera_optics.json').write_text(json.dumps({'cover_center_source_m':center.tolist(),'optical_center_source_m':lens.tolist(),'optical_forward_zero_pose':[1,0,0],'fovy_deg':36.1,'lens_calibration_status':'manufacturer_ALLXF_D80Pro_wide_vertical_FOV_lens_center_from_CAD'},indent=2))
    (ROOT/'models/metadata/collision_coverage.json').write_text(json.dumps({'coverage':coverage,'mass_added_kg':0,'self_contacts':False,'limitations':['Per-part convex hulls fill concavities.','Rotor disk contacts represent a conservative strike/failure scenario, not blade fracture.']},indent=2))
    print('Wrote',path)
if __name__=='__main__':main()
