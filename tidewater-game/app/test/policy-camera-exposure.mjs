import assert from 'node:assert/strict';
import {PolicyCamera} from '../src/landing/PolicyCamera.js';
// Onboard auto-exposure: leaves normal views alone (including the bright white
// pad close up), corrects washed-out and very dark images within bounds.
const camera=()=>Object.assign(Object.create(PolicyCamera.prototype),{ev:0,exposureState:null});
const image=(pixel)=>{const a=new Uint8Array(640*360*4);for(let y=0;y<360;y++)for(let x=0;x<640;x++){const v=pixel(x,y),i=(y*640+x)*4;a[i]=v[0];a[i+1]=v[1];a[i+2]=v[2];}return a;};
const seaWithBoat=image((x,y)=>y<60?[40,70,50]:(x>290&&x<390&&y>140&&y<190)?[150,155,160]:[30,70,120]); // like browser-acquire.png
const padCloseUp=image((x,y)=>(x>40&&x<600)?[218,216,212]:[30,45,70]); // like browser-sensor.png: mostly white pad
const glare=image((x,y)=>y<150?[250,250,248]:[60,90,130]); // a large sun-glare sheet
for(const [name,frame] of [['sea with boat',seaWithBoat],['white pad close up',padCloseUp]]){const c=camera();for(let i=0;i<30;i++)c.meter(frame);assert.equal(c.ev,0,name+' must keep the trained exposure');}
// Closed loop: the scene's light scales with 2^ev through a simple sRGB-like response.
const scale=(frame,ev)=>frame.map((v,i)=>(i&3)===3?255:Math.min(255,Math.round(255*Math.pow(v/255*Math.pow(2,ev),1/1.2))));
let c=camera();for(let i=0;i<40;i++)c.meter(scale(glare,c.ev));
assert(c.ev<0&&c.ev>=-3,'Glare must lower the exposure');assert(c.exposureState.bright_fraction<=.10,'Glare must be brought under the washed-out limit');
{const settled=c.ev,seen=[];for(let i=0;i<30;i++){c.meter(scale(glare,c.ev));seen.push(c.ev);}assert(Math.max(...seen)-Math.min(...seen)<.05,'Settled exposure must not flicker: '+settled+' '+seen.join(','));}
const dark=image(()=>[12,16,22]);c=camera();for(let i=0;i<40;i++)c.meter(scale(dark,c.ev));
assert(c.ev>0&&c.ev<=2,'A very dark image must raise the exposure within bounds');
c=camera();c.ev=-2;for(let i=0;i<60;i++)c.meter(scale(seaWithBoat,c.ev));assert.equal(c.ev,0,'Back in normal light the exposure returns to the trained value');
console.log('Onboard auto-exposure: normal sea and close-up pad untouched, glare and darkness corrected within bounds, recovery to the trained exposure.');
