import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from 'pyodide';
import {PolicyInference} from '../src/landing/PolicyInference.js';
const base=new URL('../public/policy/',import.meta.url),fixtures=new URL('../../simulation/runtime/ml-fixtures/',import.meta.url),fetchOriginal=globalThis.fetch;
globalThis.fetch=async (input,options)=>{const url=new URL(input);if(url.protocol==='file:'){try{return new Response(await fs.readFile(url));}catch{return new Response('',{status:404});}}return fetchOriginal(input,options);};
const p=new PolicyInference();
const external=process.argv.includes('--external');
await p.initialize({base:base.href,executionProvider:external?'external-webgpu':'wasm',loadPython:()=>loadPyodide({indexURL:fileURLToPath(new URL('pyodide/',base))})});
const frames=JSON.parse(await fs.readFile(new URL('neural.json',fixtures),'utf8'));
for(let i=0;i<frames.length;i++){
 const f=frames[i],rgb=new Uint8Array(await fs.readFile(new URL(`rgb-${i}.bin`,fixtures)));
 const numeric=p.numeric(f.observation);assert(Math.max(...numeric.map((x,j)=>Math.abs(x-f.numeric[j])))<1e-6,'Frozen numeric observation must be unchanged');
 const start=performance.now(),result=await p.act(rgb,f.observation,f.elapsed??i*.04,external?Float32Array.from(f.prediction):undefined);
 assert.equal(result.action.length,6);assert(result.action.every(Number.isFinite));
 const error=external?null:Math.max(...p.hidden.map((x,j)=>Math.abs(x-f.next_hidden[j])));if(!external)assert(error<1e-4,`Browser WASM recurrent state mismatch ${error}`);
 const predictionError=Math.max(...p.prediction.map((x,j)=>Math.abs(x-f.prediction[j])));assert(predictionError<1e-4);
 if(f.reference_action){const actionError=Math.max(...result.action.map((x,j)=>Math.abs(x-f.reference_action[j])));assert(actionError<1e-4,`Original controller command mismatch ${actionError}`);assert.equal(result.diagnostics.control_phase,f.reference_phase);assert.equal(result.diagnostics.metric_valid,f.metric_valid);}
 console.log(JSON.stringify({frame:i,hidden_error:error,duration_ms:performance.now()-start,result}));
}
p.reset();assert(p.hidden.every(x=>x===0));
if(p.numericCount===34){
 const missing=structuredClone(frames[0].observation);missing.beacon={valid:false};
 const numeric=p.numeric(missing);assert.equal(numeric[21],0);assert(Math.abs(numeric[19]-3.1)<1e-6);assert.equal(numeric[22],p.manifest.unknown_dock_observation_mean);assert.deepEqual(Array.from(numeric.slice(32)),[100,10]);
 const stale=structuredClone(frames[0].observation);stale.beacon.age_s=4;assert.equal(p.numeric(stale)[21],0);
 const invalid=structuredClone(frames[0].observation);invalid.beacon.relative_heading_m=[1,2];assert.equal(p.numeric(invalid)[21],0);
}
await p.close();console.log(external?'Frozen numeric observation and external-GPU controller path matched original controller commands at full 640×360 resolution.':'Browser ONNX WASM and Pyodide controller ran the checkpoint at full 640×360 resolution.');
