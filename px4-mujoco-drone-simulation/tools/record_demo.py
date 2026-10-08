"""Record genuine MuJoCo/PX4 hover footage over the flight-lab protocol.

No synthetic flight frames: the only composition adds a small live-camera
inset and a caption to JPEGs from the two simulator renderers.
"""
import argparse,asyncio,base64,io,json,time
from pathlib import Path
import aiohttp
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]

async def main(preview=False,still=False,closeup_only=False):
    async with aiohttp.ClientSession() as client,client.ws_connect('http://127.0.0.1:8793/ws') as ws:
        state={};images={}
        async def read():
            nonlocal state,images
            message=await asyncio.wait_for(ws.receive(),10)
            payload=message.json();state=payload['telemetry'];images=payload.get('images',{})
        async def send(keys=(),action=None,**extra):await ws.send_json({'keys':list(keys),'action':action,**extra})
        async def wait(predicate,timeout=70):
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                await send();await read()
                if predicate(state):return
            raise RuntimeError(state)
        async def hold(keys,seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:await send(keys);await read()
            await send()
        await wait(lambda s:s.get('ready'))
        if not state.get('armed'):
            await send(environment={'profile':'calm','seed':714,'direction_deg':90})
            await wait(lambda s:s.get('environment',{}).get('profile')=='calm')
            await send(action='takeoff')
            await wait(lambda s:s.get('armed') and abs(s['height_m']-1.5)<.05 and abs(s['velocity_m_s'][2])<.06)
        await send(action='camera_reset',view={'distance':.65,'azimuth':195,'elevation':14,'focus':'gimbal'})
        await hold([],1.)
        if still:
            world=Image.open(io.BytesIO(base64.b64decode(images['world']))).convert('RGB')
            camera=Image.open(io.BytesIO(base64.b64decode(images['camera']))).convert('RGB').resize((224,126))
            canvas=Image.new('RGB',(800,478),'#0b1015');canvas.paste(world,(0,28));canvas.paste(camera,(562,338))
            draw=ImageDraw.Draw(canvas)
            try:font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
            except OSError:font=ImageFont.load_default()
            draw.text((14,5),'X500 V2 / PX4 + MuJoCo / live camera',fill='#cee3e4',font=font)
            draw.rectangle((561,337,787,465),outline='#91c8be',width=1)
            canvas.save(ROOT/'media/flight-lab.png')
            await send(action='hover',view={'distance':2.,'azimuth':135,'elevation':-24,'focus':'aircraft'})
            print('Saved full-color flight-lab still',flush=True);return
        await hold(['ArrowRight','ArrowDown'],.8)
        await hold([],1.)
        image=Image.open(io.BytesIO(base64.b64decode(images['world'])))
        image.save(ROOT/'build/low-angle-preview.png')
        print('Low-angle preview, camera pose',state['pan_deg'],state['tilt_deg'],flush=True)
        if preview:return
        try:font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
        except OSError:font=ImageFont.load_default()
        records=[]
        async def capture(name,seconds,commands,caption,inset=False,wind_stages=None):
            wind_stages=wind_stages or [('calm',90),('steady6',90),('steady2',90),('steady8',90)]
            frames=[];durations=[];timeline=[];start=time.monotonic();last=start;stage=-1
            while time.monotonic()-start<seconds:
                elapsed=time.monotonic()-start;keys,action=commands(elapsed)
                next_stage=min(len(wind_stages)-1,int(elapsed/(seconds/len(wind_stages))))
                if next_stage!=stage:
                    stage=next_stage
                    profile,direction=wind_stages[stage]
                    await send(environment={'profile':profile,'seed':714,'direction_deg':direction})
                await send(keys,action);await read()
                profile,direction=wind_stages[stage]
                if state['environment']['profile']!=profile or state['environment']['direction_deg']!=direction:continue
                assert state.get('armed') and not any(state.get('failed_rotors',[])),state
                world=Image.open(io.BytesIO(base64.b64decode(images['world']))).convert('RGB')
                canvas=Image.new('RGB',(800,478),'#0b1015');canvas.paste(world,(0,28))
                speed=sum(v*v for v in state['environment']['velocity_m_s'])**.5
                toward={0:'E',90:'N',180:'W',270:'S'}.get(direction,str(direction)+'deg')
                draw=ImageDraw.Draw(canvas);draw.text((14,5),caption+f'  /  WIND {speed:.0f} m/s toward {toward}',fill='#cee3e4',font=font)
                if inset:
                    camera=Image.open(io.BytesIO(base64.b64decode(images['camera']))).convert('RGB').resize((224,126))
                    canvas.paste(camera,(562,338));draw.rectangle((561,337,787,465),outline='#91c8be',width=1)
                now=time.monotonic();durations.append(max(60,int((now-last)*1000)));last=now
                frames.append(canvas.convert('P',palette=Image.Palette.ADAPTIVE,colors=128))
                timeline.append({'height_m':state['height_m'],'position_m':state['position_m'],'pan_deg':state['pan_deg'],'tilt_deg':state['tilt_deg'],'wind_profile':state['environment']['profile'],'wind_direction_deg':direction,'wind_m_s':state['environment']['velocity_m_s'],'sim_time_s':state['sim_time_s']})
            await send()
            (ROOT/'media').mkdir(exist_ok=True)
            frames[0].save(ROOT/'media'/name,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True,disposal=2)
            if inset:canvas.save(ROOT/'media/flight-lab.png')
            records.append({'file':name,'frames':len(frames),'wall_duration_s':sum(durations)/1000,'timeline':timeline})
            print('Recorded',name,len(frames),'frames',flush=True)
        def closeup(elapsed):
            if elapsed<1.3:return [],None
            if elapsed<2.1:return ['ArrowLeft','ArrowUp'],None
            if elapsed<2.4:return [],'camera_reset'
            return [],None
        await capture('gimbal-closeup.gif',20.,closeup,'D-80Pro / low-angle hover',True,
                      [('calm',90),('steady10',90),('steady10',270),('steady10',0),('steady10',180)])
        if closeup_only:
            previous=json.loads((ROOT/'media/capture.json').read_text())
            previous['clips']=[records[0]]+[c for c in previous['clips'] if c['file']!='gimbal-closeup.gif']
            previous['environment']=state['environment']
            (ROOT/'media/capture.json').write_text(json.dumps(previous,indent=2))
            await send(action='hover',view={'distance':2.,'azimuth':135,'elevation':-24,'focus':'aircraft'})
            return
        await send(action='camera_reset',view={'distance':3.6,'azimuth':135,'elevation':-18,'focus':'aircraft'})
        await hold([],1.)
        def wide(elapsed):
            if 1<elapsed<2.5:return ['KeyW'],None
            if 3<elapsed<4:return ['KeyA'],None
            if 4.8<elapsed<6:return ['KeyS'],None
            if 6.3<elapsed<7.3:return ['KeyD'],None
            return [],None
        await capture('flight-wide.gif',16.,wide,'X500 V2 / PX4 + MuJoCo / crosswind steps')
        (ROOT/'media/capture.json').write_text(json.dumps({'source':'actual_MuJoCo_renderer_frames_native_PX4_SITL','environment':state['environment'],'camera_closeup':{'distance_m':.65,'azimuth_deg':195,'elevation_deg':14,'focus':'gimbal'},'clips':records},indent=2))
        await send(action='hover',view={'distance':2.,'azimuth':135,'elevation':-24,'focus':'aircraft'})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true');parser.add_argument('--still',action='store_true');parser.add_argument('--closeup-only',action='store_true');args=parser.parse_args();asyncio.run(main(args.preview,args.still,args.closeup_only))
