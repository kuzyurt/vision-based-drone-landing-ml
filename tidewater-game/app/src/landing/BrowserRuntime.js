import {BrowserForces} from './BrowserForces.js';
import {BrowserPX4} from './BrowserPX4.js';
import {BrowserGame} from './BrowserGame.js';
import {compileWorld,loadCompiledWorld,chooseRoute,remapConfiguration} from './BrowserWorld.js';

export class BrowserRuntime {
 constructor({loadMujoco,loadPX4,fetchAsset,post,prepareWorld,isolated=true}) {
  Object.assign(this,{loadMujoco,loadPX4,fetchAsset,post,prepareWorld,isolated});this.stopped=false;this.pending=[];this.compilerAbort=new AbortController();
 }
 check() {if(this.stopped)throw new DOMException('Simulation stopped','AbortError');}
 status(message) {if(!this.stopped)this.post({status:message,ready:false});}
 start(payload) {
  if(this.starting)throw new Error('Simulation already initialized');
  this.starting=this.initialize(payload);return this.starting;
 }
 async initialize({base,meta,heights}) {
  if(!this.isolated)throw new Error('PX4 needs cross-origin isolation. Use the included Tidewater static server, then reload the game.');
  this.status('Loading MuJoCo WebAssembly');
  const json=async name=>JSON.parse(new TextDecoder().decode(await this.fetchAsset(base+name)));
  const map={meta,heights:new Float32Array(heights)},c=await json('physics/configuration.json'),boot=await json('physics/px4-startup.json');this.check();
  let binary=this.prepareWorld?await this.prepareWorld({base:base+'physics/',c,map,progress:s=>this.status(s),signal:this.compilerAbort.signal}):null;this.check();
  this.mj=await this.loadMujoco();this.check();
  this.model=binary?loadCompiledWorld(this.mj,binary):await compileWorld(this.mj,c,map,base+'physics/',s=>this.status(s),this.fetchAsset);binary=null;this.check();
  remapConfiguration(this.mj,this.model,c);
  this.data=new this.mj.MjData(this.model);const forces=new BrowserForces(this.mj,this.model,this.data,c);
  BrowserGame.initializePose(this.mj,this.model,this.data,c,chooseRoute(map));
  this.status('Starting the original PX4 controller');
  this.module=await this.loadPX4(base);this.check();
  const px4=new BrowserPX4(this.module,this.mj,this.model,this.data,forces,c);px4.checkCancelled=()=>this.check();
  px4.onStartup=command=>this.status('Starting PX4 · '+command.split(' ')[0]);
  await px4.initialize(boot);this.check();
  this.game=new BrowserGame(this.mj,this.model,this.data,forces,px4,c,map);
  this.game.requestPolicy=payload=>new Promise((resolve,reject)=>{
   const id=(this.policySequence||0)+1;this.policySequence=id;
   const timer=setTimeout(()=>{if(this.policyPending?.id===id){this.policyPending=null;reject(new Error('ML camera/inference timed out'));}},30000);
   this.policyPending={id,resolve,reject,timer};this.post({type:'policy_capture',id,...payload});
  });
  this.game.cancelPolicy=()=>{if(this.policyPending){clearTimeout(this.policyPending.timer);this.policyPending.resolve(null);this.policyPending=null;}};
  for(const input of this.pending)this.game.input(input);this.pending=[];
  this.post(this.game.state(1,true));
  this.loop=this.run().catch(error=>{if(!this.stopped){this.post({ready:false,status:'Browser simulation stopped',error:error.stack||error.message});this.stop();}});
 }
 input(payload) {if(this.stopped)return;if(payload.type==='policy_result'){const pending=this.policyPending;if(pending?.id===payload.id){clearTimeout(pending.timer);this.policyPending=null;if(payload.error)pending.reject(new Error(payload.error));else pending.resolve(payload.result);}return;}if(this.game){if(payload.action==='ml'||payload.action==='reset')this.resetDeadline=true;this.game.input(payload);if(payload.action==='ml')this.post({type:'policy_control',ml:this.game.ml,message:this.game.message});}else {this.pending.push(payload);if(this.pending.length>64)this.pending.shift();}}
 async run() {
  // Yield overdue work through a task, without a clamped timer delay. Keep the
  // event loop available for PX4 proxies, policy replies and manual takeover.
  this.taskChannel=new MessageChannel();let resume;
  this.taskChannel.port1.onmessage=()=>{const next=resume;resume=null;next?.();};
  const yieldTask=()=>new Promise(resolve=>{resume=resolve;this.taskChannel.port2.postMessage(0);});
  let due=performance.now(),published=due,measured=due,simTime=this.data.time,realtimeFactor=1,pacedMl=!!this.game.ml?.enabled;
  while(!this.stopped) {
   if(!!this.game.ml?.enabled!==pacedMl){pacedMl=!!this.game.ml?.enabled;this.resetDeadline=true;}
   // A mode transition starts a new wall-clock pacing period. Slow ML must
   // not leave minutes of catch-up debt that speeds up subsequent manual flight.
   if(this.resetDeadline){due=performance.now();this.resetDeadline=false;measured=due;simTime=this.data.time;realtimeFactor=1;}
   const begin=performance.now();let cycles=0;
   while(performance.now()>=due && cycles<8 && performance.now()-begin<8 && !this.stopped){await this.game.advance();due+=4;cycles++;if(this.resetDeadline||!!this.game.ml?.enabled!==pacedMl)break;}
   // Retain the wall-clock deadline through temporary work overruns. Resetting
   // it discarded accumulated time and permanently slowed the simulation.
   const now=performance.now();
   if(now-measured>=1000){realtimeFactor=(this.data.time-simTime)/((now-measured)/1000);simTime=this.data.time;measured=now;}
   if(!this.stopped && now-published>=25){this.post(this.game.state(realtimeFactor));published=now;}
   const remaining=due-performance.now();
   if(remaining<=0)await yieldTask();
   else await new Promise(resolve=>setTimeout(resolve,Math.min(4,remaining)));
  }
 }
 stop() {
  if(this.stopping)return this.stopping;
  this.stopped=true;this.game?.cancelPolicy?.();this.compilerAbort.abort();this.module?.PThread?.terminateAllThreads();
  this.stopping=(async()=>{
   // A factory already loading its pthread pool must settle before acknowledging
   // shutdown. Otherwise reset could orphan its subsequently created workers.
   await this.starting?.catch(()=>{});await this.loop?.catch(()=>{});this.taskChannel?.port1.close();this.taskChannel?.port2.close();
   this.module?.PThread?.terminateAllThreads();
   this.data?.delete();this.model?.delete();this.game=null;this.pending=[];
  })();return this.stopping;
 }
}
