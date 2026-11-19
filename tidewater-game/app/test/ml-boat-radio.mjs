import assert from 'node:assert/strict';
import {BrowserGame} from '../src/landing/BrowserGame.js';
import {PolicyTelemetry} from '../src/landing/PolicyTelemetry.js';
import {FlightOperations} from '../src/game/FlightOperations.js';

const observation=new Float64Array(20);observation[0]=1;observation[7]=1;
const corners=[[0,0],[100,0],[100,100],[0,100],[0,0]],points=Array.from({length:41},(_,i)=>i===40?[0,0]:corners[Math.floor(i/10)].map((v,j)=>v+(corners[Math.floor(i/10)+1][j]-v)*(i%10)/10));
const game=Object.assign(Object.create(BrowserGame.prototype),{
 mj:{mjtObj:{mjOBJ_GEOM:{value:0},mjOBJ_SITE:{value:1}},mj_name2id:()=>0},
 d:{time:0,xpos:new Float64Array([10,0,0,10,0,3]),xipos:new Float64Array(6),site_xpos:new Float64Array([0,0,0]),xmat:new Float64Array([1,0,0,0,1,0,0,0,1]),qpos:new Float64Array(2)},
 c:{boat:{body:0},drone:{base:1,camera_qpos:[0,1]},pad_site:0,rng_state:{state:'123456789',inc:'17'}},
 m:{site_bodyid:[0]},f:{velocity:()=>[0,0,0,0,0,0],siteVelocity:()=>[0,0,0,.5,0,0],power:[0,0]},
 px4:{armed:true,landed:false,observation:()=>observation,pilot(){},vehicleCommand(){},policyPilot(){},manualHold(){},bodyVelocity:()=>[0,0],originENU:[0,0,0],lastSensor:0},
 route:{points,arc:points.map((_,i)=>i*10),length:400},
 progress:0,travelled:0,mode:'boat',launchComplete:true,takeoffPending:false,automatic:false,motors:[37,62],keys:['KeyW'],lookX:0,lookY:0,
 ml:{enabled:false},mlGeneration:0,radio:{enabled:true,connected:true},samples:[],tx:0,rx:0,dropped:0,randomState:0x1262,lastRx:0,retryTime:0,retryPending:false,
 map:{meta:{origin:-100,size:200,res:2,colliders:{boxes:[]}},heights:new Float64Array(4).fill(-100)},
 mechanisms:()=>({aft_lid:1,fore_lid:1,platform:1,mechanism_busy:false}),
 vehicles:()=>({boat:{position:[0,0,0]},drone:{position:[0,5,0]}}),
});
game.setPolicy(true);
assert.equal(game.automatic,false);assert.deepEqual(game.motors,[37,62]);assert.deepEqual(game.keys,['KeyW']);
game.control();assert.deepEqual(game.f.power,[37,62],'ML must preserve manual throttles');
game.input({action:'autopilot',enabled:true});game.control();
assert.equal(game.targetSpeed,1.5,'ML must preserve normal route speed (1.5 m/s cruise ceiling)');
const automaticPower=[...game.f.power];game.setPolicy(false);game.control();assert.deepEqual(game.f.power,automaticPower);
game.setPolicy(true);game.input({action:'autopilot',enabled:false,motors:[0,0]});game.control();
assert.deepEqual(game.f.power,[0,0],'Stop motors must work during ML');
game.input({motors:[19,76]});game.control();assert.deepEqual(game.f.power,[19,76]);
game.updateRadio();const telemetry=new PolicyTelemetry(game),first=telemetry.sample().beacon;
assert(first.valid&&first.dock_ready);
game.input({action:'radio',enabled:false});
assert.equal(game.radio.connected,false);assert.equal(game.radio.status,'disabled');
const counters=[game.tx,game.rx,game.dropped],remote=game.remote;
game.d.time=3;game.input({action:'reconnect'});game.updateRadio();
assert.equal(game.radio.enabled,false);assert.equal(game.retryPending,false);
assert.deepEqual([game.tx,game.rx,game.dropped],counters);assert.equal(game.remote,remote);
const stale=telemetry.sample().beacon;
assert.equal(stale.valid,false);assert.equal(stale.dock_ready,false);
assert.equal(stale.sequence,0);assert.equal(stale.capture_time_s,0);assert.equal(stale.received_time_s,0);assert.equal(stale.age_s,0);
assert.deepEqual(stale.relative_heading_m,[0,0,0]);assert.deepEqual(stale.velocity_heading_m_s,[0,0,0]);
assert.equal(stale.position_sigma_m,0);assert.equal(stale.synthetic_reference_hz,0);
const cold=new PolicyTelemetry(game).sample().beacon;
assert.equal(cold.valid,false);assert(Number.isFinite(cold.age_s));assert.deepEqual(cold.relative_heading_m,[0,0,0]);
game.radio.enabled=true;game.radio.connected=false;
assert.deepEqual(telemetry.sample().beacon,stale,'Natural link loss must also zero radio input');
game.radio.enabled=false;
game.input({action:'radio',enabled:true});assert.equal(game.radio.status,'handshake');assert.equal(game.radio.connected,false);
game.d.time=4.3;game.updateRadio();assert.equal(game.radio.connected,true);
const fresh=telemetry.sample().beacon;assert(fresh.valid&&fresh.dock_ready);assert.equal(fresh.sequence,first.sequence+1);assert.equal(fresh.age_s,0);

// Exercise the actual UI refresh and button handlers without opening a browser.
const nodes=new Map(),node=key=>{if(!nodes.has(key))nodes.set(key,{style:{setProperty(){}},dataset:{},classList:{toggle(){}},setAttribute(k,v){this[k]=v;}});return nodes.get(key);};
globalThis.document={activeElement:null};
const sent=[],op=Object.assign(Object.create(FlightOperations.prototype),{
 state:{ready:true,radio:{enabled:false,connected:false,status:'disabled'},drone:{armed:true,px4_ready:true,pan:0,tilt:0,speed:0}},
 mode:'boat',autopilot:false,boatCamera:'boat_dock',manualMotors:[19,76],app:{gpu:{},fps:60},
 bridge:{cameraView:'boat_dock',installed:true,policy:{status:{enabled:true}},send:p=>sent.push(p)},
 _ui:{root:{querySelector:node,classList:{toggle(){}}}},_bind:node,_text(k,v){node(k).textContent=v;},_toast(){},
});
op._refreshUI();
assert.equal(node('[data-control="port"]').disabled,false);assert.equal(node('[data-control="starboard"]').disabled,false);
assert.equal(node('[data-action="radio"]').textContent,'Enable SX1262');assert.equal(node('[data-action="reconnect"]').disabled,true);
assert.equal(node('link-label').textContent,'SX1262 disabled');
op.reconnect();assert.equal(sent.length,0);op.toggleRadio();assert.deepEqual(sent.pop(),{action:'radio',enabled:true});
op.state.radio={enabled:true,connected:true,status:'stable'};op._refreshUI();op.toggleRadio();assert.deepEqual(sent.pop(),{action:'radio',enabled:false});
assert.equal(node('[data-action="radio"]').textContent,'Disable SX1262');assert.equal(node('[data-action="reconnect"]').disabled,false);
op.autopilot=true;op._refreshUI();assert.equal(node('[data-control="port"]').disabled,true);
delete globalThis.document;
console.log('ML preserves boat controls; disabled or lost SX1262 zeros every radio input, blocks packets/retry; explicit enable reconnects; UI controls passed.');
