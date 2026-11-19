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
// Rotor hubs in the drone body frame (x forward, y left): prop_1..4 = PX4 motors 1..4.
const PROPS=[[.177,-.177],[.177,.1765],[-.1765,.1765],[-.1765,-.177]];
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
  send({action:'takeoff'});const start=latest.time_s,modes=new Set();let maxTilt=0,offsetAtClearance=null,last=null,rearLead=0,rampSamples=0,trailingLead=0;
  await wait(()=>{
   if(latest===last)return false;last=latest;const d=latest.drone,b=latest.boat,above=d.position[1]-b.position[1];
   modes.add(d.px4_mode);
   // spool-up on the deck: rotors 0/1 are the forward pair, 2/3 the rear pair
   const m=d.motor_commands,mean=(m[0]+m[1]+m[2]+m[3])/4;if(d.armed&&mean>.05&&mean<.45){rearLead+=(m[2]+m[3]-m[0]-m[1])/2;rampSamples++;
    // the same against the drone's motion: the pair behind it along its velocity must lead, whichever way it faces
    const vE=d.velocity[0],vN=-d.velocity[2],c=Math.cos(d.yaw),s=Math.sin(d.yaw),fwd=vE*c+vN*s,left=-vE*s+vN*c,sp=Math.hypot(fwd,left)||1;
    for(let i=0;i<4;i++)trailingLead+=m[i]*-((PROPS[i][0]*fwd+PROPS[i][1]*left)/sp)/.25;}
   if(d.armed&&above<1.6)maxTilt=Math.max(maxTilt,Math.abs(d.pitch),Math.abs(d.roll));
   if(offsetAtClearance===null&&above>1.6)offsetAtClearance=Math.hypot(d.position[0]-b.position[0],d.position[2]-b.position[2]);
   return above>1.9||latest.time_s>start+25;
  },120000);
  const d=latest.drone,b=latest.boat;
  assert(!modes.has(12),'PX4 must not fall back to a blind descent on a moving deck');
  assert(d.position[1]-b.position[1]>1.9,`The drone must climb clear of the moving deck within 25 s (${test.name})`);
  assert(offsetAtClearance<test.maximumOffset,`The drone must leave the bay vertically relative to the boat (${test.name}): `+offsetAtClearance);
  assert(rampSamples>0&&rearLead/rampSamples>-.01,`The forward rotor pair must not lead the spool-up on a moving deck (${test.name}): `+rearLead/rampSamples);
  assert(trailingLead/rampSamples>.01,`The rotor pair facing away from the motion must lead the spool-up (${test.name}): `+trailingLead/rampSamples);
  assert(maxTilt<.2,`No braking against the boat during lift-off (${test.name}): `+maxTilt);
  console.log(`Moving-deck take-off, ${test.name}, at ${b.speed.toFixed(2)} m/s: clear in ${(latest.time_s-start).toFixed(1)} s, offset ${offsetAtClearance.toFixed(2)} m at clearance, max tilt ${maxTilt.toFixed(2)} rad, trailing-pair lead ${(trailingLead/rampSamples).toFixed(3)}.`);
 }finally{worker.postMessage({type:'shutdown'});try{await wait(()=>disposed,60000);}finally{await worker.terminate();}}
}
