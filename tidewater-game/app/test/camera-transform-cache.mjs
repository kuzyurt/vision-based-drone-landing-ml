import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from 'pyodide';
import {PolicyInference} from '../src/landing/PolicyInference.js';
const base=new URL('../public/policy/',import.meta.url),runtime=new URL('../../simulation/runtime/',import.meta.url);
globalThis.fetch=async url=>new Response(await fs.readFile(new URL(url)));
const p=new PolicyInference();await p.initialize({base:base.href,executionProvider:'external-webgpu',loadPython:()=>loadPyodide({indexURL:fileURLToPath(new URL('pyodide/',base))})});
p.python.runPython(`import copy, math, time, json
import numpy as np
from reference import camera_geometry as cg, camera_geometry_fast as cgf
from reference import marker_policy as mp, marker_geometry as mg, marker_geometry_fast as mgf
original=cg.camera_body_transform_reference
fast=cgf.camera_body_transform_fast
cal=landing_api.policy.calibration
for pan in [-math.pi, -.3, 0., .3, math.pi]:
 for tilt in [-math.pi/18, 0., .7, math.pi/2]:
  expected=original(cal,[pan,tilt]);actual=fast(cal,[pan,tilt])
  np.testing.assert_array_equal(actual,expected)
  actual[:]=99
  np.testing.assert_array_equal(fast(cal,[pan,tilt]),expected)
cal2=copy.deepcopy(cal);cal2['camera_pos'][0]+=.001
np.testing.assert_array_equal(fast(cal2,[.1,.7]),original(cal2,[.1,.7]))
np.testing.assert_array_equal(fast(cal,[.1,.7]),original(cal,[.1,.7]))
def select_transform(use_fast):
 f=fast if use_fast else original
 cg.camera_body_transform=f;mp.camera_body_transform=f;mg.camera_body_transform=f;mgf.camera_body_transform=f
def transform_cost(use_fast):
 f=fast if use_fast else original
 t=time.perf_counter()
 for i in range(100):f(cal,[.2,1.4+i*1e-7])
 return (time.perf_counter()-t)*10
json.dumps({'reference_ms_per_call':transform_cost(False),'cached_ms_per_call':transform_cost(True)})
`);
const record=JSON.parse(await fs.readFile(new URL('browser-performance-2026-10-15T15-05-00-767Z-ml.json',runtime))).sensor_frame,rgb=new Uint8Array(Buffer.from(record.pixels,'base64')),expected=[];
const run=async fast=>{
 p.reset();p.python.runPython(`select_transform(${fast?'True':'False'})\nlanding_api.policy.controller.camera_branch=0.`);
 const rows=[];
 for(let i=0;i<3;i++){const observation=structuredClone(record.observation);observation.image_capture_time_s+=i*.04;observation.image_delivery_time_s+=i*.04;const start=performance.now(),result=await p.act(rgb,observation,record.elapsed+i*.04,Float32Array.from(record.prediction));rows.push({ms:performance.now()-start,result});}
 return rows;
};
const reference=await run(false),cached=await run(true);
for(let i=0;i<reference.length;i++){assert.deepEqual(cached[i].result.action,reference[i].result.action);assert.deepEqual(cached[i].result.diagnostics,reference[i].result.diagnostics);assert.deepEqual(cached[i].result.intervention,reference[i].result.intervention);}
const costs=JSON.parse(p.python.runPython("json.dumps({'reference_ms_per_call':transform_cost(False),'cached_ms_per_call':transform_cost(True)})"));
console.log(JSON.stringify({matrix_and_controller_bit_equal:true,independent_return_values:true,calibration_change_checked:true,...costs,reference_controller_ms:reference.map(x=>x.ms),cached_controller_ms:cached.map(x=>x.ms)}));
await p.close();
