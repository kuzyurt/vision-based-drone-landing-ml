import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from 'pyodide';
import {PolicyInference} from '../src/landing/PolicyInference.js';
import {GpuPolicyModel} from '../src/landing/GpuPolicyModel.js';
import {BrowserPX4} from '../src/landing/BrowserPX4.js';

const base=new URL('../public/policy/',import.meta.url),runtime=new URL('../../simulation/runtime/',import.meta.url);
const liveNeural=process.argv.includes('--live-neural');
const stepsIndex=process.argv.indexOf('--steps'),steps=stepsIndex>=0?Number(process.argv[stepsIndex+1]):3;
const expectStartCheck=process.argv.includes('--expect-start-check');
if(liveNeural)await import('./headless-policy.mjs');
globalThis.fetch=async url=>new Response(await fs.readFile(new URL(url)));
const p=new PolicyInference();
await p.initialize({base:base.href,executionProvider:'external-webgpu',loadPython:()=>loadPyodide({indexURL:fileURLToPath(new URL('pyodide/',base))})});
const recordingIndex=process.argv.indexOf('--record');
const frame=JSON.parse(await fs.readFile(new URL(recordingIndex>=0?process.argv[recordingIndex+1]:'browser-performance-2026-10-15T15-05-00-767Z-ml.json',runtime))).sensor_frame;
const missing={sequence:0,capture_time_s:0,received_time_s:0,age_s:0,position_sigma_m:0,synthetic_reference_hz:0,valid:false,dock_ready:false,relative_heading_m:[0,0,0],velocity_heading_m_s:[0,0,0]};
const observation=structuredClone(frame.observation);observation.beacon=missing;
const numeric=p.numeric(observation),connected=p.numeric(frame.observation),radioIndices=new Set([11,12,13,14,15,16,19,21,22]);
// A missing radio reads as a 3.1 s old fix (input 19), the same value the benchmark student is given when radio is blocked.
for(let i=0;i<32;i++)assert.equal(numeric[i],radioIndices.has(i)?(i===19?Math.fround(3.1):0):connected[i],`Numeric input ${i}`);
p.python.globals.set('dropout_json',JSON.stringify(observation));
p.python.runPython(`
import copy, json
import numpy as np
from reference.supervision import supervise_action
from reference.marker_policy import MarkerLandingController
obs=json.loads(dropout_json)
command=np.array([.5,.2,.1,.1,.05,.02])
actual,reason=supervise_action(command,obs,1.,90.)
np.testing.assert_array_equal(actual,command)
assert reason is None
blocked=copy.deepcopy(obs);blocked['beacon']['valid']=True
actual,reason=supervise_action(command,blocked,1.,90.)
assert reason=='dock_not_ready' and np.all(actual[:4]==0)
blocked['px4']['valid']=False
assert supervise_action(command,blocked,1.,90.)[1]=='estimator_unavailable_or_stale'
assert supervise_action(command,obs,86.,90.)[1]=='mission_deadline'
policy=landing_api.runtime.base.policy
assert policy.accept_metric(np.array([0.,0.,1.]),np.array([0.,0.,1.]),obs,0.)==(True,'acquired')
linked=copy.deepcopy(obs);linked['beacon']['valid']=True
assert policy.accept_metric(np.array([0.,0.,3.]),np.zeros(3),linked,0.)==(False,'outside_radio_context')
policy.track=np.zeros(3);policy.metric_time=0.
assert policy.accept_metric(np.ones(3),np.zeros(3),obs,.04)==(False,'tracking_innovation')
assert policy.accept_metric(np.zeros(3),np.zeros(3),obs,3.)==(True,'reacquired')
aligned=copy.deepcopy(obs)
aligned['px4'].update(attitude_ned_rad=[0.,0.,0.],velocity_enu_m_s=[0.,0.,0.],armed=True,landed=False)
aligned['previous_executed_action']=[0.]*6
estimate={'visibility':1.,'relative_position':[0.,0.,2.],'relative_velocity':[0.,0.,0.],
          'normal':[0.,0.,-1.],'heading_pair':[0.,1.],'metric_uncertainty_m':.012,'metric_age_s':0.,
          'visual_motion_window_s':1.2}  # without radio, descent needs >= 1 s of tracked boat motion
`);
p.python.globals.set('dropout_slew_json',JSON.stringify(p.manifest.slew_limits));
p.python.runPython(`
controller=MarkerLandingController(policy.calibration,json.loads(dropout_slew_json))
for i in range(8):
 command,diag=controller.act(copy.deepcopy(estimate),aligned)
 aligned['previous_executed_action']=command.tolist()
assert diag['control_phase']=='descend' and command[2]>0, (diag,command)
bad=copy.deepcopy(estimate);bad['relative_position']=[1.,0.,2.]
controller=MarkerLandingController(policy.calibration,json.loads(dropout_slew_json))
for i in range(8):
 command,diag=controller.act(copy.deepcopy(bad),aligned)
assert diag['control_phase']!='descend'
short=copy.deepcopy(estimate);short['visual_motion_window_s']=.5
controller=MarkerLandingController(policy.calibration,json.loads(dropout_slew_json))
for i in range(8):
 command,diag=controller.act(copy.deepcopy(short),aligned)
assert diag['control_phase']!='descend', 'untrusted heading must not descend'
`);
// A few full-resolution recorded-image decisions verify the production worker
// controller path. Predictions are recorded neural outputs, not a new GPU flight.
const rgb=new Uint8Array(Buffer.from(frame.pixels,'base64'));
let neural;
const planar=new Float32Array(640*360*3);
const delivered=[],transport=new Uint8Array(4096);
// The recording predates the search head: feed empty search outputs ("no boat in view").
const noBoats={search_heat:new Float32Array(45*80).fill(-20),search_offset:new Float32Array(2*45*80),search_presence:new Float32Array(1).fill(-20),search_evidence:new Float32Array(4*45*80),search_identity:new Float32Array(2*45*80)};
const pilot=Object.assign(Object.create(BrowserPX4.prototype),{
 module:{HEAPU8:transport,_tw_offboard_write(pointer,length){delivered.push(transport.slice(pointer,pointer+length));},_tw_heartbeat(){}},
 raw:0,data:{time:1},forces:{pan:0,tilt:0},lastPowerReport:100,policySequence:0,
 configuration:{parameters:{MPC_XY_VEL_MAX:2}},
});
if(liveNeural){
 for(let i=0;i<640*360;i++){planar[i]=rgb[i*3];planar[640*360+i]=rgb[i*3+1];planar[640*360*2+i]=rgb[i*3+2];}
 neural=new GpuPolicyModel();await neural.initialize(p.verifiedModel,base.href,{inputContract:p.manifest.input_contract});
}
for(const startDisconnected of [false,true]){
 p.reset();neural?.reset();
 let previous=frame.observation.previous_executed_action;
 for(let i=0;i<steps;i++){
  const obs=structuredClone(frame.observation);obs.image_capture_time_s+=i*.04;obs.image_delivery_time_s+=i*.04;
  if(startDisconnected||i>0)obs.beacon=missing;
  obs.previous_executed_action=previous;
  obs.mission={elapsed_s:1+i*.04,budget_s:180};  // the recordings predate the mission clock
  const out=neural?await neural.run(planar,p.numeric(obs)):null;
  const prediction=out?out.prediction:Float32Array.from(frame.prediction);
  const result=await p.act(rgb,obs,1+i*.04,prediction,out?.search??noBoats);
  assert.equal(result.intervention,null);assert(result.action.every(Number.isFinite));
  assert(result.action.slice(0,4).some(x=>Math.abs(x)>1e-5),'Missing radio must not zero flight commands');
  assert.notEqual(result.diagnostics.metric_acceptance,'radio_reference_stale');
  pilot.policyPilot(result.action,obs.px4.attitude_ned_rad[2]);
  const packet=delivered.at(-1),view=new DataView(packet.buffer,packet.byteOffset,packet.byteLength);
  assert.equal(packet[5],84);assert.equal(view.getUint16(54,true),1479);
  assert([22,26,30,50].some(offset=>Math.abs(view.getFloat32(offset,true))>1e-5),'Nonzero command must reach the PX4 offboard transport');
  previous=result.action;
  if(expectStartCheck){
   // The recorded drone is 6.2 m up with the boat far away. Without radio the
   // policy must not hover: it starts its one-time check, climbing to the 7 m
   // search height with the camera turning straight down.
   assert.equal(result.diagnostics.control_phase,'pre360_nadir');
   assert(result.action[2]<-.05,'Zero radio must climb to the search height');
   assert(result.action[5]>0,'The camera must turn towards straight down');
  }
  console.log(JSON.stringify({live_neural:liveNeural,startDisconnected,frame:i,visibility:result.diagnostics.raw_model_visibility_probability,phase:result.diagnostics.control_phase,metric_valid:result.diagnostics.metric_valid,acceptance:result.diagnostics.metric_acceptance,action:result.action}));
 }
}
await neural?.close();await p.close();
console.log('Radio numeric slots read as no radio (zeros, 3.1 s fix age), other sensors unchanged; commands reach PX4 transport without a radio override. Inspect frame diagnostics for actual pose acceptance/tracking; nonzero fallback commands do not prove tracking. Estimator/deadline and visual innovation guards remain.');
if(liveNeural)process.exit(0);
