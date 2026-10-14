export async function registerOffline() {
 if(import.meta.env.DEV || !('serviceWorker' in navigator))return;
 const badge=document.createElement('div');badge.setAttribute('role','status');badge.style.cssText='position:fixed;bottom:6px;right:10px;z-index:10000;color:#d6eeee;background:#10232ddd;padding:4px 8px;font:11px system-ui;border-radius:4px;pointer-events:none';badge.textContent='Preparing offline files…';document.body.append(badge);
 navigator.serviceWorker.addEventListener('message',event=>{const p=event.data?.offline;if(!p)return;badge.textContent=p.status==='ready'?'Offline files ready':p.status==='unavailable'?'Offline storage unavailable':`Preparing offline files${p.total?` · ${Math.round(100*p.complete/p.total)}%`:''}…`;});
 try {
  const registration=await navigator.serviceWorker.register(new URL('service-worker.js',new URL(import.meta.env.BASE_URL,location.href)),{scope:import.meta.env.BASE_URL,type:'classic'});
  (registration.active||registration.waiting)?.postMessage({type:'offline-status'});
  navigator.storage?.persist?.().catch(()=>{});
 }catch{badge.textContent='Offline storage unavailable';}
}
