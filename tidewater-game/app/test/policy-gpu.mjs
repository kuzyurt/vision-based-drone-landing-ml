import './headless-policy.mjs';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {GpuPolicyModel} from '../src/landing/GpuPolicyModel.js';
import {GPU} from '../src/engine/gpu/GPU.js';
const base=new URL('../public/policy/',import.meta.url),fixtures=new URL('../../simulation/runtime/ml-fixtures/',import.meta.url),frames=JSON.parse(await fs.readFile(new URL('neural.json',fixtures))),p=new GpuPolicyModel();
const manifest=JSON.parse(await fs.readFile(new URL('manifest.json',base))),inputContract=manifest.input_contract,student=manifest.browser_schema==='tidewater.search_student.browser.v1'&&manifest.algorithm_version==='radio_search_student_v1';
const model=new Uint8Array(await fs.readFile(new URL(manifest.model,base)));
const errors=[],layout=process.argv.includes('--nchw')?'NCHW':process.argv.includes('--auto-layout')?undefined:'NHWC',textureInput=process.argv.includes('--texture');
if(textureInput)await GPU.init({headless:true});
await p.initialize(model,base.href,{layout,inputContract,outputContract:manifest.output_contract,debug:process.argv.includes('--debug'),...(textureInput?{device:GPU.device,adapter:GPU.adapter}:{})});p.device.addEventListener('uncapturederror',e=>errors.push(e.error.message));
let texture;if(textureInput){assert.equal(p.device,GPU.device);texture=GPU.device.createTexture({size:[640,360],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});}
const rows=[];
for(let i=0;i<frames.length;i++){
 const f=frames[i],image=Float32Array.from(new Uint8Array(await fs.readFile(new URL(`image-${i}.bin`,fixtures))));
 if(textureInput){const rgba=new Uint8Array(640*360*4);for(let j=0;j<230400;j++){rgba[j*4]=image[j];rgba[j*4+1]=image[230400+j];rgba[j*4+2]=image[460800+j];rgba[j*4+3]=255;}GPU.queue.writeTexture({texture},rgba,{bytesPerRow:2560},{width:640,height:360});}
 const numeric=Float32Array.from(f.numeric).slice(0,student?32:34);
 const start=performance.now(),out=await (textureInput?p.runFromTexture(texture,numeric):p.run(image,numeric));
 if(textureInput&&i===0){const read=GPU.device.createBuffer({size:image.byteLength,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}),encoder=GPU.device.createCommandEncoder();encoder.copyBufferToBuffer(p.image.buffer,0,read,0,image.byteLength);GPU.queue.submit([encoder.finish()]);await read.mapAsync(GPUMapMode.READ);assert.deepEqual(new Float32Array(read.getMappedRange()),image,'Every texture channel and row must exactly match the original FP32 input');read.unmap();read.destroy();}
 if(student){
  assert(out.prediction.length===15&&out.prediction.every(Number.isFinite));assert(out.hidden.length===128&&out.hidden.every(Number.isFinite));
  for(const [name,size] of [['search_heat',3600],['search_offset',7200],['search_presence',1],['search_evidence',14400],['search_identity',7200]])assert.equal(out.search[name].length,size,`Student search output ${name} shape`);
  rows.push({frame:i,ms:performance.now()-start,student_search_outputs:true});
 }else{
  const prediction=Math.max(...out.prediction.map((x,j)=>Math.abs(x-f.prediction[j]))),hidden=Math.max(...out.hidden.map((x,j)=>Math.abs(x-f.next_hidden[j])));
  assert(prediction<1e-4&&hidden<1e-4,`GPU checkpoint mismatch frame ${i}: ${prediction}/${hidden}`);rows.push({frame:i,ms:performance.now()-start,prediction_error:prediction,hidden_error:hidden});
 }
}
if(inputContract.numeric[2]===34){
 const image=Float32Array.from(new Uint8Array(await fs.readFile(new URL('image-0.bin',fixtures)))),baseNumeric=Float32Array.from(frames[0].numeric);
 let visualState,spatial;
 for(const condition of ['nominal','false-position','missing','stale']){
  const numeric=new Float32Array(baseNumeric);
  if(condition==='false-position'){numeric[11]+=20;numeric[12]-=5;numeric[22]=0;numeric[32]=.25;}
  if(condition==='missing'||condition==='stale'){numeric.fill(0,11,17);numeric[19]=3.1;numeric[21]=condition==='stale'?1:0;numeric[32]=100;numeric[33]=10;}
  p.reset();const out=await p.run(image,numeric);
  if(!visualState){visualState=out.hidden;spatial=out.prediction.slice(15,18);}
  else {assert.deepEqual(out.hidden,visualState,'Radio faults must not alter visual recurrent memory');assert.deepEqual(out.prediction.slice(15,18),spatial,'Spatial acquisition must be image-only');}
  assert(out.prediction[18]>=0&&out.prediction[18]<=.35&&out.prediction[19]>=0&&out.prediction[19]<=.35);
  if(condition==='missing'||condition==='stale')assert.deepEqual(out.prediction.slice(18,20),new Float32Array(2),'Unavailable radio must have zero fusion weight');
 }
}
await p.close();
if(textureInput){const reopened=new GpuPolicyModel();await reopened.initialize(model,base.href,{device:GPU.device,adapter:GPU.adapter,inputContract,outputContract:manifest.output_contract});assert.equal(reopened.device,GPU.device);await reopened.runFromTexture(texture,Float32Array.from(frames[0].numeric).slice(0,student?32:34));await reopened.close();}
texture?.destroy();assert.deepEqual(errors,[]);console.log(JSON.stringify({adapter:p.adapter,layout:p.layout,shared_render_device_texture:textureInput,reopen_checked:textureInput,all_neural_operations_on_gpu:true,precision:'FP32',rows},null,2));process.exit(0);
