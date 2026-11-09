import assert from 'node:assert/strict';
import {BrowserRuntime} from '../src/landing/BrowserRuntime.js';
const runtime=new BrowserRuntime({post(){}});runtime.data={time:0};let steps=0,transition,after;
runtime.game={ml:{enabled:true},input(payload){this.ml.enabled=payload.enabled;},state(){return {};},async advance(){
 runtime.data.time+=.004;steps++;
 if(steps===1){await new Promise(resolve=>setTimeout(resolve,100));transition=performance.now();runtime.input({action:'ml',enabled:false});}
 if(steps===11)after=performance.now();
 if(steps===15)runtime.stopped=true;
}};
await runtime.run();runtime.taskChannel.port1.close();runtime.taskChannel.port2.close();
assert(after-transition>=28,`Manual flight caught up old ML debt in ${after-transition} ms`);
assert.equal(steps,15);assert(Math.abs(runtime.data.time-.06)<1e-12,'No physical steps may be dropped or enlarged');
console.log('Manual mode discards old wall-clock debt while preserving every 4 ms physics advance.');
