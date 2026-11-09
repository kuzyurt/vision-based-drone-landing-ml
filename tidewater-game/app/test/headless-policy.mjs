import './headless.mjs';
navigator.userAgent='Node.js'; // Pyodide platform detection in Node GPU verification.
// Native Dawn verification adapter: browser WebGPU accepts SharedArrayBuffer,
// while Dawn's Node binding needs an ordinary byte view at this boundary.
const adapter=await navigator.gpu.requestAdapter({powerPreference:'high-performance'}),request=adapter.requestDevice.bind(adapter);
adapter.requestDevice=async(...args)=>{const device=await request(...args),write=device.queue.writeBuffer.bind(device.queue);device.queue.writeBuffer=(buffer,offset,data,dataOffset=0,size)=>{if(data instanceof SharedArrayBuffer)return write(buffer,offset,new Uint8Array(data),dataOffset,size);return write(buffer,offset,data,dataOffset,size);};return device;};
const original=navigator.gpu.requestAdapter.bind(navigator.gpu);navigator.gpu.requestAdapter=async options=>options?.powerPreference==='high-performance'?adapter:original(options);
