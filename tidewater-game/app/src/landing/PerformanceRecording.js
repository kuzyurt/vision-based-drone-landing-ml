// Bounded local timing report with at most one synthetic onboard sensor frame.
export async function recordPerformance(app,{duration=10000,interval=250,onProgress=()=>{}}={}) {
 const bridge=app.flightOps.bridge,policy=bridge.policy,rows=[],frames=[];
 const previous=app.onFrameTiming;
 const previousRecording=policy.recordingSample,recording={};policy.recordingSample=recording;
 app.onFrameTiming=ms=>{previous?.(ms);if(frames.length<20000)frames.push(ms);};
 const start=performance.now(),wallStart=Date.now();
 try {
  while(performance.now()-start<duration){
   const state=bridge.state;
   rows.push({elapsed_ms:performance.now()-start,visibility:document.visibilityState,rtf:state?.realtime_factor,sim_time_s:state?.time_s,fps:app.fps,ml_enabled:policy.status.enabled,phase:state?.ml?.phase,applied_action:state?.ml?.action?[...state.ml.action]:null,intervention:state?.ml?.intervention??null,radio:state?.radio?{enabled:state.radio.enabled,connected:state.radio.connected,status:state.radio.status}:null,drone:{armed:state?.drone?.armed,landed:state?.drone?.landed},landing_outcome:state?.ml?.outcome?structuredClone(state.ml.outcome):null,timings:policy.status.enabled&&policy.latestTiming?structuredClone(policy.latestTiming):null,diagnostics:policy.status.enabled&&policy.latestDiagnostics?structuredClone(policy.latestDiagnostics):null});
   onProgress(Math.max(0,Math.ceil((duration-performance.now()+start)/1000)));
   await new Promise(resolve=>setTimeout(resolve,interval));
  }
 }finally{app.onFrameTiming=previous;policy.recordingSample=previousRecording;}
 let sensorFrame=null;
 if(recording.frame){const {rgb,...details}=recording.frame;let binary='';for(let i=0;i<rgb.length;i+=16384)binary+=String.fromCharCode(...rgb.subarray(i,i+16384));sensorFrame={...details,width:640,height:360,encoding:'base64-rgb8',pixels:btoa(binary)};}
 return {schema:'tidewater.performance.v1',recorded_at:new Date(wallStart).toISOString(),duration_ms:performance.now()-start,user_agent:navigator.userAgent,hardware_concurrency:navigator.hardwareConcurrency,device_memory_gb:navigator.deviceMemory,isolated:crossOriginIsolated,operator_adapter:{vendor:app.gpu.adapter.info?.vendor,device:app.gpu.adapter.info?.device,description:app.gpu.adapter.info?.description},policy_adapter:policy.adapter,policy_backend:policy.backend,viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio,render_scale:app.settings.renderScale},operator_frame_cpu_ms:frames,rows,
  render_queue_pacing:'wait-for-operator-GPU-completion-during-ML',
  neural_pipeline:'shared-render-device-texture-and-parallel-RGB-readback',
  policy_layout:policy.layout,requested_gpu_power_preference:app.gpu.powerPreference,
  sensor_bundle_cache:policy.camera?.meshRenderer.bundleCache?{...policy.camera.meshRenderer.bundleCache.stats,entries:policy.camera.meshRenderer.bundleCache.entries.size}:null,
  sensor_frame:sensorFrame,
  timing_notes:{total_ms:'Controller worker duration only with the shared neural pipeline; roundtrip_ms is the complete decision latency.',camera_gpu_ms:'GPU timestamps spanning sensor render commands; excludes earlier queued work and callback scheduling.',camera_readback_wait_ms:'Includes GPU queue completion and main-thread callback scheduling; not a GPU-only duration.',neural_ms:'GPU inference plus submission/readback scheduling; overlaps camera_ms.',operator_frame_cpu_ms:'Synchronous full scene update and command encoding, excludes asynchronous GPU execution.'}};
}
