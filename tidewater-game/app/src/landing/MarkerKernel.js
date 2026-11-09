export class MarkerKernel {
 async initialize(bytes){
  const {instance}=await WebAssembly.instantiate(bytes,{env:{emscripten_notify_memory_growth(){}},wasi_snapshot_preview1:{proc_exit:code=>{throw new Error('Marker kernel exited: '+code);},fd_close:()=>0,fd_write:()=>0,fd_seek:()=>0}});
  this.wasm=instance.exports;this.wasm._initialize?.();this.image=this.wasm.malloc(640*360*3);this.parameters=this.wasm.malloc(28*8);this.vector=this.wasm.malloc(4*8);
 }
 setImage(rgb){new Uint8Array(this.wasm.memory.buffer,this.image,rgb.length).set(rgb);this.paint=null;}
 paintPixels(){if(!this.paint){const pointer=this.wasm.marker_paint(this.image),count=new Uint32Array(this.wasm.memory.buffer,pointer,1)[0];this.paint=new Uint32Array(new Uint32Array(this.wasm.memory.buffer,pointer+4,count));}return this.paint;}
 buffer(value,type,fn){
  if(value instanceof Float64Array)return fn(value);
  const buffer=value.getBuffer(type);try{return fn(buffer.data);}finally{buffer.release();}
 }
 begin(parameters){const start=performance.now();try{return this.buffer(parameters,'f64',values=>{new Float64Array(this.wasm.memory.buffer,this.parameters,28).set(values);const valid=this.wasm.marker_begin(this.image,this.parameters);if(valid)this.count=new Float64Array(this.wasm.memory.buffer,this.wasm.marker_info(),6)[4]+180;return valid;});}finally{this.timings??={};this.timings.begin_ms=(this.timings.begin_ms||0)+performance.now()-start;}}
 info(){return new Float64Array(new Float64Array(this.wasm.memory.buffer,this.wasm.marker_info(),6));}
 call(name,v,length){const start=performance.now();try{return this.buffer(v,'f64',values=>{new Float64Array(this.wasm.memory.buffer,this.vector,4).set(values);return new Float64Array(new Float64Array(this.wasm.memory.buffer,this.wasm[name](this.vector),length));});}finally{this.timings??={};const key=name.replace('marker_','')+'_ms';this.timings[key]=(this.timings[key]||0)+performance.now()-start;}}
 residual(v){return this.call('marker_residual',v,this.count);}
 jacobian(v){return this.call('marker_jacobian',v,this.count*4);}
 fit(v){return this.call('marker_fit',v,5+this.count*4);}
 finish(v){return this.call('marker_finish',v,13);}
 close(){if(this.wasm){for(const p of [this.image,this.parameters,this.vector])this.wasm.free(p);this.wasm=null;}}
}
