import fs from 'node:fs/promises';
import {Worker} from 'node:worker_threads';
import assert from 'node:assert/strict';
import {PoseTimeline} from '../../app/src/landing/PoseTimeline.js';
const visual=JSON.parse(await fs.readFile(new URL('../../app/public/landing/vehicles.json',import.meta.url),'utf8')),meshNames=new Set(visual.geoms.map(g=>g.name));
const base=new URL('../../app/public/landing/',import.meta.url).href;
const meta=JSON.parse(await fs.readFile(new URL('../../simulation/runtime/live-map.json',import.meta.url),'utf8'));
const raw=await fs.readFile(new URL('../../simulation/runtime/live-heights.bin',import.meta.url));
const report={kind:'headless Node worker; no browser/render FPS measurement',sessions:[],cancelled_startups:[],input_latency_ms:[]};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function session(full=false,cancelDelay=null) {
 const worker=new Worker(new URL('runtime-worker.mjs',import.meta.url));let latest=null,error=null,disposed=null,phase='';
 let layout=null;
 const timeline=new PoseTimeline(),started=performance.now();let frames=0,last=-Infinity;
 worker.on('message',packet=>{if(packet.status)phase=packet.status;if(packet.geoms)layout=packet.geoms;if(packet.error)error=new Error(packet.error);if(packet.disposed)disposed=packet;else if(packet.bodies){latest=packet;timeline.push(packet,performance.now());}});
 worker.on('error',e=>error=e);
 const exited=new Promise((resolve,reject)=>worker.on('exit',code=>code?reject(new Error(`Worker exit ${code}`)):resolve()));
 const render=setInterval(()=>{const sample=timeline.sample(performance.now());if(sample){assert(sample.time>=last);last=sample.time;frames++;}},40);
 const wait=async(predicate,timeout=90000)=>{const start=performance.now();while(!predicate()){if(error)throw error;if(performance.now()-start>timeout)throw new Error('Worker integration timed out: '+JSON.stringify({phase,time:latest?.time_s,boat:latest?.boat,message:latest?.message}));await sleep(10);}return latest;};
 let sequence=0;const input=async payload=>{const n=++sequence,t=performance.now();worker.postMessage({...payload,sequence:n});await wait(()=>latest?.input_sequence===n,3000);report.input_latency_ms.push(performance.now()-t);};
 worker.postMessage({type:'initialize',base,meta,heights:raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)});
 try {
  if(cancelDelay==='px4')await wait(()=>phase==='Starting the original PX4 controller');
  else if(cancelDelay!==null)await sleep(cancelDelay);
  else {
   await wait(()=>latest?.ready);const startup=performance.now()-started;
   assert(layout.length===visual.geoms.length && layout.every(([name,pose,body])=>meshNames.has(name)&&body&&pose.length===16&&pose.every(Number.isFinite)));
   assert(latest.bodies.every(([_,pose])=>pose.length===16&&pose.every(Number.isFinite)));
   assert(Object.keys(latest.views).sort().join(',')==='boat_dock,boat_nav,drone');assert(latest.hull_pose.every(Number.isFinite));assert(latest.waves.length===4);
   if(full) {
    await input({action:'autopilot',enabled:false,motors:[0,0]});await input({action:'takeoff'});await wait(()=>latest.drone.armed && Math.abs(latest.drone.position[1]-1.5)<.12,90000);
    const position=[...latest.drone.position],time=latest.time_s;await input({mode:'drone',keys:['KeyW']});await wait(()=>latest.time_s>time+2);await input({keys:[]});assert(Math.hypot(latest.drone.position[0]-position[0],latest.drone.position[2]-position[2])>.5);
    let t=latest.time_s;await wait(()=>latest.time_s>t+3);await input({keys:['KeyS']});t=latest.time_s;await wait(()=>latest.time_s>t+2);await input({keys:[]});t=latest.time_s;await wait(()=>latest.time_s>t+3);
    assert(Math.hypot(latest.drone.position[0]-position[0],latest.drone.position[2]-position[2])<.3,'Return to deck alignment');
    t=latest.time_s;await wait(()=>latest.time_s>t+15);
    await input({mode:'boat',action:'camera',name:'boat_nav'});assert.equal(latest.mode,'boat');assert.equal(latest.boat_camera,'boat_nav');
    for(const name of ['boat_dock','boat_nav','boat_dock','boat_nav']){await input({action:'camera',name});assert.equal(latest.boat_camera,name);}
    await input({action:'autopilot',enabled:false,motors:[0,0]});await input({action:'lid',open:false});assert.match(latest.message,/Lower/);
    await wait(()=>!latest.boat.mechanism_busy,15000);await input({action:'platform',raised:false});assert.equal(latest.boat.platform_target,0);await wait(()=>latest.boat.platform<.025,30000);
    await wait(()=>!latest.boat.mechanism_busy,15000);await input({action:'lid',open:false});assert.equal(latest.boat.aft_lid_target,0);await wait(()=>latest.boat.aft_lid<.025&&latest.boat.fore_lid<.025,25000);
    await wait(()=>!latest.boat.mechanism_busy,15000);await input({action:'platform',raised:true});assert.match(latest.message,/Open/);
    await input({action:'lid',open:true});await wait(()=>latest.boat.aft_lid>.978&&latest.boat.fore_lid>.978&&!latest.boat.mechanism_busy,25000);
    await input({action:'platform',raised:true});await wait(()=>latest.boat.platform>.98&&!latest.boat.mechanism_busy,30000);
    await input({mode:'drone',keys:[]});
    await input({keys:['KeyF']});const height=latest.drone.position[1];t=latest.time_s;await wait(()=>latest.time_s>t+1.5);assert(latest.drone.position[1]<height-.3);await input({keys:[]});
    await input({action:'land'});await wait(()=>latest.drone.landed&&!latest.drone.armed,60000);

   }
   report.sessions.push({startup_ms:startup,simulated_seconds:latest.time_s,realtime_factor:latest.realtime_factor,presentation_samples:frames,full});
  }
  worker.postMessage({type:'shutdown'});await wait(()=>disposed,60000);assert.equal(disposed.threads,0);if(cancelDelay!==null)report.cancelled_startups.push({requested_at:cancelDelay,threads_after_disposal:disposed.threads});await Promise.race([exited,sleep(5000).then(()=>{throw new Error('Disposed worker retained handles');})]);
 }finally{clearInterval(render);if(!disposed)await worker.terminate();}
}
await session(true);await session();await session(false,0);await session(false,250);await session(false,'px4');
report.max_input_latency_ms=Math.max(...report.input_latency_ms);assert(report.max_input_latency_ms<250,'Keyboard message delivery stalled');
await fs.writeFile(new URL('../../benchmarks/flight-parity/browser-worker-integration.json',import.meta.url),JSON.stringify(report,null,2));console.log(report);
