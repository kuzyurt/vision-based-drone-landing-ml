import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import load from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
import {remapConfiguration,chooseRoute,heightAt} from '../../app/src/landing/BrowserWorld.js';
import {BrowserGame} from '../../app/src/landing/BrowserGame.js';
import {BrowserForces} from '../../app/src/landing/BrowserForces.js';
const base=new URL('../../app/public/landing/physics/',import.meta.url),c=JSON.parse(await fs.readFile(new URL('configuration.json',base),'utf8')),meta=JSON.parse(await fs.readFile(new URL('../../simulation/runtime/live-map.json',import.meta.url),'utf8')),raw=await fs.readFile(new URL('../../simulation/runtime/live-heights.bin',import.meta.url));
const map={meta,heights:new Float32Array(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength))},mj=await load();mj.FS.writeFile('/world.mjb',await fs.readFile(new URL('world-smoke.mjb',import.meta.url)));const vfs=new mj.MjVFS(),m=mj.MjModel.from_binary_path('/world.mjb',vfs);vfs.delete();remapConfiguration(mj,m,c);
const d=new mj.MjData(m),f=new BrowserForces(mj,m,d,c);BrowserGame.initializePose(mj,m,d,c,chooseRoute(map));
const fake={observation:()=>new Float64Array([1]),armed:false,actuators:new Float64Array(19),advance:()=>{for(let i=0;i<4;i++)f.step(false);},pilot:()=>{},vehicleCommand:()=>{}},game=new BrowserGame(mj,m,d,f,fake,c,map);game.mode='boat';const started=performance.now();let maxError=0;
for(let i=0;i<85000 && game.travelled<game.route.length+10;i++){await game.advance();maxError=Math.max(maxError,game.courseError);}
assert(game.travelled>game.route.length+5,'Boat did not wrap a full closed route');assert(maxError<8,`Route error ${maxError}`);const lap={distance_m:game.travelled,max_error_m:maxError,simulated_seconds:d.time,wall_seconds:(performance.now()-started)/1000};
await fs.writeFile(new URL('../../benchmarks/flight-parity/browser-environment.json',import.meta.url),JSON.stringify(lap,null,2));
console.log('Full closed route lap:',game.travelled,'m, max error',maxError,'m,',d.time,'sim s /',(performance.now()-started)/1000,'wall s');
for(const [x,y] of [[0,0],[120,-170],[-80,50]]){const rendered=game.state().waves.reduce((sum,[kx,kz,a,phase])=>sum+a*Math.cos(kx*x+kz*(-y)+phase),0);assert(Math.abs(rendered-f.wave(x,y,0)[0])<1e-12);}
const q=c.drone.free_qadr,original=Array.from(d.qpos.subarray(q,q+3));d.qpos.set([1000,1000,2],q);mj.mj_forward(m,d);
for(let i=0;i<6;i++){d.time+=.25;game.updateRadio();}assert(!game.radio.connected);
d.qpos.set(original,q);mj.mj_forward(m,d);for(let i=0;i<10;i++){d.time+=.25;game.updateRadio();}assert(!game.radio.connected);game.input({action:'reconnect'});
for(let i=0;i<40;i++){d.time+=.25;game.updateRadio();}assert(game.radio.connected);assert(game.radio.telemetry_age_s<1);
const hull=mj.mj_name2id(m,mj.mjtObj.mjOBJ_GEOM.value,'hull_contact');assert((m.geom_contype[hull]&3)||(12&m.geom_conaffinity[hull]));
for(let i=0;i<16;i++){const id=mj.mj_name2id(m,mj.mjtObj.mjOBJ_GEOM.value,`shore_contact_${i}`);if(id>=0)assert.equal(m.geom_contype[id],0);}
const terrainIds=new Set();for(let i=0;i<m.ngeom;i++)if(mj.mj_id2name(m,mj.mjtObj.mjOBJ_GEOM.value,i).startsWith('tidewater_terrain_')){terrainIds.add(i);assert.equal(m.geom_contype[i],12);assert.equal(m.geom_conaffinity[i],3);}
const b=c.boat.free_qadr;d.qpos.set([0,100,heightAt(map,0,100)-.1],b);d.qpos.set([1,0,0,0],b+3);mj.mj_forward(m,d);
const contacts=d.contact;let shoreline=false;try{for(let i=0;i<contacts.size();i++){const contact=contacts.get(i);try{if([...contact.geom].some(g=>terrainIds.has(g)))shoreline=true;}finally{contact.delete?.();}}}finally{contacts.delete();}assert(shoreline,'Boat did not collide with actual shoreline terrain');
console.log('Radio loss/manual reconnect, stale shore proxy masks and actual tiled-terrain contact passed');d.delete();m.delete();
