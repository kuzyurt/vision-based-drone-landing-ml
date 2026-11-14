import http from 'node:http';
import fs from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {handleSessionRecording} from './session-recording-endpoint.mjs';
const args=process.argv.slice(2),value=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const root=await fs.realpath(value('--dir',fileURLToPath(new URL('../dist/',import.meta.url)))),port=Number(value('--port','5189'));
const timingFile=value('--timing-file',null);
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.wasm':'application/wasm','.json':'application/json','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.webp':'image/webp','.mp3':'audio/mpeg','.ogg':'audio/ogg','.txt':'text/plain; charset=utf-8'};
const server=http.createServer(async(req,res)=>{
 res.setHeader('Cross-Origin-Opener-Policy','same-origin');res.setHeader('Cross-Origin-Embedder-Policy','require-corp');res.setHeader('Cross-Origin-Resource-Policy','same-origin');
 if(req.method==='POST' && req.url.startsWith('/__session-recording')){try{if(await handleSessionRecording(req,res))return;}catch{}res.writeHead(500);return res.end();}
 if(req.method==='POST' && req.url==='/__timing' && timingFile){
  if(req.headers.origin!==`http://127.0.0.1:${server.address().port}` || req.headers.host!==`127.0.0.1:${server.address().port}`){res.writeHead(403);return res.end();}
  try{
   const chunks=[];let size=0;
   for await(const chunk of req){size+=chunk.length;if(size>2*1024*1024){res.writeHead(413);return res.end();}chunks.push(chunk);}
   const report=JSON.parse(Buffer.concat(chunks).toString('utf8'));
   if(report.schema!=='tidewater.performance.v1'||!Array.isArray(report.rows))throw new Error('Invalid timing report');
   await fs.mkdir(path.dirname(path.resolve(timingFile)),{recursive:true});
   const stamp=new Date().toISOString().replace(/[:.]/g,'-'),kind=report.rows.some(row=>row.ml_enabled)?'ml':'manual',extension=path.extname(timingFile),history=timingFile.slice(0,extension? -extension.length:undefined)+`-${stamp}-${kind}.json`;
   const serialized=JSON.stringify(report,null,2);await fs.writeFile(history,serialized,{flag:'wx'});await fs.writeFile(timingFile,serialized);
   console.log(`Browser timing saved: ${timingFile}`);res.writeHead(200);return res.end('Saved locally');
  }catch{res.writeHead(400);return res.end('Invalid timing report');}
 }
 if(!['GET','HEAD'].includes(req.method)){res.writeHead(405);return res.end();}
 try {
  const url=new URL(req.url,'http://localhost'),relative=decodeURIComponent(url.pathname),candidate=path.resolve(root,'.'+relative+(relative.endsWith('/')?'index.html':'')),file=await fs.realpath(candidate);
  if(!file.startsWith(root+path.sep)){res.writeHead(403);return res.end();}
  const stat=await fs.stat(file);if(!stat.isFile()){res.writeHead(404);return res.end();}
  res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.setHeader('Content-Length',stat.size);res.setHeader('Cache-Control',file.endsWith('service-worker.js')||file.endsWith('offline-manifest.json')?'no-cache':'public, max-age=0, must-revalidate');
  res.writeHead(200);if(req.method==='HEAD')res.end();else createReadStream(file).on('error',()=>res.destroy()).pipe(res);
 }catch{res.writeHead(404);res.end('Not found');}
});
server.listen(port,'127.0.0.1',()=>console.log(`Tidewater static files: http://127.0.0.1:${server.address().port}/ — open your browser manually`));
