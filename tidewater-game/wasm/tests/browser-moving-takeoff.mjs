import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {Worker} from 'node:worker_threads';
// Take-off from the AERODOCK while it drives its route at about 1.4 m/s.
const base=new URL('../../app/public/landing/',import.meta.url).href;
const meta=JSON.parse(await fs.readFile(new URL('../../simulation/runtime/live-map.json',import.meta.url)));
const raw=await fs.readFile(new URL('../../simulation/runtime/live-heights.bin',import.meta.url));
const worker=new Worker(new URL('runtime-worker.mjs',import.meta.url));
let latest,error,disposed,sequence=0;
worker.on('message',p=>{if(p.error)error=new Error(p.error);if(p.disposed)disposed=p;else if(p.bodies)latest=p;});worker.on('error',e=>error=e);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const wait=async(predicate,timeout=60000)=>{const start=performance.now();while(!predicate()){if(error)throw error;if(performance.now()-start>timeout)throw new Error('Moving take-off timed out: '+JSON.stringify({time:latest?.time_s,drone:latest?.drone}));await sleep(10);}};
const send=p=>worker.postMessage({...p,sequence:++sequence});
worker.postMessage({type:'initialize',base,meta,heights:raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)});
try {
 await wait(()=>latest?.ready&&latest.drone.px4_ready,90000);
 send({action:'autopilot',enabled:true});await wait(()=>latest.boat.speed>1.2);
 send({action:'takeoff'});const start=latest.time_s,modes=new Set();let maxTilt=0,offsetAtClearance=null,last=null;
 await wait(()=>{
  if(latest===last)return false;last=latest;const d=latest.drone,b=latest.boat,above=d.position[1]-b.position[1];
  modes.add(d.px4_mode);
  if(d.armed&&above<1.6)maxTilt=Math.max(maxTilt,Math.abs(d.pitch),Math.abs(d.roll));
  if(offsetAtClearance===null&&above>1.6)offsetAtClearance=Math.hypot(d.position[0]-b.position[0],d.position[2]-b.position[2]);
  return above>1.9||latest.time_s>start+25;
 },120000);
 const d=latest.drone,b=latest.boat;
 assert(!modes.has(12),'PX4 must not fall back to a blind descent on a moving deck');
 assert(d.position[1]-b.position[1]>1.9,'The drone must climb clear of the moving deck within 25 s');
 assert(offsetAtClearance<.8,'The drone must leave the bay vertically relative to the boat: '+offsetAtClearance);
 assert(maxTilt<.2,'No braking against the boat during lift-off: '+maxTilt);
 console.log(`Moving-deck take-off at ${b.speed.toFixed(2)} m/s: clear in ${(latest.time_s-start).toFixed(1)} s, offset ${offsetAtClearance.toFixed(2)} m at clearance, max tilt ${maxTilt.toFixed(2)} rad.`);
}finally{worker.postMessage({type:'shutdown'});try{await wait(()=>disposed,60000);}finally{await worker.terminate();}}
