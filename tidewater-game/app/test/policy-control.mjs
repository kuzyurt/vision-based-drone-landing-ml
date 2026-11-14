import assert from 'node:assert/strict';
import {PolicyControl} from '../src/landing/PolicyControl.js';
globalThis.location={href:'http://127.0.0.1:5190/'};
const workers=[],commands=[],responses=[],bridge={installed:true,state:{drone:{armed:true,landed:false},views:{}},send:p=>commands.push(p),worker:{postMessage:p=>responses.push(p)},app:{flightOps:{_refreshUI(){}}}};
let releaseCapture;const camera={captures:0,async capture(state,{onSubmitted}={}){this.captures++;onSubmitted?.({});if(releaseCapture==='delay')await new Promise(r=>releaseCapture=r);return new Uint8Array(640*360*3);},destroy(){this.destroyed=true;}};
// Worker stub: answers controller resets itself; everything else is answered by the test.
const createWorker=()=>{const w={messages:[],postMessage(p){this.messages.push(p);if(p.type==='reset')setTimeout(()=>this.onmessage?.({data:{id:p.id,reset:true}}),0);},terminate(){this.terminated=true;}};workers.push(w);return w;};
const models=[],createNeural=async()=>{const model={calls:0,resets:0,reset(){this.resets++;},async runFromTexture(){this.calls++;return {prediction:new Float32Array(15)};},async close(){this.closed=true;}};models.push(model);return model;};
const policy=new PolicyControl(bridge,{createWorker,createCamera:()=>camera,createNeural}),tick=(ms=0)=>new Promise(r=>setTimeout(r,ms));
const lastWork=worker=>[...worker.messages].reverse().find(p=>p.type!=='reset');
const replyNumeric=async worker=>{const p=lastWork(worker);assert.equal(p.type,'numeric');worker.onmessage({data:{id:p.id,numeric:new Float32Array(32)}});await tick();assert.equal(lastWork(worker).type,'act');};
const ready=w=>w.onmessage({data:{ready:true,checkpoint:'test'}});

// 1. Cancelling while the policy still loads restores manual control but keeps loading it.
let enabling=policy.enable();assert(policy.status.loading);policy.disable();await enabling;
assert(!policy.status.loading);assert(!commands.some(p=>p.enabled));assert(!workers[0].terminated,'Cancelling must keep the background load');
ready(workers[0]);await tick(5);assert(policy.preloaded,'Background load must finish after a cancelled enable');
// 2. Preloaded: enabling only resets the controller and the recurrent network.
enabling=policy.enable();await enabling;assert(policy.status.enabled);assert(commands.at(-1).enabled);assert.equal(workers.length,1,'Preloaded policy must not reload');
assert(workers[0].messages.some(p=>p.type==='reset'));assert.equal(models[0].resets,1);
// 3. Manual takeover during inference: the stale result never regains control; the policy stays loaded.
const worker=workers[0],capture=policy.capture({id:17,state:bridge.state,observation:{},elapsed:0});await tick();await replyNumeric(worker);policy.disable();await capture;
assert(!worker.terminated,'Manual takeover keeps the loaded policy');worker.onmessage({data:{id:lastWork(worker).id,action:[1,0,0,0,0,0]}});assert(!responses.length,'Cancelled inference must never regain control');
// 4. Re-enable is instant and works.
await policy.enable();assert(policy.status.enabled);assert.equal(workers.length,1);assert.equal(models[0].resets,2);
const success=policy.capture({id:18,state:bridge.state,observation:{},elapsed:0});await tick();await replyNumeric(worker);worker.onmessage({data:{id:lastWork(worker).id,action:[0,0,0,0,0,0]}});await success;assert.equal(responses.at(-1).id,18);
releaseCapture='delay';const previousCalls=models[0].calls,parallel=policy.capture({id:19,state:bridge.state,observation:{},elapsed:0});await tick();
const numericRequest=lastWork(worker);assert.equal(numericRequest.type,'numeric');worker.onmessage({data:{id:numericRequest.id,numeric:new Float32Array(32)}});await tick();
assert.equal(models[0].calls,previousCalls+1,'GPU inference must start before RGB readback resolves');assert.equal(lastWork(worker).type,'numeric');
releaseCapture();releaseCapture=null;await tick();assert.equal(lastWork(worker).type,'act');worker.onmessage({data:{id:lastWork(worker).id,action:[0,0,0,0,0,0]}});await parallel;assert.equal(responses.at(-1).id,19);
// 5. A failure inside the pipeline unloads it and starts a fresh background load.
const failing=policy.capture({id:20,state:bridge.state,observation:{},elapsed:0});await tick();worker.onmessage({data:{id:lastWork(worker).id,error:'boom'}});await failing;
assert(!policy.status.enabled);assert.equal(policy.status.error,'boom');assert(worker.terminated,'Pipeline failure must unload the worker');await policy.neuralCleanup;assert(models[0].closed);
await tick(1100);assert.equal(workers.length,2,'A fresh background load must start after a failure');ready(workers[1]);await tick(5);assert(policy.preloaded);
// 6. Close releases everything.
policy.close();assert(camera.destroyed);assert(workers.every(w=>w.terminated));assert(!policy.worker);
await policy.neuralCleanup;assert(models.every(model=>model.closed));assert.equal(policy.requests.size,0);
bridge.state.drone.armed=false;await assert.rejects(new PolicyControl(bridge,{createWorker,createCamera:()=>camera,createNeural}).enable(),/Take off/);
console.log('ML background preload, instant enable with controller reset, cancellation, manual takeover, stale result rejection, failure reload and cleanup passed.');
