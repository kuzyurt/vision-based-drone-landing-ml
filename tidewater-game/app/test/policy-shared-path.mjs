// Focused original-CAD sensor + production neural/controller path. This does
// not include the full scenery/operator render loop or claim flight parity.
import '../../simulation/runtime/high-resolution-timer.mjs';
import './headless-policy.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {Worker} from 'node:worker_threads';
import * as E from '../src/engine/index.js';
import {GPU} from '../src/engine/gpu/GPU.js';
import {MeshRenderer} from '../src/engine/render/MeshRenderer.js';
import {SunShadows} from '../src/engine/render/Shadows.js';
import {ShaderModule} from '../src/engine/gpu/Shader.js';
import {G} from '../src/engine/render/Frame.js';
import {SimulationBridge} from '../src/landing/SimulationBridge.js';
import {PolicyControl} from '../src/landing/PolicyControl.js';
const runtime=new URL('../../simulation/runtime/',import.meta.url),assets=new URL('../public/',import.meta.url);
globalThis.location={href:assets.href,search:''};
globalThis.fetch=async url=>{const u=new URL(String(url));try{return new Response(await fs.readFile(u.protocol==='file:'?u:new URL(u.pathname.replace(/^\//,''),assets)));}catch{return new Response('',{status:404});}};
await GPU.init({headless:true});new SunShadows();const errors=[];GPU.device.addEventListener('uncapturederror',e=>errors.push(e.error.message));
const app={gpu:GPU,engine:{meshRenderer:new MeshRenderer()},scene:new E.Scene(),sceneRenderer:{hullMasks:[],addHullMask(geometry,object){this.hullMasks.push({mesh:{geometry},object});}},ocean:{material:{uniforms:{}}},sky:{module:new ShaderModule({name:'focused policy test sky',code:'fn skyRadianceWithClouds(dir:vec3f,withSun:bool)->vec3f{return vec3f(0.25,0.35,0.45);}'})},precompile:async()=>{},flightOps:{_refreshUI(){}}};
G.sunDir.value.set(.3,.6,-.7).normalize();G.sunColor.value.setRGB(3,2.9,2.7);G.skyIrradiance.value.setRGB(.25,.32,.45);
const state=JSON.parse(await fs.readFile(new URL('ml-camera-snapshot.json',runtime))),layout=JSON.parse(await fs.readFile(new URL('ml-camera-layout.json',runtime)));
const records=(await fs.readFile(new URL('ml-live-frames.jsonl',runtime),'utf8')).trim().split('\n').map(JSON.parse),record=records.findLast(r=>Math.abs(r.time-state.time_s)<1e-6);assert(record,'Recorded observation must match the sensor pose timestamp');
const replies=[],bridge=Object.create(SimulationBridge.prototype);Object.assign(bridge,{app,state,textures:new Map(),meshes:new Map(),groups:new Map(),assetAbort:new AbortController(),send(){},worker:{postMessage:p=>replies.push(p)}});await bridge._installVehicles();bridge._applyTransforms(layout);bridge._applyBodies(state.bodies);
let worker;const createWorker=()=>{worker=new Worker(new URL('../../wasm/tests/policy-controller-worker.mjs',import.meta.url));const wrapper={postMessage:(p,t)=>worker.postMessage(p,t),terminate:()=>worker.terminate()};worker.on('message',data=>wrapper.onmessage?.({data}));worker.on('error',error=>wrapper.onerror?.({message:error.message}));return wrapper;};
const policy=new PolicyControl(bridge,{createWorker});bridge.policy=policy;const rows=[];
try{
 await policy.enable();assert(policy.status.enabled,policy.status.error||'ML did not enable');
 const cameraComparison=[];
 for(let i=0;i<6;i++){
  const viewState=structuredClone(state);if(i>=3)viewState.views.drone.matrix[3]+=(i-2)*.01;
  policy.camera.meshRenderer.useRenderBundles=false;const direct=await policy.camera.capture(viewState),directTimings={...policy.camera.timings};
  policy.camera.meshRenderer.useRenderBundles=true;const bundled=await policy.camera.capture(viewState),bundleTimings={...policy.camera.timings};assert.deepEqual(bundled,direct,'Every original CAD sensor pixel must match direct rendering, including changed views');
  cameraComparison.push({moving_view:i>=3,direct:directTimings,bundled:bundleTimings});
 }
 policy.camera.meshRenderer.useRenderBundles=!process.argv.includes('--no-bundles');
 for(let i=0;i<5;i++){const observation=structuredClone(record.observation);observation.image_capture_time_s+=i*.04;observation.image_delivery_time_s+=i*.04;await policy.capture({id:i,state:{...state,time_s:state.time_s+i*.04},observation,elapsed:i*.04});const reply=replies.at(-1);assert.equal(reply.id,i);assert(!reply.error,reply.error);assert(reply.result.action.every(Number.isFinite));rows.push({frame:i,phase:reply.result.diagnostics.control_phase,timings:reply.result.timings});}
 const variant=policy.camera.meshRenderer.useRenderBundles?'bundled':'direct';
 const report={scope:'Focused original CAD sensor and production GPU/controller path; no full scenery or operator loop',adapter:policy.adapter,layout:policy.layout,variant,original_cad_pixels_identical:true,camera_comparison:cameraComparison,bundle_stats:policy.camera.meshRenderer.bundleCache?.stats,rows,errors};
 await fs.writeFile(new URL(`ml-shared-path-${policy.adapter.vendor}-${variant}.json`,runtime),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));assert.deepEqual(errors,[]);
}finally{policy.close();await policy.neuralCleanup;await worker?.terminate();}
process.exit(0);
