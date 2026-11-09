"""Create an isolated Tidewater-only evaluation driver; never change deployed policy."""
from pathlib import Path
import datetime,hashlib,json
r=Path(__file__).resolve().parent
run='tidewater_speed_20261018T152500Z'
out=r/run;out.mkdir(exist_ok=False)
source=(r/'r15_safe_handoff_patch/test/tidewater_landing_r15_moving_browser.mjs').read_text(encoding='utf-8')
def replace(old,new):
    global source
    assert source.count(old)==1,(old,source.count(old))
    source=source.replace(old,new)
replace("const root=new URL('../../../',import.meta.url),out=", "const spec=JSON.parse(process.env.TIDEWATER_CASE_JSON);\nconst root=new URL('../../../',import.meta.url),out=")
replace('game.automatic=false;game.setRadioEnabled(false);','game.automatic=false;game.setRadioEnabled(spec.radio);\napp.settings.timeOfDay=spec.timeOfDay;app.clouds.coverage.value=spec.cloudCoverage;')
replace("const target=(along+12)%length;", "const target=(along+Math.max(12,5*speed))%length;")
replace('const targetSpeed=.6*Math.max(.35,Math.cos(error));','const targetSpeed=spec.speed*Math.max(.35,Math.cos(error));')
replace('const boatSpeeds=[];','const boatSpeeds=[],boatTimeline=[];let nextAssessment=0,startAssessment=null;')
replace("async function step(){driveBoatScenario();await game.advance();", """async function step(){
 const gust=1+.2*Math.sin(data.time*.73)+.12*Math.sin(data.time*1.91);
 forces.wind=[spec.wind[0]*gust,spec.wind[1]*gust,0];
 driveBoatScenario();await game.advance();
 if(game.ml.enabled&&data.time>=nextAssessment){nextAssessment=data.time+.04;
  const assessment=game.ml.outcome;
  boatTimeline.push({time_s:data.time,speed_m_s:game.boatSpeed(),support_count:assessment?.support_count??0,stable:assessment?.stable??false,armed:px4.armed});}
""")
replace("if(performance.now()-wall>300000)throw new Error('Bounded5min probe wall deadline');", "if(performance.now()-wall>420000)throw new Error('evaluation_wall_limit');")
replace("game.keys=['KeyS'];const move=data.time;while(data.time-move<3)await step();", """px4.targetHeight=spec.height;const rise=data.time;
 while(data.time-rise<15){await step();if(Math.abs((.216-px4.observation()[3])-spec.height)<.12&&Math.abs(data.qvel[config.drone.free_vadr+2])<.1)break;}
 const launchOwn=Array.from(px4.observation().subarray(1,4));
 game.keys=['KeyS'];const move=data.time;
 while(data.time-move<spec.backDistance+8){await step();const o=px4.observation();if(Math.hypot(o[1]-launchOwn[0],o[2]-launchOwn[1])>=spec.backDistance)break;}
""")
replace('forces.pan=0;forces.tilt=35*Math.PI/180;', 'forces.pan=spec.panDeg*Math.PI/180;forces.tilt=spec.tiltDeg*Math.PI/180;')
replace("const state=game.state(1,true);for(let i=0;i<5;i++)await capture(state);", """const state=game.state(1,true);for(let i=0;i<5;i++)await capture(state);
 const b=config.boat.body,u=config.drone.base;
 startAssessment={horizontal_distance_m:Math.hypot(data.xpos[b*3]-data.xpos[u*3],data.xpos[b*3+1]-data.xpos[u*3+1]),drone_height_m:data.xpos[u*3+2],boat_speed_m_s:game.boatSpeed(),boat_position_enu:Array.from(data.xpos.subarray(b*3,b*3+3)),drone_position_enu:Array.from(data.xpos.subarray(u*3,u*3+3)),requested_camera_pan_deg:spec.panDeg,requested_camera_tilt_deg:spec.tiltDeg};
""")
replace('if(frames%250===0)', 'if(frames%100===0)')
replace('boat_motion_assessment:{scenario_setpoint_m_s:.6,', 'case:spec,start_assessment:startAssessment,boat_motion_assessment:{scenario_setpoint_m_s:spec.speed,')
replace('radio:false,frames,', 'radio:spec.radio,frames,')
replace("await rows.close();await fs.writeFile(new URL('report.json',out),JSON.stringify(result,null,2));", """await rows.close();
 const terminal=boatTimeline.filter(x=>x.time_s>=data.time-2.1),supported=boatTimeline.filter(x=>x.support_count>=3);
 result.boat_motion_assessment.final_2s_speed_m_s={mean:terminal.reduce((a,b)=>a+b.speed_m_s,0)/Math.max(1,terminal.length),min:Math.min(...terminal.map(x=>x.speed_m_s)),max:Math.max(...terminal.map(x=>x.speed_m_s))};
 result.boat_motion_assessment.first_support_speed_m_s=supported[0]?.speed_m_s??null;
 result.boat_motion_assessment.maximum_lateral_route_error_not_assessed=true;
 result.scenario='Tidewater game scene and unchanged deployed R15; independent motor-driven coastal route, measured speed, physically prepared airborne start; no training.';
 await fs.writeFile(new URL('boat_motion.json',out),JSON.stringify(boatTimeline));
 await fs.writeFile(new URL('report.json',out),JSON.stringify(result,null,2));""")
