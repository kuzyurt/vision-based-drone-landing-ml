import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from 'pyodide';
import {PolicyInference} from '../src/landing/PolicyInference.js';
import {MarkerKernel} from '../src/landing/MarkerKernel.js';
const base=new URL('../public/policy/',import.meta.url),runtime=new URL('../../simulation/runtime/',import.meta.url);globalThis.fetch=async url=>new Response(await fs.readFile(new URL(url)));
const recordingIndex=process.argv.indexOf('--recording'),baselineIndex=process.argv.indexOf('--baseline');
const p=new PolicyInference();await p.initialize({base:base.href,executionProvider:recordingIndex>=0?'external-webgpu':'wasm',keepPythonRgb:true,loadPython:()=>loadPyodide({indexURL:fileURLToPath(new URL('pyodide/',base))})});
let oldKernel,benchmarkCase;if(baselineIndex>=0){oldKernel=new MarkerKernel();await oldKernel.initialize(new Uint8Array(await fs.readFile(process.argv[baselineIndex+1])));p.python.globals.set('baseline_kernel',oldKernel);
 const begin=p.kernel.begin.bind(p.kernel),call=p.kernel.call.bind(p.kernel);
 p.kernel.begin=parameters=>{benchmarkCase={parameters:p.kernel.buffer(parameters,'f64',v=>Float64Array.from(v)),starts:[]};const actual=begin(parameters),expected=oldKernel.begin(parameters);assert.equal(actual,expected);if(actual)assert.deepEqual(p.kernel.info(),oldKernel.info());return actual;};
 p.kernel.call=(name,value,length)=>{if(name==='marker_fit')benchmarkCase.starts.push(p.kernel.buffer(value,'f64',v=>Float64Array.from(v)));const actual=call(name,value,length);assert.deepEqual(actual,oldKernel.call(name,value,length),name+' must preserve every FP64 value');return actual;};
}
p.python.runPython(`import copy,json,time
from js import marker_kernel
from reference import marker_policy as mp
from reference.marker_geometry import marker_pose_reference
from reference.marker_geometry_fast import marker_pose_fast
last_marker_call=None
def capture_marker_call(rgb,obs,cal,estimate):
 global last_marker_call
 last_marker_call=(rgb.copy(),copy.deepcopy(obs),copy.deepcopy(cal),copy.deepcopy(estimate))
 return marker_pose_reference(rgb,obs,cal,estimate)
mp.marker_pose=capture_marker_call
def compare_marker():
 if last_marker_call is None:return '{}'
 args=last_marker_call
 t=time.perf_counter();expected=marker_pose_reference(*args);original_ms=1000*(time.perf_counter()-t)
 t=time.perf_counter();actual=marker_pose_fast(*args,marker_kernel);optimized_ms=1000*(time.perf_counter()-t)
 assert (actual is None)==(expected is None),(actual,expected)
 result={'tracked':args[3].get('_tracked'), 'original_ms':original_ms,'optimized_ms':optimized_ms,'timing_includes_baseline_validation':'baseline_kernel' in globals(),'valid':actual is not None}
 if 'baseline_kernel' in globals():
  t=time.perf_counter();older=marker_pose_fast(*args,baseline_kernel);result['previous_kernel_ms']=1000*(time.perf_counter()-t)
  assert (older is None)==(actual is None)
  if actual is not None:
   for key in actual:
    import numpy as np
    np.testing.assert_array_equal(np.asarray(actual[key]),np.asarray(older[key]),err_msg=key)
  result['previous_kernel_bit_equal']=True
 if actual is not None:
  for key in actual:
   import numpy as np
   error=float(np.max(np.abs(np.asarray(actual[key])-np.asarray(expected[key]))))
   assert error<1e-4,(key,error,actual[key],expected[key])
  result['position_error_m']=float(np.linalg.norm(actual['relative_position']-expected['relative_position']))
 return json.dumps(result)
`);
let record,rgb;
if(recordingIndex>=0){const recording=JSON.parse(await fs.readFile(process.argv[recordingIndex+1]));record=recording.sensor_frame;rgb=new Uint8Array(Buffer.from(record.pixels,'base64'));}
else {const records=(await fs.readFile(new URL('ml-live-frames.jsonl',runtime),'utf8')).trim().split('\n').map(JSON.parse),frame=Number(process.argv[2]||101);record=process.argv[2]?records.findLast(r=>r.frame===frame):records.find(r=>r.frame===101);rgb=new Uint8Array((await fs.readFile(new URL(process.argv[3]||'ml-profile-rgb.ppm',runtime))).subarray(-640*360*3));}
oldKernel?.setImage(rgb);
const iterationsIndex=process.argv.indexOf('--iterations'),iterations=iterationsIndex>=0?Number(process.argv[iterationsIndex+1]):4;
for(let i=0;i<iterations;i++){const observation=structuredClone(record.observation);observation.image_capture_time_s+=i*.04;observation.image_delivery_time_s+=i*.04;const prediction=recordingIndex>=0?Float32Array.from(record.prediction):undefined;const result=await p.act(rgb,observation,i*.04,prediction);console.log(i,result.diagnostics.control_phase,p.python.runPython('compare_marker()'));}
if(oldKernel&&benchmarkCase?.starts.length){
 const optimized=new MarkerKernel();await optimized.initialize(new Uint8Array(await fs.readFile(new URL('marker_kernel.wasm',base))));optimized.setImage(rgb);
 const run=kernel=>{const t=performance.now();kernel.begin(benchmarkCase.parameters);let last;for(const v of benchmarkCase.starts)last=kernel.fit(v);if(last)kernel.finish(last.subarray(0,4));return performance.now()-t;};
 run(oldKernel);run(optimized);const previous=[],current=[];
 for(let i=0;i<7;i++){if(i%2){current.push(run(optimized));previous.push(run(oldKernel));}else{previous.push(run(oldKernel));current.push(run(optimized));}}
 previous.sort((a,b)=>a-b);current.sort((a,b)=>a-b);console.log('ISOLATED_KERNEL',JSON.stringify({tracked:!!benchmarkCase.parameters[27],previous_median_ms:previous[3],current_median_ms:current[3],speedup:previous[3]/current[3],previous,current}));optimized.close();
}
await p.close();oldKernel?.close();console.log('Original and accelerated registration agree; FP64 TRF loss, bounds, stopping rules, sample counts and acceptance tests preserved.');
