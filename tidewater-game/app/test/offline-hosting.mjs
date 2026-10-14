import fs from 'node:fs/promises';
import vm from 'node:vm';
import {webcrypto,createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
const source=await fs.readFile(new URL('../scripts/service-worker.js',import.meta.url),'utf8'),scope='https://example.test/game/';
const files=new Map([['index.html','<html>Tidewater</html>'],['landing/wasm/px4.wasm','wasm fixture'],['assets/worker.js','worker fixture']]);
const assets=[...files].map(([url,text])=>({url,bytes:text.length,sha256:createHash('sha256').update(text).digest('hex')}));
const cacheStores=new Map();const caches={async open(name){if(!cacheStores.has(name))cacheStores.set(name,new Map());const data=cacheStores.get(name);return {async put(url,response){if(name.endsWith('-quota'))throw new DOMException('Quota exceeded','QuotaExceededError');data.set(String(url),response.clone());},async match(url){return data.get(String(url))?.clone();}};},async keys(){return [...cacheStores.keys()];},async delete(name){return cacheStores.delete(name);}};
async function runtime(version,bad=false) {
 const handlers={},notifications=[];let offline=false;
 const context={self:{registration:{scope},clients:{matchAll:async()=>[{postMessage:p=>notifications.push(p)}],claim:async()=>{}},addEventListener:(kind,fn)=>handlers[kind]=fn},crypto:webcrypto,caches,URL,Response,console,fetch:async url=>{
  if(offline)throw new Error('network unavailable');const file=String(url).slice(scope.length);
  if(file==='offline-manifest.json')return new Response(JSON.stringify({version,assets,bytes:40}));
  if(!files.has(file))return new Response('',{status:404});return new Response(bad?'bad hash':files.get(file),{headers:{'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp'}});
 }};
 vm.runInNewContext(source.replace('__BUILD_VERSION__',version),context);
 const event=async(kind,props={})=>{let promise;handlers[kind]({...props,waitUntil:p=>promise=p,respondWith:p=>promise=p});return promise;};
 return {event,notifications,setOffline:()=>offline=true};
}
const old=await runtime('previous');await old.event('install');await old.event('activate');
const bad=await runtime('bad',true);await assert.rejects(bad.event('install'),/changed/);assert(cacheStores.has('tidewater-offline-'+scope+'-previous'));assert(!cacheStores.has('tidewater-offline-'+scope+'-bad'));
const next=await runtime('current');await next.event('install');assert(next.notifications.some(p=>p.offline.status==='ready'));await next.event('activate');assert(!cacheStores.has('tidewater-offline-'+scope+'-previous'));const quota=await runtime('quota');await assert.rejects(quota.event('install'),/Quota exceeded/);assert(cacheStores.has('tidewater-offline-'+scope+'-current'));assert(!cacheStores.has('tidewater-offline-'+scope+'-quota'));next.setOffline();
for(const [url,text] of files){const response=await next.event('fetch',{request:{url:scope+url,method:'GET'}});assert.equal(await response.text(),text);assert.equal(response.headers.get('Cross-Origin-Embedder-Policy'),'require-corp');}
assert.equal(await (await next.event('fetch',{request:{url:scope+'?offline=1',method:'GET',mode:'navigate'}})).text(),files.get('index.html'));
console.log('Offline atomic install, SHA-256/quota failures, version activation, subpath requests and cached isolation headers passed');
const server=spawn(process.execPath,['scripts/serve-static.mjs','--port','0'],{cwd:new URL('../',import.meta.url),stdio:['ignore','pipe','pipe']});
try {
 const origin=await new Promise((resolve,reject)=>{server.stdout.on('data',chunk=>{const match=chunk.toString().match(/http:\/\/127\.0\.0\.1:\d+\//);if(match)resolve(match[0]);});server.on('exit',code=>reject(new Error(`Static server exit ${code}`)));});
 const response=await fetch(origin);assert.equal(response.status,200);assert.equal(response.headers.get('Cross-Origin-Opener-Policy'),'same-origin');assert.equal(response.headers.get('Cross-Origin-Embedder-Policy'),'require-corp');
 const wasm=await fetch(new URL('landing/wasm/px4.wasm',origin),{method:'HEAD'});assert.equal(wasm.headers.get('content-type'),'application/wasm');assert(Number(wasm.headers.get('content-length'))>1000000);
 const sw=await fetch(new URL('service-worker.js',origin));assert.equal(sw.headers.get('cache-control'),'no-cache');assert(!((await sw.text()).includes('__BUILD_VERSION__')));
 assert.equal((await fetch(new URL('missing',origin))).status,404);
 console.log('Standalone static server headers, WASM MIME, service-worker caching and missing-path responses passed');
}finally{server.kill();}