replace("}finally{game.cancelPolicy?.();", """}catch(error){
 await fs.writeFile(new URL('error.json',out),JSON.stringify({case:spec,error:error.stack||error.message,simulation_time_s:data.time,ml:game.ml,start_assessment:startAssessment},null,2));
 console.error(error);process.exitCode=2;
}finally{game.cancelPolicy?.();""")
replace('process.exit(errors.length?1:0);', 'process.exit(process.exitCode|| (errors.length?1:0));')
driver=out/'tidewater_speed_suite.mjs';driver.write_text(source,encoding='utf-8')
cases=[]
base=dict(speed=.6,radio=False,timeOfDay=15.35,cloudCoverage=.62,wind=[0,0],height=1.5,backDistance=8,panDeg=0,tiltDeg=35)
for speed in [.6,1.,1.4,1.8,2.2,2.8]:
    for radio in [False,True]:
        cases.append(dict(base,id='speed_'+str(speed).replace('.','p')+('_radio'if radio else'_visual'),group='speed_ladder',speed=speed,radio=radio))
for label,settings in [
    ('close_oblique',dict(height=1.2,backDistance=3,panDeg=80,tiltDeg=70,wind=[1.,.7])),
    ('far20_cloudy',dict(height=4,backDistance=20,panDeg=110,tiltDeg=20,wind=[1.5,.5],cloudCoverage=.9)),
    ('far40_late',dict(height=6,backDistance=40,panDeg=-120,tiltDeg=15,wind=[1.6,1.2],timeOfDay=17.5,cloudCoverage=.85))]:
    for radio in[False,True]:cases.append(dict(base,**dict(settings,id=label+('_radio'if radio else'_visual'),group='harder_start',radio=radio)))
plan=dict(schema='tidewater.current_policy_exploratory_speed_test.v1',run=run,
    created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    candidate_policy_sha256='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35',
    driver_sha256=hashlib.sha256(driver.read_bytes()).hexdigest(),workers=2,cases=cases,
    strict_existing_physical_scoring=True,policy_and_physics_changes=False,training=False,
    maximum_speed_interpretation='Highest tested measured landing speed under this geometry; not a universal maximum. Requested motor-route speed and actual final-contact speed reported separately.',
    followup='At most one midpoint and two confirmation scenarios per radio mode after the ladder. Do not tune policy. Preserve failures.')
(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(run=run,cases=len(cases),driver_sha256=plan['driver_sha256']),indent=2))
