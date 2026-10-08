"""Exercise the local UI protocol against real PX4, with no hardware link."""
import asyncio
import json
import math
from pathlib import Path
import aiohttp
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
async def main():
    async with aiohttp.ClientSession() as client:
        async with client.ws_connect('http://127.0.0.1:8793/ws') as ws:
            state={};camera_samples=[];images={}
            async def update():
                nonlocal state,images
                message=await asyncio.wait_for(ws.receive(),5)
                if message.type!=aiohttp.WSMsgType.TEXT:raise RuntimeError(str(message))
                data=message.json();state=data['telemetry'];images=data.get('images',{})
                return state
            async def send(keys=(),action=None):await ws.send_json({'keys':list(keys),'action':action})
            async def wait_for(predicate,seconds=50):
                until=asyncio.get_running_loop().time()+seconds
                while asyncio.get_running_loop().time()<until:
                    await send();await update()
                    if predicate(state):return state.copy()
                raise AssertionError(('timeout',state))
            await wait_for(lambda s:s.get('ready') and s.get('sim_time_s',0)>8)
            episode=state.get('episode',0)
            await ws.send_json({'keys':[],'environment':{'profile':'calm','seed':714,'direction_deg':0}})
            await wait_for(lambda s:s.get('environment',{}).get('profile')=='calm')
            await send(action='reset')
            await wait_for(lambda s:s.get('ready') and s.get('episode',0)>episode and not s.get('armed'))
            await send(action='takeoff')
            hover=await wait_for(lambda s:s.get('armed') and abs(s.get('height_m',0)-1.5)<.035 and abs(s['velocity_m_s'][2])<.04)
            print('PX4 hover',hover['height_m'],flush=True)
            start=np.array(hover['position_m']);start_time=hover['sim_time_s']
            while state['sim_time_s']<start_time+2.0:
                await send(('KeyW',));await update()
            await send()
            stopped=await wait_for(lambda s:np.linalg.norm(s['velocity_m_s'][:2])<.10)
            displacement=np.linalg.norm(np.array(stopped['position_m'][:2])-start[:2])
            assert displacement>.25,displacement
            print('WASD forward travel',displacement,flush=True)
            before_pan=state['pan_deg'];before_tilt=state['tilt_deg'];until=asyncio.get_running_loop().time()+2.0
            while asyncio.get_running_loop().time()<until:
                await send(('ArrowLeft','ArrowUp'));await update();camera_samples.append([state['pan_deg'],state['tilt_deg']])
            await send()
            pan_change=(state['pan_deg']-before_pan+180)%360-180
            assert pan_change>10 and state['tilt_deg']<before_tilt-10,(pan_change,state['tilt_deg'])
            assert -.1-61<=state['tilt_deg']<=140.1
            assert len(images.get('camera',''))>3000 and len(images.get('world',''))>3000
            await send(action='camera_reset')
            await send(action='land')
            landed=await wait_for(lambda s:not s.get('armed',True) and s.get('height_m',1)<.25,seconds=60)
            assert not any('STALE' in s or 'Failsafe activated' in s for s in landed['messages']),landed['messages']
            print('Native PX4 landing',landed['height_m'],flush=True)
            report={'passed':True,'controller':'PX4 v1.16.0 native SITL','hover_height_m':hover['height_m'],'forward_displacement_m':float(displacement),'camera_pan_change_deg':pan_change,'camera_tilt_after_move_deg':camera_samples[-1][1],'live_onboard_and_world_images':True,'landed_disarmed':True,'landing_height_m':landed['height_m'],'messages':landed['messages'],'calibration_status':'integration_verified_not_real_flight_validated'}
            (ROOT/'build/live_flight_verification.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(report,indent=2),flush=True)
asyncio.run(main())
