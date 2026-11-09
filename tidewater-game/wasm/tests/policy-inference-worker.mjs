import {parentPort} from 'node:worker_threads';
import '../../app/test/headless-policy.mjs';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from '../../app/node_modules/pyodide/pyodide.mjs';
import {PolicyInference} from '../../app/src/landing/PolicyInference.js';
const policy=new PolicyInference(),base=new URL('../../app/public/policy/',import.meta.url);
delete globalThis.location;
globalThis.fetch=async url=>new Response(await fs.readFile(new URL(url)));
parentPort.on('message',async p=>{
 try{if(p.type==='initialize'){await policy.initialize({base:base.href,loadPython:()=>loadPyodide({indexURL:fileURLToPath(new URL('pyodide/',base)),stdout:s=>console.error(s),stderr:s=>console.error(s)})});parentPort.postMessage({ready:true});}
 else if(p.type==='act'){parentPort.postMessage({id:p.id,result:await policy.act(p.rgb,p.observation,p.elapsed)});}
 else if(p.type==='reset'){policy.reset();parentPort.postMessage({reset:true});}
 }catch(error){parentPort.postMessage({id:p.id,error:error.stack});}
});

