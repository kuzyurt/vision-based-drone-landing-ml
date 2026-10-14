import {BrowserForces} from './BrowserForces.js';
import {BrowserPX4} from './BrowserPX4.js';
import {BrowserGame} from './BrowserGame.js';
import {compileWorld,chooseRoute,remapConfiguration} from './BrowserWorld.js';

export class BrowserRuntime {
 constructor({loadMujoco,loadPX4,fetchAsset,post,isolated=true}) {
  Object.assign(this,{loadMujoco,loadPX4,fetchAsset,post,isolated});this.stopped=false;this.pending=[];
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
  this.mj=await this.loadMujoco();this.check();
  this.model=await compileWorld(this.mj,c,map,base+'physics/',s=>this.status(s),this.fetchAsset);this.check();
  remapConfiguration(this.mj,this.model,c);
  this.data=new this.mj.MjData(this.model);const forces=new BrowserForces(this.mj,this.model,this.data,c);
  BrowserGame.initializePose(this.mj,this.model,this.data,c,chooseRoute(map));
  this.status('Starting the original PX4 controller');
  this.module=await this.loadPX4(base);this.check();
  const px4=new BrowserPX4(this.module,this.mj,this.model,this.data,forces,c);px4.checkCancelled=()=>this.check();
  px4.onStartup=command=>this.status('Starting PX4 · '+command.split(' ')[0]);
  await px4.initialize(boot);this.check();
  this.game=new BrowserGame(this.mj,this.model,this.data,forces,px4,c,map);
  for(const input of this.pending)this.game.input(input);this.pending=[];
  this.post(this.game.state(1,true));
  this.loop=this.run().catch(error=>{if(!this.stopped){this.post({ready:false,status:'Browser simulation stopped',error:error.stack||error.message});this.stop();}});
 }
 input(payload) {if(this.stopped)return;if(this.game)this.game.input(payload);else {this.pending.push(payload);if(this.pending.length>64)this.pending.shift();}}
 async run() {
  let due=performance.now(),published=due,measured=due,simTime=this.data.time,realtimeFactor=1;
  while(!this.stopped) {
   const begin=performance.now();let cycles=0;
   while(performance.now()>=due && cycles<8 && performance.now()-begin<8 && !this.stopped){await this.game.advance();due+=4;cycles++;}
   const now=performance.now();if(now-due>250)due=now;
   if(now-measured>=1000){realtimeFactor=(this.data.time-simTime)/((now-measured)/1000);simTime=this.data.time;measured=now;}
   if(!this.stopped && now-published>=25){this.post(this.game.state(realtimeFactor));published=now;}
   await new Promise(resolve=>setTimeout(resolve,Math.max(0,Math.min(4,due-performance.now()))));
  }
 }
 stop() {
  if(this.stopping)return this.stopping;
  this.stopped=true;this.module?.PThread?.terminateAllThreads();
  this.stopping=(async()=>{
   // A factory already loading its pthread pool must settle before acknowledging
   // shutdown. Otherwise reset could orphan its subsequently created workers.
   await this.starting?.catch(()=>{});await this.loop?.catch(()=>{});
   this.module?.PThread?.terminateAllThreads();
   this.data?.delete();this.model?.delete();this.game=null;this.pending=[];
  })();return this.stopping;
 }
}
