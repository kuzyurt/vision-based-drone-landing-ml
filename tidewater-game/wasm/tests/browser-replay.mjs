import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import loadMujoco from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
import {BrowserForces} from '../../app/src/landing/BrowserForces.js';
const directory=new URL('../../app/public/landing/physics/',import.meta.url);
const c=JSON.parse(await fs.readFile(new URL('configuration.json',directory),'utf8'));
const mj=await loadMujoco();mj.FS.writeFile('/vehicles.mjb',gunzipSync(await fs.readFile(new URL('vehicles.mjb.gz',import.meta.url))));
const vfs=new mj.MjVFS(),m=mj.MjModel.from_binary_path('/vehicles.mjb',vfs);vfs.delete();mj.FS.unlink('/vehicles.mjb');
const report=[];
for(const name of ['throttle_steps','differential_motors','camera_ramp']) {
 const d=new mj.MjData(m);d.qpos.set(c.qpos_initial);d.qvel.fill(0);d.qpos.set([0,0,50,1,0,0,0],c.drone.free_qadr);
 mj.mj_setState(m,d,new Float64Array(c.eq_active_initial),mj.mjtState.mjSTATE_EQ_ACTIVE.value);mj.mj_forward(m,d);
 const f=new BrowserForces(mj,m,d,c),raw=await fs.readFile(new URL(name+'.f64',import.meta.url));
 const reference=new Float64Array(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength));
 let maxPosition=0,maxVelocity=0,maxRotor=0,maxCamera=0,maxVoltage=0;const begin=performance.now();
 for(let cycle=0;cycle<750;cycle++) {
  const t=cycle*.004;f.commands.fill(t<1?.42:t<2?.48:.43);
  if(name==='differential_motors' && t>1 && t<2) for(let i=0;i<4;i++)f.commands[i]+=[.01,-.01,-.01,.01][i];
  if(name==='camera_ramp'){f.pan=Math.min(t*.4,.6);f.tilt=-Math.min(t*.3,.4);}
  for(let i=0;i<4;i++)f.step(true);
  const row=reference.subarray(cycle*27,cycle*27+27),q=c.drone.free_qadr,v=c.drone.free_vadr;
  maxPosition=Math.max(maxPosition,Math.hypot(...[0,1,2].map(i=>d.qpos[q+i]-row[1+i])));
  maxVelocity=Math.max(maxVelocity,Math.hypot(...[0,1,2].map(i=>d.qvel[v+i]-row[8+i])));
  for(let i=0;i<4;i++)maxRotor=Math.max(maxRotor,Math.abs(d.qvel[c.drone.rotor_dofs[i]]-row[14+i])*60/(2*Math.PI));
  for(let i=0;i<2;i++)maxCamera=Math.max(maxCamera,Math.abs(d.qpos[c.drone.camera_qpos[i]]-row[22+i])*180/Math.PI);
  maxVoltage=Math.max(maxVoltage,Math.abs(f.voltage-row[24]));
 }
 const result={name,maxPosition,maxVelocity,maxRotor,maxCamera,maxVoltage,wallSeconds:(performance.now()-begin)/1000};report.push(result);console.log(result);
 assert(maxPosition<.003 && maxRotor<2 && maxCamera<.1,'Browser forces differ from original MuJoCo replay');d.delete();
}
await fs.writeFile(new URL('../../benchmarks/flight-parity/browser-replay.json',import.meta.url),JSON.stringify(report,null,2));
m.delete();
