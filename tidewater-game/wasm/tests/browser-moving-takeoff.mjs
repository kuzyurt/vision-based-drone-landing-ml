import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {Worker} from 'node:worker_threads';
// Take-off from the AERODOCK while it drives: on its route at about 1.4 m/s, and
// under full manual throttle at about 3 m/s. The second deck is faster than the
// airframe's own 2 m/s horizontal limit (MPC_XY_VEL_MAX); PX4 used to clamp the
// carried deck velocity to that limit, so the drone braked against the boat
// inside the bay, pitched back on the wrong rotor pair and crashed.
const base=new URL('../../app/public/landing/',import.meta.url).href;
const meta=JSON.parse(await fs.readFile(new URL('../../simulation/runtime/live-map.json',import.meta.url)));
const raw=await fs.readFile(new URL('../../simulation/runtime/live-heights.bin',import.meta.url));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const CASES=[
 {name:'route following',drive:{action:'autopilot',enabled:true},minimumSpeed:1.2,maximumOffset:.8},
 // at twice the speed the release of the carried velocity (from 0.9 m up) moves the drone further by 1.6 m
 {name:'full manual throttle',drive:{mode:'boat',motors:[100,100]},minimumSpeed:2.6,maximumOffset:1.2},
];
for(const test of CASES) {
 const worker=new Worker(new URL('runtime-worker.mjs',import.meta.url));
 let latest,error,disposed,sequence=0;
 worker.on('message',p=>{if(p.error)error=new Error(p.error);if(p.disposed)disposed=p;else if(p.bodies)latest=p;});worker.on('error',e=>error=e);
 const wait=async(predicate,timeout=60000)=>{const start=performance.now();while(!predicate()){if(error)throw error;if(performance.now()-start>timeout)throw new Error(`Moving take-off (${test.name}) timed out: `+JSON.stringify({time:latest?.time_s,drone:latest?.drone}));await sleep(10);}};
 const send=p=>worker.postMessage({...p,sequence:++sequence});
 worker.postMessage({type:'initialize',base,meta,heights:raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)});
 try {
  await wait(()=>latest?.ready&&latest.drone.px4_ready,90000);
  send(test.drive);await wait(()=>latest.boat.speed>test.minimumSpeed);
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
  assert(d.position[1]-b.position[1]>1.9,`The drone must climb clear of the moving deck within 25 s (${test.name})`);
  assert(offsetAtClearance<test.maximumOffset,`The drone must leave the bay vertically relative to the boat (${test.name}): `+offsetAtClearance);
  assert(maxTilt<.2,`No braking against the boat during lift-off (${test.name}): `+maxTilt);
  console.log(`Moving-deck take-off, ${test.name}, at ${b.speed.toFixed(2)} m/s: clear in ${(latest.time_s-start).toFixed(1)} s, offset ${offsetAtClearance.toFixed(2)} m at clearance, max tilt ${maxTilt.toFixed(2)} rad.`);
 }finally{worker.postMessage({type:'shutdown'});try{await wait(()=>disposed,60000);}finally{await worker.terminate();}}
}
