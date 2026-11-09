import {BrowserNoise} from './BrowserNoise.js';

// MAVLink v1 SET_POSITION_TARGET_LOCAL_NED (84), the same message and mask as
// the trained runner. Position/acceleration/yaw ignored; all velocity axes used.
export function velocityPacket(action,yaw,time,sequence=0) {
 const p=new Uint8Array(61),v=new DataView(p.buffer);p.set([254,53,sequence&255,255,190,84]);
 v.setUint32(6,Math.trunc((time+1)*1000)>>>0,true);
 v.setFloat32(22,Math.cos(yaw)*action[0]-Math.sin(yaw)*action[1],true);
 v.setFloat32(26,Math.sin(yaw)*action[0]+Math.cos(yaw)*action[1],true);
 v.setFloat32(30,action[2],true);v.setFloat32(50,action[3],true);
 v.setUint16(54,1479,true);p[56]=1;p[57]=1;p[58]=1;
 let crc=65535;const add=b=>{let x=b^(crc&255);x^=(x<<4)&255;crc=((crc>>>8)^(x<<8)^(x<<3)^(x>>>4))&65535;};
 for(let i=1;i<59;i++)add(p[i]);add(143);v.setUint16(59,crc,true);return p;
}

export function estimatorObservation(px4) {
 const o=px4.observation(),[w,x,y,z]=o.subarray(7,11),yaw=Math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));
 const age=stamp=>stamp>0?Math.max(0,(px4.lastSensor-stamp)/1e6):10;
 return {valid:!!o[0],position_enu_m:[o[2]+px4.originENU[0],o[1]+px4.originENU[1],-o[3]+px4.originENU[2]],
  velocity_enu_m_s:[o[5],o[4],-o[6]],attitude_ned_rad:[Math.atan2(2*(w*x+y*z),1-2*(x*x+y*y)),Math.asin(Math.max(-1,Math.min(1,2*(w*y-z*x)))),yaw],
  angular_rate_frd_rad_s:Array.from(o.subarray(16,19)),position_age_s:age(o[13]),attitude_age_s:age(o[14]),armed:px4.armed,landed:px4.landed};
}

export class PolicyTelemetry {
 constructor(game) {
  this.game=game;this.previous=Array(6).fill(0);this.lastBeacon=-Infinity;this.sequence=0;
  const s=game.c.rng_state;this.noise=new BrowserNoise(BigInt(s.state)^0x5a81n,s.inc);
 }
 sample() {
  const {d,c,f,px4}=this.game,t=d.time,p=estimatorObservation(px4);
  p.gimbal_commanded_rad=[f.pan,f.tilt];p.gimbal_command_source='own_last_issued_setpoint';
  const linked=this.game.radio.enabled!==false&&this.game.radio.connected;
  if(linked && (!this.beacon || t-this.lastBeacon>=1-1e-8)) {
   const id=c.pad_site,pos=Array.from(d.site_xpos.subarray(id*3,id*3+3)),vel=f.siteVelocity(this.game.m.site_bodyid[id],id).slice(3);
   this.beacon={position:pos.map(x=>x+.25*this.noise.normal()),velocity:vel.map(x=>x+.025*this.noise.normal())};this.lastBeacon=t;this.sequence++;
  }
  const yaw=p.attitude_ned_rad[2],convert=([e,n,u])=>[Math.cos(yaw)*n+Math.sin(yaw)*e,-Math.sin(yaw)*n+Math.cos(yaw)*e,-u];
  const mech=this.game.mechanisms(),dock=mech.aft_lid>.978&&mech.fore_lid>.978&&mech.platform>.98&&!mech.mechanism_busy;
  const stamp=this.beacon?this.lastBeacon:0;
  const available=!!(p.valid&&linked&&this.beacon);
  const beacon=available?{sequence:this.sequence,capture_time_s:stamp,received_time_s:stamp,age_s:t-stamp,position_sigma_m:.25,velocity_sigma_m_s:.025,synthetic_reference_hz:1,
   valid:true,dock_ready:!!dock,relative_heading_m:convert(this.beacon.position.map((x,i)=>x-p.position_enu_m[i])),velocity_heading_m_s:convert(this.beacon.velocity)}:
   {sequence:0,capture_time_s:0,received_time_s:0,age_s:0,position_sigma_m:0,synthetic_reference_hz:0,valid:false,dock_ready:false,relative_heading_m:[0,0,0],velocity_heading_m_s:[0,0,0]};
  return {px4:p,beacon,gimbal_rad:c.drone.camera_qpos.map(i=>d.qpos[i]+this.noise.normal()*Math.PI/180*.1),gimbal_source:'synthetic_encoder_unverified_hardware_interface',
   image_capture_time_s:t,image_delivery_time_s:t,image_age_s:0,image_valid:true,previous_executed_action:[...this.previous],decision_dt_s:.04,
   mission:{elapsed_s:Math.max(0,t-(this.game.mlStarted??t)),budget_s:180,water_datum_enu_m:0,nominal_deck_height_above_water_m:.45,coarse_height_uncertainty_m:.4,
    coarse_range_prior_source:'declared sea-level datum and nominal static boat geometry; no dynamic boat coordinates',home_authorized_for_landing:false,
    recovery_clearance:this.game.policyRecoveryClearance?.certify(p)??{valid:false,no_dynamic_boat_state:true,reason:'declared_static_map_unavailable'}}};
 }
}
