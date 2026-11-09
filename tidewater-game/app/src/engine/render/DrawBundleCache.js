import {GPU} from '../gpu/GPU.js';

// Record the exact existing draw commands. Buffer values remain live; a bundle
// is reused only when every resource, offset, count and ordering is identical.
// One stream per pass, at most eight passes, bounds retained references.
export class DrawBundleCache {
 constructor(){this.entries=new Map();this.scratch=[];this.stats={hits:0,misses:0};}
 draw(rp,pass,record){
  const key=pass.passKey+'|'+pass.layerMask+'|'+pass.bundleList;
  let entry=this.entries.get(key);
  const d=this.scratch;d.length=0;
  const stream={
   setPipeline:p=>d.push(0,p),
   setBindGroup:(i,g,offsets=[])=>{d.push(1,i,g,offsets.length);for(const v of offsets)d.push(v);},
   setVertexBuffer:(i,b)=>d.push(2,i,b),setIndexBuffer:(b,f)=>d.push(3,b,f),
   drawIndexed:(...v)=>d.push(4,...v),draw:(...v)=>d.push(5,...v),
   drawIndexedIndirect:(b,o)=>d.push(6,b,o),drawIndirect:(b,o)=>d.push(7,b,o),
  };
  stream.setBindGroup(0,pass.frameGroup0);record(stream);
  const same=entry&&entry.commands.length===d.length&&d.every((value,i)=>value===entry.commands[i]);
  if(same)this.stats.hits++;
  else{
   this.scratch=entry?.commands||[];entry={commands:d,bundle:null};
   if(!this.entries.has(key)&&this.entries.size>=8)this.entries.delete(this.entries.keys().next().value);
   this.entries.set(key,entry);this.stats.misses++;
   // Changing views use the original draw path. Build a reusable GPU bundle
   // only after observing the exact stream again, avoiding continual rebuilds.
   this.replay(rp,d);return;
  }
  if(!entry.bundle){
   const encoder=GPU.device.createRenderBundleEncoder({label:'Exact sensor draw stream',colorFormats:pass.colorFormats,depthStencilFormat:pass.depthFormat||undefined,sampleCount:1});
   this.replay(encoder,d);entry.bundle=encoder.finish();
  }
  rp.executeBundles([entry.bundle]);
  // executeBundles clears pass bindings; subsequent lists/background draws
  // must see the same frame binding as in the original direct draw path.
  rp.setBindGroup(0,pass.frameGroup0);
 }
 replay(encoder,d){
  for(let i=0;i<d.length;){switch(d[i++]){
    case 0:encoder.setPipeline(d[i++]);break;
    case 1:{const index=d[i++],group=d[i++],n=d[i++];encoder.setBindGroup(index,group,d.slice(i,i+n));i+=n;break;}
    case 2:encoder.setVertexBuffer(d[i++],d[i++]);break;
    case 3:encoder.setIndexBuffer(d[i++],d[i++]);break;
    case 4:encoder.drawIndexed(d[i++],d[i++],d[i++],d[i++],d[i++]);break;
    case 5:encoder.draw(d[i++],d[i++],d[i++],d[i++]);break;
    case 6:encoder.drawIndexedIndirect(d[i++],d[i++]);break;
    case 7:encoder.drawIndirect(d[i++],d[i++]);break;
    default:throw new Error('Invalid sensor draw stream');
  }}
 }
 clear(){this.entries.clear();this.scratch.length=0;}
}
