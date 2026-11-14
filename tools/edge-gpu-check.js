(async () => {
  const timeout = (promise, ms) => Promise.race([promise.then(value => ({ok:true, value}), error => ({ok:false, error:String(error?.message || error)})), new Promise(resolve => setTimeout(() => resolve({timeout:true}), ms))]);
  const adapter = await navigator.gpu.requestAdapter();
  const features = ['float32-filterable','timestamp-query','rg11b10ufloat-renderable','float32-blendable','shader-f16','clip-distances','subgroups'].filter(f => adapter.features.has(f));
  const limits = {};
  for (const key of ['maxSampledTexturesPerShaderStage','maxSamplersPerShaderStage','maxStorageBuffersPerShaderStage','maxStorageTexturesPerShaderStage','maxComputeWorkgroupStorageSize','maxComputeInvocationsPerWorkgroup','maxComputeWorkgroupSizeX','maxComputeWorkgroupSizeY','maxComputeWorkgroupSizeZ','maxComputeWorkgroupsPerDimension','maxColorAttachmentBytesPerSample','maxStorageBuffersInVertexStage','maxStorageBuffersInFragmentStage','maxStorageTexturesInFragmentStage','maxBindingsPerBindGroup','maxBufferSize','maxStorageBufferBindingSize']) limits[key] = adapter.limits[key];
  const constrained = await timeout(adapter.requestDevice({requiredFeatures:features,requiredLimits:limits}), 15000);
  return {constrained: constrained.timeout ? 'TIMEOUT' : constrained.ok ? 'OK' : constrained.error, features};
})()
