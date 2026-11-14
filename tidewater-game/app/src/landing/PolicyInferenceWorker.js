import {PolicyInference} from './PolicyInference.js';
const policy=new PolicyInference();
// Messages are handled strictly in order: a controller reset for a new flight
// can never interleave with a step that was still running for the previous one.
let queue=Promise.resolve();
const handle=async p=>{
 try{
  if(p.type==='initialize'){
   await policy.initialize({base:p.base,executionProvider:'external-webgpu',loadPython:async indexURL=>{const {loadPyodide}=await import(/* @vite-ignore */indexURL+'pyodide.mjs');return loadPyodide({indexURL});}});
   const model=policy.verifiedModel;policy.verifiedModel=null;postMessage({ready:true,checkpoint:policy.manifest.checkpoint_sha256,backend:policy.backend,inputContract:policy.manifest.input_contract,outputContract:policy.manifest.output_contract,model},[model.buffer]);
  }else if(p.type==='reset'){policy.reset();postMessage({id:p.id,reset:true});}
  else if(p.type==='numeric'){const numeric=policy.numeric(p.observation);postMessage({id:p.id,numeric},[numeric.buffer]);}
  else if(p.type==='act')postMessage({id:p.id,...await policy.act(p.rgb,p.observation,p.elapsed,p.prediction,p.search)});
 }catch(error){postMessage({id:p.id,error:error.stack||error.message});}
};
self.onmessage=event=>{const p=event.data;queue=queue.then(()=>handle(p));};
