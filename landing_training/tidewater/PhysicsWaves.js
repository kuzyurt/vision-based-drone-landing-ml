import { UniformBlock, ShaderModule } from '../engine/webgpu.js';
import { Vector4 } from '../engine/math/index.js';
export const landingWaveParams=new UniformBlock('LandingWaveParams',{
 c0:['vec4f',new Vector4()],c1:['vec4f',new Vector4()],c2:['vec4f',new Vector4()],c3:['vec4f',new Vector4()],
},{label:'landing waves'});
export const landingWaveModule=new ShaderModule({name:'landingWaves',uniforms:landingWaveParams,uniformName:'landingWaves',code:`
fn landingWaveHeight(xz:vec2f)->f32 {
 let c=array<vec4f,4>(landingWaves.c0,landingWaves.c1,landingWaves.c2,landingWaves.c3);
 var h=0.0;for(var i=0u;i<4u;i++){h+=c[i].z*cos(dot(c[i].xy,xz)+c[i].w);}return h;
}
fn landingWaveSlope(xz:vec2f)->vec2f {
 let c=array<vec4f,4>(landingWaves.c0,landingWaves.c1,landingWaves.c2,landingWaves.c3);
 var slope=vec2f(0.0);for(var i=0u;i<4u;i++){slope-=c[i].z*c[i].xy*sin(dot(c[i].xy,xz)+c[i].w);}return slope;
}
`});
