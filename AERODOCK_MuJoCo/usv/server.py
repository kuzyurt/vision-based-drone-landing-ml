"""Local web operator station. Simulation and all OpenGL calls share one thread."""
import argparse
import concurrent.futures
from contextlib import asynccontextmanager
import io
import json
import math
import queue
import threading
import time
from PIL import Image
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import Response,StreamingResponse,FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import mujoco
from .boat_sim import BoatSim,ROOT
from .world_render import WorldRenderer
from .rendering import update_wakes,upload_water,set_near


class Worker:
    def __init__(self):
        self.commands=queue.Queue(); self.frames={}; self.state={'ready':False}
        self.lock=threading.Lock(); self.stop=threading.Event(); self.thread=None
        self.view={'azimuth':140.,'elevation':-24.,'distance':4.1,'internals':False,'references':False,'underwater':False,'route':False}
        self.render_fps=12; self.camera_fps=6; self.video_enabled=True; self.water_animated=True
        self.frame_counts={'overview':0,'forward':0,'dock':0}

    def start(self):
        self.thread=threading.Thread(target=self.run,name='Boat simulation and renderer',daemon=True)
        self.thread.start()

    def command(self,name,args):
        future=concurrent.futures.Future()
        self.commands.put((name,args,future))
        try: return future.result(timeout=15)
        except concurrent.futures.TimeoutError: raise HTTPException(503,'Simulator is still loading or busy. Check the launch window.')
        except (ValueError,TypeError) as exc: raise HTTPException(409,str(exc))

    def dispatch(self,sim,name,args):
        allowed=('open_lid','close_lid','raise_platform','lower_platform','start_motor','stop_motor',
                 'set_motor_power','emergency_stop','reset_emergency_stop','set_environment','reset',
                 'add_cabin_water','set_drainage','new_world','new_path','manual_control','follow_path')
        if name in allowed: return getattr(sim,name)(**args)
        if name=='export_world':return sim.export_world()
        if name=='pause': sim.paused=bool(args.get('paused',True)); return sim.status()
        if name=='view':
            for key,value in args.items():
                if key in ('internals','references','underwater','route'): self.view[key]=bool(value)
                elif key in ('azimuth','elevation','distance'):
                    number=float(value)
                    if not math.isfinite(number): raise ValueError('View value must be finite')
                    self.view[key]=number
            self.view['elevation']=max(-85,min(-5,self.view['elevation']))
            self.view['distance']=max(1.8,min(180,self.view['distance']))
            return dict(self.view)
        if name=='quality':
            if 'fps' in args: self.render_fps=max(2,min(120,int(args['fps'])))
            if 'camera_fps' in args: self.camera_fps=max(1,min(120,int(args['camera_fps'])))
            if 'video' in args: self.video_enabled=bool(args['video'])
            if 'water' in args: self.water_animated=bool(args['water'])
            return {'fps':self.render_fps,'camera_fps':self.camera_fps,'video':self.video_enabled,'water':self.water_animated}
        raise ValueError('Unknown command: '+name)

    def run(self):
        renderer=None
        try:
            sim=BoatSim()
            sim.new_world(kind='island')
            scenery=WorldRenderer(sim.model,sim.config.get('scenery_radius_m',380))
            self.render_fps=sim.config['renderer_fps']; self.camera_fps=sim.config['camera_fps']
            render_error=None
            try:
                renderer=mujoco.Renderer(sim.model,height=sim.config['render_height'],width=sim.config['render_width'])
            except Exception as exc:
                render_error=str(exc)
            option=mujoco.MjvOption(); option.geomgroup[5]=0
            camera=mujoco.MjvCamera(); camera.type=mujoco.mjtCamera.mjCAMERA_FREE
            water=sim.model.geom('water_surface').id
            next_render=next_camera=next_water=0.
            budget=0.; last=time.perf_counter(); steps=0; physics_time=render_time=0.
            report_at=last;last_frame_counts=self.frame_counts.copy()
            while not self.stop.is_set():
                now=time.perf_counter()
                # Bound catch-up; report simulation rate when rendering is slow.
                budget=min(.12,budget+(now-last)); last=now
                while True:
                    try: name,args,future=self.commands.get_nowait()
                    except queue.Empty: break
                    try:
                        result=self.dispatch(sim,name,args)
                        future.set_result(result)
                    except Exception as exc: future.set_exception(exc)
                if sim.paused: budget=0
                nsteps=min(24,int(budget/sim.model.opt.timestep))
                if nsteps:
                    begin=time.perf_counter(); sim.step(nsteps)
                    physics_time+=time.perf_counter()-begin; steps+=nsteps
                    budget-=nsteps*sim.model.opt.timestep
                update_wakes(sim)
                if renderer and self.video_enabled and now>=next_render:
                    begin=time.perf_counter()
                    if self.water_animated and now>=next_water:
                        upload_water(sim,renderer)
                        next_water=now+1/sim.config['water_texture_fps']
                    option.geomgroup[2]=0 if self.view['internals'] else 1
                    option.geomgroup[3]=1
                    option.geomgroup[4]=int(self.view['references'])
                    camera.lookat[:]=sim.data.xpos[sim.boat]+[0,0,.35]
                    camera.azimuth=self.view['azimuth']; camera.elevation=self.view['elevation']; camera.distance=self.view['distance']
                    set_near(sim.model)
                    renderer.update_scene(sim.data,camera=camera,scene_option=option)
                    scenery.append(renderer.scene,sim.navigation.world,sim.data.xpos[sim.boat],self.view['route'],renderer)
                    renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=int(sim.config.get('render_shadows',False))
                    if self.view['underwater']:
                        for geom in renderer.scene.geoms[:renderer.scene.ngeom]:
                            if geom.objtype==mujoco.mjtObj.mjOBJ_GEOM and geom.objid==water: geom.rgba[3]=0
                    self.cache('overview',renderer.render())
                    next_render=now+1/self.render_fps
                    if now>=next_camera:
                        # Optical mesh parts remain exported and visible in the
                        # overview; filtering removes self-occluding glass/lens.
                        option.geomgroup[2]=1; option.geomgroup[3]=0; option.geomgroup[4]=0
                        set_near(sim.model,onboard=True)
                        for key,name in (('forward','NavigationCamera'),('dock','DockCamera')):
                            renderer.update_scene(sim.data,camera=name,scene_option=option)
                            scenery.append(renderer.scene,sim.navigation.world,sim.data.xpos[sim.boat],renderer=renderer)
                            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=int(sim.config.get('render_shadows',False))
                            self.cache(key,renderer.render())
                        next_camera=now+1/self.camera_fps
                    render_time+=time.perf_counter()-begin
                state=sim.status(); state.update(ready=True,view=self.view.copy(),render_error=render_error,scenery=scenery.status())
                if now-report_at>=1:
                    elapsed=now-report_at
                    self.perf={'physics_steps_per_second':round(steps/elapsed),'physics_ms_per_step':round(physics_time/max(steps,1)*1000,3),
                               'render_ms_per_second':round(render_time/elapsed*1000),'real_time_factor':round(steps*sim.model.opt.timestep/elapsed,2)}
                    self.perf['view_fps']={key:round((self.frame_counts[key]-last_frame_counts[key])/elapsed,1) for key in self.frame_counts}
                    last_frame_counts=self.frame_counts.copy()
                    steps=0; physics_time=render_time=0; report_at=now
                state['performance']=getattr(self,'perf',{})
                with self.lock: self.state=state
                self.stop.wait(.001)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            with self.lock: self.state={'ready':False,'error':str(exc)}
            while not self.commands.empty():
                _,_,future=self.commands.get_nowait(); future.set_exception(ValueError(str(exc)))
        finally:
            if renderer: renderer.close()

    def cache(self,name,pixels):
        image=Image.fromarray(pixels); output=io.BytesIO()
        image.save(output,'JPEG',quality=82,optimize=False)
        with self.lock:
            self.frames[name]=output.getvalue();self.frame_counts[name]+=1


