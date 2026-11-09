// Declared static map only. This object may veto ascent; it cannot locate a
// boat, authorize descent or claim that moving obstacles have been sensed.
const unavailable=reason=>({valid:false,source:'declared static map; upward recovery veto only',reason,max_altitude_enu_m:null});
export class PolicyRecoveryClearance {
 constructor(map) {
  this.map=map;this.boxes=[];this.sha=null;
  const c=map?.meta?.colliders;
  if(!c||!Array.isArray(c.boxes)||!Array.isArray(c.cylinders))return;
  for(const b of c.boxes){
   if(b.solid===false)continue;
   const a=b.rotY||0,cos=Math.abs(Math.cos(a)),sin=Math.abs(Math.sin(a)),[x,z,minusY]=b.center,[hx,hz,hy]=b.half;
   const ex=cos*hx+sin*hy,ey=sin*hx+cos*hy;
   this.boxes.push({min:[x-ex,-minusY-ey,z-hz],max:[x+ex,-minusY+ey,z+hz]});
  }
  for(const b of c.cylinders)this.boxes.push({min:[b.x-b.radius,-b.z-b.radius,b.yMin],max:[b.x+b.radius,-b.z+b.radius,b.yMax]});
  // Hash existing static map bytes once, before automatic recovery can use it.
  this.ready=this.identify().catch(()=>{this.sha=null;});
 }
 async identify(){
  const heights=this.map.heights,meta=new TextEncoder().encode(JSON.stringify(this.map.meta));
  if(!(heights instanceof Float32Array)||heights.length!==this.map.meta.res**2)return;
  const heightHash=new Uint8Array(await crypto.subtle.digest('SHA-256',heights));
  const bytes=new Uint8Array(meta.length+heightHash.length);bytes.set(meta);bytes.set(heightHash,meta.length);
  const hash=new Uint8Array(await crypto.subtle.digest('SHA-256',bytes));this.sha=Array.from(hash,x=>x.toString(16).padStart(2,'0')).join('');
 }
 certify(px4){
  if(!this.sha)return unavailable('static_map_not_identified');
  const p=px4?.position_enu_m,v=px4?.velocity_enu_m_s;
  if(!px4?.valid||![px4.position_age_s,px4.attitude_age_s].every(Number.isFinite)||px4.position_age_s>.25||px4.attitude_age_s>.25||!p||!v||p.length!==3||v.length!==3||![...p,...v].every(Number.isFinite))return unavailable('own_estimator_unavailable');
  // Full <=16s bounded recovery, .8m/s maximum target-velocity hold, braking
  // distance and vehicle margin. Recomputed from own position each decision.
  const radius=.7+Math.hypot(v[0],v[1])+.8*16,up=Math.max(0,v[2]),margin=.3+up*up/(2*.5);
  const {origin,size,res}=this.map.meta,h=this.map.heights;
  if(![origin,size,res].every(Number.isFinite)||size<=0||res<2||p[0]-radius<origin||p[0]+radius>=origin+size||-p[1]-radius<origin||-p[1]+radius>=origin+size)return unavailable('unknown_static_map_coverage');
  let maximum=10.5,reason='mission_ceiling';
  for(const b of this.boxes){
   if(b.max[2]<p[2]-.3||b.min[0]>p[0]+radius||b.max[0]<p[0]-radius||b.min[1]>p[1]+radius||b.max[1]<p[1]-radius)continue;
   const cap=b.min[2]-margin;if(cap<maximum){maximum=cap;reason='static_obstacle_column';}
  }
  // Include every height sample touched by the swept column, with a one-cell
  // border covering the collision heightfield's interpolation/downsampling.
  const scale=res/size,loX=Math.max(0,Math.floor((p[0]-radius-origin)*scale)-1),hiX=Math.min(res-1,Math.ceil((p[0]+radius-origin)*scale)+1);
  const loY=Math.max(0,Math.floor((-p[1]-radius-origin)*scale)-1),hiY=Math.min(res-1,Math.ceil((-p[1]+radius-origin)*scale)+1);
  let top=-Infinity;
  for(let y=loY;y<=hiY;y++)for(let x=loX;x<=hiX;x++){const z=h[y*res+x];if(!Number.isFinite(z))return unavailable('unknown_terrain_sample');top=Math.max(top,z);}
  if(top>=p[2]-.3){maximum=Math.min(maximum,p[2]-.3);reason='terrain_in_recovery_column';}
  return {valid:true,source:'declared static obstacle prior; upward recovery veto only',static_map_sha256:this.sha,max_altitude_enu_m:maximum,
   free_upward_m:Math.max(0,maximum-p[2]),horizontal_column_radius_m:radius,reason,no_dynamic_boat_state:true};
 }
}
