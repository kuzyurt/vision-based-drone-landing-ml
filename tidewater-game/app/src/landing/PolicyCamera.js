import {PerspectiveCamera,Matrix4} from '../engine/index.js';
import {GPU} from '../engine/gpu/GPU.js';
import {RenderTarget} from '../engine/gpu/Texture.js';
import {createViewUniforms,setFrameCamera,G} from '../engine/render/Frame.js';
import {SceneRenderer,SCENE_FORMATS,DEPTH_FORMAT} from '../engine/render/SceneRenderer.js';
import {MeshRenderer} from '../engine/render/MeshRenderer.js';
import {FullscreenPass} from '../engine/render/FullscreenPass.js';
import {RefractionPass} from '../ocean/RefractionPass.js';
import {WaterMaterial} from '../ocean/WaterMaterial.js';
import {ACES} from '../post/PostFX.js';
import {landingWaveParams} from './PhysicsWaves.js';

// Onboard auto-exposure, like a real camera with highlight protection. It
// meters only this camera's own pixels (no simulator state) and acts only in
// clearly bad light, so normal views - including the bright white pad seen
// close up during landing - keep exactly the exposure the policy is used to:
//  - washed out: more than 10% of the image is nearly white (luma > 0.93)
//    -> step the exposure down;
//  - too dark: mean luma under 0.15 and almost no bright detail (99th
//    percentile under 0.35) -> step up;
//  - otherwise drift back to the trained exposure, but only as far as the
//    image stays clear of both limits (no flicker between two settings).
// Steps are at most 0.35 EV per frame (about 0.3 s to settle) and the total
// correction is limited to -3 EV ... +2 EV.
const AE={brightLuma:.93,brightFraction:.10,brightRelease:.90,darkMean:.15,darkRelease:.17,darkTail:.35,minEV:-3,maxEV:2,maxStep:.35,gamma:2.2};

