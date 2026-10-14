"""Export existing physical CAD and coefficients for the static browser build."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'simulation'))
import json, shutil, hashlib
import gzip,tempfile
import numpy as np
import mujoco
import server
from sim.propulsion import THROTTLE, OMEGA, THRUST, TORQUE, CURRENT

out=server.GAME_DIR/'app/public/landing/physics'
out.mkdir(parents=True,exist_ok=True)
source=mujoco.MjModel.from_binary_path(str(server.RUNTIME/'physics-base.mjb'))
spec=mujoco.MjSpec.from_file(str(server.RUNTIME/'physics-base-linux.xml'))
for geom in list(spec.geoms):
    gid=mujoco.mj_name2id(source,mujoco.mjtObj.mjOBJ_GEOM,geom.name)
    if gid>=0 and geom.name!='water_surface' and not geom.name.startswith('shore_contact_') and source.geom_contype[gid]==0 and source.geom_conaffinity[gid]==0:
        spec.delete(geom)
    else:
        geom.material=''
used={geom.meshname for geom in spec.geoms if geom.meshname}
for mesh in list(spec.meshes):
    if mesh.name not in used:
        spec.delete(mesh)
    else:
        original=Path(mesh.file)
        target=out/(mesh.name+original.suffix)
        shutil.copyfile(original,target)
        mesh.file=target.name
for material in list(spec.materials):spec.delete(material)
for texture in list(spec.textures):spec.delete(texture)
spec.modelfiledir=str(out)
model=spec.compile()
for attr in ('body_mass','body_inertia','body_ipos','body_iquat','jnt_axis'):
    assert np.array_equal(getattr(source,attr),getattr(model,attr)),attr
model.opt.timestep=.001
# Preserve source decimal precision: MjSpec.to_xml() rounds physical values.
import xml.etree.ElementTree as ET
xml=ET.parse(server.RUNTIME/'physics-base-linux.xml')
for mesh in xml.getroot().find('asset').findall('mesh'):
    source=Path(mesh.get('file'));mesh.set('file',mesh.get('name')+source.suffix)
xml.write(out/'vehicles.xml',encoding='unicode')
meta=json.loads((server.RUNTIME/'live-map.json').read_text())
heights=np.fromfile(server.RUNTIME/'live-heights.bin',dtype='<f4')
env=server.GameEnvironment(model,meta,heights,visual_layout=json.loads((server.RUNTIME/'visual-layout.json').read_text()))
u,b,n,d=env.drone,env.boat,env.native,env.data
config={'version':1,'mujoco_version':mujoco.__version__,'px4_revision':'6ea3539157ca358c70a515878b77077af7d4611d',
    'files':['vehicles.xml']+[mesh.file for mesh in spec.meshes],
    'tables':{key:value.tolist() for key,value in {'throttle':THROTTLE,'omega':OMEGA,'thrust':THRUST,'torque':TORQUE,'current':CURRENT}.items()},
    'drone':{key:(getattr(u,key).tolist() if isinstance(getattr(u,key),np.ndarray) else getattr(u,key))
        for key in ('base','free_qadr','free_vadr','props','hubs','rotor_dofs','rotor_I','rotor_radii','motor_act','camera_act','camera_dofs','camera_qpos','aero','aero_bodies','aero_sites')},
    'boat':{'config':b.config,'body':b.boat,'free_qadr':b.free_qadr,'free_vadr':b.free_vadr,
        'cells':b.cells_local.tolist(),'bottom':b.bottom.tolist(),'top':b.top.tolist(),'area':b.area.tolist(),
        'waves':n.waves.tolist(),'current':b.current.tolist(),'act':b.act,'qadr':b.qadr,'joints':b.joints,
        'mass':b.mass,'gravity':b.gravity,'prop_sites':b.prop_sites,'prop_dofs':b.prop_dofs,
        'lift_mass':n.lift_mass,'lift_dof':n.lift_dof},
    'qpos_initial':d.qpos.tolist(),'qvel_initial':d.qvel.tolist(),'eq_active_initial':d.eq_active.tolist(),
    'dof_damping_initial':model.dof_damping.tolist(),
    'geom_contype_initial':model.geom_contype.tolist(),'geom_conaffinity_initial':model.geom_conaffinity.tolist(),
    'geom_names':[model.geom(i).name for i in range(model.ngeom)],
    'visual_layout':env.geom_transforms(),'route':env.world.route.export(),
    'coastline':[[float(p[0]),float(-p[1])] for p in env.world.coast[:-1:8]],
    'gps_site':model.site('drone_gps_antenna').id,'platform_body':env.platform_body,'pad_site':env.pad_site,
    'imu_sensors':{name:int(model.sensor('drone_'+name).adr[0]) for name in ('imu_accel_FLU','imu_gyro_FLU')},
    'hull_geom':model.geom('hull_contact').id,'cameras':{name:model.camera(camera).id for name,camera in [('drone','drone_onboard'),('boat_nav','NavigationCamera'),('boat_dock','DockCamera')]},
    'bodies':[[model.body(i).name,int(i)] for i in env.visual_bodies],
    'rotor_geoms':{model.geom(gid).name:index for gid,index in u.rotor_geoms.items()},
    'parameters':json.loads((server.DRONE/'build/px4_configuration.json').read_text())['parameters']}
config['asset_sha256']={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in config['files']}
(out/'configuration.json').write_text(json.dumps(config,separators=(',',':'),default=lambda v:v.tolist() if hasattr(v,'tolist') else int(v)),encoding='utf-8')
seed=np.random.PCG64(714).state['state'];config['rng_state']={key:str(value) for key,value in seed.items()}
(out/'configuration.json').write_text(json.dumps(config,separators=(',',':'),default=lambda v:v.tolist() if hasattr(v,'tolist') else int(v)),encoding='utf-8')
binary=Path(tempfile.gettempdir())/'tidewater-browser-physics.mjb'
mujoco.mj_saveModel(model,str(binary),None)
with binary.open('rb') as original, gzip.open(server.GAME_DIR/'wasm/tests/vehicles.mjb.gz','wb',compresslevel=6) as compressed:
    shutil.copyfileobj(original,compressed)
binary.unlink()
print('Browser physics assets:',out,'collision meshes:',len(used),'model bytes:',mujoco.mj_sizeModel(model))
