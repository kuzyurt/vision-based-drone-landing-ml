import * as E from '../engine/index.js';
import { standard } from '../materials/Materials.js';
import { Texture } from '../engine/gpu/Texture.js';
import { readTexture } from '../engine/gpu/Readback.js';
import { G } from '../core/Globals.js';
import { landingWaveParams } from './PhysicsWaves.js';

export class StreamingLandingBridge {
 constructor(app){
  this.app=app;this.meshes=new Map();this.textures=new Map();
  app.engine.stop();app.freeCam=true;app.fly.update=()=>{};
  app.boat.group.visible=false;app.boatCtl.update=()=>{};app.boatCtl.queueQueries=()=>{};
  app.boatSpray.update=()=>{};app.wake.update=()=>{};app.game.update=()=>{};
  app.boat.update=()=>{};
  app.sceneRenderer.hullMasks=[];app.sceneRenderer.hullMaskScene.children=[];
  app.post.aaMode='smaa';app.post.autoExposure.enabled.value=0;
  app.post.params.grain.value=0;
  app.engine.canvas.width=640;app.engine.canvas.height=360;
  this.output=new Texture({width:640,height:360,format:app.gpu.format,usage:['render','copySrc','sample'],label:'landing camera output'});
  app.post.outputTexture=this.output;
  app.post.outputSize=new E.Vector2(640,360);
 }
 async install(url){
  if(this.installedURL===url)return this.installation;
  for(const mesh of this.meshes.values()){this.app.scene.remove(mesh);mesh.geometry.dispose();}
  this.meshes.clear();
  const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error('CAD manifest HTTP '+response.status);
  const payload=await response.json();
  for(const t of payload.textures){
   const bytes=new Uint8Array(await(await fetch(t.url)).arrayBuffer());
   const tex=new Texture({width:t.width,height:t.height,format:'rgba8unorm-srgb',data:bytes,usage:['sample','copyDst'],mips:true,label:t.name});
   this.textures.set(t.id,tex);
  }
  const materialCache=new Map();
  for(const part of payload.geoms){
   const bytes=await(await fetch(part.url)).arrayBuffer();const n=part.vertex_count;
   const geometry=new E.BufferGeometry();
   geometry.setAttribute('position',new E.Float32BufferAttribute(new Float32Array(bytes,0,n*3),3));
   geometry.setAttribute('normal',new E.Float32BufferAttribute(new Float32Array(bytes,n*12,n*3),3));
   geometry.setAttribute('uv',new E.Float32BufferAttribute(new Float32Array(bytes,n*24,n*2),2));
   geometry.setIndex(new E.Uint32BufferAttribute(new Uint32Array(bytes,n*32,part.index_count),1));
   const key=JSON.stringify(part.material);let material=materialCache.get(key);
   if(!material){
    const m=part.material;
    material=standard({name:'landing '+m.name,color:new E.Color().setRGB(...m.rgba.slice(0,3)),opacity:m.rgba[3],roughness:m.roughness,metalness:0,side:'double'});
    if(m.texture>=0)material.map=this.textures.get(m.texture);
    material.underwaterLighting='lite';materialCache.set(key,material);
   }
   const mesh=new E.Mesh(geometry,material);mesh.matrixAutoUpdate=false;mesh.castShadow=true;mesh.receiveShadow=true;mesh.frustumCulled=true;
   this.meshes.set(part.id,mesh);this.app.scene.add(mesh);
  }
  // Use the original boat's physical hull volume to keep sea out of the hull.
  if(payload.hull){
   const h=payload.hull;const bytes=await(await fetch(h.url)).arrayBuffer();const geometry=new E.BufferGeometry();geometry.setAttribute('position',new E.Float32BufferAttribute(new Float32Array(bytes),3));geometry.computeVertexNormals();
   this.hullObject=new E.Group();this.hullObject.matrixAutoUpdate=false;this.app.scene.add(this.hullObject);
   this.app.sceneRenderer.addHullMask(geometry,this.hullObject);
  }
  await this.app.precompile();await this.app.gpu.pipelinesReady();
  this.installedURL=url;this.installation={geoms:this.meshes.size,textures:this.textures.size,source:payload.source};return this.installation;
 }
 transform(object,t){object.matrix.set(...t);object.matrixWorldNeedsUpdate=true;}
 async render(packet){
  const app=this.app;
  for(const [id,t] of packet.geoms)this.transform(this.meshes.get(id),t);
  if(this.hullObject)this.transform(this.hullObject,packet.hull_pose);
  landingWaveParams.fields.enabled.value=1;packet.waves.forEach((c,i)=>landingWaveParams.fields['c'+i].value.fromArray([c[0],c[1],c[2]*Math.min(1,0.025/packet.waves.reduce((sum,w)=>sum+Math.abs(w[2]),0)),c[3]]));
  app.settings.timeOfDay=packet.time_of_day??16.2;
  G.windSpeed.value=packet.wind_speed??0;
  const result={};
  for(const view of packet.views){
   const c=app.camera;c.matrixAutoUpdate=false;c.matrix.set(...view.matrix);c.matrixWorldNeedsUpdate=true;
   c.position.set(view.matrix[3],view.matrix[7],view.matrix[11]);
   c.fov=view.fovy;c.aspect=(view.width??640)/(view.height??360);c.near=.001;c.updateProjectionMatrix();
   if(view.name==='onboard'){app.post._hasPrev=false;app.post.motionBlur._hasPrev=false;}
   G.time.value=packet.time_s;
   app.frame(0);await app.gpu.pipelinesReady();await app.gpu.queue.onSubmittedWorkDone();
   const pixels=await readTexture(this.output);
   await fetch('http://127.0.0.1:5191/_pixels/'+view.name,{method:'POST',body:pixels.data});
   // Verification data, never supplied to the policy.
   result[view.name]={width:pixels.width,height:pixels.height,fovy:c.fov,projection:c.projectionMatrix.elements,view:c.matrixWorldInverse.elements};
  }
  return result;
 }
 async exportTerrain(){
  const t=this.app.terrainData;
  await fetch('http://127.0.0.1:5191/_terrain',{method:'POST',body:t.heights.buffer});
  const p=this.app.colliders;
  return {res:t.res,texel:t.texel,origin:t.origin,size:t.size,
   colliders:{boxes:p.boxes.filter(b=>b.solid).map(b=>({center:b.center.toArray(),half:b.half.toArray(),rotY:b.rotY,tag:b.tag})),cylinders:p.cylinders},
   format:'float32 little endian; rows increase Tidewater z'};
 }
}
