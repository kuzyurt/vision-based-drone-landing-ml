import { BrowserNoise } from './BrowserNoise.js';
import { clamp } from './BrowserForces.js';
import {velocityPacket,estimatorObservation} from './PolicyTelemetry.js';

const FRD = [1,-1,-1];
// Launch and recovery on a moving AERODOCK. PX4's GNSS drift and speed checks
// (EKF2_GPS_CHECK bits 5-8) assume a vehicle that stands still while landed.
// On a moving deck they fail: arming is refused ("GPS Horizontal Pos Drift too
// high") and after ~5 s EKF2 stops using GPS, so offboard setpoints become
// invalid and PX4 falls back to a blind descent. PX4's guidance for moving
// platforms is to disable exactly these checks; all other GNSS quality checks
// (satellites, PDOP, accuracy, spoofing) stay on.
const MOVING_PLATFORM_PARAMETERS = {EKF2_GPS_CHECK: 1023 & ~(32|64|128|256)};
// Take-off from a moving deck: before lift-off the drone's own velocity
// estimate is the deck's velocity. That velocity is carried through the climb
// so the drone leaves the bay without being dragged against it, then eased
// out once it is clear of the boat.
// Deck trim: a boat under way does not sit level (about 1.5 degrees at full
// throttle). During the thrust ramp PX4 already steers attitude, so it tried
// to level the drone against the deck it was still standing on and spun the
// forward rotor pair up first. Until lift-off the velocity setpoint therefore
// carries the small lead that makes PX4's wanted thrust direction equal the
// deck normal (acceleration g*tan(tilt), through the velocity gain), with a
// slight bias toward the deck's direction of travel so the pair that leads
// is the one that pushes the drone along with the boat. It fades out after
// lift-off (trimRelease seconds).
const TAKEOFF = {clearHeight: .9, liftoffHeight: .15, release: .6, filter: .5, limitMargin: .4, velocityGain: 1.8, trimLead: .022, liftThrust: .46, trimRelease: .4};
const NED = vector => [vector[1],vector[0],-vector[2]];

