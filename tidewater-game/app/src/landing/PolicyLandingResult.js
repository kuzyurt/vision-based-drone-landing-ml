// Physical outcome assessment is kept outside the policy observation. The
// controller receives camera/estimator/beacon data; it never receives contacts.
const FEET=['LinkGroup005__Solid006','LinkGroup005__Link','LinkGroup005__Link010','LinkGroup005__Link011'];
const cross=(a,b)=>a[0]*b[1]-a[1]*b[0];
export class PolicyLandingResult {
 constructor(game){
  this.game=game;const {mj,m}=game,id=(kind,name)=>{const value=mj.mj_name2id(m,kind.value,name);if(value<0)throw new Error('Missing landing assessment geometry: '+name);return value;};
  this.pad=id(mj.mjtObj.mjOBJ_GEOM,'landing_contact');this.feet=FEET.map(n=>id(mj.mjtObj.mjOBJ_GEOM,'drone_contact__'+n));this.sites=FEET.map((_,i)=>id(mj.mjtObj.mjOBJ_SITE,'drone_foot_'+i));this.stableSeconds=0;
 }
 update(dt) {
  const {d,m,c,f,px4}=this.game,support=new Set(),contacts=d.contact;
  let forbidden=false;const isDrone=g=>m.body_rootid[m.geom_bodyid[g]]===c.drone.base;
  try{for(let i=0;i<d.ncon;i++){const contact=contacts.get(i);try{const [a,b]=contact.geom;if(a===this.pad||b===this.pad){const other=a===this.pad?b:a,foot=this.feet.indexOf(other);if(foot>=0)support.add(foot);else if(isDrone(other))forbidden=true;}else if(isDrone(a)||isDrone(b)){const launch=this.game.mj.mj_name2id(m,this.game.mj.mjtObj.mjOBJ_BODY.value,'launch_pad');if(m.geom_bodyid[a]!==launch&&m.geom_bodyid[b]!==launch)forbidden=true;}}finally{contact.delete?.();}}}finally{contacts.delete();}
  const origin=Array.from(d.site_xpos.subarray(c.pad_site*3,c.pad_site*3+3)),R=d.site_xmat.subarray(c.pad_site*9,c.pad_site*9+9),local=p=>{const v=p.map((x,i)=>x-origin[i]);return [R[0]*v[0]+R[3]*v[1]+R[6]*v[2],R[1]*v[0]+R[4]*v[1]+R[7]*v[2],R[2]*v[0]+R[5]*v[1]+R[8]*v[2]];};
  const feet=this.sites.map(i=>local(Array.from(d.site_xpos.subarray(i*3,i*3+3)))),com=local(Array.from(d.subtree_com.subarray(c.drone.base*3,c.drone.base*3+3)));
  let supported=false;
  if(support.size>=3){const points=[...support].map(i=>feet[i]),center=points.reduce((p,q)=>[p[0]+q[0]/points.length,p[1]+q[1]/points.length],[0,0]);points.sort((a,b)=>Math.atan2(a[1]-center[1],a[0]-center[0])-Math.atan2(b[1]-center[1],b[0]-center[0]));supported=points.every((p,i)=>{const q=points[(i+1)%points.length];return cross([q[0]-p[0],q[1]-p[1]],[com[0]-p[0],com[1]-p[1]])>=-1e-6;});}
  const drone=f.velocity(c.drone.base,Array.from(d.xpos.subarray(c.drone.base*3,c.drone.base*3+3))),pad=f.siteVelocity(m.site_bodyid[c.pad_site],c.pad_site),relative=drone.slice(3).map((x,i)=>x-pad[i+3]);
  const down=R[2]*relative[0]+R[5]*relative[1]+R[8]*relative[2],horizontal=Math.sqrt(Math.max(0,relative.reduce((s,x)=>s+x*x,0)-down*down)),D=d.xmat.subarray(c.drone.base*9,c.drone.base*9+9),tilt=Math.acos(Math.max(-1,Math.min(1,D[2]*R[2]+D[5]*R[5]+D[8]*R[8])));
  const failed=forbidden||f.failed.some(Boolean),stable=!failed&&supported&&feet.every(p=>Math.max(Math.abs(p[0]),Math.abs(p[1]))<=.28)&&horizontal<.1&&Math.abs(down)<.05&&tilt<5*Math.PI/180&&Math.hypot(...drone.slice(0,3).map((x,i)=>x-pad[i]))<5*Math.PI/180;
  this.stableSeconds=stable&&!px4.armed?this.stableSeconds+dt:0;
  return {support_count:support.size,stable,landed:this.stableSeconds>=2,collision_failure:failed,disarmed_contact_s:this.stableSeconds};
 }
}
