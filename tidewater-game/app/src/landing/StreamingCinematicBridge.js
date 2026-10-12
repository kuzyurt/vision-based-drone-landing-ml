import { StreamingLandingBridge as LandingBridge } from './StreamingLandingBridge.js';
import { Texture } from '../engine/gpu/Texture.js';
import { Vector2 } from '../engine/index.js';

export class StreamingCinematicBridge extends LandingBridge {
 constructor(app){
  super(app);this.size='640x360';
  app.boat.group.traverse(object=>{object.visible=false;});
  // Exact values from Tidewater's live AppUI Breezy preset.
  app.fft.local.windSpeed=7;app.fft.local.fetch=120;
  app.fft.swell.scale=.48;app.fft.choppiness.value=.9;
  app.fft.foamBias.value=.58;app.fft.foamDecay.value=.425;
  app.fft.updateSpectrumUniforms();
  app.shore.amplitude.value=.025;app.shore.period.value=9;
  app.clouds.coverage.value=.62;
  app.settings.timeOfDay=7+7/60;app.settings.timeSpeed=0;
  app.setRenderScale(1);app.shadows.enabled=true;
  app.waterMaterial.params.ssr.value=1;
  this.quality={renderScale:1,cloudCoverage:.62,timeOfDay:7+7/60,seaState:'Breezy',
   seaPreset:{wind:7,fetch:120,chop:.9,swell:.48,surf:.34,period:9,whitecaps:.5},
   shadows:true,waterReflections:true,spectatorAA:'taa16',native4K:true};
 }
 async render(packet){
  const first=packet.views[0],width=first.width??640,height=first.height??360;
  if(packet.views.some(v=>(v.width??640)!==width||(v.height??360)!==height))throw Error('Use separate passes for different camera resolutions');
  const key=width+'x'+height,app=this.app;
  if(key!==this.size){
   this.output.resize(width,height);
   app.engine.canvas.width=width;app.engine.canvas.height=height;
   app.post.outputTexture=this.output;app.post.outputSize={width,height};
   app.clouds.outputSize=new Vector2(width,height);app.clouds.resetHistory();
   this.size=key;
  }
  app.post.aaMode=first.name==='onboard'?'smaa':'taa';
  app.post.taau.jitterPhaseOverride=16;
  const result=await super.render(packet);
  for(const v of Object.values(result))v.quality=this.quality;
  return result;
 }
}
