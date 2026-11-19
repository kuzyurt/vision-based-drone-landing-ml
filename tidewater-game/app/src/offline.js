export async function registerOffline() {
 if(import.meta.env.DEV || !('serviceWorker' in navigator))return;
 // Hosted web build: no offline copy. Installing it would download every file
 // (~300 MB) for each visitor. Remove a worker left by an earlier visit.
 if(import.meta.env.VITE_WEB_HOSTED==='1'){
  for(const registration of await navigator.serviceWorker.getRegistrations().catch(()=>[]))registration.unregister().catch(()=>{});
  return;
 }
 const badge=document.createElement('div');badge.setAttribute('role','status');badge.style.cssText='position:fixed;bottom:6px;right:10px;z-index:10000;color:#d6eeee;background:#10232ddd;padding:4px 8px;font:11px system-ui;border-radius:4px;pointer-events:none';badge.textContent='Preparing offline files…';document.body.append(badge);
 let registration,reloadRequested=false,updateReady=false;
 const showUpdate=()=>{if(!registration?.waiting||!navigator.serviceWorker.controller)return;updateReady=true;badge.textContent='Update ready · click to reload';badge.style.pointerEvents='auto';badge.style.cursor='pointer';badge.setAttribute('role','button');badge.tabIndex=0;};
 const applyUpdate=()=>{if(!registration?.waiting)return;reloadRequested=true;registration.waiting.postMessage({type:'activate-update'});};
 badge.addEventListener('click',applyUpdate);badge.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();applyUpdate();}});
 navigator.serviceWorker.addEventListener('controllerchange',()=>{if(reloadRequested)location.reload();else navigator.serviceWorker.controller?.postMessage({type:'offline-status'});});
 navigator.serviceWorker.addEventListener('message',event=>{const p=event.data?.offline;if(!p||updateReady||event.source!==navigator.serviceWorker.controller)return;badge.textContent=(p.status==='ready'?'Offline files ready':p.status==='unavailable'?'Offline storage unavailable':`Preparing offline files${p.total?` · ${Math.round(100*p.complete/p.total)}%`:''}…`)+(p.version?` · build ${p.version.slice(0,12)}`:'');});
 try {
  registration=await navigator.serviceWorker.register(new URL('service-worker.js',new URL(import.meta.env.BASE_URL,location.href)),{scope:import.meta.env.BASE_URL,type:'classic'});
  const watch=worker=>worker?.addEventListener('statechange',()=>{if(worker.state==='installed')showUpdate();});
  registration.addEventListener('updatefound',()=>watch(registration.installing));watch(registration.installing);showUpdate();
  navigator.serviceWorker.controller?.postMessage({type:'offline-status'});
  registration.update().catch(()=>{});
  navigator.storage?.persist?.().catch(()=>{});
 }catch{badge.textContent='Offline storage unavailable';}
}
