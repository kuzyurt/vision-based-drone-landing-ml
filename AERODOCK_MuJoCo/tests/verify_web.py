"""Browser checks against the running local server; screenshots included."""
import json
import time
import urllib.request
from playwright.sync_api import sync_playwright
from boat_sim import ROOT


def api(name,**args):
    request=urllib.request.Request('http://127.0.0.1:8765/api/command/'+name,data=json.dumps(args).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(request))


if __name__=='__main__':
    api('reset');api('set_environment',wave_height=.06)
    results=[]; errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8765',wait_until='domcontentloaded')
        page.wait_for_function("document.querySelector('#connection').textContent==='Simulator connected'",timeout=30000)
        page.wait_for_function("[...document.querySelectorAll('img')].every(i=>i.naturalWidth>0)",timeout=30000)
        page.screenshot(path=str(ROOT/'reports/previews/control_page.png'),full_page=True)
        page.locator('#open-lid').click()
        page.wait_for_function("!document.querySelector('#raise-platform').disabled",timeout=15000)
        page.locator('#raise-platform').click()
        page.wait_for_function("document.querySelector('#platform-position').textContent==='Raised'",timeout=15000)
        results.append('Web controls open both lids and raise the platform')
        page.screenshot(path=str(ROOT/'reports/previews/control_page_dock_open.png'),full_page=True)
        page.locator('#port').evaluate('el=>{el.value=30;el.dispatchEvent(new Event("input",{bubbles:true}));el.dispatchEvent(new Event("change",{bubbles:true}));}')
        page.locator('#starboard').evaluate('el=>{el.value=30;el.dispatchEvent(new Event("input",{bubbles:true}));el.dispatchEvent(new Event("change",{bubbles:true}));}')
        page.wait_for_function("+document.querySelector('#speed').textContent>.3",timeout=10000)
        results.append('Web motor controls work with open lids and a raised platform')
        page.locator('#stop-motors').click()
        page.locator('#lower-platform').click()
        page.wait_for_function("!document.querySelector('#close-lid').disabled",timeout=15000)
        page.locator('#close-lid').click()
        page.wait_for_function("!document.querySelector('#port').disabled",timeout=15000)
        results.append('Web controls lower platform and close lids')
        for name,value in (('port',35),('starboard',50)):
            page.locator('#'+name).evaluate('(el,value)=>{el.value=value;el.dispatchEvent(new Event("input",{bubbles:true}));el.dispatchEvent(new Event("change",{bubbles:true}));}',value)
        page.wait_for_function("+document.querySelector('#speed').textContent>.3",timeout=10000)
        results.append('Separate motor sliders drive the simulated boat')
        page.locator('#emergency').click()
        page.wait_for_function("document.querySelector('#connection').textContent==='Emergency stop latched'",timeout=10000)
        results.append('Emergency stop is visible and latched in the page')
        page.locator('#test-water').fill('5');page.locator('#test-drain').click()
        page.wait_for_function("document.querySelector('#drain-pumps').textContent.includes('On')",timeout=10000)
        results.append('Automatic drainage stays active during emergency stop')
        page.locator('#reset-emergency').click();page.locator('#reset-sim').click()
        page.locator('#internals').check();page.locator('#underwater').check()
        page.wait_for_timeout(1200)
        page.screenshot(path=str(ROOT/'reports/previews/control_page_internals.png'),full_page=True)
        page.locator('#internals').uncheck();page.locator('#underwater').uncheck()
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(600)
        page.screenshot(path=str(ROOT/'reports/previews/control_page_mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), 'Mobile page has horizontal overflow'
        results.append('Mobile layout fits 390 px without horizontal overflow')
        assert not errors,errors
        browser.close()
    (ROOT/'reports/web_validation.json').write_text(json.dumps({'passed':True,'checks':results,'browser_errors':errors},indent=2))
    print('PASS: '+ '; '.join(results))
