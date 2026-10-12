import { chromium } from 'playwright';
import fs from 'node:fs';
const out=process.argv[2];
const browser=await chromium.launch({headless:true,channel:'chromium',args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-webgpu','--ignore-gpu-blocklist','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
const page=await browser.newPage({viewport:{width:800,height:450},deviceScaleFactor:1});
const errors=[];
page.on('console',m=>{if(m.type()==='error'){errors.push(m.text());console.error(m.text().slice(0,600));}});
page.on('pageerror',e=>{errors.push(String(e));console.error(String(e));});
await page.goto('http://127.0.0.1:5189/?bench&fly&noAudio',{waitUntil:'domcontentloaded'});
const adapter=await page.evaluate(async()=>{const a=await navigator.gpu?.requestAdapter({powerPreference:'high-performance'});return a?{info:{...a.info},features:[...a.features],fallback:a.isFallbackAdapter}:null;});
console.log('ADAPTER',JSON.stringify(adapter));
try{
 await page.waitForFunction(()=>window.__bench&&window.__app,{},{timeout:240000});
 const info=await page.evaluate(async()=>{
  const a=window.__app;
  a.engine.canvas.width=800;a.engine.canvas.height=450;a.camera.aspect=800/450;a.camera.updateProjectionMatrix();
  a.fly.setPose(new (await import('/src/engine/math/Vector3.js')).Vector3(12,5,20),Math.PI,-.1);
  document.querySelectorAll('body > *').forEach(e=>{if(e.id!=='app'&&e.tagName!=='SCRIPT')e.style.display='none';});
  for(let i=0;i<8;i++){a.frame(0);await a.gpu.queue.onSubmittedWorkDone();}
  return {gpu:a.gpu.adapter.info,terrain:{size:a.terrainData.size,res:a.terrainData.res},boatMass:a.boatCtl.mass,seaLevel:(await import('/src/core/Globals.js')).G.seaLevel.value};
 });
 await page.screenshot({path:out+'/upstream_probe.png'});
 fs.writeFileSync(out+'/upstream_probe.json',JSON.stringify({adapter,info,errors},null,2));
 console.log('TIDEWATER_READY',JSON.stringify(info));
}catch(e){
 await page.screenshot({path:out+'/upstream_failure.png'});
 fs.writeFileSync(out+'/upstream_failure.json',JSON.stringify({adapter,error:String(e),errors},null,2));
 throw e;
}finally{await browser.close();}
