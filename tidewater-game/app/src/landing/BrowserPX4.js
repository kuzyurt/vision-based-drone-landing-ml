import { BrowserNoise } from './BrowserNoise.js';
import { clamp } from './BrowserForces.js';

const FRD = [1,-1,-1];
const NED = vector => [vector[1],vector[0],-vector[2]];

export class BrowserPX4 {
	constructor(module,mj,model,data,forces,configuration) {
		this.module=module;this.mj=mj;this.model=model;this.data=data;this.forces=forces;this.configuration=configuration;
		this.pointer=module._malloc(64*8);this.raw=module._malloc(4096);
		this.noise=new BrowserNoise(configuration.rng_state.state,configuration.rng_state.inc);
		this.sensorCount=0;this.lastSensor=0;this.firstActuator=false;this.armed=false;this.landed=true;
		this.flightRequested=false;this.targetHeight=0;this.armRequestTime=0;this.lastArmTry=0;this.lastDisarmTry=0;
		this.lastPowerReport=-1e9;this.status=new Float64Array(16);this.actuators=new Float64Array(19);
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
		this.module._tw_observation(this.pointer);this.status.set(this.buffer().subarray(0,16));
		this.landed=!!this.status[12];return this.status;
	}
	vehicleCommand(command,parameters=[]) {
		const values=this.buffer();values.fill(0);values[0]=command;values.set(parameters,1);
		this.module._tw_vehicle_command(this.pointer);
	}
	pilot(keys,lookX=0,lookY=0) {
		const t=this.data.time,f=this.forces,held=key=>keys.includes(key);
		f.pan+=lookX*.0022+((held('ArrowLeft')?1:0)-(held('ArrowRight')?1:0))*Math.PI/180*50*.04;
		f.tilt-=lookY*.0022;f.tilt+=((held('ArrowDown')?1:0)-(held('ArrowUp')?1:0))*Math.PI/180*40*.04;
		f.tilt=clamp(f.tilt,-61*Math.PI/180,140*Math.PI/180);
		this.targetHeight=clamp(this.targetHeight+((held('KeyR')?1:0)-(held('KeyF')?1:0))*.6*.04,.205,8);
		this.module._tw_heartbeat();
		if(t-this.lastPowerReport>.2) {
			const values=this.buffer();values[0]=f.voltage;values[1]=f.current;values[2]=f.charge;values[3]=f.current>.1?Math.trunc(3600*f.charge/f.current):0;
			this.module._tw_battery(this.pointer);this.lastPowerReport=t;
		}
		if(!this.flightRequested) return;
		const d=this.data,b=this.configuration.drone.base,R=d.xmat.subarray(b*9,b*9+9);
		let x=(held('KeyW')?1:0)-(held('KeyS')?1:0),y=(held('KeyA')?1:0)-(held('KeyD')?1:0);
		const length=Math.hypot(x,y);if(length>1){x/=length;y/=length;}
		const velocity=NED([R[0]*x+R[1]*y,R[3]*x+R[4]*y,R[6]*x+R[7]*y]);
		const values=this.buffer();values[0]=Math.trunc(t*1000)>>>0;values[1]=-(this.targetHeight-.216);values.set(velocity,2);
		values[5]=((held('KeyE')?1:0)-(held('KeyQ')?1:0))*.5;
		this.module._tw_setpoint(this.pointer);
		const observation=this.observation();
		if(!this.armed && observation[0] && t>=8 && t-this.armRequestTime>2 && t-this.lastArmTry>2) {
			this.vehicleCommand(176,[1,6]);this.vehicleCommand(400,[1]);this.lastArmTry=t;
		}
		if(this.armed && this.targetHeight<.23 && this.landed && t-this.lastDisarmTry>1) {this.vehicleCommand(400,[0]);this.lastDisarmTry=t;}
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