// A fixed camera sensor, independent of the operator viewport and HUD. No
// resizing/cropping or privileged marker projection is supplied to inference.
export class PolicyCamera {
 constructor(bridge) {
  this.bridge=bridge;const a=bridge.app;this.app=a;
  this.camera=new PerspectiveCamera(36.1,640/360,.001,60000);this.block=createViewUniforms('ML onboard camera');
  this.ev=0;this.exposureState=null;const follow=this.block.onBeforePack;this.block.onBeforePack=()=>{follow();this.block.fields.cameraWaterHeight.value=G.seaLevel.value;this.block.fields.cameraUnderwater.value=0;this.block.fields.exposure.value=G.exposure.value*2**this.ev;};
  this.meshRenderer=new MeshRenderer();this.meshRenderer.syncPipelines=false;this.meshRenderer.geometries=a.engine.meshRenderer.geometries;
  // Capture updates the complete scene once after applying its timestamped
  // poses. All sensor passes use those same matrices during this synchronous
  // submission; updating the full tree again in every pass is redundant.
  this.meshRenderer.updateSceneMatrices=false;this.meshRenderer.useRenderBundles=true;
  this.renderer=new SceneRenderer(this.meshRenderer,a.scene,this.camera,{frameBlock:this.block});this.renderer.setSize(640,360);
  this.refraction=new RefractionPass({meshRenderer:this.meshRenderer,scene:a.scene,camera:this.camera,sceneRenderer:this.renderer,frameBlock:this.block});
  this.renderer.onBeforeWater=()=>this.refraction.render(G.seaLevel.value);
  for(const h of a.sceneRenderer.hullMasks)this.renderer.addHullMask(h.mesh.geometry,h.object);
  this.water=new WaterMaterial({surface:a.surface,sky:a.sky,sceneCopy:this.renderer.opaqueCopy,sceneDepthHalf:this.renderer.opaqueDepthHalf.texture,refraction:this.refraction,hullMask:this.renderer.hullMaskRT.texture,hullMaskActive:this.renderer.hullMaskActive});this.water.clouds=a.clouds;
  // Sky uses the same world cloud panorama. Operator view cloud reprojection
  // history belongs to its camera and must never be reused by this sensor.
  this.background=new FullscreenPass({label:'ML camera sky',modules:[a.sky.module],colorFormats:SCENE_FORMATS,depthFormat:DEPTH_FORMAT,depthCompare:'equal',depthWrite:false,depth:0,
   code:'struct SensorSky { @location(0) color:vec4f, @location(1) velocity:vec4f, @location(2) mask:vec4f }; @fragment fn fs(in:FSIn)->SensorSky { var o:SensorSky; o.color=vec4f(skyRadianceWithClouds(viewRay(in.pos.xy*frame.invResolution),true),1.0); o.velocity=vec4f(0.0); o.mask=vec4f(0.0); return o; }'});
  this.renderer.background={draw:(rp,block)=>this.background.draw(rp,block)};
  this.output=new RenderTarget(640,360,{colors:['rgba8unorm'],label:'ML camera RGB'});
  this.tone=new FullscreenPass({label:'ML camera tone mapping',colorFormats:['rgba8unorm'],bindings:{sensorHDR:{texture:()=>this.renderer.sceneRT.texture}},code:ACES+'\nfn fragment(in:FSIn)->vec4f { let hdr=textureLoad(sensorHDR,vec2i(in.pos.xy),0).rgb; return vec4f(linearToSrgb(acesFilmicToneMapping(hdr,frame.exposure)),1.0); }'});
  if(GPU.hasTimestamp){this.timestampQuery=GPU.device.createQuerySet({type:'timestamp',count:2});this.timestampResolve=GPU.device.createBuffer({label:'ML camera timestamps',size:16,usage:GPUBufferUsage.QUERY_RESOLVE|GPUBufferUsage.COPY_SRC});}
  this.readback=GPU.device.createBuffer({label:'ML camera bounded readback',size:640*360*4+(this.timestampQuery?16:0),usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
 }
 async capture(state,{onSubmitted}={}) {
  if(this.closed)throw new Error('ML camera is closed');if(this.busy)throw new Error('ML capture already in progress');this.busy=true;
  const started=performance.now();let submitted,restored,mapped;
  const a=this.app,b=this.bridge,saved=[],swapped=[],hidden=[],shown=[],oldWater=a.ocean.material,oldWaves=[0,1,2,3].map(i=>landingWaveParams.fields['c'+i].value.clone());
  try {
   GPU.submit();GPU.beginFrame(); // Own draw buffer and camera history.
   for(const [name,values] of state.bodies){const group=b.groups.get(name);if(!group)continue;saved.push([group,group.position.clone(),group.quaternion.clone(),group.scale.clone()]);new Matrix4().set(...values).decompose(group.position,group.quaternion,group.scale);}
   if(b.hull&&state.hull_pose){saved.push([b.hull,b.hull.position.clone(),b.hull.quaternion.clone(),b.hull.scale.clone()]);new Matrix4().set(...state.hull_pose).decompose(b.hull.position,b.hull.quaternion,b.hull.scale);}
   // The sensor sees exactly the meshes the policy was trained on, never the operator-view detail meshes.
   for(const [trained,detail] of b.detailPairs||[])if(detail.visible){swapped.push([trained,detail]);detail.visible=false;trained.visible=true;}
   // Parts of the operator view only (the battery cradle) are not part of the trained scene either.
   for(const extra of b.detailExtras||[])if(extra.visible){hidden.push(extra);extra.visible=false;}
   // Parts the operator view leaves out are still in the trained scene: show them for the capture.
   for(const mesh of b.operatorHidden||[])if(mesh.operatorPlaced&&!mesh.visible){shown.push(mesh);mesh.visible=true;}
   const view=state.views.drone;if(Math.abs(view.fovy-36.1)>1e-5)throw new Error('Onboard camera calibration does not match trained policy');
   new Matrix4().set(...view.matrix).decompose(this.camera.position,this.camera.quaternion,this.camera.scale);this.camera.updateProjectionMatrix();setFrameCamera(this.camera,640,360,{block:this.block});
   for(const key of Object.keys(this.water.uniforms))if(key!=='hullActive'&&oldWater.uniforms[key])this.water.uniforms[key].value=oldWater.uniforms[key].value;
   state.waves?.forEach((c,i)=>landingWaveParams.fields['c'+i].value.fromArray(c));
   a.ocean.material=this.water;a.scene.updateMatrixWorld(true);
   if(this.timestampQuery)GPU.getEncoder().beginComputePass({label:'ML camera GPU begin',timestampWrites:{querySet:this.timestampQuery,beginningOfPassWriteIndex:0}}).end();
   this.renderer.render();this.tone.render({colorViews:[this.output.texture],clear:[0,0,0,1],frameBlock:this.block});
   if(this.timestampQuery){const encoder=GPU.getEncoder();encoder.beginComputePass({label:'ML camera GPU end',timestampWrites:{querySet:this.timestampQuery,endOfPassWriteIndex:1}}).end();encoder.resolveQuerySet(this.timestampQuery,0,2,this.timestampResolve,0);encoder.copyBufferToBuffer(this.timestampResolve,0,this.readback,640*360*4,16);}
   GPU.getEncoder().copyTextureToBuffer({texture:this.output.texture.getGPU()},{buffer:this.readback,bytesPerRow:640*4,rowsPerImage:360},{width:640,height:360});GPU.submit();submitted=performance.now();
   onSubmitted?.(this.output.texture.getGPU());
  }catch(error){this.busy=false;throw error;}finally{
   for(const [trained,detail] of swapped){trained.visible=false;detail.visible=true;}
   for(const extra of hidden)extra.visible=true;
   for(const mesh of shown)mesh.visible=false;
   a.ocean.material=oldWater;oldWaves.forEach((c,i)=>landingWaveParams.fields['c'+i].value.copy(c));for(const [g,p,q,s] of saved){g.position.copy(p);g.quaternion.copy(q);g.scale.copy(s);}a.scene.updateMatrixWorld(true);restored=performance.now();
  }
  try {await this.readback.mapAsync(GPUMapMode.READ);mapped=performance.now();const buffer=this.readback.getMappedRange(),rgba=new Uint8Array(buffer,0,640*360*4),metered=this.meter(rgba),rgb=new Uint8Array(640*360*3);for(let i=0,j=0;i<rgba.length;i+=4){rgb[j++]=rgba[i];rgb[j++]=rgba[i+1];rgb[j++]=rgba[i+2];}this.timings={camera_encode_ms:submitted-started,camera_restore_ms:restored-submitted,camera_readback_wait_ms:mapped-restored,camera_rgb_ms:performance.now()-mapped};if(this.timestampQuery){const ticks=new BigUint64Array(buffer,640*360*4,2);this.timings.camera_gpu_ms=Number(ticks[1]-ticks[0])/1e6;}if(!this.prepared){this.readback.unmap();this.busy=false;await GPU.pipelinesReady();this.prepared=true;return await this.capture(state);}return rgb;}
  finally{if(this.readback.mapState==='mapped')this.readback.unmap();this.busy=false;}
 }
 // Meter the delivered frame (every 4th pixel) and set the exposure of the
 // next one. See AE above.
 meter(rgba){
  const histogram=new Uint32Array(256);let sum=0,n=0,bright=0;
  for(let y=2;y<360;y+=4)for(let x=2,i=(y*640+2)*4;x<640;x+=4,i+=16){const l=(.2126*rgba[i]+.7152*rgba[i+1]+.0722*rgba[i+2])/255;sum+=l;n++;if(l>AE.brightLuma)bright++;histogram[Math.min(255,Math.round(l*255))]++;}
  const percentile=q=>{for(let c=0,k=255;k>=0;k--){c+=histogram[k];if(c>=n*(1-q))return k/255;}return 0;};
  const mean=sum/n,brightFraction=bright/n,p90=percentile(.9),p99=percentile(.99);let step=0,reason='normal';
  if(brightFraction>AE.brightFraction){step=-Math.min(AE.maxStep,.5*Math.log2(brightFraction/AE.brightFraction)+.15);reason='washed_out';}
  else if(mean<AE.darkMean&&p99<AE.darkTail){step=Math.min(AE.maxStep,Math.log2(AE.darkMean/Math.max(mean,.01))+.05);reason='too_dark';}
  else if(this.ev<0){
   // Brighten back only while the brightest 10% stays under the release level.
   const room=AE.gamma*Math.log2(AE.brightRelease/Math.max(p90,1e-3));
   if(room>.02){step=Math.min(AE.maxStep*.5,-this.ev,room);reason='recovering';}
  }else if(this.ev>0){
   const room=AE.gamma*Math.log2(AE.darkRelease/Math.max(mean,1e-3));
   if(room<-.02){step=Math.max(-AE.maxStep*.5,-this.ev,room);reason='recovering';}
  }
  this.ev=Math.max(AE.minEV,Math.min(AE.maxEV,this.ev+step));
  this.exposureState={ev:this.ev,mean_luma:mean,bright_fraction:brightFraction,p90_luma:p90,p99_luma:p99,reason};
  return mean;
 }
 destroy(){this.closed=true;this.readback.destroy();this.timestampQuery?.destroy();this.timestampResolve?.destroy();for(const rt of [this.renderer.sceneRT,this.renderer.opaqueCopy,this.renderer.opaqueDepthHalf,this.renderer.hullMaskRT,this.refraction.target,this.output]){for(const t of rt.textures)t.destroy();rt.depthTexture?.destroy();}this.block.buffer?.destroy();this.refraction.block.buffer?.destroy();this.water.uniformBlock.buffer?.destroy();this.renderer.hullMaskMaterial.uniformBlock.buffer?.destroy();this.meshRenderer.drawBuffer?.destroy();this.meshRenderer.pipelines.clear();this.meshRenderer.bundleCache?.clear();}
}
