import assert from 'node:assert/strict';
import {AerodockWake} from '../src/ocean/AerodockWake.js';
import {Vector2,Vector3,Quaternion} from '../src/engine/index.js';
// The AERODOCK wake follows the physics boat speed, heading and motor powers,
// not frame-to-frame jumps of the drawn pose.
const field=v=>({value:v});
const make=()=>{const w=Object.create(AerodockWake.prototype);Object.assign(w,{
 kernelParams:{fields:Object.fromEntries(['origin','prev','center','boatPos','fwd','right','vel','propThrust'].map(k=>[k,field(new Vector2())]).concat(['speed','fwdSpeed','latSpeed','yawRate','dt','reset'].map(k=>[k,field(0)])))},
 center:new Vector2(),hasWindow:false,_fwd:new Vector2(0,1),_right:new Vector2(1,0),_prevPos:new Vector2(),_vel:new Vector2(),_hasPrev:false,_heading:null,_speed:0,_fwdSpeed:0,_latSpeed:0,_fwdAccel:0,_yawRate:0,_portThrust:0,_stbdThrust:0,_idleTime:1e9,_everActive:false,_portProp:null,_stbdProp:null,_prevPortSpin:null,_prevStbdSpin:null,_portSpinRate:0,_stbdSpinRate:0,dispatched:0});
 w.amount=field(0);w._dispatch=function(){this.dispatched++;};return w;};
// Boat group with two propeller siblings whose quaternion sign flips every frame (q and -q are the same pose).
const scene=()=>{const parent={children:[]};const boat={name:'Physics body boat',parent,position:new Vector3(),quaternion:new Quaternion(),initialized:true};
 const prop=name=>({name,parent,position:new Vector3(),quaternion:new Quaternion(),initialized:true});const port=prop('Physics body port_prop'),stbd=prop('Physics body starboard_prop');parent.children.push(boat,port,stbd);return {boat,port,stbd};};
const dt=1/60;
// 1. A boat at rest (waves only) never shows a wake, even with a jittery drawn pose and flipping propeller quaternions.
{const w=make(),{boat,port,stbd}=scene();let t=0,amounts=[];
 for(let i=0;i<1200;i++){t+=dt;const stall=i%30<12;if(!stall)boat.position.set(.02*Math.sin(i*.3),0,.02*Math.cos(i*.2)); // drawn pose freezes then jumps
  port.position.set(-.2,0,-1.2);stbd.position.set(.2,0,-1.2);const s=i%2?-1:1;port.quaternion.set(0,.7071*s,0,.7071*s);stbd.quaternion.set(0,-.7071*s,0,.7071*s);
  w.update(dt,boat,true,{time_s:Math.floor(t/.04)*.04,boat:{velocity:[.001,0,-.001],yaw:.3,port_power:0,starboard_power:0}});amounts.push(w.amount.value);}
 assert.equal(Math.max(...amounts),0,'A boat at rest must not raise a wake');}
// 2. A moving boat keeps a steady wake although the drawn pose stalls and catches up (ML pauses).
{const w=make(),{boat,port,stbd}=scene();let t=0,x=0,amounts=[];
 for(let i=0;i<1500;i++){t+=dt;x+=1.4*dt;if(i%40>=10)boat.position.set(x,0,0); // stalled for 10 of every 40 frames
  port.position.set(boat.position.x-1.2,0,-.2);stbd.position.set(boat.position.x-1.2,0,.2);
  w.update(dt,boat,true,{time_s:Math.floor(t/.04)*.04,boat:{velocity:[1.4,0,0],yaw:0,port_power:18,starboard_power:18}});if(i>600)amounts.push(w.amount.value);}
 assert(Math.min(...amounts)>.97,'A moving boat must keep a steady wake: min '+Math.min(...amounts));
 assert(w.dispatched>800,'The wake simulation must keep running while moving');}
console.log('AERODOCK wake: none at rest with a jittery pose, steady while moving through physics pauses.');
