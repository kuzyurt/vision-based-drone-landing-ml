// Local, version-matched runtimes and packages keep policy inference offline-capable.
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
const app=new URL('../',import.meta.url),destination=new URL('public/policy/',app);
const source=new URL('node_modules/pyodide/',app),pyodide=new URL('pyodide/',destination);
await fs.mkdir(pyodide,{recursive:true});
for(const name of ['pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json'])await fs.copyFile(new URL(name,source),new URL(name,pyodide));
const lock=JSON.parse(await fs.readFile(new URL('pyodide-lock.json',source)));
const packages=new Set();function visit(name){if(packages.has(name))return;packages.add(name);for(const dependency of lock.packages[name].depends)visit(dependency);}visit('scipy');
for(const name of packages){const entry=lock.packages[name],file=new URL(entry.file_name,pyodide);let bytes;try{bytes=await fs.readFile(file);}catch{}
 if(!bytes||createHash('sha256').update(bytes).digest('hex')!==entry.sha256){const url='https://cdn.jsdelivr.net/pyodide/v314.0.7/full/'+entry.file_name,response=await fetch(url);if(!response.ok)throw new Error(`${response.status}: ${url}`);bytes=new Uint8Array(await response.arrayBuffer());if(createHash('sha256').update(bytes).digest('hex')!==entry.sha256)throw new Error('Package hash mismatch: '+name);await fs.writeFile(file,bytes);}
 console.log(name,entry.version,bytes.length);
}
const ort=new URL('ort/',destination);await fs.mkdir(ort,{recursive:true});
for(const name of ['ort-wasm-simd-threaded.mjs','ort-wasm-simd-threaded.wasm','ort-wasm-simd-threaded.jsep.mjs','ort-wasm-simd-threaded.jsep.wasm'])await fs.copyFile(new URL('node_modules/onnxruntime-web/dist/'+name,app),new URL(name,ort));
const notices=[];for(const library of ['pyodide','onnxruntime-web','onnxruntime-common'])for(const name of ['LICENSE','LICENSE.txt','LICENSE.md','ThirdPartyNotices.txt']){try{const text=await fs.readFile(new URL('node_modules/'+library+'/'+name,app),'utf8');notices.push(library+'/'+name+'\n'+text);}catch{}}
for(const [name,url] of [
 ['Pyodide 314.0.7','https://raw.githubusercontent.com/pyodide/pyodide/314.0.7/LICENSE'],
 ['ONNX Runtime 1.30.0','https://raw.githubusercontent.com/microsoft/onnxruntime/v1.30.0/LICENSE'],
 ['ONNX Runtime third party notices','https://raw.githubusercontent.com/microsoft/onnxruntime/v1.30.0/ThirdPartyNotices.txt'],
]){const response=await fetch(url);if(!response.ok)throw new Error('Runtime license unavailable: '+url);notices.push(name+'\nSource: '+url+'\n'+await response.text());}
notices.push('SciPy TRF FP64 port\n'+await fs.readFile(new URL('../../wasm/SCIPY-LICENSE.txt',import.meta.url),'utf8'));
await fs.writeFile(new URL('RUNTIME-NOTICES.txt',destination),notices.join('\n\n'));
console.log('Policy runtime files prepared locally; no external runtime downloads are needed by the player.');
