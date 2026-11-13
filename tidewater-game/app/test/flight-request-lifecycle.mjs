import assert from 'node:assert/strict';
import {BrowserPX4} from '../src/landing/BrowserPX4.js';
import {BrowserGame} from '../src/landing/BrowserGame.js';
import {FlightOperations} from '../src/game/FlightOperations.js';
const memory=new Float64Array(64),observed=new Float64Array(20),commands=[];
observed[0]=1;observed[12]=1;
const pilot=Object.assign(Object.create(BrowserPX4.prototype),{status:new Float64Array(20),pointer:0,buffer:()=>memory,module:{_tw_observation:()=>memory.set(observed),_tw_heartbeat(){},_tw_battery(){},_tw_setpoint(){}},vehicleCommand:(...args)=>commands.push(args),flightRequested:true,landingRequested:false,armed:false,landed:true,targetHeight:1.5,armRequestTime:0,lastArmTry:0,lastDisarmTry:0,lastPowerReport:100,data:{time:100,xmat:new Float64Array([1,0,0,0,1,0,0,0,1])},configuration:{drone:{base:0}},forces:{pan:0,tilt:0,voltage:16,current:0,charge:12}});
pilot.observation();assert(pilot.flightRequested,'Grounded arming sequence must not be cleared');
pilot.landingRequested=true;pilot.armed=true;observed[11]=1;pilot.observation();assert(pilot.flightRequested,'Landing must keep control active while armed');
pilot.armed=false;observed[11]=0;pilot.observation();assert(!pilot.flightRequested&&!pilot.landingRequested,'Grounded and disarmed landing must end the request');
pilot.pilot([]);assert(!commands.some(([cmd,args])=>cmd===400&&args[0]===1),'Idle landing must not rearm');
pilot.armed=true;pilot.targetHeight=.204;pilot.pilot([]);assert(commands.some(([cmd,args])=>cmd===400&&args[0]===0),'Late arm after cancellation must be disarmed');
pilot.armed=false;pilot.flightRequested=true;pilot.landingRequested=true;observed[11]=0;observed[12]=0;pilot.pilot([]);assert(!commands.some(([cmd,args])=>cmd===400&&args[0]===1),'Landing request must never issue arm commands');
pilot.landingRequested=false;pilot.targetHeight=.205;observed[12]=1;pilot.observation();assert(!pilot.flightRequested,'Keyboard landing also ends the flight request');
const game=Object.assign(Object.create(BrowserGame.prototype),{px4:pilot,ml:{enabled:false},takeoffPending:true,keys:['KeyW']});game.input({action:'land'});assert(!game.takeoffPending);assert.deepEqual(game.keys,[]);assert(pilot.landingRequested);assert.equal(pilot.targetHeight,.204);
const sent=[],op=Object.assign(Object.create(FlightOperations.prototype),{state:{ready:true,drone:{px4_ready:true,landed:true,armed:false,flight_requested:false}},bridge:{installed:true,cameraView:'drone',send:p=>sent.push(p)},_toast(){}});
assert.equal(op._flightControl().label,'Take off');op.toggleFlight();assert.equal(sent.at(-1).action,'takeoff');
op.state.drone.flight_requested=true;assert.equal(op._flightControl().label,'Cancel takeoff');op.toggleFlight();assert.equal(sent.at(-1).action,'land');
op.state.drone.armed=true;assert.equal(op._flightControl().label,'Land');
op.state.drone.landing_requested=true;const before=sent.length;assert.equal(op._flightControl().label,'Landing…');op.toggleFlight();assert.equal(sent.length,before);
op.state.drone.takeoff_pending=true;assert.equal(op._flightControl().label,'Preparing takeoff…');
// Capture the velocity at the moment the setpoint is handed to PX4: the fake observation below
// reuses the same buffer, so reading it afterwards would see zeros.
let sentVelocity=null;pilot.module._tw_setpoint=()=>{sentVelocity=Array.from(memory.subarray(2,5));};
pilot.configuration.parameters={MPC_XY_VEL_MAX:2};pilot.armed=true;pilot.landed=false;pilot.flightRequested=true;pilot.landingRequested=false;
pilot.pilot(['KeyW']);assert(Math.abs(Math.hypot(...sentVelocity)-2)<1e-9,'Full stick must ask for MPC_XY_VEL_MAX, not a 1 m/s unit vector');
pilot.pilot([]);assert(Math.hypot(...sentVelocity)<1e-9,'No keys must command a hover');
console.log('Flight intent clears only on confirmed grounding/disarming; cancellation, late arming, keyboard landing, button states and the 2 m/s stick setpoint passed');
