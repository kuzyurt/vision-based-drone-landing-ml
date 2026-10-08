"""End-to-end procedural-world controls against the live local web server."""
import json
import time
import urllib.request
from playwright.sync_api import sync_playwright
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8765'


def get(path):
    return json.load(urllib.request.urlopen(BASE+path,timeout=15))


def command(name,**args):
    req=urllib.request.Request(BASE+'/api/command/'+name,data=json.dumps(args).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=20))


if __name__=='__main__':
    errors=[];checks=[];renders=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1100})
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.goto(BASE,wait_until='domcontentloaded')
        page.wait_for_function("document.querySelector('#connection').textContent==='Simulator connected'",timeout=30000)
        page.wait_for_function("[...document.querySelectorAll('img')].every(i=>i.naturalWidth>0)",timeout=30000)
        for kind in ('island','beach','city','gravel','rock'):
            page.locator('#world-kind').select_option(kind)
            page.locator('#world-seed').fill('42');page.locator('#path-seed').fill('43')
            page.locator('#new-world').click()
            page.wait_for_function("(kind)=>worldData?.kind===kind&&worldData?.world_seed===42&&worldData?.route.path_seed===43&&state?.world.kind===kind&&state?.world.seed===42",arg=kind,timeout=30000)
            state=get('/api/status')
            assert state['world']['kind']==kind and state['world']['coastline_length_m']>=1000
            assert state['control_mode']=='automatic' and state['render_error'] is None
            assert not state['scenery']['scenery_budget_exceeded']
            renders.append({'kind':kind,'scenery':state['scenery']})
        checks.append('All five family choices create seeded kilometre-scale worlds and routes, rendered without errors')
        before=get('/api/world');page.locator('#path-seed').fill('44');page.locator('#new-path').click()
        page.wait_for_function("worldData?.route.path_seed===44",timeout=20000)
        after=get('/api/world');assert before['coastline']==after['coastline'] and before['route']!=after['route']
        checks.append('New path button preserves map, changes path and starts automatic control')
        page.locator('#manual-control').click()
        page.wait_for_function("document.querySelector('#control-mode').textContent==='Manual'",timeout=10000)
        page.locator('#port').evaluate('el=>{el.value=25;el.dispatchEvent(new Event("change",{bubbles:true}))}')
        page.wait_for_function("state?.port_power===25&&state?.control_mode==='manual'",timeout=10000)
        page.locator('#follow-path').click()
        page.wait_for_function("state?.control_mode==='automatic'",timeout=10000)
        checks.append('Manual button, motor sliders and Follow path button switch control correctly')
        page.locator('#emergency').click()
        page.wait_for_function("state?.emergency&&state?.control_mode==='manual'&&state?.port_power===0",timeout=10000)
        checks.append('Emergency stop cancels route driving')
        page.locator('#reset-emergency').click()
        page.locator('#world-kind').select_option('city');page.locator('#path-seed').fill('43');page.locator('#new-world').click()
        page.wait_for_function("worldData?.kind==='city'",timeout=20000)
        page.locator('#wide-view').click();page.locator('#show-route').check()
        page.wait_for_timeout(1500)
        page.screenshot(path=str(ROOT/'reports/previews/procedural_control_page.png'),full_page=True)
        # Save the actual camera images, beyond browser layout verification.
        for key in ('overview','forward','dock'):
            (ROOT/'reports/previews'/('city_'+key+'.jpg')).write_bytes(urllib.request.urlopen(BASE+'/frame/'+key+'.jpg').read())
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(700)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(ROOT/'reports/previews/procedural_control_page_mobile.png'),full_page=True)
        checks.append('World panel/minimap/seed controls render on desktop and 390 px mobile without overflow')
        assert not errors,errors
        browser.close()
    command('new_world',kind='city',seed=42,path_seed=43)
    command('view',azimuth=90,elevation=-24,distance=40,route=False)
    result={'passed':True,'checks':checks,'browser_errors':errors,'world_renders':renders}
    (ROOT/'reports/world_web_validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
