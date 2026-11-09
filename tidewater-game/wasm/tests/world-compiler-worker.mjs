import {parentPort} from 'node:worker_threads';
import fs from 'node:fs/promises';
import loadMujoco from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
import {compileWorldBinary} from '../../app/src/landing/BrowserWorld.js';
parentPort.on('message',async ({base,c,meta,heights})=>{
 try{
  const mj=await loadMujoco();
  const binary=await compileWorldBinary(mj,c,{meta,heights},base,status=>parentPort.postMessage({status}),async url=>new Uint8Array(await fs.readFile(new URL(url))));
  parentPort.postMessage({binary},[binary.buffer]);
 }catch(error){parentPort.postMessage({error:error.stack||error.message});}
});
