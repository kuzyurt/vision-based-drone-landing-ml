import {BrowserDrainage} from './BrowserDrainage.js';
// Double precision translations of simulation/native_forces.py and the original
// Propulsion class. MuJoCo integrates the existing CAD; no prescribed motion.
export const clamp = (x,lo,hi) => Math.max(lo,Math.min(hi,x));
export function interp(x, xs, ys) {
	if (x<=xs[0]) return ys[0];
	for(let i=1;i<xs.length;i++) if(x<=xs[i]) return ys[i-1]+(ys[i]-ys[i-1])*(x-xs[i-1])/(xs[i]-xs[i-1]);
	return ys.at(-1);
}
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const plus=(a,b)=>a.map((v,i)=>v+b[i]);
const minus=(a,b)=>a.map((v,i)=>v-b[i]);
const times=(a,s)=>a.map(v=>v*s);
const vec=(a,id)=>[a[id*3],a[id*3+1],a[id*3+2]];
const mat=(a,id)=>Array.from(a.subarray(id*9,id*9+9));
const mul=(R,v)=>[dot(R.slice(0,3),v),dot(R.slice(3,6),v),dot(R.slice(6,9),v)];
const transposeMul=(R,v)=>[R[0]*v[0]+R[3]*v[1]+R[6]*v[2],R[1]*v[0]+R[4]*v[1]+R[7]*v[2],R[2]*v[0]+R[5]*v[1]+R[8]*v[2]];

