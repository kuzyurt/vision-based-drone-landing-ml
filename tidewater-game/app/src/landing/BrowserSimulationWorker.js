import loadMujoco from '@mujoco/mujoco';
import mujocoWasm from '@mujoco/mujoco/mujoco.wasm?url';
import {BrowserForces} from './BrowserForces.js';
import {BrowserPX4} from './BrowserPX4.js';
import {BrowserGame} from './BrowserGame.js';
import {compileWorld,chooseRoute} from './BrowserWorld.js';

let game=null,module=null,stopped=false;
const status=message=>postMessage({status:message,ready:false});
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function dispose() {
 stopped=true;module?.PThread?.terminateAllThreads();postMessage({disposed:true});
}
self.onmessage=event=>{
 const p=event.data;
 if(p.type==='initialize')start(p).catch(error=>{stopped=true;module?.PThread?.terminateAllThreads();postMessage({ready:false,status:'Browser simulation stopped',error:error.stack||error.message});});
 else if(p.type==='shutdown')dispose();
 else game?.input(p);
};
async function start({base,meta,heights}) {
 if(!self.crossOriginIsolated || typeof SharedArrayBuffer==='undefined')throw new Error('PX4 needs cross-origin isolation. Use the included Tidewater static server, then reload the game.');
 status('Loading MuJoCo WebAssembly');
 const map={meta,heights:new Float32Array(heights)},c=await (await fetch(base+'physics/configuration.json')).json();
 const boot=await (await fetch(base+'physics/px4-startup.json')).json();
 const mj=await loadMujoco({locateFile:name=>name.endsWith('.wasm')?mujocoWasm:name});
 const model=await compileWorld(mj,c,map,base+'physics/',status);
 // World geoms come before articulated bodies in MuJoCo. Resolve original
 // geometry masks by name instead of reusing indices from the smaller model.
 const types=Array.from(model.geom_contype),affinity=Array.from(model.geom_conaffinity);
 c.geom_names.forEach((name,i)=>{const id=mj.mj_name2id(model,mj.mjtObj.mjOBJ_GEOM.value,name);if(id>=0){types[id]=c.geom_contype_initial[i];affinity[id]=c.geom_conaffinity_initial[i];}});
 c.geom_contype_initial=types;c.geom_conaffinity_initial=affinity;
 const data=new mj.MjData(model),forces=new BrowserForces(mj,model,data,c);
 BrowserGame.initializePose(mj,model,data,c,chooseRoute(map));
 status('Starting the original PX4 controller');
 const url=base+'wasm/px4.mjs',factory=(await import(/* @vite-ignore */url)).default;
 module=await factory({noInitialRun:true,mainScriptUrlOrBlob:url,locateFile:name=>base+'wasm/'+name,print:()=>{},printErr:line=>console.warn('PX4:',line)});
 const px4=new BrowserPX4(module,mj,model,data,forces,c);px4.onStartup=command=>status('Starting PX4 · '+command.split(' ')[0]);
 await px4.initialize(boot);if(stopped)return;
 game=new BrowserGame(mj,model,data,forces,px4,c,map);postMessage(game.state(1,true));
 let due=performance.now(),published=due,measured=due,simTime=data.time,realtimeFactor=1;
 while(!stopped) {
  const begin=performance.now();let cycles=0;
  // Yield often so keyboard events reach the worker even during catch-up.
  while(performance.now()>=due && cycles<8 && performance.now()-begin<8 && !stopped){await game.advance();due+=4;cycles++;}
  const now=performance.now();
  if(now-due>250)due=now;
  if(now-measured>=1000){realtimeFactor=(data.time-simTime)/((now-measured)/1000);simTime=data.time;measured=now;}
  if(now-published>=25){postMessage(game.state(realtimeFactor));published=now;}
  await delay(Math.max(0,Math.min(4,due-performance.now())));
 }
}
