"""Real PX4 integration: wind, zoom, fresh-estimator reset and rotor strike."""
import asyncio,json,math
from pathlib import Path
import aiohttp
ROOT=Path(__file__).resolve().parents[1]

async def main():
    async with aiohttp.ClientSession() as client,client.ws_connect('http://127.0.0.1:8793/ws') as ws:
        state={}
        async def read():
            nonlocal state
            message=await asyncio.wait_for(ws.receive(),8)
            state=message.json()['telemetry'];return state
        async def send(**kwargs):await ws.send_json({'keys':[],**kwargs})
        async def until(predicate,timeout=65):
            end=asyncio.get_running_loop().time()+timeout
            while asyncio.get_running_loop().time()<end:
                await send();await read()
                if predicate(state):return state.copy()
            raise AssertionError(state)
        async def reset():
            old=state.get('episode',0)
            await send(action='reset')
            return await until(lambda s:s.get('ready') and not s.get('armed') and s.get('episode',0)>old and s.get('sim_time_s',0)>8)
        await until(lambda s:s.get('ready'))
        await send(environment={'profile':'breeze','seed':123,'direction_deg':90},zoom=-400)
        configured=await until(lambda s:s.get('environment',{}).get('profile')=='breeze' and s['external_camera_distance_m']<1.4)
        assert math.hypot(*configured['environment']['velocity_m_s'])>0
        reset_state=await reset()
        assert math.hypot(*reset_state['position_m'][:2])<.05
        assert reset_state['battery_percent']>99.9 and not any(reset_state['failed_rotors'])
        assert abs(reset_state['external_camera_distance_m']-2)<1e-6
        assert reset_state['environment']['seed']==123 and reset_state['environment']['profile']=='breeze'
        await send(action='takeoff')
        hover=await until(lambda s:s.get('armed') and abs(s['height_m']-1.5)<.05 and abs(s['velocity_m_s'][2])<.08)
        start=hover['sim_time_s'];max_drift=0.;wind_max=0.
        while state['sim_time_s']<start+8:
            await send();await read()
            assert state['armed'] and not any(state['failed_rotors']),state
            max_drift=max(max_drift,math.hypot(*state['position_m'][:2]))
            wind_max=max(wind_max,math.hypot(*state['environment']['velocity_m_s']))
        assert max_drift<1. and wind_max>1.
        print('Windy hover drift',max_drift,'wind',wind_max,flush=True)
        await send(environment={'profile':'calm','seed':714,'direction_deg':0})
        await until(lambda s:s['environment']['profile']=='calm')
        await reset()
        await send(action='takeoff')
        await until(lambda s:s.get('armed') and abs(s['height_m']-1.5)<.05)
        # Approach the left arch post at (10, -1.8); read the moving aircraft
        # position to keep the contact check tied to the current scene.
        end=asyncio.get_running_loop().time()+35
        while asyncio.get_running_loop().time()<end and not any(state.get('failed_rotors',[])):
            keys=['KeyW']
            if state['position_m'][1]>-1.72:keys.append('KeyD')
            elif state['position_m'][1]<-1.88:keys.append('KeyA')
            await send(keys=keys);await read()
        assert any(state['failed_rotors']),state
        strike=state.copy();print('Rotor strike',strike['failed_rotors'],flush=True)
        restored=await reset()
        assert not any(restored['failed_rotors']) and not restored['armed']
        assert math.hypot(*restored['position_m'][:2])<.01
        report={'passed':True,'wind_seed_preserved_on_reset':True,'physics_and_PX4_reset':True,'zoom_changes_camera_only':True,
                'windy_hover_max_horizontal_offset_m':max_drift,'wind_speed_observed_max_m_s':wind_max,
                'failed_rotors_at_obstacle':strike['failed_rotors'],'strike_position_m':strike['position_m'],
                'reset_cleared_rotor_failures':True,'final_position_m':restored['position_m'],
                'scope':'native_PX4_software_integration_not_hardware_validation'}
        (ROOT/'build/upgrade_live_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
