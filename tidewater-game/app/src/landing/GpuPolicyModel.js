import * as ort from 'onnxruntime-web/all';

// Fixed FP32 tensors and a captured graph. Every neural operation must have a
// GPU kernel; unsupported operations fail initialization instead of silently
// falling back to CPU inference.
export class GpuPolicyModel {
 async initialize(model,base,{capture=true,debug=false,layout,device,adapter,inputContract,outputContract}={}){
  if(!globalThis.navigator?.gpu)throw new Error('ML landing requires WebGPU');
  ort.env.wasm.numThreads=1;ort.env.wasm.wasmPaths=base+'ort/';
  // Pinned ORT 1.30 JSEP requests its device through the adapter hook and
  // ignores a preassigned env.webgpu.device. Supply the existing render device
  // through that hook, advertising only its already enabled limits/features.
  // ORT locks this property after its first session; later toggles reuse it.
  if(Object.getOwnPropertyDescriptor(ort.env.webgpu,'adapter')?.writable!==false){
   const nativeAdapter=adapter||await navigator.gpu.requestAdapter({powerPreference:'high-performance'});
   if(!nativeAdapter)throw new Error('No GPU adapter available for ML landing');
   ort.env.webgpu.adapter=device?{info:nativeAdapter.info,limits:device.limits,features:device.features,requestDevice:async descriptor=>{
    for(const feature of descriptor.requiredFeatures||[])if(!device.features.has(feature))throw new Error('Shared GPU lacks required feature: '+feature);
    for(const [key,value] of Object.entries(descriptor.requiredLimits||{}))if(device.limits[key]<value)throw new Error('Shared GPU lacks required limit: '+key);
    return device;
   }}:nativeAdapter;
  }
  const info=ort.env.webgpu.adapter.info;this.adapter={vendor:info?.vendor,device:info?.device,description:info?.description};
  // Verified on this laptop's Intel UHD: NCHW avoids the slower NHWC path.
  // Layout changes tensor storage/kernels, never weights, dimensions or FP32.
  this.layout=layout||(String(info?.vendor).toLowerCase()==='intel'?'NCHW':'NHWC');
  if(debug)ort.env.logLevel='verbose';
  this.session=await ort.InferenceSession.create(model,{executionProviders:[{name:'webgpu',preferredLayout:this.layout}],graphOptimizationLevel:'all',enableGraphCapture:capture,preferredOutputLocation:'gpu-buffer',logSeverityLevel:debug?0:2,logVerbosityLevel:debug?1:0,extra:{session:{disable_cpu_ep_fallback:'1'}}});
  this.device=ort.env.webgpu.device;this.buffers=[];this.tensors=[];
  if(device&&this.device!==device)throw new Error('Policy and sensor must share the same GPU device');
  const align=value=>Math.ceil(value/16)*16;
  const tensor=(name,dims)=>{const count=dims.reduce((a,b)=>a*b,1),size=align(count*4),buffer=this.device.createBuffer({label:'ML '+name,size,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC|GPUBufferUsage.COPY_DST});this.buffers.push(buffer);const value=ort.Tensor.fromGpuBuffer(buffer,{dataType:'float32',dims});this.tensors.push(value);return {buffer,tensor:value,count,bytes:count*4,size};};
  this.numericCount=inputContract?.numeric?.[2]??32;this.predictionCount=inputContract?.prediction?.[2]??15;
  if(!((this.numericCount===32&&this.predictionCount===15)||(this.numericCount===34&&this.predictionCount===20)))throw new Error('Unsupported neural tensor contract');
  this.prediction=tensor('pose output',[1,1,this.predictionCount]);this.hiddenOut=tensor('hidden output',[1,1,128]);this.image=tensor('image',[1,1,3,360,640]);this.numeric=tensor('numeric',[1,1,this.numericCount]);this.hiddenIn=tensor('hidden input',[1,1,128]);
  this.searchSpecs=[];const search=outputContract?.search;
  if(search){
   const specs=[['search_heat','search_heat',search.heat],['search_offset','search_offset',search.offset],['search_presence','search_presence',search.presence],['search_evidence','search_evidence',search.evidence],['search_identity','search_identity',search.identity]];
   for(const [key,name,dims] of specs){
    if(!Array.isArray(dims)||!dims.length)throw new Error('Student search output contract is missing '+key);
    const output=tensor(name,dims);this.searchSpecs.push({key,name,dims,...output});
   }
  }
  this.feeds={image:this.image.tensor,numeric:this.numeric.tensor,hidden:this.hiddenIn.tensor};
  this.outputs={prediction:this.prediction.tensor,next_hidden:this.hiddenOut.tensor};
  for(const item of this.searchSpecs)this.outputs[item.name]=item.tensor;
  this.predictionBytes=this.prediction.bytes;this.hiddenOffset=align(this.predictionBytes);this.searchOffset=align(this.hiddenOffset+this.hiddenOut.bytes);
  let cursor=this.searchOffset;const offsets=new Map();
  for(const item of this.searchSpecs){cursor=align(cursor);offsets.set(item.key,cursor);item.readbackOffset=cursor;cursor+=item.bytes;}
  this.readbackBytes=align(cursor);
  this.readback=this.device.createBuffer({label:'ML fixed output readback',size:Math.max(this.readbackBytes,16),usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
  const shader=this.device.createShaderModule({label:'ML exact RGB texture to FP32 CHW',code:`
   @group(0) @binding(0) var image:texture_2d<f32>;
   @group(0) @binding(1) var<storage,read_write> output:array<f32>;
   @compute @workgroup_size(8,8) fn main(@builtin(global_invocation_id) p:vec3u){
    if(p.x>=640u||p.y>=360u){return;}
    let rgb=round(textureLoad(image,vec2i(p.xy),0).rgb*255.0);
    let i=p.y*640u+p.x;output[i]=rgb.r;output[230400u+i]=rgb.g;output[460800u+i]=rgb.b;
   }`});
  this.texturePipeline=await this.device.createComputePipelineAsync({label:'ML full 640×360 FP32 input',layout:'auto',compute:{module:shader,entryPoint:'main'}});
  this.reset();const pixels=new Float32Array(640*360*3),numeric=new Float32Array(this.numericCount);
  for(let i=0;i<3;i++)await this.run(pixels,numeric);
  this.reset();
 }
 reset(){this.device.queue.writeBuffer(this.hiddenIn.buffer,0,new Float32Array(128));}
 run(image,numeric){
  return this.startRun(()=>this.device.queue.writeBuffer(this.image.buffer,0,image),numeric);
 }
 runFromTexture(texture,numeric){
  if(texture.width!==640||texture.height!==360||texture.format!=='rgba8unorm')throw new Error('Policy texture requires full 640×360 rgba8unorm sensor output');
  return this.startRun(()=>{
   const bindings=this.device.createBindGroup({layout:this.texturePipeline.getBindGroupLayout(0),entries:[{binding:0,resource:texture.createView()},{binding:1,resource:{buffer:this.image.buffer}}]});
   const encoder=this.device.createCommandEncoder({label:'ML sensor texture input'}),pass=encoder.beginComputePass();pass.setPipeline(this.texturePipeline);pass.setBindGroup(0,bindings);pass.dispatchWorkgroups(80,45);pass.end();this.device.queue.submit([encoder.finish()]);
  },numeric);
 }
 startRun(upload,numeric){
  if(this.busy)throw new Error('ML recurrent inference already in progress');
  if(numeric.length!==this.numericCount)throw new Error('Policy requires '+this.numericCount+' numeric inputs');
  this.busy=true;
  this.inFlight=(async()=>{try{upload();return await this.execute(numeric);}finally{this.busy=false;}})();return this.inFlight;
 }
 async execute(numeric){
  this.device.queue.writeBuffer(this.numeric.buffer,0,numeric);
  await this.session.run(this.feeds,this.outputs);
  const encoder=this.device.createCommandEncoder();encoder.copyBufferToBuffer(this.prediction.buffer,0,this.readback,0,this.predictionBytes);encoder.copyBufferToBuffer(this.hiddenOut.buffer,0,this.readback,this.hiddenOffset,this.hiddenOut.bytes);
  for(const item of this.searchSpecs)encoder.copyBufferToBuffer(item.buffer,0,this.readback,item.readbackOffset,item.bytes);
  encoder.copyBufferToBuffer(this.hiddenOut.buffer,0,this.hiddenIn.buffer,0,this.hiddenOut.bytes);this.device.queue.submit([encoder.finish()]);
  try{await this.readback.mapAsync(GPUMapMode.READ);const bytes=this.readback.getMappedRange();const result={prediction:new Float32Array(new Float32Array(bytes,0,this.predictionCount)),hidden:new Float32Array(new Float32Array(bytes,this.hiddenOffset,128))};
   if(this.searchSpecs.length){result.search={};for(const item of this.searchSpecs)result.search[item.key]=new Float32Array(new Float32Array(bytes,item.readbackOffset,item.count));}
   return result;
  }finally{if(this.readback.mapState==='mapped')this.readback.unmap();}
 }
 async close(){await this.inFlight?.catch(()=>{});await this.session?.release();for(const t of this.tensors||[])t.dispose();for(const b of this.buffers||[])b.destroy();this.readback?.destroy();this.session=null;}
}
