import {chromium} from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
const out=process.argv[2];fs.mkdirSync(out,{recursive:true});
const pixels=new Map();let page,browser,ready=false;const errors=[],failedResources=[];
const server=http.createServer(async(req,res)=>{
 res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Access-Control-Allow-Headers','Content-Type');
 if(req.method==='OPTIONS'){res.end();return;}
 try{const chunks=[];for await(const c of req)chunks.push(c);const body=Buffer.concat(chunks);
  if(req.url.startsWith('/_pixels/')){pixels.set(req.url.slice(9),body);res.end('ok');return;}
  if(req.url==='/status'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({ready,errors,failedResources}));return;}
  if(!ready){res.writeHead(503);res.end('not ready');return;}
  const packet=body.length?JSON.parse(body):{};
  if(req.url==='/install'){const result=await page.evaluate(url=>window.__landing.install(url),packet.url);res.end(JSON.stringify(result));return;}
  if(req.url==='/render'){pixels.clear();const result=await page.evaluate(p=>window.__landing.render(p),packet);const names=packet.views.map(v=>v.name);const header=Buffer.from(JSON.stringify({views:result,names,errors,failedResources,format:info.format})+'\n');const n=Buffer.alloc(4);n.writeUInt32LE(header.length);res.end(Buffer.concat([n,header,...names.map(name=>pixels.get(name))]));return;}
  res.writeHead(404);res.end('unknown');
 }catch(e){res.writeHead(500);res.end(String(e));console.error(e);}
});
await new Promise(r=>server.listen(5192,'127.0.0.1',r));
browser=await chromium.launch({channel:'msedge',args:['--enable-unsafe-webgpu','--ignore-gpu-blocklist']});
page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
page.on('console',m=>{if(m.type()==='error'){errors.push(m.text());console.error(m.text().slice(0,600));}});
page.on('pageerror',e=>{errors.push(String(e));console.error(String(e));});
page.on('response',r=>{if(r.status()>=400)failedResources.push({url:r.url(),status:r.status()});});
await page.goto('http://127.0.0.1:5191/?bench&fly&noAudio&landing',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.__bench&&window.__app,{},{timeout:240000});
const info=await page.evaluate(async()=>{const {FastComparisonBridge}=await import('/src/landing/FastComparisonBridge.js');window.__landing=new FastComparisonBridge(window.__app);const g=window.__app.gpu;return {vendor:g.adapter.info.vendor,architecture:g.adapter.info.architecture,device:g.adapter.info.device,description:g.adapter.info.description,format:g.format,quality:window.__landing.quality};});
fs.writeFileSync(out+'/adapter.json',JSON.stringify(info,null,2));console.log('WINDOWS_RENDER_READY',JSON.stringify(info));ready=true;
for(const s of ['SIGTERM','SIGINT'])process.on(s,async()=>{await browser.close();server.close();process.exit(0);});
