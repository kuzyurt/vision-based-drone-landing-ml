import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import load from '../../app/public/landing/wasm/px4.mjs';
const base=new URL('../../app/public/landing/physics/',import.meta.url),c=JSON.parse(await fs.readFile(new URL('configuration.json',base),'utf8')),boot=JSON.parse(await fs.readFile(new URL('px4-startup.json',base),'utf8')),lines=[];
const module=await load({noInitialRun:true,print:s=>lines.push(s),printErr:s=>lines.push(s)}),command=s=>module.ccall('tw_command','number',['string'],[s]);
const report={reference:'Original X500 effective configuration exported from px4_configuration.json; all explicit flight/sensor parameters override numeric ROMFS defaults',required:[],optional_default_warnings:[]};
try {
 module.FS.mkdirTree('/fs/microsd');module._tw_init();assert.equal(command('param select /fs/microsd/parameters'),0);
 for(const cmd of boot){const result=command(cmd);if(result!==0)report.optional_default_warnings.push({command:cmd,result});}
 for(const [name,value] of Object.entries(c.parameters)){assert.equal(command(`param set ${name} ${value}`),0,`Required reference parameter ${name}`);lines.length=0;assert.equal(command(`param show -q ${name}`),0);const numeric=lines.flatMap(line=>String(line).replace(/\u001b\[[0-9;]*m/g,'').split('\n')).filter(line=>/^[-+]?\d+(\.\d+)?([eE][-+]?\d+)?$/.test(line.trim())).map(Number);assert(numeric.length>0,`No effective value for ${name}: ${lines.join(' ')}`);assert(Math.abs(numeric.at(-1)-value)<.000051,`${name} changed: ${numeric.at(-1)} != ${value}`);report.required.push({name,reference:value,effective:numeric.at(-1)});}
 await fs.writeFile(new URL('../../benchmarks/flight-parity/browser-parameters.json',import.meta.url),JSON.stringify(report,null,2));console.log('Effective original parameters passed:',report.required.length,'; optional ROMFS defaults absent:',report.optional_default_warnings);
}finally{module.PThread.terminateAllThreads();}
process.exit(0);
