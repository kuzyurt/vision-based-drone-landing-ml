import {chromium} from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
const [url,out,device='pc']=process.argv.slice(2);
let received=0;
const collector=http.createServer(async(req,res)=>{res.setHeader('Access-Control-Allow-Origin','*');for await(const c of req)received+=c.length;res.end('ok');});
await new Promise(r=>collector.listen(5684,'127.0.0.1',r));
let browser;
try{
 const args=device==='vm'?['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-webgpu','--ignore-gpu-blocklist','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']:['--enable-unsafe-webgpu','--ignore-gpu-blocklist'];
 browser=await chromium.launch({headless:true,channel:device==='vm'?'chromium':'msedge',args});
 const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
 page.on('pageerror',e=>process.stdout.write('PAGE_ERROR '+String(e)+'\n'));
 await page.goto(url+'/?bench&fly&noAudio',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.__bench&&window.__app,{},{timeout:240000});
 const result=await page.evaluate(async()=>{
  const a=window.__app,b=window.__bench,G=a.gpu;
  a.engine.stop();b.setSize(1280,720);b.pose('beach');
  a.settings.timeOfDay=15.35;a.clouds.coverage.value=.62;a.setRenderScale(1);
  a.post.aaMode='taa';a.post.taau.jitterPhaseOverride=16;a.shadows.enabled=true;a.waterMaterial.params.ssr.value=1;
  await b._frames(16,1/60);const start=performance.now();await b._frames(60,1/60);const renderMs=(performance.now()-start)/60;
  const {Texture}=await import('/src/engine/gpu/Texture.js');const {readTexture}=await import('/src/engine/gpu/Readback.js');
  const t=new Texture({width:1280,height:720,format:G.format,usage:['render','copySrc','sample'],label:'performance capture'});
  a.post.outputTexture=t;const stages=[];
  for(let i=0;i<3;i++){
   let s=performance.now();a.frame(1/60);const cpu=performance.now()-s;
   s=performance.now();await G.pipelinesReady();const pipelines=performance.now()-s;
   s=performance.now();await G.queue.onSubmittedWorkDone();const gpuWait=performance.now()-s;
   s=performance.now();const image=await readTexture(t);const readback=performance.now()-s;
   s=performance.now();await fetch('http://127.0.0.1:5684/pixels',{method:'POST',body:image.data});const upload=performance.now()-s;
   stages.push({cpuMs:cpu,pipelinesMs:pipelines,gpuWaitMs:gpuWait,readbackMs:readback,uploadMs:upload,bytes:image.data.byteLength});
  }
  return {adapter:G.adapter.info,format:G.format,resolution:[1280,720],renderScale:1,ordinaryRenderMs:renderMs,ordinaryRenderFps:1000/renderMs,cpuMs:a.cpuMs,captureStages:stages,scope:'Stock pinned Tidewater map, full quality, no PX4, no aircraft CAD; existing background workloads unchanged.'};
 });
 result.device=device;result.receivedBytes=received;fs.writeFileSync(out,JSON.stringify(result,null,2));process.stdout.write(JSON.stringify(result)+'\n');
}finally{if(browser)await browser.close();await new Promise(r=>collector.close(r));}
