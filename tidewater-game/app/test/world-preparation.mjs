import assert from 'node:assert/strict';
import {prepareBrowserWorld} from '../src/landing/PrepareBrowserWorld.js';
const map={meta:{res:2},heights:new Float32Array([1,2,3,4])};
function fake(){return {terminated:false,postMessage(packet){this.packet=packet;},async terminate(){await new Promise(r=>setTimeout(r,10));this.terminated=true;}};}
let worker=fake();const options={createWorker:()=>worker,base:'physics/',c:{version:1},map,progress:()=>{}};
let result=prepareBrowserWorld(options);assert.notEqual(worker.packet.heights.buffer,map.heights.buffer);assert.deepEqual(worker.packet.heights,map.heights);
worker.onmessage({data:{binary:new Uint8Array([1,2])}});assert(!worker.terminated);assert.deepEqual(await result,new Uint8Array([1,2]));assert(worker.terminated);
worker=fake();result=prepareBrowserWorld({...options,createWorker:()=>worker});worker.onmessage({data:{error:'compile failed'}});await assert.rejects(result,/compile failed/);assert(worker.terminated);
worker=fake();const controller=new AbortController();result=prepareBrowserWorld({...options,createWorker:()=>worker,signal:controller.signal});controller.abort();await assert.rejects(result,{name:'AbortError'});assert(worker.terminated);
let created=false;await assert.rejects(prepareBrowserWorld({...options,createWorker:()=>{created=true;},signal:controller.signal}),{name:'AbortError'});assert(!created);
worker=fake();result=prepareBrowserWorld({...options,createWorker:()=>worker});worker.onerror({message:'worker failed'});await assert.rejects(result,/worker failed/);assert(worker.terminated);
console.log('World preparation owns terrain copies and completes worker termination before success, error, or cancellation');
