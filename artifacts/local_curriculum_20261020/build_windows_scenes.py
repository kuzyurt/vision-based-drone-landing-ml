"""New local basic/hard caches; assert original target/drone physical properties."""
import local_paths
from pathlib import Path
from copy import deepcopy
import ast,gc,hashlib,json,time,xml.etree.ElementTree as ET
import mujoco,numpy as np,psutil
from target_learning.scenes import compile_variant,add_boat,annotation_groups

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signature(model):
    result={}
    target=model.body('boat').id;drone=model.body('drone_base_link').id
    def belongs(body):
        while body:
            if body in [target,drone]:return True
            body=int(model.body_parentid[body])
        return False
    for i in range(model.nbody):
        if belongs(i):result['body:'+model.body(i).name]={n:np.asarray(getattr(model,'body_'+n)[i]).tolist() for n in ['pos','quat','mass','inertia','ipos','iquat']}
    for i in range(model.ngeom):
        if belongs(int(model.geom_bodyid[i])):result['geom:'+model.geom(i).name]={n:np.asarray(getattr(model,'geom_'+n)[i]).tolist() for n in ['type','size','pos','quat','contype','conaffinity','condim','friction','solref','solimp']}
    for i in range(model.njnt):
        if belongs(int(model.jnt_bodyid[i])):result['joint:'+model.joint(i).name]={n:np.asarray(getattr(model,'jnt_'+n)[i]).tolist() for n in ['type','pos','axis','limited','range']}
    result['options']={n:np.asarray(getattr(model.opt,n)).tolist()for n in ['timestep','gravity','integrator','iterations','cone','solver']}
    return result

def main():
    out=local_paths.ROOT/'models';out.mkdir(exist_ok=False);begin=time.monotonic()
    assert psutil.virtual_memory().available>2.5*1024**3,'Need free RAM to compile caches safely'
    model=mujoco.MjModel.from_binary_path(str(local_paths.REPO/'landing_training/build/combined_1000us.mjb'));original=signature(model);del model;gc.collect()
    basic=out/'basic';model=compile_variant(local_paths.REPO/'landing_training/build/combined_1000us.xml',basic,seed=440100,sun=True,distractors=True)
    assert signature(model)==original,'Basic changed original physical components';del model;gc.collect()
    template=local_paths.REPO/'artifacts/mujoco_target_discrimination_20261018/hard_scene_probe_v3.py'
    source=template.read_text();tree=ast.parse(source);functions={node.name:ast.get_source_segment(source,node)for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ['add_cross','compile_hard']}
    hard_source=functions['compile_hard'];needle="ROOT/'scene_cache_v2/seed_870000/scene.xml'";assert hard_source.count(needle)==1
    hard_source=hard_source.replace('def compile_hard(out):','def compile_hard(base_xml,out):').replace(needle,'Path(base_xml)')
    namespace=dict(ET=ET,mujoco=mujoco,np=np,deepcopy=deepcopy,add_boat=add_boat,annotation_groups=annotation_groups,Path=Path)
    exec(compile(functions['add_cross']+'\n'+hard_source,str(template),'exec'),namespace)
    hard=out/'hard';hard.mkdir();model=namespace['compile_hard'](basic/'scene.xml',hard)
    assert signature(model)==original,'Hard changed original physical components';del model;gc.collect()
    models={name:dict(mjb=str(path.resolve()),sha256=sha(path))for name,path in [('basic',basic/'scene.mjb'),('hard',hard/'hard_scene.mjb')]}
    receipt=dict(status='local_basic_hard_cache_physics_checks_passed',models=models,original_physical_records=len(original),original_signature_sha256=hashlib.sha256(json.dumps(original,sort_keys=True).encode()).hexdigest(),original_target_and_drone_unchanged=True,added_static_distractors_are_separate_collision_objects=True,source_scripts={str(template):sha(template),str(Path(__file__)):sha(__file__)},wall_s=time.monotonic()-begin,scope='Only these authored caches; no universal environment qualification')
    (out/'index.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))

if __name__=='__main__':main()
