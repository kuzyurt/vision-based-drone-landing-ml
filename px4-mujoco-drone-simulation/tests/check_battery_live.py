"""Observe battery draw in actual PX4-controlled flight, using the local UI."""
import asyncio
import json
from pathlib import Path
import aiohttp
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

async def main():
    async with aiohttp.ClientSession() as client:
        async with client.ws_connect('http://127.0.0.1:8793/ws',heartbeat=15) as ws:
            state={}
            async def step(keys=(),action=None):
                nonlocal state
                await ws.send_json({'keys':list(keys),'action':action})
                response=await asyncio.wait_for(ws.receive_json(),10)
                state=response['telemetry']
                return state
            async def until(predicate,timeout=70):
                deadline=asyncio.get_running_loop().time()+timeout
                while asyncio.get_running_loop().time()<deadline:
                    await step()
                    if predicate(state):return
                raise AssertionError(('timeout',state.get('status'),state.get('messages')))
            async def sample(keys,seconds):
                start=asyncio.get_running_loop().time()
                rows=[]
                while asyncio.get_running_loop().time()-start<seconds:
                    await step(keys)
                    rows.append((state['current_A'],state['battery_V'],state['velocity_m_s'][2],state['height_m'],state['battery_percent']))
                return np.array(rows)
            await until(lambda s:s.get('ready') and s.get('sim_time_s',0)>8)
            await step(action='takeoff')
            await until(lambda s:s.get('armed') and abs(s.get('height_m',0)-1.5)<.05 and abs(s['velocity_m_s'][2])<.08)
            hover=await sample((),1.5)
            climb=await sample(('KeyR',),4.)
            descent=await sample(('KeyF',),4.)
            await step()
            def mean_current(rows,condition):
                selected=rows[condition(rows)]
                assert len(selected)>3,rows[:,2].tolist()
                return float(selected[:,0].mean())
            hover_A=mean_current(hover,lambda x:np.abs(x[:,2])<.10)
            climb_A=mean_current(climb,lambda x:x[:,2]>.15)
            descent_A=mean_current(descent,lambda x:x[:,2]<-.15)
            assert climb_A>hover_A>descent_A,(climb_A,hover_A,descent_A)
            assert descent[-1,4]<hover[0,4],(descent[-1,4],hover[0,4])
            await step(action='land')
            await until(lambda s:not s.get('armed') and s.get('height_m',1)<.25)
            report={'passed':True,'native_PX4':True,'hover_A':hover_A,'climb_A':climb_A,'descent_A':descent_A,
                    'start_charge_percent':float(hover[0,4]),'end_charge_percent':float(descent[-1,4]),
                    'landed_disarmed':True,'limitation':'Bench-informed model; no measured airframe power calibration'}
            (ROOT/'build/battery_live_verification.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(report,indent=2),flush=True)

asyncio.run(main())