export class BrowserPX4 {
	constructor(module,mj,model,data,forces,configuration) {
		this.module=module;this.mj=mj;this.model=model;this.data=data;this.forces=forces;this.configuration=configuration;
		this.pointer=module._malloc(64*8);this.raw=module._malloc(4096);
		this.noise=new BrowserNoise(configuration.rng_state.state,configuration.rng_state.inc);
		this.sensorCount=0;this.lastSensor=0;this.firstActuator=false;this.armed=false;this.landed=true;
		this.flightRequested=false;this.landingRequested=false;this.targetHeight=0;this.armRequestTime=0;this.lastArmTry=0;this.lastDisarmTry=0;
		this.lastPowerReport=-1e9;this.status=new Float64Array(20);this.actuators=new Float64Array(19);
		this.originENU=Array.from(data.site_xpos.subarray(configuration.gps_site*3,configuration.gps_site*3+3));this.policySequence=0;
	}
	buffer() {return this.module.HEAPF64.subarray(this.pointer/8,this.pointer/8+64);}
	command(command) {return this.module.ccall('tw_command','number',['string'],[command]);}
	async startCommand(command) {
		this.checkCancelled?.();
		this.onStartup?.(command);
		this.module.ccall('tw_command_async','number',['string'],[command]);
		const begin=performance.now();let result;
		while((result=this.module._tw_command_result())===-2147483648) {
			this.checkCancelled?.();
			if(performance.now()-begin>10000) throw new Error(`PX4 startup timed out: ${command}`);
			if(command.startsWith('simulator_mavlink start') || this.simulationStarted) await this.advance();
			await new Promise(resolve=>setTimeout(resolve,1));
		}
		if(result!==0) throw new Error(`PX4 browser startup: ${command} returned ${result}`);
		if(command.startsWith('simulator_mavlink start')) this.simulationStarted=true;
	}
	async initialize(boot) {
		this.module.FS.mkdirTree('/fs/microsd');
		this.module._tw_init();
		this.command('param select /fs/microsd/parameters');
		this.parameterWarnings=[];
		for(const command of boot){const result=this.command(command);if(result!==0)this.parameterWarnings.push({command,result});}
		for(const [name,value] of Object.entries(this.configuration.parameters)){const result=this.command(`param set ${name} ${value}`);if(result!==0)throw new Error(`Required reference parameter ${name} failed: ${result}`);}
		for(const [name,value] of Object.entries(MOVING_PLATFORM_PARAMETERS)){const result=this.command(`param set ${name} ${value}`);if(result!==0)this.parameterWarnings.push({command:`param set ${name} ${value}`,result});}
		for(const command of ['dataman start','simulator_mavlink start -t 127.0.0.1 4560',
			'system_power_simulator start','rc_update start','manual_control start','sensors start','commander start',
			'ekf2 start','pwm_out_sim start -m sim','control_allocator start','mc_rate_control start','mc_att_control start',
			'mc_autotune_attitude_control start','mc_hover_thrust_estimator start','flight_mode_manager start','mc_pos_control start',
			'land_detector start multicopter','navigator start','gyro_fft start','gyro_calibration start']) {
			await this.startCommand(command);
			// Let pthread startup proxies run between module commands.
			await new Promise(resolve=>setTimeout(resolve,0));
		}
	}
	observation() {
		this.module._tw_observation(this.pointer);this.status.set(this.buffer().subarray(0,20));
		this.landed=!!this.status[12];
		// A flight request is intent, not proof that the aircraft is airborne.
		// Only confirmed landing/disarming ends it; a grounded arming sequence
		// with a takeoff target must remain active until PX4 actually arms.
		if(this.landed && !this.armed && !this.status[11] && (this.landingRequested || this.flightRequested && this.targetHeight<.23)) {
			this.flightRequested=false;this.landingRequested=false;
		}
		return this.status;
	}
	vehicleCommand(command,parameters=[]) {
		const values=this.buffer();values.fill(0);values[0]=command;values.set(parameters,1);
		this.module._tw_vehicle_command(this.pointer);
	}
	policyPilot(action,yawNed) {
		if(action.length!==6 || !action.every(Number.isFinite))throw new Error('Invalid ML action');
		this.carryLimit([0,0]);
		const yaw=yawNed??estimatorObservation(this).attitude_ned_rad[2],packet=velocityPacket(action,yaw,this.data.time,this.policySequence++);
		this.module.HEAPU8.set(packet,this.raw);this.module._tw_offboard_write(this.raw,packet.length);this.module._tw_heartbeat();
		this.forces.pan+=action[4]*.04;this.forces.tilt=clamp(this.forces.tilt+action[5]*.04,-61*Math.PI/180,140*Math.PI/180);
		if(this.data.time-this.lastPowerReport>.2){const values=this.buffer();values[0]=this.forces.voltage;values[1]=this.forces.current;values[2]=this.forces.charge;values[3]=this.forces.current>.1?Math.trunc(3600*this.forces.charge/this.forces.current):0;this.module._tw_battery(this.pointer);this.lastPowerReport=this.data.time;}
	}
	manualHold() {this.targetHeight=Math.max(.205,.216-this.observation()[3]);this.landingRequested=false;}
	pilot(keys,lookX=0,lookY=0) {
		const t=this.data.time,f=this.forces,held=key=>keys.includes(key);
		f.pan+=lookX*.0022+((held('ArrowLeft')?1:0)-(held('ArrowRight')?1:0))*Math.PI/180*50*.04;
		f.tilt-=lookY*.0022;f.tilt+=((held('ArrowDown')?1:0)-(held('ArrowUp')?1:0))*Math.PI/180*40*.04;
		f.tilt=clamp(f.tilt,-61*Math.PI/180,140*Math.PI/180);
		this.targetHeight=clamp(this.targetHeight+((held('KeyR')?1:0)-(held('KeyF')?1:0))*.6*.04,.205,Math.max(8,this.targetHeight));
		this.module._tw_heartbeat();
		if(t-this.lastPowerReport>.2) {
			const values=this.buffer();values[0]=f.voltage;values[1]=f.current;values[2]=f.charge;values[3]=f.current>.1?Math.trunc(3600*f.charge/f.current):0;
			this.module._tw_battery(this.pointer);this.lastPowerReport=t;
		}
		// Also disarm a late arming response after a grounded takeoff cancellation.
		if(this.armed && this.targetHeight<.23 && this.landed && t-this.lastDisarmTry>1) {this.vehicleCommand(400,[0]);this.lastDisarmTry=t;}
		if(!this.flightRequested){this.carryLimit([0,0]);return;}
		const d=this.data,b=this.configuration.drone.base,R=d.xmat.subarray(b*9,b*9+9);
		let x=(held('KeyW')?1:0)-(held('KeyS')?1:0),y=(held('KeyA')?1:0)-(held('KeyD')?1:0);
		const length=Math.hypot(x,y);if(length>1){x/=length;y/=length;}
		// Full stick is the airframe's declared horizontal limit, not a unit vector: the old 1 m/s
		// setpoint made the X500 slower than the boat while MPC_XY_VEL_MAX already caps it.
		const maxSpeed=this.configuration.parameters?.MPC_XY_VEL_MAX??2;
		const velocity=NED([R[0]*x+R[1]*y,R[3]*x+R[4]*y,R[6]*x+R[7]*y]).map(v=>v*maxSpeed);
		const carry=this.takeoffCarry(.04);this.carryLimit(carry);velocity[0]+=carry[0];velocity[1]+=carry[1];
		const trim=this.deckTrim(R,carry,.04);velocity[0]+=trim[0];velocity[1]+=trim[1];
		const values=this.buffer();values[0]=Math.trunc(t*1000)>>>0;values[1]=-(this.targetHeight-.216);values.set(velocity,2);
		values[5]=((held('KeyE')?1:0)-(held('KeyQ')?1:0))*.5;
		this.module._tw_setpoint(this.pointer);
		const observation=this.observation();
		if(!this.landingRequested && this.flightRequested && !this.armed && observation[0] && t>=8 && t-this.armRequestTime>2 && t-this.lastArmTry>2) {
			this.vehicleCommand(176,[1,6]);this.vehicleCommand(400,[1]);this.lastArmTry=t;
		}
	}
	// Deck velocity carried through a take-off (see TAKEOFF). Uses only PX4's
	// own estimate (status 3: NED z, 4-5: NED vx/vy, 12: landed).
	takeoffCarry(dt) {
		const s=this.status;
		if(!this.flightRequested||this.landingRequested){this.carry=null;return [0,0];}
		const height=-s[3],landed=!!s[12];
		if(!this.carry){
			// A flight request while already well above the deck needs no carry.
			if(!landed&&height>TAKEOFF.liftoffHeight)return [0,0];
			this.carry={phase:'deck',velocity:[0,0]};
		}
		const c=this.carry;
		if(c.phase==='deck'){
			// only while the deck still carries the drone: near hover thrust its velocity is its own
			if(!this.lifting()&&Number.isFinite(s[4])&&Number.isFinite(s[5])){const k=Math.min(1,dt/TAKEOFF.filter);c.velocity[0]+=(s[4]-c.velocity[0])*k;c.velocity[1]+=(s[5]-c.velocity[1])*k;}
			if(this.armed&&!landed&&height>TAKEOFF.liftoffHeight)c.phase='climb';
		}else if(c.phase==='climb'){
			if(height>TAKEOFF.clearHeight)c.phase='release';
		}else if(c.phase==='release'){
			const speed=Math.hypot(...c.velocity),next=Math.max(0,speed-TAKEOFF.release*dt);
			if(next<.02){c.phase='done';c.velocity=[0,0];}else c.velocity=c.velocity.map(v=>v*next/speed);
		}
		return c.phase==='done'?[0,0]:c.velocity;
	}
	// Thrust close to hover: the drone is leaving (or has left) the deck.
	lifting() {return this.armed&&(this.actuators[3]+this.actuators[4]+this.actuators[5]+this.actuators[6])/4>TAKEOFF.liftThrust;}
	// Velocity lead that matches PX4's thrust direction to the deck normal while
	// the drone still stands on a moving deck (see TAKEOFF). R is the drone's
	// own attitude; the result is NED north/east in m/s.
	deckTrim(R,carry,dt) {
		const c=this.carry,speed=Math.hypot(carry[0],carry[1]);
		if(!c||c.phase==='done'||c.phase==='release'||speed<.3){this.trim=null;return [0,0];}
		const gain=(this.configuration.parameters?.MPC_XY_VEL_P_ACC??TAKEOFF.velocityGain)||TAKEOFF.velocityGain;
		if(c.phase==='deck'&&!this.lifting()){
			const up=Math.max(.5,R[8]),g=9.80665;
			// body z axis in the world (east, north, up) -> horizontal acceleration that needs this tilt
			const north=g*R[5]/up,east=g*R[2]/up,lead=g*TAKEOFF.trimLead;
			this.trim={value:[(north+lead*carry[0]/speed)/gain,(east+lead*carry[1]/speed)/gain],scale:1};
		}else if(this.trim)this.trim.scale=Math.max(0,this.trim.scale-dt/TAKEOFF.trimRelease);
		const t=this.trim;return t?[t.value[0]*t.scale,t.value[1]*t.scale]:[0,0];
	}
	// PX4 clamps every horizontal velocity setpoint to MPC_XY_VEL_MAX. A deck
	// that moves faster than that limit (the boat reaches about 3 m/s under
	// manual throttle, the airframe limit is 2 m/s) had its carried velocity
	// cut down: the drone braked against the boat while still inside the bay,
	// pitched back on the wrong rotor pair and struck the bay. While a deck
	// velocity is carried the limit therefore follows it, and returns to the
	// airframe's own value as soon as the carry has been released below it.
	carryLimit(carry) {
		const base=this.configuration.parameters?.MPC_XY_VEL_MAX??12,speed=Math.hypot(carry[0],carry[1]);
		// Steps of 0.5 m/s keep parameter updates rare while the deck speed drifts.
		const wanted=speed+TAKEOFF.limitMargin>base?Math.ceil((speed+TAKEOFF.limitMargin)*2)/2:base;
		if(wanted===(this.velocityLimit??base))return;
		if(this.command(`param set MPC_XY_VEL_MAX ${wanted}`)===0)this.velocityLimit=wanted;
	}
	sensors() {
		const d=this.data,c=this.configuration,b=c.drone.base,R=d.xmat.subarray(b*9,b*9+9),s=d.sensordata;
		const values=this.buffer();values.fill(0);values[0]=Math.trunc((d.time+1)*1e6);this.lastSensor=values[0];
		const accel=c.imu_sensors.imu_accel_FLU,gyro=c.imu_sensors.imu_gyro_FLU;
		for(let i=0;i<3;i++) values[1+i]=FRD[i]*s[accel+i]+this.noise.normal()*.025;
		for(let i=0;i<3;i++) values[4+i]=FRD[i]*s[gyro+i]+this.noise.normal()*.0015;
		const field=[.004,.215,-.427];
		for(let i=0;i<3;i++) values[7+i]=FRD[i]*(R[i]*field[0]+R[3+i]*field[1]+R[6+i]*field[2])+this.noise.normal()*.0004;
		const altitude=488+d.xpos[b*3+2];values[10]=1013.25*(1-altitude/44330)**5.255+this.noise.normal()*.012;
		values[11]=altitude;values[12]=63|(this.sensorCount%5===0?(448|6656):0);
		const gps=this.sensorCount%12===0;
		if(gps) {
			const site=c.gps_site,p=NED(Array.from(d.site_xpos.subarray(site*3,site*3+3)));
			const velocity=NED(this.forces.siteVelocity(this.model.site_bodyid[site],site).slice(3));
			const latitude=47.397742+p[0]/111111,longitude=8.545594+p[1]/(111111*Math.cos(latitude*Math.PI/180));
			values[13]=Math.trunc(latitude*1e7);values[14]=Math.trunc(longitude*1e7);values[15]=Math.trunc((488+d.site_xpos[site*3+2])*1000);
			values[16]=Math.trunc(Math.hypot(velocity[0],velocity[1])*100);for(let i=0;i<3;i++) values[17+i]=Math.trunc(velocity[i]*100);
			values[20]=Math.trunc(((Math.atan2(velocity[1],velocity[0])*180/Math.PI+360)%360)*100);
		}
		this.module._tw_sensors(this.pointer,gps?1:0);this.sensorCount++;
	}
	async advance() {
		const begin=performance.now();
		while(true) {
			this.checkCancelled?.();
			const signal=this.module._tw_actuator_signal(),view=new Int32Array(this.module.HEAPU8.buffer),sequence=Atomics.load(view,signal/4);
			const result=this.module._tw_actuators(this.pointer,this.firstActuator?this.lastSensor:0);
			if(result===0)break;
			if(result<0 || performance.now()-begin>3000)throw new Error('PX4 WebAssembly lockstep timed out');
			// Waiting asynchronously keeps worker messages and Emscripten FS proxies
			// responsive. No stale motor frame advances the simulation.
			if(Atomics.waitAsync) {
				const waiting=Atomics.waitAsync(view,signal/4,sequence,20);
				if(waiting.async) await new Promise(resolve=>{
					const timer=setTimeout(resolve,20);
					waiting.value.then(()=>{clearTimeout(timer);resolve();});
				});
			}
			else await new Promise(resolve=>setTimeout(resolve,0));
		}
		this.actuators.set(this.buffer().subarray(0,19));this.firstActuator=!!this.actuators[0];this.armed=!!this.actuators[2];
		const order=[0,2,1,3];for(let i=0;i<4;i++) this.forces.commands[order[i]]=this.armed?clamp(this.actuators[3+i],0,1):0;
		for(let i=0;i<4;i++) this.forces.step(this.armed);
		this.sensors();
	}
}
