import fs from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';
import loadMujoco from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
import loadPX4 from '../../app/public/landing/wasm/px4.mjs';
import { BrowserForces } from '../../app/src/landing/BrowserForces.js';
import { BrowserPX4 } from '../../app/src/landing/BrowserPX4.js';

const directory=new URL('../../app/public/landing/physics/',import.meta.url);
const config=JSON.parse(await fs.readFile(new URL('configuration.json',directory),'utf8'));
const boot=JSON.parse(await fs.readFile(new URL('px4-startup.json',directory),'utf8'));
const mj=await loadMujoco();mj.FS.writeFile('/vehicles.mjb',gunzipSync(await fs.readFile(new URL('vehicles.mjb.gz',directory))));
const start=performance.now();const vfs=new mj.MjVFS();const model=mj.MjModel.from_binary_path('/vehicles.mjb',vfs);vfs.delete();mj.FS.unlink('/vehicles.mjb');
console.log('Browser binary CAD loaded:',model.nbody,'bodies;',performance.now()-start,'ms');
const data=new mj.MjData(model);data.qpos.set(config.qpos_initial);data.qvel.set(config.qvel_initial);
mj.mj_setState(model,data,new Float64Array(config.eq_active_initial),mj.mjtState.mjSTATE_EQ_ACTIVE.value);
mj.mj_forward(model,data);
const forces=new BrowserForces(mj,model,data,config);
const module=await loadPX4({noInitialRun:true,print:line=>{if(/WARN|ERROR|ERR|Armed|arming|commander|ekf/.test(line))console.log(line);},printErr:console.error});
console.log('Browser PX4 loaded; heap',!!module.HEAPF64);
const px4=new BrowserPX4(module,mj,model,data,forces,config);
px4.onStartup=console.log;
await px4.initialize(boot);console.log('All PX4 browser flight modules started');
let nextControl=0,requested=false;const run=performance.now();
for(let cycle=0;cycle<8000;cycle++) {
    if(data.time>=nextControl) {
        const obs=px4.observation();
        if(obs[0] && data.time>=8 && !requested) {px4.flightRequested=true;px4.targetHeight=1.5;px4.armRequestTime=data.time;requested=true;}
        px4.pilot([]);nextControl=data.time+.04;
    }
    await px4.advance();
    if(cycle%250===0) console.log('Simulation',data.time.toFixed(3),'armed',px4.armed,'height',data.xpos[config.drone.base*3+2].toFixed(3),'observation',Array.from(px4.observation()).slice(0,4));
    // Permit Emscripten's pending thread proxies to drain.
    if(cycle%10===0) await new Promise(resolve=>setTimeout(resolve,0));
}
console.log('Flight simulation:',data.time,'seconds in',(performance.now()-run)/1000,'wall seconds');
process.exit(0);
