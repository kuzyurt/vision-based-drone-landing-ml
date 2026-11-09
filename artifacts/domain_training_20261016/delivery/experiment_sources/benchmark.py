"""One prepared pool; 20 wall seconds per worker count, actual RGB/HDF5 path."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE))

def worker(i,pipe):
    px4=renderer=writer=None
    try:
        import numpy as np
        from dataclasses import asdict
        import fast_physics;fast_physics.install()
        import domain_visuals;domain_visuals.install()
        from landing_training.config import Scenario
        from landing_training.environment import Environment
        from landing_training.expert import Expert,Beacon,pad_visibility
        from landing_training.px4 import NativePX4
        from landing_training.rendering import ReviewRenderer
        from landing_training.recording import Recorder
        case=Scenario(name=f'bench_{i}',kind='beach',world_seed=402,path_seed=502,seed=700+i,
                      distance=3.,height=3.,boat_speed=.35,wave_height=.03,wind_profile='breeze',duration=180.)
        env=Environment(case);env.boat.navigation.manual();directory=ROOT/'benchmark'/f'worker_{i}';directory.mkdir(parents=True)
        px4=NativePX4(env,directory/'px4',40+i,flight_logging=False);expert=Expert(env);beacon=Beacon(case.seed+40);px4.start()
        for tick in range(int(env.preparation_budget_s*25)):
            if tick>125 and tick%50==0 and not px4.armed:px4.arm_offboard()
            px4.send_action(expert.prepare(px4));px4.advance()
            if px4.was_airborne and px4.armed and abs(env.vertical_clearance-case.height)<.15 and np.linalg.norm(env.drone.velocity)<.3:break
        else:raise RuntimeError('Benchmark preparation failed')
        renderer=ReviewRenderer(env,overview=False);renderer.onboard_image()
        pipe.send(dict(ready=True,pid=os.getpid(),worker=i))
        while True:
            command=pipe.recv()
            if command['kind']=='stop':break
            count=command['count'];start=command['start'];stop=start+command['seconds']
            writer=Recorder(directory/f'count_{count}',asdict(case),'review')
            while time.monotonic()<start:time.sleep(.005)
            frames=0
            while time.monotonic()<stop:
                rgb=renderer.onboard_image();visible,pixels=pad_visibility(env);packet=beacon.sample(env,px4)
                action=expert.prepare(px4)
                row=dict(frame_index=frames,time_s=float(env.data.time),role='review',phase='throughput_hover',outcome=env.outcome,
                         observation=dict(px4=px4.observation(),beacon=packet,gimbal_rad=env.data.qpos[env.drone.camera_qpos].tolist()),
                         privileged=dict(pad_visible=visible,pad_keypoints_px=pixels),output=dict(executed_action=action.tolist()))
                writer.append(rgb,row);px4.send_action(action);px4.advance();frames+=1
            ended=time.monotonic();writer.close();writer=None
            pipe.send(dict(worker=i,frames=frames,elapsed_s=ended-start,end=ended))
    except BaseException as e:
        import traceback
        pipe.send(dict(worker=i,error=f'{type(e).__name__}: {e}',traceback=traceback.format_exc()))
    finally:
        if writer:writer.close()
        if renderer:renderer.close()
        if px4:px4.close()
        pipe.close()

def main():
    (ROOT/'benchmark').mkdir(exist_ok=False)
    context=mp.get_context('spawn');processes=[];pipes=[]
    for i in range(16):
        parent,child=context.Pipe();p=context.Process(target=worker,args=(i,child));p.start();child.close();pipes.append(parent);processes.append(p)
    try:
        ready=[]
        for pipe in pipes:
            if not pipe.poll(600):raise TimeoutError('Worker initialization timeout')
            r=pipe.recv();ready.append(r)
            if 'error' in r:raise RuntimeError(r)
        (ROOT/'benchmark/ready.json').write_text(json.dumps(ready,indent=2));print('ALL_WORKERS_READY',flush=True)
        results=[]
        for count in [4,8,12,16]:
            start=time.monotonic()+1.
            for pipe in pipes[:count]:pipe.send(dict(kind='measure',count=count,start=start,seconds=20.))
            measured=[pipe.recv() for pipe in pipes[:count]]
            if any('error' in r for r in measured):raise RuntimeError(measured)
            elapsed=max(r['end'] for r in measured)-start;frames=sum(r['frames'] for r in measured)
            r=dict(workers=count,wall_s=elapsed,frames=frames,aggregate_fps=frames/elapsed,per_worker_fps=frames/elapsed/count,workers_detail=measured)
            results.append(r);(ROOT/'benchmark/results.json').write_text(json.dumps(results,indent=2));print('BENCHMARK',json.dumps(r),flush=True)
        best=max(results,key=lambda r:r['aggregate_fps'])
        report=dict(status='completed',best_workers=best['workers'],best_aggregate_fps=best['aggregate_fps'],counts=results,
                    scope='20 measured wall seconds per count after preparation; FP64 optimized physics, varied sky/water, onboard 640x360 RGB, real native PX4 and LZF HDF5 writes',initialization_excluded=True)
        (ROOT/'benchmark/report.json').write_text(json.dumps(report,indent=2));print('BENCHMARK_COMPLETE',json.dumps(report),flush=True)
    finally:
        for pipe in pipes:
            try:pipe.send(dict(kind='stop'))
            except:pass
        for p in processes:
            p.join(30)
            if p.is_alive():p.terminate();p.join(10)

if __name__=='__main__':main()
