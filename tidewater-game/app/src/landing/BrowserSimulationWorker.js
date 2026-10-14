import loadMujoco from '@mujoco/mujoco';
import mujocoWasm from '@mujoco/mujoco/mujoco.wasm?url';
import {BrowserRuntime} from './BrowserRuntime.js';

const runtime=new BrowserRuntime({
 isolated:self.crossOriginIsolated && typeof SharedArrayBuffer!=='undefined',
 post:packet=>postMessage(packet),
 fetchAsset:async url=>{const response=await fetch(url);if(!response.ok)throw new Error(`Missing simulation asset: ${url} (${response.status})`);return new Uint8Array(await response.arrayBuffer());},
 loadMujoco:()=>loadMujoco({locateFile:name=>name.endsWith('.wasm')?mujocoWasm:name}),
 loadPX4:async base=>{const url=base+'wasm/px4.mjs',factory=(await import(/* @vite-ignore */url)).default;return factory({noInitialRun:true,mainScriptUrlOrBlob:url,locateFile:name=>base+'wasm/'+name,print:()=>{},printErr:line=>console.warn('PX4:',line)});},
});
self.onmessage=event=>{
 const packet=event.data;
 if(packet.type==='initialize')runtime.start(packet).catch(error=>{if(!runtime.stopped)postMessage({ready:false,status:'Browser simulation startup failed',error:error.stack||error.message});runtime.stop();});
 else if(packet.type==='shutdown')runtime.stop().then(()=>postMessage({disposed:true}));
 else runtime.input(packet);
};
