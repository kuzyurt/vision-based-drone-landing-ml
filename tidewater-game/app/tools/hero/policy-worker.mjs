// Node adapter for the production controller worker; no browser is launched.
import {parentPort} from 'node:worker_threads';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {loadPyodide} from '../../node_modules/pyodide/pyodide.mjs';
import {PolicyInference} from '../../src/landing/PolicyInference.js';
globalThis.self=globalThis;globalThis.__policyChecksumReportOnly=true; // LF checkout: the manifest hashes the Windows (CRLF) files
delete globalThis.location;
globalThis.fetch=async url=>{try{return new Response(await fs.readFile(new URL(url)));}catch{return new Response('',{status:404});}};
globalThis.postMessage=(message,transfer=[])=>parentPort.postMessage(message,transfer);
// Pyodide's Node loader requires a filesystem path instead of a browser URL.
const initialize=PolicyInference.prototype.initialize;
PolicyInference.prototype.initialize=function(options){return initialize.call(this,{...options,loadPython:indexURL=>loadPyodide({indexURL:fileURLToPath(new URL(indexURL)),stdout(){},stderr:message=>console.error(message)})});};
await import('../../src/landing/PolicyInferenceWorker.js');
parentPort.on('message',data=>self.onmessage({data}));
