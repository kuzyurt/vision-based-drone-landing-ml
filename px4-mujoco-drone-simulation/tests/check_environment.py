"""Independent physical invariants and CAD collision coverage checks."""
import json,sys
import xml.etree.ElementTree as ET
from pathlib import Path
import mujoco
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim.environment import Wind,directional_drag

def main():
    # Reproducibility is essential for comparing ML runs and reset episodes.
    first=Wind('gusty',123);second=Wind('gusty',123);other=Wind('gusty',124)
    a=np.array([first.step(i*.001,.001).copy() for i in range(5000)])
    b=np.array([second.step(i*.001,.001).copy() for i in range(5000)])
    c=np.array([other.step(i*.001,.001).copy() for i in range(5000)])
    assert np.array_equal(a,b) and not np.array_equal(a,c)
    first.reset();assert np.array_equal(first.step(0,.001),a[0])
    assert all(np.array_equal(Wind('calm',s).step(0,.001),np.zeros(3)) for s in (1,2,9))
    for speed in (-10.,-2.,0.,2.,10.):
        force=directional_drag(speed,.025,1.225,1.)
        assert force*speed<=0
        assert abs(abs(force)-.5*1.225*.025*speed**2)<1e-12
        assert abs(directional_drag(2*speed,.025)-4*force)<1e-12
    fixture=ET.parse(ROOT/'models/flight.xml').getroot()
    fixture.find('compiler').set('meshdir',str(ROOT/'models/flight_meshes'))
    fixture.find('compiler').set('texturedir',str(ROOT/'models/textures'))
    probe=ET.SubElement(fixture.find('worldbody'),'body',name='contact_probe',mocap='true',pos='10 10 10')
    ET.SubElement(probe,'geom',name='probe_box',type='box',size='.01 .01 .01',contype='1',conaffinity='2')
    model=mujoco.MjModel.from_xml_string(ET.tostring(fixture,encoding='unicode'))
    data=mujoco.MjData(model);data.qpos[2]=2.;mujoco.mj_forward(model,data)
    mass=json.loads((ROOT/'models/metadata/mass_model.json').read_text())
    assert abs(model.body_mass.sum()-mass['whole_assembly_zero_pose']['mass_kg'])<1e-12
    coverage=json.loads((ROOT/'models/metadata/collision_coverage.json').read_text())['coverage']
    assert len(coverage)==303
    tested=[]
    selected=[next(c for c in coverage if c['part']==part) for part in ('CombinedShell','Shell003','Body004','Body005','LinkGroup005__Solid003','LinkGroup005__LinkGroup__Solid012','LinkGroup005__LinkGroup__Solid022')]
    selected += [c for c in coverage if c['method'].startswith('conservative_')]
    obstacle=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'probe_box')
    for entry in selected:
        geom=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,entry['geom'])
        assert model.geom_contype[geom]==2 and model.geom_conaffinity[geom]==1
        data.mocap_pos[0]=data.geom_xpos[geom]+[.002,.003,.001]
        mujoco.mj_forward(model,data)
        pairs=[{int(c.geom1),int(c.geom2)} for c in data.contact[:data.ncon]]
        assert {geom,obstacle} in pairs,(entry['geom'],data.geom_xpos[geom].tolist(),data.geom_xpos[obstacle].tolist(),float(mujoco.mj_geomDistance(model,data,geom,obstacle,10,None)),pairs)
        tested.append(entry['part'])
    report={'passed':True,'seed_reproducible':True,'reset_repeats_wind':True,'quadratic_dissipative_drag':True,
            'collision_geoms':len(coverage),'obstacle_contact_parts_tested':tested,'mass_unchanged_kg':float(model.body_mass.sum()),
            'scope':'integration_and_physical_invariants_not_airframe_validation'}
    (ROOT/'build').mkdir(exist_ok=True);(ROOT/'build/environment_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