worker=Worker()
@asynccontextmanager
async def lifespan(app):
    worker.start()
    yield
    worker.stop.set()
    if worker.thread: worker.thread.join(timeout=5)


app=FastAPI(title='AERODOCK operator station',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=ROOT/'web'),name='static')


@app.get('/')
def home(): return FileResponse(ROOT/'web/index.html')


@app.get('/api/status')
def status():
    with worker.lock: return dict(worker.state)


@app.get('/api/manifest')
def manifest(): return FileResponse(ROOT/'models/manifest.json')


@app.get('/api/world')
def world():
    return Response(json.dumps(worker.command('export_world',{})),media_type='application/json',
                    headers={'Content-Disposition':'attachment; filename="aerodock_world.json"'})


@app.post('/api/command/{name}')
async def command(name:str,request:Request):
    args=await request.json()
    if not isinstance(args,dict): raise HTTPException(422,'Expected a JSON object')
    # Do not block the asyncio loop while the simulation thread handles a command.
    import asyncio
    return await asyncio.to_thread(worker.command,name,args)


@app.get('/frame/{name}.jpg')
def frame(name:str):
    if name not in ('overview','forward','dock'): raise HTTPException(404,'Unknown camera')
    with worker.lock: data=worker.frames.get(name)
    if data is None: raise HTTPException(503,'Camera is loading')
    return Response(data,media_type='image/jpeg',headers={'Cache-Control':'no-store'})


@app.get('/stream/{name}')
def stream(name:str):
    if name not in ('overview','forward','dock'): raise HTTPException(404,'Unknown camera')
    def frames():
        last=None
        while not worker.stop.is_set():
            with worker.lock: data=worker.frames.get(name)
            if data and data is not last:
                yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(data)).encode()+b'\r\n\r\n'+data+b'\r\n'
                last=data
            worker.stop.wait(.04)
    return StreamingResponse(frames(),media_type='multipart/x-mixed-replace; boundary=frame',headers={'Cache-Control':'no-store'})


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    print('Open http://%s:%d in your browser.'%(args.host,args.port),flush=True)
    uvicorn.run(app,host=args.host,port=args.port,log_level='warning')


if __name__=='__main__': main()
