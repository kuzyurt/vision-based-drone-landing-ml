import {Worker} from 'node:worker_threads';
export function createCompilerWorker() {
 const native=new Worker(new URL('world-compiler-worker.mjs',import.meta.url));
 const worker={postMessage:(...args)=>native.postMessage(...args),terminate:()=>native.terminate()};
 native.on('message',data=>worker.onmessage?.({data}));
 native.on('error',error=>worker.onerror?.(error));
 return worker;
}
