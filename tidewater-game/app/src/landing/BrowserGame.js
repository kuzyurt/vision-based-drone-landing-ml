import {clamp} from './BrowserForces.js';
import {heightAt,chooseRoute,coastPoints} from './BrowserWorld.js';
const vector=(a,i)=>Array.from(a.subarray(i*3,i*3+3));
const viewPosition=p=>[p[0],p[2],-p[1]];
export function pose(p,R) {return [R[0],R[1],R[2],p[0],R[6],R[7],R[8],p[2],-R[3],-R[4],-R[5],-p[1],0,0,0,1];}

export class BrowserGame {
 constructor(mj,m,d,f,px4,c,map) {
  Object.assign(this,{mj,m,d,f,px4,c,map});this.route=chooseRoute(map);this.coast=coastPoints(map);
  this.mode='drone';this.camera='boat_dock';this.automatic=true;this.keys=[];this.lookX=0;this.lookY=0;this.motors=[0,0];
  this.progress=0;this.travelled=0;this.courseError=0;this.targetSpeed=2.8;this.launchComplete=false;this.takeoffPending=false;this.message=null;
  this.nextControl=d.time;this.nextRadio=d.time;this.radio={connected:true,quality:100,status:'stable',simulated:true};
  this.remote=null;this.samples=[];this.tx=0;this.rx=0;this.dropped=0;this.retryTime=0;this.retryPending=false;this.lastRx=0;this.randomState=0x1262;
 }
 static initializePose(mj,m,d,c,route) {
  d.qpos.set(c.qpos_initial);d.qvel.set(c.qvel_initial);mj.mj_setState(m,d,new Float64Array(c.eq_active_initial),mj.mjtState.mjSTATE_EQ_ACTIVE.value);
  const b=c.boat.free_qadr,q=c.drone.free_qadr,yaw=Math.atan2(route.points[1][1]-route.points[0][1],route.points[1][0]-route.points[0][0]);
  const old=c.qpos_initial.slice(b,b+3),quaternion=c.qpos_initial.slice(b+3,b+7);
  const oldYaw=Math.atan2(2*(quaternion[0]*quaternion[3]+quaternion[1]*quaternion[2]),1-2*(quaternion[2]**2+quaternion[3]**2));
  const angle=yaw-oldYaw,cos=Math.cos(angle),sin=Math.sin(angle),dx=d.qpos[q]-old[0],dy=d.qpos[q+1]-old[1];
  d.qpos.set(route.points[0],b);d.qpos.set([Math.cos(yaw/2),0,0,Math.sin(yaw/2)],b+3);
  d.qpos[q]=route.points[0][0]+cos*dx-sin*dy;d.qpos[q+1]=route.points[0][1]+sin*dx+cos*dy;
  const original=c.qpos_initial.slice(q+3,q+7),h=Math.cos(angle/2),z=Math.sin(angle/2);
  d.qpos.set([h*original[0]-z*original[3],h*original[1]-z*original[2],h*original[2]+z*original[1],h*original[3]+z*original[0]],q+3);
  // Actual tiled terrain owns shoreline collisions, avoiding stale proxy boxes
  // from the source scene's procedural training island.
  for(let i=0;i<16;i++){const g=mj.mj_name2id(m,mj.mjtObj.mjOBJ_GEOM.value,`shore_contact_${i}`);if(g>=0){m.geom_contype[g]=0;m.geom_conaffinity[g]=0;}}
  mj.mj_forward(m,d);
 }
 input(p) {
  if(p.sequence!==undefined)this.inputSequence=p.sequence;
  if(p.mode && p.mode!==this.mode){this.mode=p.mode;this.keys=[];this.lookX=this.lookY=0;}
  if(p.keys)this.keys=p.keys;this.lookX+=p.look_x||0;this.lookY+=p.look_y||0;if(p.motors)this.motors=p.motors.map(v=>clamp(v,0,100));
  if(p.action==='camera')this.camera=p.name;
  if(p.action==='autopilot')this.automatic=!!p.enabled;
  if(p.action==='takeoff'){this.mode='drone';this.takeoffPending=true;this.launchComplete=false;}
  if(p.action==='land'){this.px4.targetHeight=.204;this.px4.vehicleCommand(21,[0,0,0,NaN,NaN,NaN,NaN]);this.keys=[];}
  if(p.action==='hover')this.keys=[];
  if(p.action==='reconnect'){this.retryTime=this.d.time+1.2;this.retryPending=true;}
  if(p.action==='lid' || p.action==='platform') {
   const s=this.mechanisms();
   if(s.mechanism_busy){this.message='Wait for the current mechanism movement to finish';return;}
   if(p.action==='lid') {
    if(!p.open && s.platform>.02){this.message='Lower the launch platform before closing both lids';return;}
    this.f.boatTargets[1]=this.f.boatTargets[2]=p.open?.46:0;
   } else {
    if(p.raised && Math.min(s.aft_lid,s.fore_lid)<.978){this.message='Open both lids before raising the launch platform';return;}
    this.f.boatTargets[0]=p.raised?.4:0;
   }
   this.message=null;
  }
 }
 mechanisms() {
  const names=['platform_slide','aft_lid_slide','fore_lid_slide'],positions=names.map(n=>this.d.qpos[this.c.boat.qadr[n]]),limits=[.4,.46,.46];
  return {platform:clamp(positions[0]/.4,0,1),aft_lid:clamp(positions[1]/.46,0,1),fore_lid:clamp(positions[2]/.46,0,1),
   platform_target:this.f.boatTargets[0]/.4,aft_lid_target:this.f.boatTargets[1]/.46,fore_lid_target:this.f.boatTargets[2]/.46,
   mechanism_busy:positions.some((p,i)=>Math.abs(p-this.f.boatTargets[i])>.004 || Math.abs(this.f.servos[i]-this.f.boatTargets[i])>.0005)};
 }
 boatSpeed() {const velocity=this.f.velocity(this.c.boat.body,vector(this.d.xipos,this.c.boat.body));return Math.hypot(velocity[3],velocity[4]);}
 routeControl() {
  const {points,arc,length}=this.route,p=vector(this.d.xpos,this.c.boat.body),speed=this.boatSpeed();let index=0;
  while(index<arc.length && arc[index]<=this.progress)index++;
  const count=points.length-1;let distance=Infinity,projected=this.progress;
  for(let offset=-5;offset<25;offset++){const i=(index-1+offset+count)%count;
   const a=points[i],b=points[i+1],dx=b[0]-a[0],dy=b[1]-a[1],u=clamp(((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy),0,1);
   const gap=Math.hypot(a[0]+dx*u-p[0],a[1]+dy*u-p[1]);if(gap<distance){distance=gap;projected=arc[i]+u*(arc[i+1]-arc[i]);}
  }
  const delta=(projected-this.progress+length*1.5)%length-length*.5;this.travelled+=Math.max(0,delta);this.progress=this.travelled%length;this.courseError=distance;
  const target=(this.progress+Math.max(12,5*speed))%length;index=0;while(index<arc.length-2 && arc[index+1]<target)index++;
  const u=(target-arc[index])/(arc[index+1]-arc[index]),goal=points[index].map((v,i)=>v+u*(points[index+1][i]-v));
  const R=this.d.xmat.subarray(this.c.boat.body*9,this.c.boat.body*9+9),yaw=Math.atan2(R[3],R[0]),desired=Math.atan2(goal[1]-p[1],goal[0]-p[0]);
  const error=Math.atan2(Math.sin(desired-yaw),Math.cos(desired-yaw)),targetSpeed=2.8*Math.max(.35,Math.cos(error));
  const base=clamp(2.8*targetSpeed**3+4*targetSpeed+12*(targetSpeed-speed),0,78),turn=clamp(60*error-85*this.f.velocity(this.c.boat.body,vector(this.d.xipos,this.c.boat.body))[2],-base,base);
  this.f.power=[clamp(base+turn,0,100),clamp(base-turn,0,100)];this.targetSpeed=targetSpeed;
 }
 control() {
  const p=this.px4,obs=p.observation();
  if(this.takeoffPending && this.boatSpeed()<.15 && obs[0]) {this.takeoffPending=false;p.flightRequested=true;p.targetHeight=1.5;p.armRequestTime=this.d.time;p.lastArmTry=0;}
  if(p.armed && this.d.xpos[this.c.drone.base*3+2]>this.d.site_xpos[this.c.pad_site*3+2]+1)this.launchComplete=true;
  const hold=this.takeoffPending || (!this.launchComplete && this.mode==='drone');
  if(hold || !obs[0])this.f.power=[0,0];else if(this.automatic)this.routeControl();else this.f.power=[...this.motors];
  p.pilot(this.mode==='drone'?this.keys:[],this.mode==='drone'?this.lookX:0,this.mode==='drone'?this.lookY:0);this.lookX=this.lookY=0;
 }
 async advance() {
  if(this.d.time+1e-8>=this.nextControl){this.control();this.nextControl+=.04;}
  await this.px4.advance();
  if(this.d.time>=this.nextRadio){this.updateRadio();this.nextRadio=this.d.time+.25;}
 }
 vehicle(body) {
  const d=this.d,p=vector(d.xpos,body),v=this.f.velocity(body,vector(d.xipos,body)).slice(3),R=d.xmat.subarray(body*9,body*9+9),yaw=Math.atan2(R[3],R[0]);
  return {position:viewPosition(p),velocity:viewPosition(v),roll:Math.atan2(R[7],R[8]),pitch:Math.asin(clamp(-R[6],-1,1)),yaw,heading:(Math.PI/2-yaw+2*Math.PI)%(2*Math.PI),speed:Math.hypot(...v)};
 }
 vehicles() {
  const p=this.px4,obs=p.observation(),u=this.c.drone,drone=this.vehicle(u.base),boat=this.vehicle(this.c.boat.body);
  Object.assign(drone,{pan:this.d.qpos[u.camera_qpos[0]],tilt:this.d.qpos[u.camera_qpos[1]],altitude:drone.position[1],battery_v:this.f.voltage,battery_pct:this.f.charge/12*100,armed:p.armed,landed:p.landed,failed_rotors:[...this.f.failed],px4_ready:!!obs[0],px4_mode:obs[15],flight_requested:p.flightRequested,takeoff_pending:this.takeoffPending});
  Object.assign(boat,this.mechanisms(),this.f.drainage.status(),{speed:this.boatSpeed(),port_power:this.f.power[0],starboard_power:this.f.power[1]});return {drone,boat};
 }
 updateRadio() {
  const vehicles=this.vehicles(),a=[...vehicles.boat.position],b=vehicles.drone.position;a[1]+=2.5;
  const distance=Math.hypot(...a.map((v,i)=>v-b[i])),steps=Math.max(4,Math.min(80,Math.trunc(distance/4)));let blocked=false;
  for(let i=0;i<steps;i++) {
   const t=.08+.84*i/(steps-1),p=a.map((v,j)=>v+(b[j]-v)*t);
   if(heightAt(this.map,p[0],-p[2])>p[1]-.35){blocked=true;break;}
   for(const box of this.map.meta.colliders.boxes){const c=box.center,h=box.half,angle=box.rotY||0,dx=p[0]-c[0],dz=p[2]-c[2];if(Math.abs(p[1]-c[1])<h[1] && Math.abs(dx*Math.cos(angle)-dz*Math.sin(angle))<h[0]+.5 && Math.abs(dx*Math.sin(angle)+dz*Math.cos(angle))<h[2]+.5){blocked=true;break;}}
   if(blocked)break;
  }
  const quality=Math.round(clamp(100-distance*.26-(blocked?82:0),0,100));
  this.tx++;this.randomState^=this.randomState<<13;this.randomState^=this.randomState>>>17;this.randomState^=this.randomState<<5;
  if((this.randomState>>>0)/4294967296<clamp((quality-5)/95,0,1)){this.rx++;this.samples.push(0);this.remote=vehicles;this.lastRx=this.d.time;}else{this.dropped++;this.samples.push(1);}
  if(this.samples.length>40)this.samples.shift();const loss=100*this.samples.reduce((a,b)=>a+b,0)/this.samples.length;
  let connected=this.radio.connected;
  if(this.d.time>=this.retryTime && (quality<8 || this.samples.length>=4 && loss>78))connected=false;
  else if(this.retryPending && this.d.time>=this.retryTime && quality>24 && loss<62){connected=true;this.retryPending=false;}
  this.radio={status:this.d.time<this.retryTime?'handshake':!connected?'lost':quality<30?'critical':quality<62?'degraded':'stable',connected,quality,rssi:-42-20*Math.log10(Math.max(distance,1))-(blocked?38:0),snr:clamp(10.5-(100-quality)*.38,-20,10.5),latency:Math.trunc(36+(100-quality)*1.2),packet_loss:loss,distance,tx:this.tx,rx:this.rx,dropped:this.dropped,simulated:true,frequency_mhz:868,spreading_factor:7,telemetry_age_s:this.d.time-this.lastRx};
 }
 state(realtimeFactor=1,includeLayout=false) {
  const {d,m,c,px4:p}=this,vehicles=this.vehicles(),obs=p.observation(),views={};
  for(const [name,id] of Object.entries(c.cameras))views[name]={matrix:pose(vector(d.cam_xpos,id),d.cam_xmat.subarray(id*9,id*9+9)),fovy:m.cam_fovy[id]};
  const bodies=c.bodies.map(([name,id])=>[name,pose(vector(d.xpos,id),d.xmat.subarray(id*9,id*9+9))]);
  const hull=this.mj.mj_name2id(m,this.mj.mjtObj.mjOBJ_GEOM.value,'hull_contact');
  const state={...vehicles,ready:!!obs[0],status:p.armed?'Flying · PX4 browser':obs[0]?'PX4 ready · press Take off':'PX4 warming sensors',parameter_warnings:p.parameterWarnings||[],input_sequence:this.inputSequence,source:'PX4 v1.16 + MuJoCo 3.14 · WebAssembly',physics_hz:1000,sensor_hz:250,controller_lag_ms:Math.max(0,(p.lastSensor-p.actuators[1])/1000),time_s:d.time,tick:this.f.tick,views,bodies,hull_pose:pose(vector(d.geom_xpos,hull),d.geom_xmat.subarray(hull*9,hull*9+9)),mode:this.mode,boat_camera:this.camera,boat_autopilot:this.automatic,radio:this.radio,remote:this.remote,message:this.message,messages:[],wind:[0,0,0],route:{valid:true,length_m:this.route.length,progress_m:this.progress,laps:Math.floor(this.travelled/this.route.length),error_m:this.courseError,target_speed_m_s:this.targetSpeed},waves:c.boat.waves.map(([kx,ky,a,w,phase])=>[kx,-ky,a,phase-d.time*w]),wave_height_m:.05,realtime_factor:realtimeFactor};
  if(includeLayout){state.geoms=c.visual_layout;state.coastline=this.coast;state.route.points=this.route.points.map(([x,y])=>[x,-y]);}
  return state;
 }
}
