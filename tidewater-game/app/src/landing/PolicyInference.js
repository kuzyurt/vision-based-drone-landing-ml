import * as ort from 'onnxruntime-web/wasm';
import {GpuPolicyModel} from './GpuPolicyModel.js';
import {MarkerKernel} from './MarkerKernel.js';

export class PolicyInference {
 async initialize({base,loadPython,executionProvider='webgpu',accelerateMarker=true,keepPythonRgb=false}) {
  this.base=base;
  this.keepPythonRgb=keepPythonRgb;
  const response=await fetch(base+'manifest.json');if(!response.ok)throw new Error('Trained policy manifest is unavailable');
  this.manifest=await response.json();
  const legacy=this.manifest.browser_schema==='tidewater.marker_policy.browser.v1'&&this.manifest.algorithm_version==='metric_marker_v5';
  const visionFirst=this.manifest.browser_schema==='tidewater.vision_first_policy.browser.v2'&&this.manifest.algorithm_version==='vision_first_fusion_v1';
  if(!legacy&&!visionFirst)throw new Error('Unsupported trained policy contract');
  this.numericCount=visionFirst?34:32;this.predictionCount=visionFirst?20:15;
  if(this.manifest.input_contract.numeric[2]!==this.numericCount||this.manifest.input_contract.prediction[2]!==this.predictionCount)throw new Error('Policy manifest tensor dimensions disagree');
  const verified=async(url,expected)=>{const r=await fetch(url);if(!r.ok)throw new Error('Policy file unavailable: '+url);const bytes=new Uint8Array(await r.arrayBuffer()),sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');if(sha!==expected)throw new Error('Policy file checksum mismatch: '+url);return bytes;};
  const model=await verified(base+this.manifest.model,this.manifest.model_sha256);
  this.python=await loadPython(base+'pyodide/');await this.python.loadPackage(['numpy','scipy']);
  if(executionProvider==='webgpu'){
   this.gpuModel=new GpuPolicyModel();await this.gpuModel.initialize(model,base,{inputContract:this.manifest.input_contract});this.backend='WebGPU FP32';this.adapter=this.gpuModel.adapter;
  }else if(executionProvider==='wasm'){
   // Explicit reference-test mode only. Gameplay never falls back to CPU.
   ort.env.wasm.numThreads=1;ort.env.wasm.wasmPaths=base+'ort/';this.session=await ort.InferenceSession.create(model,{executionProviders:['wasm'],graphOptimizationLevel:'all'});this.backend='WASM reference';
  }else if(executionProvider==='external-webgpu'){
   // The verified FP32 network shares the render device and reads its sensor
   // texture directly. This worker retains the complete frozen controller.
   this.verifiedModel=model;this.backend='WebGPU FP32 shared sensor device';this.externalNeural=true;
  }else throw new Error('Unsupported policy execution provider');
  if(accelerateMarker){this.kernel=new MarkerKernel();await this.kernel.initialize(await verified(base+this.manifest.marker_kernel,this.manifest.marker_kernel_sha256));globalThis.marker_kernel=this.kernel;}
  this.python.FS.mkdirTree('/policy/reference');
  for(const [name,sha] of Object.entries(this.manifest.reference_adapter_sha256))this.python.FS.writeFile('/policy/reference/'+name,await verified(base+'reference/'+name,sha));
  this.python.runPython("import sys\nsys.path.insert(0,'/policy')\nfrom reference import browser_api as landing_api");
  this.python.globals.set('policy_configuration_json',JSON.stringify(this.manifest));this.python.runPython('landing_api.initialize(policy_configuration_json)');this.python.globals.delete('policy_configuration_json');
  this.hidden=new Float32Array(128);this.image=new Float32Array(640*360*3);return this.manifest;
 }
 reset(){this.hidden.fill(0);this.gpuModel?.reset();this.python.globals.set('policy_configuration_json',JSON.stringify(this.manifest));this.python.runPython('landing_api.initialize(policy_configuration_json)');this.python.globals.delete('policy_configuration_json');}
 numeric(observation){
  if(observation.decision_dt_s!==.04)throw new Error('Policy requires 25 Hz simulation decisions');
  const py=this.python;let numeric;
  try{py.globals.set('observation_json',JSON.stringify(observation));numeric=py.runPython('landing_api.numeric(observation_json)');return Float32Array.from(numeric.toJs());}
  finally{numeric?.destroy();py.globals.delete('observation_json');}
 }
 async act(rgb,observation,elapsed,externalPrediction) {
  if(!(rgb instanceof Uint8Array)||rgb.length!==640*360*3)throw new Error('Policy requires an unoverlaid 640×360 RGB image');
  if(observation.decision_dt_s!==.04)throw new Error('Policy requires 25 Hz simulation decisions');
  const start=performance.now(),py=this.python;py.globals.set('observation_json',JSON.stringify(observation));
  let numeric,feeds,output,pyRGB,pyPrediction;
  try{
  let values;const image=this.image;
  if(!this.externalNeural){numeric=py.runPython('landing_api.numeric(observation_json)');values=Float32Array.from(numeric.toJs());numeric.destroy();numeric=null;
   const pixels=640*360;for(let i=0;i<pixels;i++){image[i]=rgb[i*3];image[pixels+i]=rgb[i*3+1];image[pixels*2+i]=rgb[i*3+2];}}
  if(this.kernel){this.kernel.timings={};this.kernel.setImage(rgb);}const prepared=performance.now();
  if(this.externalNeural){if(!(externalPrediction instanceof Float32Array)||externalPrediction.length!==this.predictionCount||!externalPrediction.every(Number.isFinite))throw new Error('Missing verified GPU pose prediction');this.prediction=externalPrediction;}
  else if(this.gpuModel){const result=await this.gpuModel.run(image,values);this.hidden=result.hidden;this.prediction=result.prediction;}
  else {feeds={image:new ort.Tensor('float32',image,[1,1,3,360,640]),numeric:new ort.Tensor('float32',values,[1,1,this.numericCount]),hidden:new ort.Tensor('float32',this.hidden,[1,1,128])};output=await this.session.run(feeds);this.hidden=new Float32Array(output.next_hidden.data);this.prediction=new Float32Array(output.prediction.data);}
  // The compiled registration already owns the complete RGB sensor buffer.
  // Python uses only its pose result. Avoid a second full image conversion;
  // reference verification can request the original Python RGB path.
  const inferred=performance.now();pyRGB=this.kernel&&!this.keepPythonRgb?null:py.toPy(rgb);pyPrediction=py.toPy(this.prediction);
   if(pyRGB)py.globals.set('policy_rgb',pyRGB);else py.runPython('policy_rgb=None');py.globals.set('policy_prediction',pyPrediction);py.globals.set('policy_elapsed',elapsed);
   const result=JSON.parse(py.runPython('landing_api.step(policy_rgb,policy_prediction,observation_json,policy_elapsed)')),end=performance.now();
   result.timings={prepare_ms:prepared-start,neural_ms:inferred-prepared,controller_ms:end-inferred,total_ms:end-start,backend:this.backend,marker:this.kernel?.timings};return result;
  }finally{
   py.globals.delete('policy_rgb');py.globals.delete('policy_prediction');py.globals.delete('policy_elapsed');py.globals.delete('observation_json');numeric?.destroy();pyRGB?.destroy();pyPrediction?.destroy();
   for(const tensor of Object.values(feeds||{}))tensor.dispose();for(const tensor of Object.values(output||{}))tensor.dispose();
  }
 }
 async close(){await this.session?.release();await this.gpuModel?.close();if(globalThis.marker_kernel===this.kernel)delete globalThis.marker_kernel;this.kernel?.close();this.session=null;this.gpuModel=null;}
}
