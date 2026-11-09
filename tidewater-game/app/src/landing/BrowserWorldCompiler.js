import loadMujoco from '@mujoco/mujoco';
import mujocoWasm from '@mujoco/mujoco/mujoco.wasm?url';
import {compileWorldBinary} from './BrowserWorld.js';

self.onmessage=async event=>{
 try{
  const {base,c,meta,heights}=event.data;
  const mj=await loadMujoco({locateFile:name=>name.endsWith('.wasm')?mujocoWasm:name});
  const fetchAsset=async url=>{const response=await fetch(url);if(!response.ok)throw new Error(`Missing simulation asset: ${url} (${response.status})`);return new Uint8Array(await response.arrayBuffer());};
  const binary=await compileWorldBinary(mj,c,{meta,heights},base,status=>postMessage({status}),fetchAsset);
  postMessage({binary},[binary.buffer]);
 }catch(error){postMessage({error:error.stack||error.message});}
};
