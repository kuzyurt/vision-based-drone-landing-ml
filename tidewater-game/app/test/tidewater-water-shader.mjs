import './headless.mjs';
import {GPU} from '../src/engine/gpu/GPU.js';
import '../src/engine/render/Frame.js';
import {Texture} from '../src/engine/gpu/Texture.js';
import {composeShader} from '../src/engine/gpu/Shader.js';
import {OceanFFT} from '../src/ocean/OceanFFT.js';
import {CDLOD} from '../src/core/CDLOD.js';
import {WaterSurface} from '../src/ocean/WaterSurface.js';
await GPU.init({headless:true});
GPU.device.pushErrorScope('validation');
const fft=new OceanFFT(GPU);
const cdlod=new CDLOD({gridSize:32,leafSize:8,levels:12,minY:-25,maxY:25});
const foamTexture=new Texture({width:4,height:4,format:'rgba8unorm',data:new Uint8Array(64),usage:['sample','copyDst']});
const surface=new WaterSurface({fft,cdlod,foamTexture});
const {code}=composeShader({modules:[surface.module],code:`
@vertex fn testVertex(@builtin(vertex_index) i:u32)->@builtin(position) vec4f {
 let v=waterSurfaceVertex(vec4f(0.0,0.0,8.0,0.0),vec2f(f32(i),0.0));return vec4f(v.position,1.0);
}
@fragment fn testFragment()->@location(0) vec4f {
 let v=waterSurfaceFragment(vec2f(0.0),0.01,10.0,0.0,vec3f(0.0,1.0,0.0),0.0,0.0,vec4f(0.0),vec2f(0.0),vec3f(0.0));return vec4f(v.normal,1.0);
}`});
const shader=GPU.device.createShaderModule({code,label:'Shared physical waves validation'});
const info=await shader.getCompilationInfo();
const errors=info.messages.filter(m=>m.type==='error');
if(errors.length)throw new Error(errors.map(m=>`${m.lineNum}: ${m.message}`).join('\n'));
await GPU.pipelinesReady();
const validation=await GPU.device.popErrorScope();
if(validation)throw new Error(validation.message);
console.log(`Shared-wave vertex and fragment WGSL validated by Dawn (${process.env.TIDEWATER_GPU_BACKEND || 'native GPU'} backend); no browser launched`);
process.exit(0);
