// Terrain and obstacle compilation runs once in the physics worker. The cache
// key includes the actual map, collision shapes, CAD source and model version.
export function heightAt(map,x,y) {
 const {origin,size,res}=map.meta,scale=res/size;
 const col=Math.max(0,Math.min(res-1,Math.trunc((x-origin)*scale)));
 const row=Math.max(0,Math.min(res-1,Math.trunc((-y-origin)*scale)));
 return map.heights[row*res+col];
}
export function clearObstacle(meta,x,y,radius=9) {
 for(const box of meta.colliders.boxes) {
  const c=box.center,h=box.half;if(c[1]-h[1]>1.8 || c[1]+h[1]<-2)continue;
  const a=box.rotY||0,dx=x-c[0],dy=y+c[2];
  if(Math.abs(dx*Math.cos(a)-dy*Math.sin(a))<h[0]+radius && Math.abs(dx*Math.sin(a)+dy*Math.cos(a))<h[2]+radius)return false;
 }
 for(const c of meta.colliders.cylinders)if(c.yMin<=1.8 && c.yMax>=-2 && Math.hypot(x-c.x,y+c.z)<radius+c.radius)return false;
 return true;
}
export function chooseRoute(map) {
 const candidates=[];
 for(const [cx,cz,rx,rz] of [[40,170,100,65],[20,190,110,65],[40,190,100,65],[20,210,110,75],[0,230,120,75],[0,260,120,75]]) {
  const points=[];let valid=true;
  for(let i=0;i<721;i++) {
   const a=Math.PI+2*Math.PI*i/721,x=cx+rx*Math.cos(a),y=-(cz+rz*Math.sin(a));points.push([x,y]);
   // A 14 m sampled clearance ring also covers the original 8 m hull envelope.
   for(let j=0;j<16;j++) {const angle=j*Math.PI/8;if(heightAt(map,x+14*Math.cos(angle),y+14*Math.sin(angle))>-2.2)valid=false;}
   if(heightAt(map,x,y)>-2.2 || !clearObstacle(map.meta,x,y))valid=false;
  }
  if(!valid)continue;points.push([...points[0]]);const arc=[0];
  for(let i=1;i<points.length;i++)arc.push(arc.at(-1)+Math.hypot(points[i][0]-points[i-1][0],points[i][1]-points[i-1][1]));
  const length=arc.at(-1);if(length<480)continue;
  candidates.push({points,arc,length,score:Math.abs(cz-150)+Math.abs(cx-135)*.25-length*.012});
 }
 if(!candidates.length)throw new Error('No closed water route clears this terrain and pier');
 return candidates.sort((a,b)=>a.score-b.score)[0];
}
export function coastPoints(map) {
 // Actual terrain shoreline samples, ordered by heading around the island.
 // Used only by the minimap; route safety uses heightfield and colliders above.
 const points=[],{res,origin,size}=map.meta,stride=4,scale=size/res;
 for(let row=stride;row<res-stride;row+=stride)for(let col=stride;col<res-stride;col+=stride) {
  if(map.heights[row*res+col]<=0)continue;
  if(map.heights[(row-stride)*res+col]<=0 || map.heights[(row+stride)*res+col]<=0 || map.heights[row*res+col-stride]<=0 || map.heights[row*res+col+stride]<=0)
   points.push([origin+(col+.5)*scale,origin+(row+.5)*scale]);
 }
 if(!points.length)return [];
 const cx=points.reduce((s,p)=>s+p[0],0)/points.length,cy=points.reduce((s,p)=>s+p[1],0)/points.length;
 return points.sort((a,b)=>Math.atan2(a[1]-cy,a[0]-cx)-Math.atan2(b[1]-cy,b[0]-cx));
}
async function cached(key,value) {
 if(typeof indexedDB==='undefined')return null;
 const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('tidewater-physics',1);r.onupgradeneeded=()=>r.result.createObjectStore('models');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
 try {return await new Promise((resolve,reject)=>{const transaction=db.transaction('models',value?'readwrite':'readonly'),store=transaction.objectStore('models');
  const r=value?store.put(value,key):store.get(key);r.onsuccess=()=>{if(!value)resolve(r.result||null);};r.onerror=()=>reject(r.error);transaction.oncomplete=()=>{if(value)resolve(value);};transaction.onabort=()=>reject(transaction.error);
 });}finally{db.close();}
}
export async function compileWorld(mj,c,map,base,progress,fetchAsset=async url=>new Uint8Array(await (await fetch(url)).arrayBuffer())) {
 const xmlBytes=await fetchAsset(base+'vehicles.xml'),xml=new TextDecoder().decode(xmlBytes);
 const hash=await crypto.subtle.digest('SHA-256',new Uint8Array([...new Uint8Array(await crypto.subtle.digest('SHA-256',map.heights)),...new TextEncoder().encode(JSON.stringify(map.meta)+xml+c.version+c.mujoco_version)]));
 const key=Array.from(new Uint8Array(hash),v=>v.toString(16).padStart(2,'0')).join('');
 let binary=null;try{binary=await cached(key);}catch{/* Storage limits do not stop flight. */}
 if(binary) {
  progress('Loading cached Tidewater collision world');mj.FS.writeFile('/world.mjb',binary);
  const vfs=new mj.MjVFS();try{return mj.MjModel.from_binary_path('/world.mjb',vfs);}finally{vfs.delete();mj.FS.unlink('/world.mjb');}
 }
 progress('Loading original collision meshes');let done=0,next=1;
 await Promise.all(Array.from({length:8},async()=>{while(next<c.files.length){const file=c.files[next++];mj.FS.writeFile('/'+file,await fetchAsset(base+file));progress(`Loading original collision meshes · ${++done}/${c.files.length-1}`);}}));
 const assets=[],geoms=[],temporary=[],{res,size}=map.meta,n=Math.ceil(res/2),resolution=size/res*2,start=-(n-1)*resolution*.5-.5;
 for(let row=0;row<n-1;row+=64)for(let col=0;col<n-1;col+=64) {
  const nr=Math.min(65,n-row),nc=Math.min(65,n-col),values=new Float32Array(nr*nc);let low=Infinity,high=-Infinity;
  for(let y=0;y<nr;y++)for(let x=0;x<nc;x++){const h=map.heights[(res-1-(row+y)*2)*res+(col+x)*2];values[y*nc+x]=h;low=Math.min(low,h);high=Math.max(high,h);}
  const span=Math.max(high-low,.01);for(let i=0;i<values.length;i++)values[i]=(values[i]-low)/span;
  const name=`tidewater_terrain_${row}_${col}`,file='/'+name+'.bin',bytes=new Uint8Array(8+values.byteLength),view=new DataView(bytes.buffer);view.setInt32(0,nr,true);view.setInt32(4,nc,true);bytes.set(new Uint8Array(values.buffer),8);mj.FS.writeFile(file,bytes);temporary.push(file);
  const hx=(nc-1)*resolution*.5,hy=(nr-1)*resolution*.5;
  assets.push(`<hfield name="${name}" file="${file}" size="${hx} ${hy} ${span} .1"/>`);
  geoms.push(`<geom name="${name}_collision" type="hfield" hfield="${name}" pos="${start+col*resolution+hx} ${start+row*resolution+hy} ${low}" contype="12" conaffinity="3" group="5"/>`);
 }
 map.meta.colliders.boxes.forEach((b,i)=>{if(b.solid===false)return;const a=(b.rotY||0)/2;geoms.push(`<geom name="tidewater_box_${i}" type="box" pos="${b.center[0]} ${-b.center[2]} ${b.center[1]}" size="${b.half[0]} ${b.half[2]} ${b.half[1]}" quat="${Math.cos(a)} 0 0 ${Math.sin(a)}" contype="12" conaffinity="3" group="5"/>`);});
 map.meta.colliders.cylinders.forEach((b,i)=>geoms.push(`<geom name="tidewater_cylinder_${i}" type="cylinder" pos="${b.x} ${-b.z} ${(b.yMin+b.yMax)/2}" size="${b.radius} ${(b.yMax-b.yMin)/2}" contype="12" conaffinity="3" group="5"/>`));
 progress('Compiling original CAD and Tidewater terrain · first load');
 mj.FS.writeFile('/world.xml',xml.replace('</asset>',assets.join('')+'</asset>').replace('</worldbody>',geoms.join('')+'</worldbody>'));
 let model;try{model=mj.MjModel.from_xml_path('/world.xml');}finally{for(const file of [...temporary,'/world.xml',...c.files.slice(1).map(f=>'/'+f)])mj.FS.unlink(file);}
 try{mj.mj_saveModel(model,'/world.mjb',null);const bytes=mj.FS.readFile('/world.mjb');await cached(key,bytes);mj.FS.unlink('/world.mjb');}catch{/* Flight works even when cache quota is exhausted. */}
 return model;
}
