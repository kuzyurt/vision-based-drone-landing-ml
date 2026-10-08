import asyncio,json,time
import aiohttp

async def main():
    async with aiohttp.ClientSession() as client,client.ws_connect('http://127.0.0.1:8793/ws') as ws:
        state={}
        async def read():
            nonlocal state
            data=await asyncio.wait_for(ws.receive(),8);state=data.json()['telemetry']
        async def send(**kw):await ws.send_json({'keys':[],**kw})
        async def wait(predicate):
            end=time.monotonic()+65
            while time.monotonic()<end:
                await send();await read()
                if predicate(state):return
            raise RuntimeError(state)
        await wait(lambda s:s.get('ready'))
        previous=state.get('episode',0)
        await send(action='reset')
        await wait(lambda s:s.get('ready') and s.get('episode',0)>previous)
        await send(environment={'profile':'breeze','seed':714,'direction_deg':0})
        await wait(lambda s:s.get('environment',{}).get('profile')=='breeze')
        await send(action='takeoff')
        await wait(lambda s:s.get('armed') and abs(s['height_m']-1.5)<.04 and abs(s['velocity_m_s'][2])<.05)
        await send(action='camera_reset')
        print(json.dumps({'status':state['status'],'height_m':state['height_m'],'wind':state['environment']['profile'],'episode':state['episode'],'failed_rotors':state['failed_rotors']},indent=2))
asyncio.run(main())
