import assert from 'node:assert/strict';
import {SimulationBridge} from '../src/landing/SimulationBridge.js';
const workers=[];class Worker {
 constructor(){this.messages=[];workers.push(this);}
 postMessage(packet){this.messages.push(packet);if(packet.type==='shutdown')setTimeout(()=>this.onmessage?.({data:{disposed:true}}),30);}
 terminate(){assert(this.shuttingDown);this.terminated=true;}
}
globalThis.Worker=Worker;
const install=SimulationBridge.prototype._installVehicles,upload=SimulationBridge.prototype._uploadMap;
SimulationBridge.prototype._installVehicles=async function(){this.installed=true;};
SimulationBridge.prototype._uploadMap=async function(){this.worker.postMessage({type:'initialize'});};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
try {
 const statuses=[],bridge=new SimulationBridge({},state=>statuses.push(state.status));await delay(0);const first=workers[0];
 const restarting=bridge.retry();bridge.retry();await delay(5);assert.equal(workers.length,1,'Reset started a second pool before shutdown');
 first.onmessage({data:{status:'stale running state',ready:true}});assert(!statuses.includes('stale running state'));await restarting;assert(first.terminated);assert.equal(workers.length,2);await bridge.close();assert(workers[1].terminated);
 let release,installs=0;
 SimulationBridge.prototype._installVehicles=()=>{installs++;return new Promise(r=>release=r);};
 const pending=new SimulationBridge({});await delay(0);const original=workers.at(-1),reset=pending.retry();await delay(40);const replacement=workers.at(-1);assert.notEqual(original,replacement);assert.equal(installs,1,'Reset duplicated CAD installation');release();await reset;
 assert(!original.messages.some(p=>p.type==='initialize'));assert.equal(replacement.messages.filter(p=>p.type==='initialize').length,1,'Replacement initialized twice');await pending.close();
 SimulationBridge.prototype._installVehicles=()=>new Promise(r=>release=r);
 const closing=new SimulationBridge({});await delay(0);const worker=workers.at(-1);const closed=closing.close();release();await closed;assert(worker.terminated);assert(!worker.messages.some(p=>p.type==='initialize'),'Closed startup uploaded a map into disposed runtime');
 console.log('Bridge reset waits for pthread disposal, ignores stale packets and shares pending CAD across startup resets and closes safely');
}finally{SimulationBridge.prototype._installVehicles=install;SimulationBridge.prototype._uploadMap=upload;}
