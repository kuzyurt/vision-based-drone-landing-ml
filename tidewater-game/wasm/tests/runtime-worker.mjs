import {parentPort} from 'node:worker_threads';
import fs from 'node:fs/promises';
import loadMujoco from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
import loadPX4 from '../../app/public/landing/wasm/px4.mjs';
import {BrowserRuntime} from '../../app/src/landing/BrowserRuntime.js';
import {prepareBrowserWorld} from '../../app/src/landing/PrepareBrowserWorld.js';
import {createCompilerWorker} from './world-compiler-adapter.mjs';
import {BrowserPX4} from '../../app/src/landing/BrowserPX4.js';
import {PolicyLandingResult} from '../../app/src/landing/PolicyLandingResult.js';
import {BrowserForces} from '../../app/src/landing/BrowserForces.js';
const profile={physics_ms:0,assessment_ms:0,steps:0},profiling=!!process.env.TIDEWATER_PROFILE_TIMING;
if(profiling){const advance=BrowserPX4.prototype.advance,update=PolicyLandingResult.prototype.update;BrowserPX4.prototype.advance=async function(){const start=performance.now();try{return await advance.call(this);}finally{profile.physics_ms+=performance.now()-start;profile.steps++;}};PolicyLandingResult.prototype.update=function(dt){const start=performance.now();try{return update.call(this,dt);}finally{profile.assessment_ms+=performance.now()-start;}};}
if(profiling)for(const name of ['beforeStep','applyBoat','applyDrone','afterStep']){const original=BrowserForces.prototype[name];BrowserForces.prototype[name]=function(...args){const start=performance.now();try{return original.apply(this,args);}finally{profile[name]=(profile[name]||0)+performance.now()-start;}};}
const runtime=new BrowserRuntime({loadMujoco,prepareWorld:options=>prepareBrowserWorld({...options,createWorker:createCompilerWorker}),loadPX4:()=>loadPX4({noInitialRun:true,print:()=>{},printErr:()=>{}}),fetchAsset:async url=>new Uint8Array(await fs.readFile(new URL(url))),post:packet=>{if(profiling&&packet.bodies)packet.verification_profile={...profile};parentPort.postMessage(packet);}});
parentPort.on('message',packet=>{
 if(packet.type==='initialize')runtime.start(packet).catch(error=>{if(!runtime.stopped)parentPort.postMessage({error:error.stack});runtime.stop();});
 else if(packet.type==='shutdown')runtime.stop().then(()=>{const p=runtime.module?.PThread;parentPort.postMessage({disposed:true,threads:(p?.runningWorkers?.length||0)+(p?.unusedWorkers?.length||0)});parentPort.close();});
 else runtime.input(packet);
});
