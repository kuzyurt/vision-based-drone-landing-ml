import json,time,urllib.request,math
from pathlib import Path
from websockets.sync.client import connect
API='http://127.0.0.1:5195'
report={}
for _ in range(180):
 state=json.load(urllib.request.urlopen(API+'/api/status'))
 if state.get('error'):raise RuntimeError(state['error'])
 if state.get('ready'):break
 time.sleep(1)
else:raise RuntimeError('Flight controller did not become ready')
with connect('ws://127.0.0.1:5195/ws',max_size=8000000) as ws:
 def receive():
  s=json.loads(ws.recv(timeout=20))
  if s.get('error'):raise RuntimeError(s['error'])
  return s
 def run(seconds):
  start=time.monotonic();s=receive()
  while time.monotonic()-start<seconds:s=receive()
  return s
 run(2)  # Allow reset/startup caches to settle before measuring steady pacing.
 before=receive();wall=time.monotonic();after=run(5)
 report['realtime_factor']=(after['time_s']-before['time_s'])/(time.monotonic()-wall)
 print('Realtime:',report['realtime_factor'],flush=True)
 initial=after['drone']['position'][1];ws.send(json.dumps({'action':'takeoff'}))
 start=time.monotonic()
 while time.monotonic()-start<30:
  after=receive()
  if after['drone']['armed'] and after['drone']['position'][1]>initial+1.:break
 else:raise RuntimeError('Takeoff did not climb')
 report['takeoff_climb_m']=after['drone']['position'][1]-initial
 print('Takeoff:',report['takeoff_climb_m'],flush=True)
 ws.send(json.dumps({'keys':[]}));run(4)
 before=receive();wall=time.monotonic();after=run(5)
 report['flight_realtime_factor']=(after['time_s']-before['time_s'])/(time.monotonic()-wall)
 print('Flight realtime:',report['flight_realtime_factor'],flush=True)
 assert min(report['realtime_factor'],report['flight_realtime_factor'])>.94,report
 origin=after['drone']['position'];ws.send(json.dumps({'mode':'drone','keys':['KeyW']}));after=run(3)
 report['forward_distance_3s_m']=math.dist(origin,after['drone']['position'])
 ws.send(json.dumps({'keys':[]}));assert report['forward_distance_3s_m']>2,report
 print('Forward 3 seconds:',report['forward_distance_3s_m'],flush=True)
 heading=after['drone']['yaw'];origin=after['drone']['position'];ws.send(json.dumps({'keys':['KeyD']}));after=run(2)
 delta=[after['drone']['position'][i]-origin[i] for i in range(3)]
 report['right_strafe_2s_m']=delta[0]*math.sin(heading)+delta[2]*math.cos(heading)
 assert report['right_strafe_2s_m']>.5,report
 heading=after['drone']['yaw'];ws.send(json.dumps({'keys':['KeyE']}));after=run(2)
 report['right_yaw_2s_rad']=math.atan2(math.sin(after['drone']['yaw']-heading),math.cos(after['drone']['yaw']-heading))
 assert report['right_yaw_2s_rad']<-.3,report
 height=after['drone']['position'][1];ws.send(json.dumps({'keys':['KeyF']}));after=run(2)
 report['descent_2s_m']=height-after['drone']['position'][1]
 assert report['descent_2s_m']>.3,report
 ws.send(json.dumps({'keys':['KeyR']}));run(2)
 ws.send(json.dumps({'keys':['ArrowLeft','ArrowDown']}));after=run(1)
 report['camera_pan_rad']=after['drone']['pan'];report['camera_tilt_rad']=after['drone']['tilt']
 assert abs(report['camera_pan_rad'])>.2 and abs(report['camera_tilt_rad'])>.2,report
 ws.send(json.dumps({'keys':[]}))
 ws.send(json.dumps({'mode':'boat','action':'autopilot','enabled':False,'motors':[0,0]}));after=run(.5)
 platform_start_sim=after['time_s']
 ws.send(json.dumps({'action':'platform','raised':False}));start=time.monotonic()
 while time.monotonic()-start<12:
  after=receive()
  if after['boat']['platform']<.01:break
 else:raise RuntimeError('Platform did not lower')
 report['platform_lower_wall_s']=time.monotonic()-start
 report['platform_lower_sim_s']=after['time_s']-platform_start_sim
 after=run(.3);lid_start_sim=after['time_s'];ws.send(json.dumps({'action':'lid','open':False}));start=time.monotonic()
 while time.monotonic()-start<9:
  after=receive()
  if max(after['boat']['aft_lid'],after['boat']['fore_lid'])<.01:break
 else:raise RuntimeError('Lids did not close: '+str(after.get('message')))
 report['lids_close_wall_s']=time.monotonic()-start
 report['lids_close_sim_s']=after['time_s']-lid_start_sim
 assert report['platform_lower_wall_s']<9.5 and report['lids_close_wall_s']<7.,report
 ws.send(json.dumps({'motors':[70,50]}));origin=after['boat']['position'];after=run(3)
 report['boat_manual_distance_3s_m']=math.dist(origin,after['boat']['position'])
 assert report['boat_manual_distance_3s_m']>1,report
 report['max_wave_height_m']=2*sum(abs(row[2]) for row in after['waves'])
 assert report['max_wave_height_m']<=.050001,report
 for camera in ['boat_nav','boat_dock','boat_nav','boat_dock']:
  ws.send(json.dumps({'mode':'boat','action':'camera','name':camera}))
  after=run(.15);assert after['mode']=='boat' and after['boat_camera']==camera
 ws.send(json.dumps({'mode':'drone'}));after=run(.15);assert after['mode']=='drone'
 ws.send(json.dumps({'motors':[0,0],'action':'reset','keys':[]}))
 print(json.dumps(report),flush=True)
 (Path(__file__).resolve().parents[1]/'runtime'/'live-verification.json').write_text(json.dumps(report,indent=2))
