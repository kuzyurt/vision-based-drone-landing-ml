// Compiler lifetime is owned by the flight worker. Terminate it before exposing
// the binary to the flight runtime, including on reset, cancellation or failure.
export function prepareBrowserWorld({createWorker,base,c,map,progress,signal}) {
 if(signal?.aborted)return Promise.reject(new DOMException('Simulation stopped','AbortError'));
 return new Promise((resolve,reject)=>{
  let worker,settled=false;
  const finish=async(error,binary)=>{
   if(settled)return;settled=true;signal?.removeEventListener('abort',abort);
   if(worker){worker.onmessage=null;worker.onerror=null;worker.onmessageerror=null;}
   try{await worker?.terminate();}catch(terminationError){error ||= terminationError;}
   if(error)reject(error);else resolve(binary);
  };
  const abort=()=>finish(new DOMException('Simulation stopped','AbortError'));
  try{
   worker=createWorker();
   worker.onmessage=event=>{
    const packet=event.data;
    if(packet.error)finish(new Error(packet.error));
    else if(packet.binary instanceof Uint8Array)finish(null,packet.binary);
    else if(packet.status)progress(packet.status);
   };
   worker.onerror=event=>finish(new Error(event.message||'World compiler worker failed'));
   worker.onmessageerror=()=>finish(new Error('Could not receive compiled Tidewater world'));
   signal?.addEventListener('abort',abort,{once:true});
   const heights=new Float32Array(map.heights);
   worker.postMessage({base,c,meta:map.meta,heights},[heights.buffer]);
  }catch(error){finish(error);}
 });
}
