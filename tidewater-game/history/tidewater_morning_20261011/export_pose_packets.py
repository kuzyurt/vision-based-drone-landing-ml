from landing_training.morning_flight import *
import gzip
out=Path('/tmp/tidewater_policy_1521_packets.jsonl.gz')
e=bridge.TidewaterEnvironment(scenario())
ids=bridge.vehicle_geoms(e)
state_dir=OUTPUT/'flight/states'
files=sorted(state_dir.glob('*.npz'))
with gzip.open(out,'wt',encoding='utf-8',compresslevel=6) as f:
 for i,path in enumerate(files):
  z=np.load(path);e.data.time=float(z['time']);e.data.qpos[:]=z['qpos'];e.data.qvel[:]=z['qvel'];e.data.mocap_pos[:]=z['mocap_pos'];e.data.mocap_quat[:]=z['mocap_quat'];e.wind.velocity[:]=z['wind'];e.boat.navigation.progress=float(z['progress']);mujoco.mj_forward(e.model,e.data)
  angles=math.radians(e.boat.wave_direction)+np.array([0.,.38,-.52,.9]);omega=2*np.pi/(e.boat.wave_period*np.array([1.,.72,1.31,.52]));k=omega**2/e.boat.gravity;amp=e.boat.wave_height*.5*np.array([.55,.23,.15,.07])
  view=frame_camera(e);view.update(width=1920,height=1080)
  packet={'time_s':float(e.data.time),'time_of_day':15+21/60,'wind_speed':float(np.linalg.norm(e.wind.velocity)),'waves':np.column_stack((k*np.cos(angles),-k*np.sin(angles),amp,e.boat.wave_phases-float(e.data.time)*omega)).tolist(),'geoms':[[gid,bridge.matrix(e.data.geom_xpos[gid],e.data.geom_xmat[gid])] for gid in ids],'hull_pose':bridge.matrix(e.data.geom_xpos[e.model.geom('hull_contact').id],e.data.geom_xmat[e.model.geom('hull_contact').id]),'views':[view]}
  f.write(json.dumps(packet,separators=(',',':'))+'\n')
print(json.dumps({'frames':len(files),'packet_file':str(out),'bytes':out.stat().st_size,'mesh_count':len(ids)}))
