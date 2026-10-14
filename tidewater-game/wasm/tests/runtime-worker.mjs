import {parentPort} from 'node:worker_threads';
import fs from 'node:fs/promises';
import loadMujoco from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
import loadPX4 from '../../app/public/landing/wasm/px4.mjs';
import {BrowserRuntime} from '../../app/src/landing/BrowserRuntime.js';
const runtime=new BrowserRuntime({loadMujoco,loadPX4:()=>loadPX4({noInitialRun:true,print:()=>{},printErr:()=>{}}),fetchAsset:async url=>new Uint8Array(await fs.readFile(new URL(url))),post:packet=>parentPort.postMessage(packet)});
parentPort.on('message',packet=>{
 if(packet.type==='initialize')runtime.start(packet).catch(error=>{if(!runtime.stopped)parentPort.postMessage({error:error.stack});runtime.stop();});
 else if(packet.type==='shutdown')runtime.stop().then(()=>{const p=runtime.module?.PThread;parentPort.postMessage({disposed:true,threads:(p?.runningWorkers?.length||0)+(p?.unusedWorkers?.length||0)});parentPort.close();});
 else runtime.input(packet);
});
