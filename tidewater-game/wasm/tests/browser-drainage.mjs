import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import load from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
import {BrowserForces} from '../../app/src/landing/BrowserForces.js';
const base=new URL('../../app/public/landing/physics/',import.meta.url),c=JSON.parse(await fs.readFile(new URL('configuration.json',base),'utf8'));
const mj=await load();for(const file of c.files)mj.FS.writeFile('/'+file,await fs.readFile(new URL(file,base)));
const m=mj.MjModel.from_xml_path('/vehicles.xml'),d=new mj.MjData(m);d.qpos.set(c.qpos_initial);d.qvel.set(c.qvel_initial);mj.mj_forward(m,d);
const f=new BrowserForces(mj,m,d,c),r=f.drainage,rows=JSON.parse(await fs.readFile(new URL('drainage-reference.json',import.meta.url),'utf8'));r.add(12);let maxError=0;
for(let i=0;i<120;i++){
 r.rain=i<40?100:0;r.failures=[i>=40,i>=80];const angle=(i<20?0:i<60?12:-15)*Math.PI/180,q=c.boat.free_qadr;
 d.qpos.set([Math.cos(angle/2),Math.sin(angle/2),0,0],q+3);d.qvel[c.boat.free_vadr]=2.5;d.time=(i+1)*.05;mj.mj_forward(m,d);r.step(.05);
 const values={litres:r.litres,pumped:r.totalPumped,ingress:r.totalIngress,flow:r.flow,head:r.head,mass:m.body_mass[r.body],com:Array.from(m.body_pos.subarray(r.body*3,r.body*3+3)),time:d.time,selected:r.selected};
 for(const key of Object.keys(values)){const a=[values[key]].flat(),b=[rows[i][key]].flat();for(let j=0;j<a.length;j++){if(a[j]===null){assert.equal(b[j],null);continue;}maxError=Math.max(maxError,Math.abs(a[j]-b[j]));assert(Math.abs(a[j]-b[j])<1e-8,`${i} ${key}: ${a[j]} vs ${b[j]}`);}}
}
const output=new mj.DoubleBuffer(6);d.qvel.set([1.2,-.3,.2,.1,.25,-.7],c.boat.free_vadr);mj.mj_forward(m,d);mj.mj_objectVelocity(m,d,mj.mjtObj.mjOBJ_BODY.value,c.boat.body,output,0);
const velocity=f.velocity(c.boat.body,Array.from(d.xipos.subarray(c.boat.body*3,c.boat.body*3+3)));
velocity.forEach((v,i)=>assert(Math.abs(v-output.GetView()[i])<1e-12));
assert(c.boat.act.speed_needle_position>=0);f.applyBoat();const target=(135-Math.min(Math.hypot(velocity[3],velocity[4])*3.6,30)/30*270)*Math.PI/180;assert(Math.abs(d.ctrl[c.boat.act.speed_needle_position]-target)<1e-12);
console.log('120 independent drainage samples, retained mass, clock preservation, angular/COM velocity and km/h speed needle passed; max error',maxError);output.delete();d.delete();m.delete();
