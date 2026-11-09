"""Separate declared moving-boat scenario through existing independent motors."""
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parent
source=r/'vm_r14_browser_stage/test/tidewater_landing_r14_browser.mjs'
s=source.read_text().replace('tidewater_stationary_r14_browser/','tidewater_moving_r14_browser/')
a='let nextProgress=0;const wall=performance.now(),yieldTask=()=>new Promise(r=>setImmediate(r));'
b=a+'''
// Boat scenario controller is independent of the drone policy. It uses only
// the boat's own pose/speed/static coastal route and existing motor input.
// No boat data from this controller is supplied to ML. Production2.8m/s cruise
// and all user controls/source files remain unchanged.
let movingBoat=false,boatStart=null;const boatSpeeds=[];
function driveBoatScenario(){
 if(!movingBoat)return;
 const {points,arc,length}=game.route,b=config.boat.body;
 const position=Array.from(data.xpos.subarray(b*3,b*3+3));
 const speed=game.boatSpeed();let nearest=Infinity,along=0;
 for(let i=0;i<points.length-1;i++){
  const a=points[i],z=points[i+1],dx=z[0]-a[0],dy=z[1]-a[1];
  const u=Math.max(0,Math.min(1,((position[0]-a[0])*dx+(position[1]-a[1])*dy)/(dx*dx+dy*dy)));
  const gap=Math.hypot(a[0]+u*dx-position[0],a[1]+u*dy-position[1]);
  if(gap<nearest){nearest=gap;along=arc[i]+u*(arc[i+1]-arc[i]);}
 }
 const target=(along+12)%length;let i=0;while(i<arc.length-2&&arc[i+1]<target)i++;
 const u=(target-arc[i])/(arc[i+1]-arc[i]),goal=points[i].map((v,k)=>v+u*(points[i+1][k]-v));
 const R=data.xmat.subarray(b*9,b*9+9),yaw=Math.atan2(R[3],R[0]);
 const desired=Math.atan2(goal[1]-position[1],goal[0]-position[0]),error=Math.atan2(Math.sin(desired-yaw),Math.cos(desired-yaw));
 const targetSpeed=.6*Math.max(.35,Math.cos(error));
 const base=Math.max(0,Math.min(78,2.8*targetSpeed**3+4*targetSpeed+12*(targetSpeed-speed)));
 const angular=forces.velocity(b,Array.from(data.xipos.subarray(b*3,b*3+3)))[2];
 const turn=Math.max(-base,Math.min(base,60*error-85*angular));
 game.input({motors:[Math.max(0,Math.min(100,base+turn)),Math.max(0,Math.min(100,base-turn))]});
 if(game.ml.enabled)boatSpeeds.push(speed);
}
'''
assert s.count(a)==1;s=s.replace(a,b)
a='async function step(){await game.advance();';assert s.count(a)==1;s=s.replace(a,'async function step(){driveBoatScenario();await game.advance();')
a=' const state=game.state(1,true);for(let i=0;i<5;i++)await capture(state);';assert s.count(a)==1
b=" movingBoat=true;boatStart=Array.from(data.xpos.subarray(config.boat.body*3,config.boat.body*3+3));const boatSettle=data.time;while(data.time-boatSettle<2)await step();\n"+a
s=s.replace(a,b)
s=s.replace("scenario:'Stationary boat, physical manual takeoff and3s backward flight before camera-only handoff'","scenario:'Moving boat following its independent static coastal route with declared0.6m/s scenario setpoint; physical manual takeoff/3s backward flight before no-radio handoff',boat_motion_assessment:{scenario_setpoint_m_s:.6,mean_speed_m_s:boatSpeeds.reduce((a,b)=>a+b,0)/Math.max(1,boatSpeeds.length),maximum_speed_m_s:Math.max(...boatSpeeds),displacement_m:Math.hypot(...Array.from(data.xpos.subarray(config.boat.body*3,config.boat.body*3+2)).map((v,i)=>v-boatStart[i]))}")
out=r/'tidewater_landing_r14_moving_browser.mjs';assert not out.exists();out.write_text(s)
receipt=dict(file='test/tidewater_landing_r14_moving_browser.mjs',sha256=hashlib.sha256(out.read_bytes()).hexdigest(),scope='Independent boat motors follow existing static coastal route at declared0.6m/s scenario setpoint; boat speed/pose used only by boat driver and physical scoring, never drone task inputs. Original controls/2.8m/s default unchanged.')
(r/'vm_r14_moving_driver_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
