// Translation of AERODOCK_MuJoCo/usv/drainage.py: horizontal retained water,
// four pickups, dual pumps, hose losses and physical mass/centre updates.
import {clamp,interp} from './BrowserForces.js';
const transform=(R,p,o)=>p.map((_,i)=>o[i]+R[i*3]*p[0]+R[i*3+1]*p[1]+R[i*3+2]*p[2]);
export class BrowserDrainage {
 constructor(forces) {
  this.f=forces;const {mj,m,b}=forces;this.body=mj.mj_name2id(m,mj.mjtObj.mjOBJ_BODY.value,'cabin_water');
  if(this.body<0)throw new Error('Original cabin_water body is missing');
  this.floor=[];for(let y=0;y<10;y++)for(let x=0;x<10;x++){const xx=.827+x*(1.493-.827)/9,yy=-.333+y*.666/9;this.floor.push([xx-1.2,yy,.132+.004*(1-Math.max(Math.abs((xx-1.16)/.37),Math.abs(yy/.37)))]);}
  this.area=.74*.74/100;this.pickups=[[-.405,-.363,.135],[.325,-.363,.135],[-.405,.363,.135],[.325,.363,.135]];
  this.loops=[[-.67,-.51,.705],[-.67,.51,.705]];this.rims=[[-.43,-.39,.62],[.35,-.39,.62],[-.43,.39,.62],[.35,.39,.62]];
  this.litres=0;this.totalPumped=0;this.totalIngress=0;this.on=[false,false];this.failures=[false,false];this.rain=0;this.accumulator=0;this.selected=null;this.flow=[0,0];this.head=[0,0];this.wet=[false,false,false,false];this.alarm=false;
  this.lastMass=m.body_mass[this.body];this.lastCom=Array.from(m.body_pos.subarray(this.body*3,this.body*3+3));
  this.dryMass=b.mass-this.lastMass;
 }
 geometry() {
  const {d,b}=this.f,R=Array.from(d.xmat.subarray(b.body*9,b.body*9+9)),o=Array.from(d.xpos.subarray(b.body*3,b.body*3+3));
  const points=this.floor.map(p=>transform(R,p,o)),volume=this.litres/1000,vertical=Math.max(.1,R[8]);
  let lo=Math.min(...points.map(p=>p[2]))-.001,hi=Math.max(...points.map(p=>p[2]))+volume/(100*this.area)*vertical+.001;
  if(volume<=1e-9)return {level:lo,depth:Array(100).fill(0),com:[0,1,2].map(i=>this.floor.reduce((s,p)=>s+p[i],0)/100),R,o,points};
  for(let i=0;i<22;i++){const mid=(lo+hi)/2,fill=points.reduce((s,p)=>s+Math.max(0,(mid-p[2])/vertical),0);if(fill*this.area<volume)lo=mid;else hi=mid;}
  const level=(lo+hi)/2,depth=points.map(p=>Math.max(0,(level-p[2])/vertical)),sum=Math.max(depth.reduce((a,b)=>a+b,0),1e-12);
  const com=[0,1,2].map(j=>this.floor.reduce((s,p,i)=>s+(p[j]+(j===2?depth[i]/2:0))*depth[i],0)/sum);
  return {level,depth,com,R,o,points};
 }
 pumpFlow(head,index) {
  const length=index===0?6:6.3,diameter=.019,area=Math.PI*diameter**2/4;let q=.0002,total=0;
  for(let i=0;i<10;i++){const velocity=q/area,loss=(.03*length/diameter+24)*velocity**2/(2*this.f.b.gravity);total=Math.max(0,head)+loss;q=(q+interp(total,[0,1,2,7],[.23,.215,.19,0])/1000)/2;}
  return [q*1000,total];
 }
 step(dt) {
  this.accumulator+=dt;if(this.accumulator<.05)return;dt=this.accumulator;this.accumulator=0;
  const {f}=this,{d,b}=f;let g=this.geometry();const {R,o}=g,opened=clamp(Math.min(d.qpos[b.qadr.aft_lid_slide],d.qpos[b.qadr.fore_lid_slide])/.46,0,1);
  const velocity=f.velocity(b.body,Array.from(d.xipos.subarray(b.body*3,b.body*3+3))),speed=Math.hypot(velocity[3],velocity[4]);
  const rims=this.rims.map(p=>transform(R,p,o));
  let incoming=this.rain/1000/3600*.74*.74*1000*opened+.003*speed**2*opened;
  incoming+=rims.reduce((s,p)=>s+.6*(2/3)*Math.sqrt(2*b.gravity)*.78*Math.max(0,f.wave(p[0],p[1],0)[0]-p[2])**1.5*1000,0)*opened;
  this.litres+=incoming*dt;this.totalIngress+=incoming*dt;g=this.geometry();
  const pickupDepth=this.pickups.map(p=>g.level-transform(R,p,o)[2]),maximum=Math.max(...g.depth);this.wet=pickupDepth.map(v=>v>.001);this.alarm=maximum>.04;
  const deepest=pickupDepth.indexOf(Math.max(...pickupDepth));
  if(this.selected===null || !this.wet[this.selected])this.selected=this.wet.some(Boolean)?deepest:null;
  else if(pickupDepth[deepest]-pickupDepth[this.selected]>.006)this.selected=deepest;
  if(maximum>.009)this.on[0]=true;else if(maximum<.004)this.on[0]=false;
  if(maximum>.025 || this.failures[0] && maximum>.006)this.on[1]=true;else if(maximum<.006)this.on[1]=false;
  this.flow=[0,0];this.head=[0,0];
  for(let i=0;i<2;i++)if(this.on[i] && !this.failures[i] && this.selected!==null)[this.flow[i],this.head[i]]=this.pumpFlow(transform(R,this.loops[i],o)[2]-g.level,i);
  const removed=Math.min(this.litres,(this.flow[0]+this.flow[1])*dt);this.litres=Math.max(0,this.litres-removed);this.totalPumped+=removed;
  const rim=Math.min(...rims.map(p=>p[2])),capacity=g.points.reduce((s,p)=>s+Math.max(0,(rim-p[2])/Math.max(.1,R[8])),0)*this.area*1000;
  this.litres=Math.min(this.litres,capacity);this.updateMass(Math.max(.000001,this.litres*b.config.water_density/1000),this.geometry().com);
 }
 updateMass(mass,com) {
  if(Math.abs(mass-this.lastMass)<.03 && Math.hypot(...com.map((v,i)=>v-this.lastCom[i]))<.006)return;
  const {mj,m,d,b}=this.f,spec=mj.mjtState.mjSTATE_INTEGRATION.value,buffer=new mj.DoubleBuffer(mj.mj_stateSize(m,spec));mj.mj_getState(m,d,buffer,spec);const saved=buffer.GetView().slice();buffer.delete();
  m.body_mass[this.body]=mass;m.body_pos.set(com,this.body*3);m.body_inertia.set([.046,.046,.091].map(v=>Math.max(1e-9,mass*v)),this.body*3);
  const extent=m.stat.extent,center=Array.from(m.stat.center);mj.mj_setConst(m,d);m.stat.extent=extent;m.stat.center.set(center);mj.mj_setState(m,d,saved,spec);mj.mj_forward(m,d);
  this.lastMass=mass;this.lastCom=[...com];b.mass=this.dryMass+mass;
 }
 add(litres) {if(!Number.isFinite(litres)||litres<0||litres>200)throw new Error('Add between 0 and 200 litres');this.litres+=litres;this.totalIngress+=litres;this.accumulator=.05;this.step(0);}
 status(){return {cabin_water_l:this.litres,drain_primary:this.on[0]&&!this.failures[0],drain_backup:this.on[1]&&!this.failures[1],drain_flow_lpm:this.flow.map(q=>q*60),drain_head_m:this.head,drain_high_water:this.alarm,drain_pickup:this.selected,drain_wet_pickups:this.wet,drain_failures:this.failures,drain_pumped_l:this.totalPumped,rain_mm_h:this.rain};}
}
