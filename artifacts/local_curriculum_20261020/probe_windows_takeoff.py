"""Twenty simulated seconds of real PX4 sensor/actuator lockstep, no teacher dataset."""
import local_paths
from pathlib import Path
import datetime,hashlib,json,time,traceback
import mujoco,numpy as np,psutil
from landing_training import environment
from landing_training.config import Scenario
from landing_training.expert import Expert
from windows_px4 import WindowsPX4

def main():
    out=local_paths.ROOT/'px4_takeoff_probe_v1';out.mkdir(exist_ok=False)
    environment.compile_scene=lambda *a,**k:mujoco.MjModel.from_binary_path(str(local_paths.REPO/'landing_training/build/combined_1000us.mjb'))
    from mission_setup import VerticalLaunchEnvironment
    s=Scenario(name='windows_px4_compatibility',seed=440020,world_seed=401,path_seed=501,distance=8.,height=1.2,duration=20.,wave_height=0.)
    VerticalLaunchEnvironment.audit_directory=out
    env=VerticalLaunchEnvironment(s);env.boat.navigation.manual();px4=WindowsPX4(env,out/'px4',instance=700);expert=Expert(env)
    start=time.monotonic();source_stamps=set();rows=[]
    try:
        px4.start()
        with(out/'actual_lockstep.jsonl').open('x')as f:
            for tick in range(500):
                if psutil.virtual_memory().available<1.5*1024**3:raise MemoryError('Windows free RAM below1.5GiB; stop own probe')
                own=px4.observation()
                if own.get('valid'):source_stamps.add(own['position_source_boot_ms'])
                if tick>125 and tick%50==0 and len(source_stamps)>=5 and not px4.armed:px4.arm_offboard()
                px4.send_action(expert.prepare(px4));px4.advance()
                if tick%25==0:
                    row=dict(sim_s=float(env.data.time),own=px4.observation(),actual_height_m=float(env.drone.position[2]),last_sensor_usec=px4.last_sensor_time_usec,actuator_usec=px4.actuator_time_usec,startup_complete=px4.startup_complete)
                    f.write(json.dumps(row)+'\n');f.flush();rows.append(row)
                    (out/'state.json').write_text(json.dumps(dict(status='actual_sensor_actuator_probe',**row,wall_s=time.monotonic()-start),indent=2));print(json.dumps(row),flush=True)
        peak=max(r['actual_height_m'] for r in rows)
        checks=dict(actual_PX4_own_estimator=any(r['own'].get('valid')for r in rows),distinct_observed_positions=len(source_stamps)>=5,real_arm=any(r['own'].get('armed')for r in rows),actual_airborne=px4.was_airborne,physical_height_increased=peak>env.data.mocap_pos[env.launch_mid,2]+.6,lockstep_maintained=all(r['actuator_usec']>=r['last_sensor_usec']-4000 for r in rows if r['own'].get('armed')))
        result=dict(status='passed'if all(checks.values())else'failed',checks=checks,wall_s=time.monotonic()-start,simulated_s=float(env.data.time),peak_height_m=peak,physical_landing_test=False,teacher_episode=False,training_eligible=False,linux_used=False,PX4_backend='pinned real PX4 WebAssembly Windows Node; native Linux numerical parity not claimed')
        (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
        assert all(checks.values()),checks
    except BaseException as e:
        (out/'error.json').write_text(json.dumps(dict(error=repr(e),traceback=traceback.format_exc()),indent=2));raise
    finally:px4.close()

if __name__=='__main__':main()