export class BrowserForces {
	constructor(mj,model,data,configuration) {
		this.mj=mj;this.m=model;this.d=data;this.c=configuration;
		this.u=configuration.drone;this.b=configuration.boat;this.t=configuration.tables;
		if(configuration.dof_damping_initial) model.dof_damping.set(configuration.dof_damping_initial);
		if(configuration.geom_contype_initial) model.geom_contype.set(configuration.geom_contype_initial);
		if(configuration.geom_conaffinity_initial) model.geom_conaffinity.set(configuration.geom_conaffinity_initial);
		// Embind otherwise creates a fresh typed view for every property read.
		// These arrays retain their underlying MuJoCo storage for this model.
		this.viewGetters=[];
		for(const [object,names] of [[data,['qpos','qvel','ctrl','xpos','xipos','xmat','site_xpos','subtree_com','cvel','cdof','xfrc_applied','qfrc_applied']],
			[model,['body_rootid','body_parentid','body_dofadr','body_dofnum','dof_parentid']]]) {
			for(const name of names) {
				const descriptor=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(object),name);
				if(!descriptor?.get) continue;
				const get=()=>descriptor.get.call(object);
				this.viewGetters.push({object,name,get});Object.defineProperty(object,name,{value:get(),writable:true,configurable:true});
			}
		}
		this.memoryBuffer=data.qpos.buffer;
		this.pan=0;this.tilt=0;this.commands=new Float64Array(4);this.targets=new Float64Array(4);
		this.failed=[false,false,false,false];this.charge=12;this.voltage=16.8;this.current=0;this.limited=false;
		this.boatTargets=[.4,.46,.46];this.servos=[...this.boatTargets];this.rps=[0,0];this.power=[0,0];
		this.tick=0;this.wind=[0,0,0];
		this.b.act.speed_needle_position=mj.mj_name2id(model,mj.mjtObj.mjOBJ_ACTUATOR.value,'speed_needle_position');
		this.boatQ=new Float64Array(model.nv);this.boatX=new Float64Array(model.nbody*6);
		this.droneBodies=[...new Set([...this.u.aero_bodies,...this.u.props,this.u.base])].sort((a,b)=>a-b);
		this.waterPoints=new Float64Array(this.b.bottom.length*3);this.waterVolumes=new Float64Array(this.b.bottom.length);this.waveResult=new Float64Array(4);
		this.waveCoefficients=new Float64Array(this.b.waves.flat());
		this.drainage=new BrowserDrainage(this);
		this.rotorGeoms=new Map(Object.entries(configuration.rotor_geoms).map(([name,i])=>[mj.mj_name2id(model,mj.mjtObj.mjOBJ_GEOM.value,name),i]));
	}

	velocity(body,position) {
		const d=this.d,m=this.m,offset=minus(position,vec(d.subtree_com,m.body_rootid[body]));
		const angular=Array.from(d.cvel.subarray(body*6,body*6+3));
		return [...angular,...plus(Array.from(d.cvel.subarray(body*6+3,body*6+6)),cross(angular,offset))];
	}
	siteVelocity(body,site) {return this.velocity(body,vec(this.d.site_xpos,site));}
	loads(speed) {
		speed=Math.abs(speed);const t=this.t;
		if(speed<t.omega[1]) {const ratio=(speed/t.omega[1])**2;return [t.thrust[1]*ratio,t.torque[1]*ratio];}
		return [interp(speed,t.omega,t.thrust),interp(speed,t.omega,t.torque)];
	}
	motorTargets() {
		const t=this.t;
		if(!this.charge) {this.targets.fill(0);this.limited=false;return;}
		const voltage=Math.max(12,13.2+3.6*clamp(this.charge/12,0,1)-this.current*.030);
		const maximum=interp(1.2*9.80665,t.thrust,t.omega);
		for(let i=0;i<4;i++) this.targets[i]=Math.min(interp(this.failed[i]?0:clamp(this.commands[i],0,1),t.throttle,t.omega)*voltage/16,maximum);
		let predicted=0;for(const target of this.targets) predicted+=interp(target,t.omega,t.current);
		this.limited=predicted>30;
		if(this.limited) {
			let lo=0,hi=1;
			for(let n=0;n<20;n++) {const scale=(lo+hi)*.5;let total=0;for(const target of this.targets) total+=interp(target*scale,t.omega,t.current);if(total>30) hi=scale;else lo=scale;}
			for(let i=0;i<4;i++) this.targets[i]*=lo;
		}
	}
	wave(x,y,z,time=this.d.time) {
		const out=new Float64Array(4);this.waveInto(x,y,z,time,out);return Array.from(out);
	}
	waveInto(x,y,z,time,out) {
		let height=0,vx=this.b.current[0],vy=this.b.current[1],vz=0;
		const coefficients=this.waveCoefficients;
		for(let i=0;i<4;i++) {
			const j=i*6,kx=coefficients[j],ky=coefficients[j+1],a=coefficients[j+2],omega=coefficients[j+3],phase=coefficients[j+4],k=coefficients[j+5];
			const angle=kx*x+ky*y-omega*time+phase,c=Math.cos(angle),s=Math.sin(angle);
			height+=a*c;const flow=a*omega*Math.exp(Math.min(z,0)*k);
			vx+=c*flow*kx/k;vy+=c*flow*ky/k;vz+=s*flow;
		}
		out[0]=height;out[1]=vx;out[2]=vy;out[3]=vz;
	}
	beforeStep() {
		const cfg=this.b.config,speeds=[cfg.lift_speed_mps,cfg.lid_speed_mps,cfg.lid_speed_mps];
		for(let i=0;i<3;i++) this.servos[i]+=clamp(this.boatTargets[i]-this.servos[i],-speeds[i]*.001,speeds[i]*.001);
		const denominator=2*Math.PI*cfg.water_density*cfg.propeller_diameter_m**5*cfg.propeller_KQ;
		for(let i=0;i<2;i++) {
			const desired=Math.min(cfg.max_propeller_rps,Math.cbrt(this.power[i]/100*cfg.max_shaft_power_w/denominator));
			this.rps[i]+=(desired-this.rps[i])*(1-Math.exp(-.001/cfg.motor_response_seconds));
		}
	}
	applyBoat() {
		const d=this.d,b=this.b,cfg=b.config,R=mat(d.xmat,b.body),origin=vec(d.xpos,b.body),center=vec(d.xipos,b.body);
		const velocity=this.velocity(b.body,center),points=this.waterPoints,volumes=this.waterVolumes,wave=this.waveResult,time=d.time;let volume=0;
		const rho=cfg.water_density,gravity=b.gravity,vertical=R[8];
		for(let i=0;i<b.bottom.length;i++) {
			const [x,y]=b.cells[i],bottom=b.bottom[i],span=b.top[i]-bottom;
			const px=R[0]*x+R[1]*y+R[2]*bottom+origin[0],py=R[3]*x+R[4]*y+R[5]*bottom+origin[1],pz=R[6]*x+R[7]*y+R[8]*bottom+origin[2];
			this.waveInto(px,py,0,time,wave);const eta=wave[0];let wet,h;
			if(vertical>.05) {wet=clamp((eta-pz)/vertical,0,span);h=bottom+.5*wet;}
			else if(vertical<-.05) {wet=clamp(span-(eta-pz)/vertical,0,span);h=b.top[i]-.5*wet;}
			else {wet=span*clamp(.5+(eta-pz)/.08,0,1);h=.5*(bottom+b.top[i]);}
			points[i*3]=R[0]*x+R[1]*y+R[2]*h+origin[0];points[i*3+1]=R[3]*x+R[4]*y+R[5]*h+origin[1];points[i*3+2]=R[6]*x+R[7]*y+R[8]*h+origin[2];
			volumes[i]=wet*b.area[i];volume+=volumes[i];
		}
		const wetScale=Math.min(1.5,volume/(b.mass/rho));let force=[0,0,0],torque=[0,0,0];
		for(let i=0;i<volumes.length;i++) {
			const px=points[i*3],py=points[i*3+1],pz=points[i*3+2],x=px-center[0],y=py-center[1],z=pz-center[2];
			this.waveInto(px,py,pz,time,wave);
			const vx=velocity[3]+velocity[1]*z-velocity[2]*y-wave[1],vy=velocity[4]+velocity[2]*x-velocity[0]*z-wave[2],vz=velocity[5]+velocity[0]*y-velocity[1]*x-wave[3];
			let bx=R[0]*vx+R[3]*vy+R[6]*vz,by=R[1]*vx+R[4]*vy+R[7]*vz,bz=R[2]*vx+R[5]*vy+R[8]*vz;
			const weight=volumes[i]/Math.max(volume,1e-12)*wetScale;
			bx=-(cfg.drag_linear[0]*bx+cfg.drag_quadratic[0]*Math.abs(bx)*bx)*weight;
			by=-(cfg.drag_linear[1]*by+cfg.drag_quadratic[1]*Math.abs(by)*by)*weight;
			bz=-(cfg.drag_linear[2]*bz+cfg.drag_quadratic[2]*Math.abs(bz)*bz)*weight;
			const fx=R[0]*bx+R[1]*by+R[2]*bz,fy=R[3]*bx+R[4]*by+R[5]*bz,fz=R[6]*bx+R[7]*by+R[8]*bz+rho*gravity*volumes[i];
			force[0]+=fx;force[1]+=fy;force[2]+=fz;torque[0]+=y*fz-z*fy;torque[1]+=z*fx-x*fz;torque[2]+=x*fy-y*fx;
		}
		const omega=transposeMul(R,velocity.slice(0,3));
		torque=plus(torque,mul(R,omega.map((v,i)=>-(cfg.angular_drag[i]*v+cfg.angular_drag_quadratic[i]*Math.abs(v)*v)*wetScale)));
		for(let i=0;i<2;i++) {
			const p=vec(d.site_xpos,b.prop_sites[i]),water=this.wave(...p),axis=[R[0],R[3],R[6]];
			const axial=dot(minus(plus(velocity.slice(3),cross(velocity.slice(0,3),minus(p,center))),water.slice(1)),axis);
			const n=Math.max(0,d.qvel[b.prop_dofs[i]]*(i===0?1:-1)/(2*Math.PI));
			const advance=Math.max(0,axial)/(Math.max(n,1e-6)*cfg.propeller_diameter_m);
			const immersion=clamp((water[0]-p[2]+cfg.propeller_diameter_m/2)/cfg.propeller_diameter_m,0,1);
			const thrust=rho*n*n*cfg.propeller_diameter_m**4*Math.max(0,cfg.propeller_KT0-cfg.propeller_KT_advance_slope*advance)*immersion;
			const f=times(axis,thrust);force=plus(force,f);torque=plus(torque,cross(minus(p,center),f));
		}
		const windCenter=plus(origin,mul(R,[0,0,.55]));
		const relative=transposeMul(R,minus(plus(velocity.slice(3),cross(velocity.slice(0,3),minus(windCenter,center))),this.wind));
		const windForce=mul(R,relative.map((v,i)=>-.5*1.225*[.22,.6,0][i]*v*Math.abs(v)));
		force=plus(force,windForce);torque=plus(torque,cross(minus(windCenter,center),windForce));
		for(let i=0;i<3;i++) {d.xfrc_applied[b.body*6+i]+=force[i];d.xfrc_applied[b.body*6+3+i]+=torque[i];}
		d.qfrc_applied[b.lift_dof]+=b.lift_mass*gravity*R[8];
		for(const [i,name] of ['lift_position','aft_lid_position','fore_lid_position'].entries()) d.ctrl[b.act[name]]=this.servos[i];
		d.ctrl[b.act.port_prop_velocity]=this.rps[0]*2*Math.PI;d.ctrl[b.act.starboard_prop_velocity]=-this.rps[1]*2*Math.PI;
		if(b.act.speed_needle_position>=0) d.ctrl[b.act.speed_needle_position]=(135-Math.min(Math.hypot(velocity[3],velocity[4])*3.6,30)/30*270)*Math.PI/180;
	}
	applyDrone() {
		const d=this.d,u=this.u,spin=[-1,1,-1,1];
		const add=(body,force,torque,point)=> {
			const lever=cross(minus(point,vec(d.xipos,body)),force);
			for(let j=0;j<3;j++) {d.xfrc_applied[body*6+j]+=force[j];d.xfrc_applied[body*6+3+j]+=torque[j]+lever[j];}
		};
		for(let i=0;i<4;i++) {
			const body=u.props[i],R=mat(d.xmat,body),axis=[R[2],R[5],R[8]],speed=d.qvel[u.rotor_dofs[i]];
			let [thrust,torque]=this.loads(speed);
			if(this.failed[i]) {thrust=0;d.ctrl[u.motor_act[i]]=0;}
			else d.ctrl[u.motor_act[i]]=clamp(u.rotor_I[i]*(spin[i]*this.targets[i]-speed)/.080+spin[i]*torque,-.18,.18);
			add(body,times(axis,thrust),times(axis,-spin[i]*torque),vec(d.site_xpos,u.hubs[i]));
		}
		for(let i=0;i<2;i++) d.ctrl[u.camera_act[i]]=clamp(3*([this.pan,this.tilt][i]-d.qpos[u.camera_qpos[i]])-.10*d.qvel[u.camera_dofs[i]],-.8,.8);
		for(let i=0;i<u.aero.length;i++) {
			const element=u.aero[i],body=u.aero_bodies[i],site=u.aero_sites[i],R=mat(d.xmat,body),axis=[R[element.axis],R[3+element.axis],R[6+element.axis]];
			const velocity=this.siteVelocity(body,site),relative=dot(minus(velocity.slice(3),this.wind),axis);
			add(body,times(axis,-.5*1.225*element.area_m2*element.coefficient*relative*Math.abs(relative)),[0,0,0],vec(d.site_xpos,site));
		}
		for(const body of this.droneBodies) {
			this.project(body);
			d.xfrc_applied.fill(0,body*6,body*6+6);
		}
		const damping=mul(mat(d.xmat,u.base),Array.from(d.qvel.subarray(u.free_vadr+3,u.free_vadr+6)));
		for(let i=0;i<3;i++) d.xfrc_applied[u.base*6+3+i]=-.015*damping[i];
	}
	project(body) {
		// The same sparse Jacobian projection as mj_applyFT/mj_jac, evaluated
		// before mj_step. Avoid marshaling eight temporary vectors per 1 ms.
		const m=this.m,d=this.d,root=m.body_rootid[body],p=body*3,c=root*3,f=body*6;
		const x=d.xipos[p]-d.subtree_com[c],y=d.xipos[p+1]-d.subtree_com[c+1],z=d.xipos[p+2]-d.subtree_com[c+2];
		let ancestor=body;while(ancestor && !m.body_dofnum[ancestor]) ancestor=m.body_parentid[ancestor];
		if(!m.body_dofnum[ancestor]) return;
		let dof=m.body_dofadr[ancestor]+m.body_dofnum[ancestor]-1;
		while(dof>=0) {
			const j=dof*6,ax=d.cdof[j],ay=d.cdof[j+1],az=d.cdof[j+2];
			const vx=d.cdof[j+3]+ay*z-az*y,vy=d.cdof[j+4]+az*x-ax*z,vz=d.cdof[j+5]+ax*y-ay*x;
			d.qfrc_applied[dof]+=vx*d.xfrc_applied[f]+vy*d.xfrc_applied[f+1]+vz*d.xfrc_applied[f+2];
			d.qfrc_applied[dof]+=ax*d.xfrc_applied[f+3]+ay*d.xfrc_applied[f+4]+az*d.xfrc_applied[f+5];
			dof=m.dof_parentid[dof];
		}
	}
	afterStep(armed) {
		const d=this.d,u=this.u,t=this.t;let current=0;
		for(let i=0;i<4;i++) {
			if(this.targets[i]<=0) continue;
			const speed=Math.abs(d.qvel[u.rotor_dofs[i]]),R=mat(d.xmat,u.props[i]);
			const axial=dot(minus(this.siteVelocity(u.props[i],u.hubs[i]).slice(3),this.wind),[R[2],R[5],R[8]]);
			const rpmCurrent=interp(speed,t.omega,t.current),[thrust,torque]=this.loads(speed);
			const vi=Math.sqrt(thrust/(2*1.225*Math.PI*u.rotor_radii[i]**2));
			const flow=axial/2+Math.sqrt(vi**2+(axial/2)**2),efficiency=rpmCurrent>0?torque*speed/(16*rpmCurrent):1;
			const correction=speed>=t.omega[1] && efficiency>0?thrust*(flow-vi)/(this.voltage*efficiency):0;
			current+=Math.max(0,rpmCurrent+correction);
		}
		this.current=current;this.voltage=Math.max(12,13.2+3.6*clamp(this.charge/12,0,1)-current*.030);
		this.charge=Math.max(0,this.charge-current*.001/3600);
		if(armed && d.ncon) {
			const contacts=d.contact;
			try {for(let i=0;i<contacts.size();i++) {const contact=contacts.get(i);try {for(const geom of contact.geom) {const rotor=this.rotorGeoms.get(geom);if(rotor!==undefined && Math.abs(d.qvel[u.rotor_dofs[rotor]])>40) this.failed[rotor]=true;}} finally {contact.delete?.();}}}
			finally {contacts.delete();}
		}
	}
	step(armed=false) {
		const d=this.d;
		if(this.tick%4===0) {
			const live=this.viewGetters.find(view=>view.object===d && view.name==='qpos')?.get();
			if(live && live.buffer!==this.memoryBuffer) {for(const view of this.viewGetters) view.object[view.name]=view.get();this.memoryBuffer=d.qpos.buffer;}
		}
		this.beforeStep();
		if(this.tick%4===0) {
			d.qfrc_applied.fill(0);d.xfrc_applied.fill(0);this.applyBoat();
			this.boatQ.set(d.qfrc_applied);this.boatX.set(d.xfrc_applied);this.motorTargets();
		} else {d.qfrc_applied.set(this.boatQ);d.xfrc_applied.set(this.boatX);}
		this.applyDrone();this.mj.mj_step(this.m,d);this.drainage.step(.001);this.afterStep(armed);this.tick++;
	}
}
