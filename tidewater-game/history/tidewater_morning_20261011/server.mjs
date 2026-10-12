import {chromium} from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
const out=process.argv[2];fs.mkdirSync(out,{recursive:true});
const pixels=new Map();let page,browser,ready=false;const errors=[],failedResources=[];
const server=http.createServer(async(req,res)=>{
 res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Access-Control-Allow-Headers','Content-Type');
 if(req.method==='OPTIONS'){res.end();return;}
 try{
  const chunks=[];for await(const chunk of req)chunks.push(chunk);const body=Buffer.concat(chunks);
  if(req.url.startsWith('/_pixels/')){pixels.set(req.url.slice(9),body);res.end('ok');return;}
  if(req.url==='/_terrain'){fs.writeFileSync(out+'/terrain.f32',body);res.end('ok');return;}
  if(req.url==='/status'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({ready,errors,failedResources}));return;}
  if(!ready){res.writeHead(503);res.end('not ready');return;}
  const packet=body.length?JSON.parse(body):{};
  if(req.url==='/install'){
   const result=await page.evaluate(url=>window.__landing.install(url),packet.url);
   res.end(JSON.stringify(result));return;
  }
  if(req.url==='/render'){
   pixels.clear();const result=await page.evaluate(packet=>window.__landing.render(packet),packet);
   const names=packet.views.map(v=>v.name);const header=Buffer.from(JSON.stringify({views:result,names,errors,failedResources,format:info.format})+'\n');
   const length=Buffer.alloc(4);length.writeUInt32LE(header.length);
   res.end(Buffer.concat([length,header,...names.map(n=>pixels.get(n))]));return;
  }
  if(req.url==='/terrain'){res.end(JSON.stringify(await page.evaluate(()=>window.__landing.exportTerrain())));return;}
  if(req.url==='/verify_waves'){
   const result=await page.evaluate(async points=>{
    const app=window.__app,q=app.query;
    points.forEach((p,i)=>q.setPoint(i+1,p[0],p[1]));
    q.update();
    const {readBuffer}=await import('/src/engine/gpu/Readback.js');
    const values=new Float32Array(await readBuffer(q.results,q.results.byteLength));
    return points.map((p,i)=>({point:p,height:values[(i+1)*4],normal_x:values[(i+1)*4+1],normal_z:values[(i+1)*4+2],floor:values[(i+1)*4+3]}));
   },packet.points);res.end(JSON.stringify(result));return;
  }
  res.writeHead(404);res.end('unknown');
 }catch(e){res.writeHead(500);res.end(String(e));console.error(e);}
});
await new Promise(r=>server.listen(5190,'127.0.0.1',r));
browser=await chromium.launch({headless:true,channel:'chromium',args:['--no-sandbox','--disable-dev-shm-usage','--enable-unsafe-webgpu','--ignore-gpu-blocklist','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
page=await browser.newPage({viewport:{width:640,height:360},deviceScaleFactor:1});
page.on('console',m=>{if(m.type()==='error'){errors.push(m.text());console.error(m.text().slice(0,600));}});
page.on('pageerror',e=>{errors.push(String(e));console.error(String(e));});
page.on('response',r=>{if(r.status()>=400)failedResources.push({url:r.url(),status:r.status()});});
await page.goto('http://127.0.0.1:5189/?bench&fly&noAudio&landing',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.__bench&&window.__app,{},{timeout:240000});
const info=await page.evaluate(async()=>{
 const {LandingBridge}=await import('/src/landing/LandingBridge.js');window.__landing=new LandingBridge(window.__app);
 const a=window.__app.gpu.adapter.info;
 return {vendor:a.vendor,architecture:a.architecture,device:a.device,description:a.description,isFallbackAdapter:a.isFallbackAdapter,format:window.__app.gpu.format};
});
fs.writeFileSync(out+'/adapter.json',JSON.stringify(info,null,2));console.log('LANDING_RENDER_READY',JSON.stringify(info));ready=true;
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,async()=>{await browser.close();server.close();process.exit(0);});
