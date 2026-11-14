import {PolicyCamera} from './PolicyCamera.js';
import {GPU} from '../engine/gpu/GPU.js';

async function createSharedNeural(model,base,inputContract,outputContract){
 const {GpuPolicyModel}=await import('./GpuPolicyModel.js');const neural=new GpuPolicyModel();
 try{await neural.initialize(model,base,{device:GPU.device,adapter:GPU.adapter,inputContract,outputContract});return neural;}
 catch(error){await neural.close().catch(()=>{});throw error;}
}

export class PolicyControl {
 // The trained policy (Python controller worker, verified ONNX network on the
 // shared GPU device and the onboard sensor pipelines) is loaded once in the
 // background while the start screen is shown (preload). Enabling ML then only
 // resets the controller state; disabling keeps everything loaded for the next
 // flight. A failure inside the policy pipeline discards it and reloads quietly.
 constructor(bridge,{createWorker=()=>new Worker(new URL('./PolicyInferenceWorker.js',import.meta.url),{type:'module',name:'AERODOCK trained landing policy'}),createCamera=()=>new PolicyCamera(bridge),createNeural=createSharedNeural}={}){this.bridge=bridge;this.createWorker=createWorker;this.createCamera=createCamera;this.createNeural=createNeural;this.requests=new Map();this.requestSequence=0;this.generation=0;this.loadToken=0;this.loading=null;this.preloaded=false;this.cameraPrimed=false;this.closed=false;this.status={enabled:false,loading:false,error:null};}
 // Start loading in the background. Safe to call repeatedly; errors are kept
 // quiet here and reported only if the player actually enables ML.
 preload(){
  if(this.closed)return null;
  const loading=this._load();
  loading.then(()=>this._primeCamera()).catch(error=>{if(error?.name!=='AbortError')this.preloadError=error?.message||String(error);});
  return loading;
 }
 _load(){
  if(this.loading)return this.loading;
  const token=++this.loadToken;
  const loading=(async()=>{
   const worker=this.createWorker();
   const base=new URL('policy/',new URL(import.meta.env?.BASE_URL||'./',location.href)).href;
   let neural=null;
   try{
    const ready=await new Promise((resolve,reject)=>{
     const timer=setTimeout(()=>reject(new Error('Policy loading timed out')),120000);
     this.abortLoad=()=>{clearTimeout(timer);reject(new DOMException('Policy loading cancelled','AbortError'));};
     worker.onerror=e=>{clearTimeout(timer);reject(new Error(e.message||'ML worker failed'));};
     worker.onmessage=e=>{if(e.data.error){clearTimeout(timer);reject(new Error(e.data.error));}else if(e.data.ready){clearTimeout(timer);resolve(e.data);}};
     worker.postMessage({type:'initialize',base});
    });
    if(token!==this.loadToken)throw new DOMException('Policy loading cancelled','AbortError');
    neural=await this.createNeural(ready.model,base,ready.inputContract,ready.outputContract);
    if(token!==this.loadToken)throw new DOMException('Policy loading cancelled','AbortError');
    this.abortLoad=null;this.worker=worker;this.neural=neural;this.backend=ready.backend;this.checkpoint=ready.checkpoint;this.adapter=neural.adapter;this.layout=neural.layout;
    worker.onmessage=e=>{const p=this.requests.get(e.data.id);if(p){clearTimeout(p.timer);this.requests.delete(e.data.id);if(e.data.error)p.reject(new Error(e.data.error));else p.resolve(e.data);}};
    worker.onerror=e=>{if(this.worker===worker)this.disable(e.message||'ML worker failed',{discard:true});};
    this.preloaded=true;this.preloadError=null;this.notify();
    return ready;
   }catch(error){
    worker.terminate();if(neural)await neural.close().catch(()=>{});
    if(token===this.loadToken){this.loading=null;this.abortLoad=null;}
    throw error;
   }
  })();
  this.loading=loading;
  return loading;
 }
 // Compile the onboard sensor pipelines once the vehicles are installed, so the
 // first ML frame does not wait for them.
 _primeCamera(){
  if(this.cameraPrimed||this.cameraPriming||this.closed)return this.cameraPriming;
  const token=this.loadToken;
  this.cameraPriming=(async()=>{
   while(!this.closed&&token===this.loadToken&&!(this.bridge.installed&&this.bridge.state?.views))await new Promise(r=>setTimeout(r,250));
   if(this.closed||token!==this.loadToken)return;
   this.camera??=this.createCamera();
   await this._cameraIdle();
   await this.camera.capture(this.bridge.state);
   this.cameraPrimed=true;
  })().catch(error=>{this.preloadError=error?.message||String(error);}).finally(()=>{this.cameraPriming=null;});
  return this.cameraPriming;
 }
 async _cameraIdle(){for(let i=0;i<200&&this.camera?.busy;i++)await new Promise(r=>setTimeout(r,10));}
 async enable(){
  if(this.status.enabled||this.status.loading)return;
  if(!this.bridge.state?.drone?.armed||this.bridge.state.drone.landed||this.bridge.state.drone.landing_requested)throw new Error('Take off before enabling ML landing');
  const generation=++this.generation;this.status={enabled:false,loading:true,error:null};this.notify();
  try{
   // Cancelling (manual control) stops waiting at once; the load itself keeps
   // running in the background for the next attempt.
   const cancelled=new Promise((_,reject)=>{this.cancelWait=()=>reject(new DOMException('Policy loading cancelled','AbortError'));});
   cancelled.catch(()=>{});
   const ready=await Promise.race([this._load(),cancelled]);
   this.cancelWait=null;
   if(generation!==this.generation)return;
   // A result still in flight from the previous flight must finish before the
   // recurrent network and the Python controller start from a clean state.
   await this.neuralInFlight?.catch?.(()=>{});await this.neural?.inFlight?.catch?.(()=>{});
   if(generation!==this.generation)return;
   await this.request({type:'reset'});
   this.neural.reset?.();
   if(generation!==this.generation)return;
   if(this.cameraPriming)await this.cameraPriming;
   this.camera??=this.createCamera();
   await this._cameraIdle();
   if(!this.cameraPrimed){await this.camera.capture(this.bridge.state);this.cameraPrimed=true;} // Prepare complete sensor pipelines before takeover.
   if(generation!==this.generation)return;
   this.awaitActivation=true;this.status={enabled:true,loading:false,error:null,checkpoint:ready.checkpoint};this.bridge.send({action:'ml',enabled:true});this.notify();
  }catch(error){if(generation===this.generation)this.disable(error.name==='AbortError'?null:error.message,{discard:error.name!=='AbortError'});}
 }
 // Manual takeover keeps the loaded policy; {discard:true} (pipeline failure)
 // unloads it and starts a fresh background load for the next attempt.
 disable(error=null,{discard=false}={}){
  this.generation++;this.cancelWait?.();this.cancelWait=null;
  for(const p of this.requests.values()){clearTimeout(p.timer);p.reject(new DOMException('Manual control selected','AbortError'));}this.requests.clear();
  const wasActive=this.status.enabled||this.status.loading;
  this.awaitActivation=false;this.status={enabled:false,loading:false,error};
  if(wasActive||error)this.bridge.send({action:'ml',enabled:false});
  if(discard)this._unload(true);
  this.notify();
 }
 _unload(reload=false){
  this.loadToken++;this.abortLoad?.();this.abortLoad=null;this.loading=null;this.preloaded=false;
  const worker=this.worker;this.worker=null;worker?.terminate();
  const neural=this.neural;this.neural=null;if(neural)this.neuralCleanup=neural.close().catch(error=>console.error('ML GPU cleanup:',error));
  if(reload&&!this.closed)setTimeout(()=>{if(!this.closed&&!this.worker&&!this.loading)this.preload();},1000);
 }
 notify(){this.bridge.app?.flightOps?._refreshUI?.();}
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
    neuralResult=this.neuralInFlight=(async()=>{const prepared=await numeric;if(prepared.error)throw prepared.error;if(generation!==this.generation)return null;const begin=performance.now();const output=await neural.runFromTexture(texture,prepared.result.numeric);return {prediction:output.prediction,search:output.search,ms:performance.now()-begin};})().then(result=>({result}),error=>({error}));
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
  }catch(error){if(generation===this.generation){this.bridge.worker?.postMessage({type:'policy_result',id:packet.id,error:error.message});this.disable(error.message,{discard:true});}}
 }
 close(){this.closed=true;this.disable();this._unload(false);const camera=this.camera;this.camera=null;if(camera){if(camera.busy)this.cleanup=setTimeout(()=>camera.busy?this.closeCamera(camera):camera.destroy(),100);else camera.destroy();}}
 closeCamera(camera){if(camera.busy)this.cleanup=setTimeout(()=>this.closeCamera(camera),100);else camera.destroy();}
}
