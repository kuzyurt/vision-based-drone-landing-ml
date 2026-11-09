"""Bounded real MuJoCo physics/render/annotation/write workload, not a PX4 flight."""
import local_paths
from pathlib import Path
import argparse,hashlib,json,os,time,traceback,zlib
import mujoco,numpy as np,psutil

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--index',type=int,required=True);a=p.parse_args()
    out=Path(a.out);out.mkdir(exist_ok=True);me=psutil.Process();start=time.monotonic()
    def save(name,value):
        dest=out/f'{a.index}_{name}.json';tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(dest)
    renderer=None
    try:
        from landing_training import environment
        from landing_training.config import Scenario
        from windows_renderer import OnboardRenderer
        environment.compile_scene=lambda *args,**kwargs:mujoco.MjModel.from_binary_path(str(local_paths.REPO/'landing_training/build/combined_1000us.mjb'))
        env=environment.Environment(Scenario(name='windows_short_benchmark',seed=440000,world_seed=401,path_seed=501,distance=8.,height=6.,duration=20.))
        renderer=OnboardRenderer(env);rgb=renderer.onboard_image()
        save('ready',dict(pid=os.getpid(),startup_s=time.monotonic()-start,rss=me.memory_info().rss,unique_capture_scope='actual independent physics state and render; no teacher actions or PX4'))
        go=out/'GO.json';deadline=time.monotonic()+180
        while not go.exists():
            if (out/'STOP').exists():return
            if time.monotonic()>deadline:raise TimeoutError('Parent did not start measurement')
            time.sleep(.025)
        instruction=json.loads(go.read_text());frames=0;size=0;rss=me.memory_info().rss;begin=time.monotonic();samples=[]
        with (out/f'{a.index}_capture_proof.jsonl').open('w') as proof:
            while time.time()<instruction['finish_unix'] and not(out/'STOP').exists():
                for _ in range(40):env.step(False)
                rgb=renderer.onboard_image();uid=hashlib.sha256(rgb.tobytes()).hexdigest()
                renderer.onboard.enable_segmentation_rendering()
                try:seg=renderer.onboard_image()
                finally:renderer.onboard.disable_segmentation_rendering()
                assert rgb.shape==(360,640,3) and seg.shape==(360,640,2)
                # Exact offline per-geom segmentation, never supplied to an actor.
                ids,count=np.unique(seg[...,0],return_counts=True)
                encoded=zlib.compress(rgb.tobytes(),1);size+=len(encoded)
                proof.write(json.dumps(dict(capture_s=float(env.data.time),rgb_sha256=uid,segmentation_pixels=dict(zip(map(str,ids.tolist()),count.tolist()))))+'\n')
                if frames==0:
                    from PIL import Image
                    Image.fromarray(rgb).save(out/f'{a.index}_actual_rgb.jpg')
                frames+=1;rss=max(rss,me.memory_info().rss)
        save('result',dict(status='completed',frames=frames,wall_s=time.monotonic()-begin,simulated_s=float(env.data.time),peak_rss=rss,compressed_bytes_processed=size,startup_s=json.loads((out/f'{a.index}_ready.json').read_text())['startup_s'],px4_flight=False,teacher_data=False))
    except BaseException as e:
        save('error',dict(error=repr(e),traceback=traceback.format_exc()));raise
    finally:
        if renderer is not None:renderer.close()

if __name__=='__main__':main()

