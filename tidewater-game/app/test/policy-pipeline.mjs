import assert from 'node:assert/strict';
import {BrowserGame} from '../src/landing/BrowserGame.js';
const requests=[],actions=[],data={time:0},game=Object.create(BrowserGame.prototype);
Object.assign(game,{d:data,nextControl:0,nextRadio:Infinity,ml:{enabled:true},mlStarted:0,mlGeneration:1,mlWasAirborne:true,keys:[],lookX:0,lookY:0,
 control(){},state(){return {time_s:data.time};},landingResult:{update:()=>({collision_failure:false})},
 px4:{landed:false,armed:true,advance:async()=>{data.time+=.004;},policyPilot:(action,yaw)=>actions.push({action,yaw}),manualHold(){}},
 policyTelemetry:{previous:Array(6).fill(0),sample(){return {px4:{attitude_ned_rad:[0,0,.7]},previous_executed_action:[...this.previous],decision_dt_s:.04};}},
 requestPolicy(payload){return new Promise(resolve=>requests.push({payload,resolve}));},cancelPolicy(){requests.at(-1)?.resolve(null);}});
for(let i=0;i<10;i++)await game.advance();
assert(Math.abs(data.time-.04)<1e-12);assert.equal(requests.length,1);assert.equal(actions.length,0,'Physics must run during inference');
let advanced=false;const pending=game.advance().then(()=>advanced=true);await Promise.resolve();assert(!advanced,'An overdue result must be awaited, never skipped');
requests[0].resolve({action:[.8,0,.22,0,0,0],diagnostics:{control_phase:'descend'},timings:{backend:'WebGPU FP32'}});await pending;
assert.equal(actions.length,1);assert.equal(actions[0].yaw,.7,'Use the observation heading to encode the delayed world velocity');assert.equal(requests.length,2);assert(Math.abs(game.ml.timings.command_age_s-.04)<1e-12);assert.deepEqual(requests[1].payload.observation.previous_executed_action,actions[0].action);
for(let i=0;i<9;i++)await game.advance();
const cancelled=game.advance();await Promise.resolve();game.setPolicy(false);requests[1].resolve({action:[-1,0,0,0,0,0]});await cancelled;
assert.equal(actions.length,1,'Manual takeover must reject the pending decision');assert.equal(game.policyFrame,null);assert.equal(requests.length,2);
game.ml.enabled=true;game.policyTelemetry={previous:Array(6).fill(0)};game.nextControl=data.time;
game.policyFrame={time:data.time-.04,yaw:.7,promise:Promise.resolve({result:{action:[0,0,-.5,0,0,0],intervention:'mission_deadline'}})};
await game.advance();assert.equal(game.ml.enabled,false);assert.equal(game.ml.phase,'mission deadline · manual hold');
assert.equal(actions.length,1,'Mission deadline must restore manual hold before applying another command');assert.equal(requests.length,2);
console.log('25 Hz decisions overlap physics; overruns are awaited; captured-heading commands, 40 ms age and manual cancellation passed.');
