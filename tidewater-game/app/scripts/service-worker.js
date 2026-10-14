const scope=self.registration.scope;
const PREFIX='tidewater-offline-'+scope+'-';
const VERSION='__BUILD_VERSION__',CACHE=PREFIX+VERSION;
async function notify(packet){for(const client of await self.clients.matchAll({includeUncontrolled:true}))client.postMessage({offline:packet});}
async function manifest(){const response=await fetch(new URL('offline-manifest.json',scope),{cache:'no-store'});if(!response.ok)throw new Error('Offline manifest unavailable');return response.json();}
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const m=await manifest(),name=CACHE,cache=await caches.open(name);let complete=0;
 try {
  // Limit concurrent memory and network use; install is complete only after the
  // entire version has passed hash checks. A failed update preserves the old one.
  let next=0;
  const results=await Promise.allSettled(Array.from({length:4},async()=>{while(next<m.assets.length){const asset=m.assets[next++],url=new URL(asset.url,scope),response=await fetch(url,{cache:'reload'});if(!response.ok)throw new Error(`Offline asset failed: ${asset.url}`);
   const bytes=await response.clone().arrayBuffer(),digest=await crypto.subtle.digest('SHA-256',bytes),hash=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');if(hash!==asset.sha256)throw new Error(`Offline asset changed: ${asset.url}`);
   await cache.put(url,response);await notify({status:'loading',complete:++complete,total:m.assets.length});
  }}));
  const failed=results.find(result=>result.status==='rejected');if(failed)throw failed.reason;
  await cache.put(new URL('offline-manifest.json',scope),new Response(JSON.stringify(m),{headers:{'Content-Type':'application/json'}}));
  await notify({status:'ready',bytes:m.bytes});
 }catch(error){await caches.delete(name);await notify({status:'unavailable',error:error.message});throw error;}
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 // The manifest belongs to the installed worker version, even when offline.
 for(const name of await caches.keys())if(name.startsWith(PREFIX)&&name!==CACHE)await caches.delete(name);
 await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==new URL(scope).origin||!url.href.startsWith(scope))return;
 event.respondWith((async()=>{
  const cache=await caches.open(CACHE),cached=await cache.match(new URL(url.pathname,scope));if(cached)return cached;
  if(event.request.mode==='navigate'){const index=await cache.match(new URL('index.html',scope));if(index)return index;}
  return fetch(event.request);
 })());
});
self.addEventListener('message',event=>{if(event.data?.type==='offline-status')event.waitUntil((async()=>{
 const ready=await (await caches.open(CACHE)).match(new URL('offline-manifest.json',scope));event.source?.postMessage({offline:{status:ready?'ready':'loading'}});
})());});
