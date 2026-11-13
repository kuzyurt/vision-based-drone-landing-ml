import {PolicyCamera} from './PolicyCamera.js';
import {GPU} from '../engine/gpu/GPU.js';

async function createSharedNeural(model,base,inputContract,outputContract){
 const {GpuPolicyModel}=await import('./GpuPolicyModel.js');const neural=new GpuPolicyModel();
 try{await neural.initialize(model,base,{device:GPU.device,adapter:GPU.adapter,inputContract,outputContract});return neural;}
 catch(error){await neural.close().catch(()=>{});throw error;}
}

export class PolicyControl {
 constructor(bridge,{createWorker=()=>new Worker(new URL('./PolicyInferenceWorker.js',import.meta.url),{type:'module',name:'AERODOCK trained landing policy'}),createCamera=()=>new PolicyCamera(bridge),createNeural=createSharedNeural}={}){this.bridge=bridge;this.createWorker=createWorker;this.createCamera=createCamera;this.createNeural=createNeural;this.requests=new Map();this.requestSequence=0;this.generation=0;this.status={enabled:false,loading:false,error:null};}
 async enable(){
  if(this.worker)return;
  if(!this.bridge.state?.drone?.armed||this.bridge.state.drone.landed||this.bridge.state.drone.landing_requested)throw new Error('Take off before enabling ML landing');
  const generation=++this.generation;this.status={enabled:false,loading:true,error:null};this.notify();
  const worker=this.createWorker();this.worker=worker;
  try{
   const base=new URL('policy/',new URL(import.meta.env?.BASE_URL||'./',location.href)).href;
   const ready=await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('Policy loading timed out')),120000);this.cancelLoad=()=>{clearTimeout(timer);reject(new DOMException('Policy loading cancelled','AbortError'));};
    worker.onerror=e=>{clearTimeout(timer);reject(new Error(e.message||'ML worker failed'));};
    worker.onmessage=e=>{if(e.data.error){clearTimeout(timer);reject(new Error(e.data.error));}else if(e.data.ready){this.backend=e.data.backend;clearTimeout(timer);resolve(e.data);}};
    worker.postMessage({type:'initialize',base});
   });
   if(generation!==this.generation)return;
   const neural=await this.createNeural(ready.model,base,ready.inputContract,ready.outputContract);
   if(generation!==this.generation){await neural.close();return;}this.neural=neural;this.adapter=neural.adapter;this.layout=neural.layout;
   this.camera??=this.createCamera();
   await this.camera.capture(this.bridge.state); // Prepare complete sensor pipelines before takeover.
   if(generation!==this.generation)return;this.cancelLoad=null;
   worker.onmessage=e=>{const p=this.requests.get(e.data.id);if(p){clearTimeout(p.timer);this.requests.delete(e.data.id);if(e.data.error)p.reject(new Error(e.data.error));else p.resolve(e.data);}};
   worker.onerror=e=>{this.disable(e.message||'ML worker failed');};
   this.awaitActivation=true;this.status={enabled:true,loading:false,error:null,checkpoint:ready.checkpoint};this.bridge.send({action:'ml',enabled:true});this.notify();
  }catch(error){if(generation===this.generation)this.disable(error.name==='AbortError'?null:error.message);}
 }
 disable(error=null){
  this.generation++;this.cancelLoad?.();this.cancelLoad=null;this.worker?.terminate();this.worker=null;
  for(const p of this.requests.values()){clearTimeout(p.timer);p.reject(new DOMException('Manual control selected','AbortError'));}this.requests.clear();
  const neural=this.neural;this.neural=null;if(neural)this.neuralCleanup=neural.close().catch(error=>console.error('ML GPU cleanup:',error));
  this.awaitActivation=false;this.status={enabled:false,loading:false,error};this.bridge.send({action:'ml',enabled:false});this.notify();
 }
 notify(){this.bridge.app.flightOps?._refreshUI();}
 request(payload,transfer=[]){
  if(!this.worker)return Promise.reject(new Error('ML worker is unavailable'));
  const id=++this.requestSequence;
  return new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>{this.requests.delete(id);reject(new Error('Policy inference timed out'));},25000);
   this.requests.set(id,{resolve,reject,timer});
   try{this.worker.postMessage({...payload,id},transfer);}catch(error){clearTimeout(timer);this.requests.delete(id);reject(error);}
  });
 }
 async capture(packet){
  const generation=this.generation;
  try {
   if(!this.worker||!this.status.enabled)throw new Error('ML policy is unavailable');
   const start=performance.now(),neural=this.neural;let neuralResult;
   // Prepare the original Python numeric observation while the sensor renders.
   // Its GPU texture feeds the network before RGB readback finishes. The CPU
   // registration still receives every original RGB pixel from that same frame.
   const numeric=this.request({type:'numeric',observation:packet.observation}).then(result=>({result}),error=>({error}));
   const rgb=await this.camera.capture(packet.state,{onSubmitted:texture=>{
    neuralResult=(async()=>{const prepared=await numeric;if(prepared.error)throw prepared.error;if(generation!==this.generation)return null;const begin=performance.now();const output=await neural.runFromTexture(texture,prepared.result.numeric);return {prediction:output.prediction,search:output.search,ms:performance.now()-begin};})().then(result=>({result}),error=>({error}));
   }});
   const captured=performance.now();
   if(generation!==this.generation)return;
   const recording=this.recordingSample;
   if(recording&&!recording.frame)recording.frame={id:packet.id,time_s:packet.state.time_s,rgb:new Uint8Array(rgb),observation:structuredClone(packet.observation),elapsed:packet.elapsed};
   if(!neuralResult)throw new Error('Policy camera did not submit its sensor texture');
   const completed=await neuralResult;if(completed.error)throw completed.error;if(!completed.result||generation!==this.generation)return;
   const inferred=performance.now(),prediction=completed.result.prediction;
   if(recording?.frame?.id===packet.id)recording.frame.prediction=Array.from(prediction);
   const result=await this.request({type:'act',rgb,observation:packet.observation,elapsed:packet.elapsed,prediction,search:completed.result.search},[rgb.buffer,prediction.buffer]);
   result.timings={...result.timings,...this.camera.timings,neural_ms:completed.result.ms,camera_ms:captured-start,parallel_camera_neural_ms:inferred-start,controller_roundtrip_ms:performance.now()-inferred,roundtrip_ms:performance.now()-start};
   this.latestTiming=result.timings;this.latestDiagnostics=result.diagnostics;this.latestSearch=completed.result.search;
   if(recording?.frame?.id===packet.id)recording.frame.diagnostics=result.diagnostics;
   if(generation===this.generation)this.bridge.worker?.postMessage({type:'policy_result',id:packet.id,result});
  }catch(error){if(generation===this.generation){this.bridge.worker?.postMessage({type:'policy_result',id:packet.id,error:error.message});this.disable(error.message);}}
 }
 close(){this.disable();const camera=this.camera;this.camera=null;if(camera){if(camera.busy)this.cleanup=setTimeout(()=>camera.busy?this.closeCamera(camera):camera.destroy(),100);else camera.destroy();}}
 closeCamera(camera){if(camera.busy)this.cleanup=setTimeout(()=>this.closeCamera(camera),100);else camera.destroy();}
}
