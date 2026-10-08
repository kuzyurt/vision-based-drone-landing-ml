"""Mass ledger: published assembly totals, exact CAD distributions, flagged estimates.

Never substitutes shipping weights or counts coincident motor overlays twice.
"""
import csv
import json
from pathlib import Path
import numpy as np
from make_viewer import unique_parts
ROOT=Path(__file__).resolve().parents[1]
DATUM=np.array([-19.5,100.,115.])*1e-3
def box_unit(size):
    x,y,z=np.maximum(size,1e-4)
    return np.diag([(y*y+z*z)/12,(x*x+z*z)/12,(x*x+y*y)/12])
def combine(items):
    mass=sum(r['mass_kg'] for r in items)
    center=sum(r['mass_kg']*np.array(r['center_source_m']) for r in items)/mass
    tensor=np.zeros((3,3))
    for r in items:
        d=np.array(r['center_source_m'])-center
        tensor+=np.array(r['inertia_kg_m2'])+r['mass_kg']*(np.eye(3)*np.dot(d,d)-np.outer(d,d))
    if np.linalg.eigvalsh(tensor).min()<=0:raise ValueError('Invalid body inertia')
    return dict(mass_kg=mass,center_source_m=center.tolist(),inertia_kg_m2=tensor.tolist())
def main():
    exp=json.loads((ROOT/'models/metadata/export.json').read_text())
    cad=json.loads((ROOT/'models/metadata/cad_mass_properties.json').read_text())
    mats=json.loads((ROOT/'models/metadata/materials.json').read_text())
    parts=list(unique_parts(exp['parts']))
    rows=[]
    for p in parts:
        c=cad[p['part']]
        bb=p['world_bbox_mm']
        if bb is None:
            # Wire-only drawing/artwork is not an independent physical object.
            rows.append(dict(part=p['part'],label=p['label'],body=p['body'],mass_kg=0.,status='nonphysical_wire_artwork',center_source_m=[0,0,0],inertia_kg_m2=np.zeros((3,3)).tolist(),group='wire_artwork'))
            continue
        size=(np.array(bb[3:])-bb[:3])*1e-3
        center=np.array(c.get('center_mm',p['world_centre']))*1e-3
        unit=np.array(c.get('unit_inertia_m2',box_unit(size)))
        if np.linalg.eigvalsh(unit).min()<=0 or np.max(unit)>1:
            unit=box_unit(size)
        material=mats['assignments'][p['part']]['material']
        density=mats['palette'][material]['density_gcm3']
        # The old appearance map assigned steel/aluminum to carbon landing
        # tubes and molded connectors. Appearance isn't evidence of density.
        # Maker identifies these families; exact resin/fiber loading is unknown.
        physical_material=material
        if p['target']=='Solid003':physical_material='carbon_fiber_landing_tube';density=1.55
        if p['target'] in ('Solid002','Solid004','Solid007','Solid012','Solid013','Solid014','Solid015','Solid024'):
            physical_material='fiber_reinforced_nylon_connector';density=1.35
        if p['target']=='Solid025':physical_material='silicone_ring';density=1.10
        volume=c['volume_mm3']
        mass=volume*density*1e-6 # mm3 x g/cm3 -> kg
        status='CAD_volume_with_inferred_material_density'
        group='frame_mechanical'
        if p['body']=='camera_mount':group='camera_mount'
        elif p['body']=='cam_x_pan':group='camera_pan'
        elif p['body']=='cam_y_tilt':group='camera_tilt'
        elif p['body'].startswith('prop_'):group=p['body'];mass=.0125;status='manufacturer_total'
        elif p['part']=='Body005':group='battery';mass=.465;status='manufacturer_total'
        elif p['part'].startswith('LinkGroup015'):group='khadas_edge2'
        elif p['part']=='xiao_esp32s3_v3_with_pins':group='xiao_esp32s3';mass=.006;status='provisional_installed_board_estimate_3_to_12_g'
        elif p['target']=='Solid022':group='motor';mass=.064;status='manufacturer_total_KV920_variant_CAD_says_KV880'
        elif 'LinkGroup004' in p['part']:group='power_module_pm06'
        if mass<=0:
            # Open-shell / mesh fallback only weights allocation within a
            # published whole assembly. It is never an asserted measurement.
            mass=max(float(np.prod(size))*density*1000,1e-7)
            status='open_geometry_box_distribution_estimate'
        rows.append(dict(part=p['part'],label=p['label'],body=p['body'],group=group,material=material,physical_material=physical_material,inferred_density_g_cm3=density,mass_kg=mass,status=status,inertia_method='CAD_solid_uniform_density' if c.get('unit_inertia_m2') else 'bounding_box_estimate',center_source_m=center.tolist(),unit_inertia_m2=unit.tolist()))
    # Preserve the camera's user-provided 400 g sum. Subassembly splits need
    # weighing. Pan is deliberately heavier, as requested by the owner.
    budgets={'camera_mount':.080,'camera_pan':.180,'camera_tilt':.140,'khadas_edge2':.025,'power_module_pm06':.024}
    for group,total in budgets.items():
        members=[r for r in rows if r['group']==group]
        raw=sum(r['mass_kg'] for r in members)
        assert raw>0,group
        for r in members:
            r['mass_kg']*=total/raw
            r['status']='user_400g_total_provisional_subassembly_allocation' if group.startswith('camera') else 'manufacturer_total_CAD_distribution'
    for r in rows:
        if 'unit_inertia_m2' in r:r['inertia_kg_m2']=(r['mass_kg']*np.array(r.pop('unit_inertia_m2'))).tolist()
    def proxy(name,mass,center,size,status,group):
        rows.append(dict(part=name,label=name,body='base_link',group=group,mass_kg=mass,status=status,inertia_method='unrepresented_hardware_box_estimate',center_source_m=list(center),inertia_kg_m2=(mass*box_unit(np.array(size))).tolist()))
    # Required X500 propulsion and control components absent from the CAD.
    for b in exp['bodies']:
        if b['name'].startswith('prop_'):
            hub=np.array(b['origin'])*1e-3
            proxy('ESC_'+b['name'],.021,DATUM+.52*(hub-DATUM)+[0,0,-.020],[.026,.014,.005],'manufacturer_mass_provisional_under_arm_position','ESC')
    proxy('Pixhawk_6C_plastic',.0346,DATUM+[0,0,.015],[.0848,.044,.0124],'manufacturer_mass_provisional_between_plates_position','flight_controller')
    tray=next(p for p in parts if p['target']=='Solid036')
    proxy('GPS_M10_V1',.032,np.array(tray['world_centre'])*1e-3+[0,0,.009],[.05,.05,.0144],'manufacturer_mass_provisional_mount_position','GPS')
    proxy('SiK_onboard_radio',.0235,DATUM+[-.05,0,.010],[.025,.050,.012],'manufacturer_mass_provisional_position','telemetry')
    # Cables already included in motor/ESC totals are excluded here.
    proxy('extra_payload_wires_regulator',.015,DATUM+[.02,0,-.005],[.04,.04,.01],'provisional_extra_payload_wiring_estimate_5_to_30_g','payload_wiring')
    bodies={b['name']:combine([r for r in rows if r['body']==b['name'] and r['mass_kg']>0]) for b in exp['bodies']}
    total=combine([r for r in rows if r['mass_kg']>0])
    totals={g:sum(r['mass_kg'] for r in rows if r['group']==g) for g in sorted(set(r['group'] for r in rows))}
    assert abs(sum(totals[g] for g in ('camera_mount','camera_pan','camera_tilt'))-.4)<1e-12
    assert len([r for r in rows if r['group']=='motor'])==4
    out={'source_sha256':exp['sha256'],'calibration_status':'PROVISIONAL_NOT_VALIDATED_FOR_REAL_FLIGHT_TRANSFER','datum_source_m':DATUM.tolist(),'camera_mass_split_g':{'fixed':80,'pan':180,'tilt':140},'groups_kg':totals,'whole_assembly_zero_pose':total,'bodies':bodies,'parts':rows,'excluded_duplicate_instances':[p['part'] for p in exp['parts'] if p['part'] not in {q['part'] for q in parts}], 'notes':['610 g manufacturer frame/ARF scope is unresolved; no extra 610 g is added. Frame parts use CAD volumes and inferred material densities.','CAD camera open surfaces use box inertia. Hidden motors/electronics and actual mass split require measurement.','CAD PM06 is modeled at 24 g; current stock kit instead uses PM02 V3 at 20 g.','KV920 manufacturer thrust table is a selected scenario; CAD motor labels say KV880. Confirm physical motors.','Unrepresented ESC/controller/GPS/radio placement is provisional. Verify against installed hardware.','XIAO and extra payload wiring masses are explicit estimates, not published data.']}
    (ROOT/'models/metadata/mass_model.json').write_text(json.dumps(out,indent=2))
    with (ROOT/'docs/component_masses.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['instance','label','group','body','mass_g','evidence','inertia_method','center_x_m','center_y_m','center_z_m'])
        for r in rows:w.writerow([r['part'],r['label'],r['group'],r['body'],r['mass_kg']*1000,r['status'],r.get('inertia_method','none'),*r['center_source_m']])
    print(json.dumps({'mass_kg':total['mass_kg'],'groups_kg':totals,'center_FLU_m':(np.array(total['center_source_m'])-DATUM).tolist()},indent=2))
if __name__=='__main__':main()
