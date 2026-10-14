// Clean-checkout fixtures from the committed physical assets and the same CPU
// builders used by App. This neither initializes a GPU nor opens a browser.
import fs from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import loadMujoco from '../../app/node_modules/@mujoco/mujoco/mujoco.js';
const base=new URL('../../app/public/landing/physics/',import.meta.url),c=JSON.parse(await fs.readFile(new URL('configuration.json',base),'utf8'));
const mj=await loadMujoco();for(const file of c.files)mj.FS.writeFile('/'+file,await fs.readFile(new URL(file,base)));
const xml=await fs.readFile(new URL('vehicles.xml',base),'utf8');
for(const [name,source] of [['vehicles',xml],['closed-loop',xml.replace('</worldbody>','<geom name="benchmark_ground" type="plane" size="30 30 .1" contype="1" conaffinity="2" friction=".9 .005 .0001"/></worldbody>')]]) {
 mj.FS.writeFile('/fixture.xml',source);const model=mj.MjModel.from_xml_path('/fixture.xml');mj.mj_saveModel(model,'/fixture.mjb',null);
 const bytes=mj.FS.readFile('/fixture.mjb');await fs.writeFile(name==='vehicles'?new URL('vehicles.mjb.gz',import.meta.url):new URL('closed-loop.mjb',import.meta.url),name==='vehicles'?gzipSync(bytes):bytes);model.delete();
}
if(!process.argv.includes('--models-only')) {
 globalThis.location={search:''};
 const {StorageBuffer}=await import('../../app/src/engine/gpu/Texture.js');
 // Decorative fish upload GPU buffers during Village construction. Collision
 // fixtures need only the original CPU builders, never those rendering uploads.
 StorageBuffer.prototype.write=function(){return this;};
 const {Scene}=await import('../../app/src/engine/index.js');
 const {TerrainData}=await import('../../app/src/world/TerrainData.js');
 const {Colliders}=await import('../../app/src/world/Colliders.js');
 const {Village}=await import('../../app/src/world/Village.js');
 const {Vegetation}=await import('../../app/src/world/Vegetation.js');
 const {Rocks}=await import('../../app/src/world/Rocks.js');
 const {Builder}=await import('../../app/src/world/village/GeoBuilder.js');
 const {InstancedProps}=await import('../../app/src/world/Props.js');
 const {DebrisPlacer}=await import('../../app/src/world/debris/DebrisPlacement.js');
 const scene=new Scene(),terrain=new TerrainData(),colliders=new Colliders();
 const village=new Village({scene,terrain,colliders}),vegetation=new Vegetation({scene,terrain,village}),rocks=new Rocks({scene,terrain,village,colliders});
 const B=new Builder();new DebrisPlacer({B,inst:new InstancedProps(B),terrain,village,vegetation,rocks,colliders,seed:5150}).run();
 const meta={origin:terrain.origin,size:terrain.size,res:terrain.res,colliders:{boxes:colliders.boxes.filter(b=>b.solid).map(b=>({center:b.center.toArray(),half:b.half.toArray(),rotY:b.rotY,solid:true,tag:b.tag})),cylinders:colliders.cylinders.map(c=>({...c}))}};
 const runtime=new URL('../../simulation/runtime/',import.meta.url);await fs.mkdir(runtime,{recursive:true});
 await fs.writeFile(new URL('live-map.json',runtime),JSON.stringify(meta));await fs.writeFile(new URL('live-heights.bin',runtime),new Uint8Array(terrain.heights.buffer));
 console.log('Prepared actual default world:',meta.res,'height samples per axis,',meta.colliders.boxes.length,'boxes,',meta.colliders.cylinders.length,'cylinders');
}
console.log('Regenerated MuJoCo 3.14 fixtures');
