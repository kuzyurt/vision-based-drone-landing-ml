// Windows Node host for the existing pinned PX4 binary ONLY.
// No Tidewater world, rendering, policy or training data is imported.
import readline from 'node:readline';
import fs from 'node:fs';
import crypto from 'node:crypto';
import loadPX4 from '../../tidewater-game/app/public/landing/wasm/px4.mjs';

const base=new URL('../../tidewater-game/app/public/landing/wasm/',import.meta.url);
for(const [name,expected] of Object.entries(JSON.parse(fs.readFileSync(new URL('../environments/runtime.json',import.meta.url))).px4_hashes)) {
 if(crypto.createHash('sha256').update(fs.readFileSync(new URL(name,base))).digest('hex')!==expected)throw new Error('Unexpected PX4 artifact '+name);
}
const log=text=>process.stderr.write(String(text)+'\n');
const module=await loadPX4({noInitialRun:true,print:log,printErr:log});
const bytes=module._malloc(4096),values=module._malloc(64*8);
let started=false,initialization=null,initializationError=null,initializationDone=false,lastCommand=null;
const commands=['dataman start','simulator_mavlink start -t 127.0.0.1 4560','system_power_simulator start','rc_update start','manual_control start','sensors start','commander start','ekf2 start','pwm_out_sim start -m sim','control_allocator start','mc_rate_control start','mc_att_control start','mc_autotune_attitude_control start','mc_hover_thrust_estimator start','flight_mode_manager start','mc_pos_control start','land_detector start multicopter','navigator start','gyro_fft start','gyro_calibration start'];
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function write(kind,encoded) {
 if(!encoded)return;
 const data=Buffer.from(encoded,'base64');
 for(let at=0;at<data.length;at+=4096){const chunk=data.subarray(at,at+4096);module.HEAPU8.set(chunk,bytes);const got=module[kind](bytes,chunk.length);if(got<0)throw new Error('PX4 input rejected');}
}
async function begin(parameters) {
 module.FS.mkdirTree('/fs/microsd');module._tw_init();module.ccall('tw_command','number',['string'],['param select /fs/microsd/parameters']);
 const boot=JSON.parse(fs.readFileSync(new URL('../../tidewater-game/app/public/landing/physics/px4-startup.json',import.meta.url)));
 for(const command of boot)module.ccall('tw_command','number',['string'],[command]);
 for(const [name,value] of Object.entries(parameters)) {
  const result=module.ccall('tw_command','number',['string'],[`param set ${name} ${value}`]);
  if(result!==0)throw new Error('Required reference parameter rejected: '+name);
 }
 for(const command of commands) {
  lastCommand=command;log("STARTUP "+command);
  if(module.ccall('tw_command_async','number',['string'],[command])!==0)throw new Error('Concurrent startup command');
  const deadline=Date.now()+20000;let result;
  while((result=module._tw_command_result())===-2147483648) {
   if(Date.now()>deadline)throw new Error('PX4 startup timeout '+command);
   await sleep(1);
  }
  if(result!==0)throw new Error('PX4 startup failed '+command+':'+result);
  await sleep(0);
 }
 initializationDone=true;
}
async function request(r) {
 if(r.op==='initialize') {
  if(started)throw new Error('Already initialized');started=true;
  initialization=begin(r.parameters).catch(e=>{initializationError=e.stack;log(e.stack);});
  return {status:'startup_in_progress',px4_revision:'6ea3539157ca358c70a515878b77077af7d4611d'};
 }
 if(r.op==='dispose') {
  module.PThread.terminateAllThreads();return {disposed:true};
 }
 if(r.op!=='poll')throw new Error('Unsupported operation');
 if(r.id<8)log('POLL '+r.id+' before inputs '+lastCommand);
 if(initializationError)throw new Error(initializationError);
 write('_tw_sim_write',r.sensors);if(r.id<8)log('POLL '+r.id+' sensors written');
 if(initializationDone)write('_tw_offboard_write',r.offboard);
 if(r.id<8)log('POLL '+r.id+' before actuators');
 const deadline=Date.now()+15000;
 while(module._tw_actuators(values,r.minimum_time||0)===1) {
  if(initializationError)throw new Error(initializationError);
  if(Date.now()>deadline)throw new Error('PX4 actuator lockstep timeout, command='+lastCommand);
  await sleep(0);
 }
 const actuators=Array.from(module.HEAPF64.subarray(values/8,values/8+19));
 module._tw_observation(values);
 return {actuators,observation:Array.from(module.HEAPF64.subarray(values/8,values/8+20)),startup_complete:initializationDone,startup_command:lastCommand};
}
const input=readline.createInterface({input:process.stdin});let chain=Promise.resolve();
input.on('line',line=>{chain=chain.then(async()=>{
 try {const r=JSON.parse(line),value=await request(r);process.stdout.write(JSON.stringify({id:r.id,ok:true,...value})+'\n');if(r.op==='dispose')process.exit(0);}
 catch(e){process.stdout.write(JSON.stringify({ok:false,error:e.stack})+'\n');}
});});
input.on('close',()=>{module.PThread.terminateAllThreads();process.exit(0);});
process.stdout.write(JSON.stringify({status:'bridge_ready',autopilot:'real_pinned_PX4_WebAssembly',physics_and_rendering:'external_Windows_MuJoCo_not_Tidewater'})+'\n');

