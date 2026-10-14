import http from 'node:http';
import fs from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const args=process.argv.slice(2),value=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const root=await fs.realpath(value('--dir',fileURLToPath(new URL('../dist/',import.meta.url)))),port=Number(value('--port','5189'));
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.wasm':'application/wasm','.json':'application/json','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.webp':'image/webp','.mp3':'audio/mpeg','.ogg':'audio/ogg','.txt':'text/plain; charset=utf-8'};
const server=http.createServer(async(req,res)=>{
 res.setHeader('Cross-Origin-Opener-Policy','same-origin');res.setHeader('Cross-Origin-Embedder-Policy','require-corp');res.setHeader('Cross-Origin-Resource-Policy','same-origin');
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
