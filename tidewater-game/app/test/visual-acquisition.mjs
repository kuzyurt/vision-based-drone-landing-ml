import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from 'pyodide';
import {PolicyInference} from '../src/landing/PolicyInference.js';

const base=new URL('../public/policy/',import.meta.url);
globalThis.fetch=async url=>new Response(await fs.readFile(new URL(url)));
const p=new PolicyInference();
await p.initialize({base:base.href,executionProvider:'external-webgpu',loadPython:()=>loadPyodide({indexURL:fileURLToPath(new URL('pyodide/',base))})});
p.python.runPython(`
import copy, json, math
import numpy as np
from reference.visual_acquisition import camera_geometry, visual_motion
from reference.marker_geometry import marker_pose_reference
cal=landing_api.policy.calibration
zero_beacon={'valid':False,'age_s':0.,'dock_ready':False,'relative_heading_m':[0.,0.,0.],'velocity_heading_m_s':[0.,0.,0.]}
synthetic_observation={'px4':{'valid':True,'armed':True,'landed':False,'position_enu_m':[0.,0.,2.],
 'velocity_enu_m_s':[0.,0.,0.],'attitude_ned_rad':[0.,0.,0.],'angular_rate_frd_rad_s':[0.,0.,0.],
 'position_age_s':0.,'attitude_age_s':0.},'beacon':zero_beacon,'gimbal_rad':[0.,math.pi/2],
 'image_capture_time_s':0.,'image_delivery_time_s':0.,'image_age_s':0.,'image_valid':True,
 'decision_dt_s':.04,'previous_executed_action':[0.]*6}
rotation,origin,focal,_=camera_geometry(synthetic_observation,cal)
normal=np.array([0.,0.,-1.]);x=np.array([1.,0.,0.]);y=np.cross(normal,x)
center=np.array([0.,0.,1.6]);distance=-np.dot(normal,center-origin)
qcenter=np.array([(center-origin)@x,(center-origin)@y])/((center-origin)@normal)
yy,xx=np.indices((360,640))
rays=np.stack(((xx-320)/focal,-(yy-180)/focal,-np.ones_like(xx)),axis=-1)@rotation.T
denominator=rays@normal;valid=denominator<-.05
q=rays/np.where(valid,denominator,-1.)[...,None]
coordinates=distance*(qcenter-np.stack((q@x,q@y),axis=-1))
u,w=np.abs(coordinates[...,0]),np.abs(coordinates[...,1]);extent=np.maximum(u,w)
paint=valid&(((extent<=.13)&(extent>=.123))|((u<=.005)&(w<=.085))|((w<=.005)&(u<=.085)))
synthetic_rgb=np.zeros((360,640,3),dtype=np.uint8);synthetic_rgb[paint]=[40,220,220]
assert paint.sum()>=12
cam=rotation.T@(center-origin)
pixel=np.array([320+focal*cam[0]/-cam[2],180-focal*cam[1]/-cam[2]])
assert 15<pixel[0]<625 and 15<pixel[1]<345
# Deliberately wrong zero-radio range prior: the image must provide the scale.
synthetic_prediction=np.array([12.,0.,0.,.001,0.,0.,0.,0.,1.,0.,0.,-1.,pixel[0]/320-1,pixel[1]/180-1,-12.],dtype=np.float32)
`);
const rgbProxy=p.python.runPython('synthetic_rgb.ravel()'),rgb=Uint8Array.from(rgbProxy.toJs());rgbProxy.destroy();
const predProxy=p.python.globals.get('synthetic_prediction'),prediction=Float32Array.from(predProxy.toJs());predProxy.destroy();
const template=JSON.parse(p.python.runPython('json.dumps(synthetic_observation)'));
let previous=Array(6).fill(0),last,first;
for(let i=0;i<10;i++){
 const observation=structuredClone(template);observation.previous_executed_action=previous;observation.image_capture_time_s=observation.image_delivery_time_s=i*.04;
 const result=await p.act(rgb,observation,i*.04,prediction);first??=result;last=result;previous=result.action;
 assert.equal(result.intervention,null);assert.equal(result.diagnostics.metric_valid,true,'Full paint must acquire despite the zero range prior');
 assert(result.diagnostics.marker_paint_precision>=.7&&result.diagnostics.marker_paint_recall>=.65);
}
assert.equal(first.diagnostics.metric_acceptance,'acquired');assert.equal(last.diagnostics.control_phase,'descend');assert(last.action[2]>0);
assert(Math.abs(last.diagnostics.estimated_clearance_m-1.4)<.3);
// A confident neural detection alone is insufficient: blank/partial paint
// cannot bypass metric acceptance or enable descent.
for(const image of [new Uint8Array(rgb.length),rgb.map((v,i)=>i%(640*3)<320*3?0:v)]){
 p.reset();const observation=structuredClone(template);const result=await p.act(image,observation,0,prediction);
 assert.equal(result.diagnostics.metric_valid,false);assert.notEqual(result.diagnostics.control_phase,'descend');
 assert.equal(result.diagnostics.pose_valid,false);assert.equal(result.action[2],0);
}
p.python.runPython(`
from types import SimpleNamespace
policy=SimpleNamespace()
observation=copy.deepcopy(synthetic_observation)
for i in range(8):
 current={'relative_position':np.array([.8*i*.04,0.,1.6]),'relative_velocity':np.zeros(3)}
 current=visual_motion(policy,current,observation,i*.04,{})
np.testing.assert_allclose(current['relative_velocity'],[.8,0.,0.],atol=1e-10)
np.testing.assert_allclose(policy.visual_velocity_enu,[0.,.8,0.],atol=1e-10)
`);
console.log(JSON.stringify({zero_radio_metric_acquisition:true,wrong_neural_range_prior:.001,phase:last.diagnostics.control_phase,action:last.action,marker_rms_px:last.diagnostics.marker_fit_rms_px,blank_and_clipped_paint_rejected:true,visual_boat_velocity_checked:true}));
await p.close();
