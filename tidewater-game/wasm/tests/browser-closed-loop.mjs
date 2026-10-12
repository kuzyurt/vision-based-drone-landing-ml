import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import loadMujoco from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
import loadPX4 from '../../app/public/landing/wasm/px4.mjs';
import {BrowserForces} from '../../app/src/landing/BrowserForces.js';
import {BrowserPX4} from '../../app/src/landing/BrowserPX4.js';
const base=new URL('../../app/public/landing/physics/',import.meta.url),c=JSON.parse(await fs.readFile(new URL('configuration.json',base),'utf8'));
const boot=JSON.parse(await fs.readFile(new URL('px4-startup.json',base),'utf8')),mj=await loadMujoco();
mj.FS.writeFile('/closed.mjb',await fs.readFile(new URL('closed-loop.mjb',import.meta.url)));
const vfs=new mj.MjVFS(),m=mj.MjModel.from_binary_path('/closed.mjb',vfs);vfs.delete();
const types=Array.from(m.geom_contype),aff=Array.from(m.geom_conaffinity);
c.geom_names.forEach((name,i)=>{const id=mj.mj_name2id(m,mj.mjtObj.mjOBJ_GEOM.value,name);if(id>=0){types[id]=c.geom_contype_initial[i];aff[id]=c.geom_conaffinity_initial[i];}});c.geom_contype_initial=types;c.geom_conaffinity_initial=aff;
const d=new mj.MjData(m);d.qpos.set(c.qpos_initial);d.qpos.set([0,0,.225,1,0,0,0],c.drone.free_qadr);d.qvel.fill(0);
mj.mj_setState(m,d,new Float64Array(c.eq_active_initial),mj.mjtState.mjSTATE_EQ_ACTIVE.value);mj.mj_forward(m,d);
const f=new BrowserForces(mj,m,d,c),module=await loadPX4({noInitialRun:true,print:()=>{},printErr:console.error}),p=new BrowserPX4(module,mj,m,d,f,c);
await p.initialize(boot);
function snapshot(){const q=c.drone.free_qadr,v=c.drone.free_vadr;return [d.time,...d.qpos.subarray(q,q+7),...d.qvel.subarray(v,v+6),...c.drone.rotor_dofs.map(i=>d.qvel[i]),...f.commands,...c.drone.camera_qpos.map(i=>d.qpos[i]),f.voltage,f.current,f.charge];}
let next=0,requested=false,settled=false,requestAt,armedAt;
for(let cycle=0;cycle<15000;cycle++) {
 if(d.time>=next){if(p.observation()[0] && d.time>8 && !requested){p.flightRequested=true;p.targetHeight=1.5;p.armRequestTime=0;requested=true;requestAt=d.time;}p.pilot([]);next=d.time+.04;}
 await p.advance();if(p.armed && armedAt===undefined)armedAt=d.time;
 const v=f.velocity(c.drone.base,Array.from(d.xipos.subarray(c.drone.base*3,c.drone.base*3+3)));
 if(p.armed && Math.abs(d.xpos[c.drone.base*3+2]-1.5)<.04 && Math.abs(v[5])<.04){settled=true;break;}
 if(cycle%10===0)await new Promise(r=>setTimeout(r,0));
}
assert(settled,'PX4 WASM did not reach stable reference hover');console.log('Browser hover settled',d.time);
const initial=snapshot(),samples=[],phases=[],begin=performance.now(),start=d.time;
for(const [name,keys,duration] of [['forward',['KeyW'],2],['brake',[],3],['right',['KeyD'],2],['yaw',['KeyE'],2],['climb',['KeyR'],2],['descend',['KeyF'],2],['camera',['ArrowLeft','ArrowUp'],1],['hover',[],3]]) {
 const phaseStart=samples.length;
 for(let cycle=0;cycle<Math.round(duration/.004);cycle++){if(cycle%10===0)p.pilot(keys);await p.advance();const row=snapshot();row[0]-=start;samples.push(row);if(cycle%10===0)await new Promise(r=>setTimeout(r,0));}
 phases.push({name,start:phaseStart,end:samples.length});console.log(name,'complete');
}
const wall=(performance.now()-begin)/1000;
async function f64(name){const b=await fs.readFile(new URL(name,import.meta.url));return new Float64Array(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));}
const reference=await f64('px4-reference-samples.f64'),refInitial=await f64('px4-reference-initial.f64');
function metrics(lo=0,hi=samples.length) {
 let position=0,velocity=0,attitude=0,rotor=0,camera=0;
 for(let k=lo;k<hi;k++){const a=samples[k],b=reference.subarray(k*27,(k+1)*27);
  position=Math.max(position,Math.hypot(...[1,2,3].map(i=>a[i]-initial[i]-b[i]+refInitial[i])));
  velocity=Math.max(velocity,Math.hypot(...[8,9,10].map(i=>a[i]-b[i])));
  attitude=Math.max(attitude,2*Math.acos(Math.min(1,Math.abs([4,5,6,7].reduce((s,i)=>s+a[i]*b[i],0))))*180/Math.PI);
  for(let i=14;i<18;i++)rotor=Math.max(rotor,Math.abs(a[i]-b[i])*60/(2*Math.PI));
  for(let i=22;i<24;i++)camera=Math.max(camera,Math.abs(a[i]-b[i])*180/Math.PI);
 }
 return {position_max_m:position,velocity_max_m_s:velocity,attitude_max_deg:attitude,rotor_max_rpm:rotor,camera_max_deg:camera};
}
const report={px4_revision:c.px4_revision,mujoco:c.mujoco_version,closed_loop:metrics(),phases:phases.map(p=>({name:p.name,...metrics(p.start,p.end)})),performance:{simulated_seconds:d.time-start,wall_seconds:wall,compute_realtime_factor:(d.time-start)/wall,arming_delay_sim_s:armedAt-requestAt,takeoff_to_hover_sim_s:start-requestAt}};
report.passed=report.closed_loop.position_max_m<.05 && report.closed_loop.velocity_max_m_s<.1 && report.closed_loop.attitude_max_deg<2;
await fs.writeFile(new URL('../../benchmarks/flight-parity/browser-closed-loop.json',import.meta.url),JSON.stringify(report,null,2));
await fs.writeFile(new URL('../../benchmarks/flight-parity/browser.csv',import.meta.url),samples.map(row=>row.join(',')).join('\n'));
console.log(report);module.PThread.terminateAllThreads();assert(report.passed,'Browser PX4 differs beyond measured reference tolerance');process.exit(0);
