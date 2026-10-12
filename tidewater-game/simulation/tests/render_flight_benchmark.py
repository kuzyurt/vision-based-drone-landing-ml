"""Render/export the recorded benchmark; no browser or live scene required."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path(__file__).resolve().parents[2]/'benchmarks/flight-parity'
report=json.loads((out/'report.json').read_text())
a=np.load(out/'px4-reference.npz')['samples']
b=np.load(out/'px4-tidewater.npz')['samples']
initial_a=np.load(out/'px4-reference.npz')['initial']
initial_b=np.load(out/'px4-tidewater.npz')['initial']
t=a[:,0]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
    'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18})
fig,axes=plt.subplots(3,2,figsize=(14,10),sharex=True,layout='constrained')
colors=['#2563a6','#e67e22']
def pair(ax,values,title,unit):
    for data,value,color,label,style in zip((a,b),values,colors,('Original MuJoCo + PX4','Tidewater + same PX4'),('-','--')):
        ax.plot(t,value,color=color,label=label,linewidth=1.5,linestyle=style)
    ax.set_title(title,loc='left',fontweight='bold');ax.set_ylabel(unit)
pair(axes[0,0],(a[:,3],b[:,3]),'Altitude','m')
pair(axes[0,1],(np.linalg.norm(a[:,8:10],axis=1),np.linalg.norm(b[:,8:10],axis=1)),'Horizontal speed: acceleration and braking','m/s')
def angles(data):
    w,x,y,z=data[:,4:8].T
    return np.degrees(np.arcsin(np.clip(2*(w*y-z*x),-1,1))),np.degrees(np.unwrap(np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z))))
pitch_a,yaw_a=angles(a);pitch_b,yaw_b=angles(b)
pair(axes[1,0],(pitch_a,pitch_b),'Pitch','degrees')
pair(axes[1,1],(yaw_a,yaw_b),'Yaw','degrees')
pair(axes[2,0],(np.mean(np.abs(a[:,14:18]),axis=1)*60/(2*np.pi),np.mean(np.abs(b[:,14:18]),axis=1)*60/(2*np.pi)),'Mean rotor speed','RPM')
axes[2,1].plot(t,np.linalg.norm((a[:,1:4]-initial_a[1:4])-(b[:,1:4]-initial_b[1:4]),axis=1)*1000,color='#9333a1')
axes[2,1].set_title('Displacement response difference from each hover start',loc='left',fontweight='bold');axes[2,1].set_ylabel('mm')
cursor=0.
for name,duration in [('forward',2),('brake',3),('right',2),('yaw',2),('climb',2),('descend',2),('camera',1),('hover',3)]:
    for ax in axes.flat:
        ax.axvline(cursor,color='#94a3b8',alpha=.3,linewidth=.8)
        if name in ('brake','yaw','descend','hover'):ax.axvspan(cursor,cursor+duration,color='#64748b',alpha=.045)
    axes[0,1].text(cursor+duration/2,.95,name,transform=axes[0,1].get_xaxis_transform(),ha='center',va='top',fontsize=7,rotation=65,
        bbox={'facecolor':'white','edgecolor':'none','alpha':.75,'pad':1})
    cursor+=duration
axes[0,0].legend(loc='upper left',fontsize=9)
for ax in axes[-1]:ax.set_xlabel('Simulation time after settled hover (s)')
fig.suptitle('Flight parity benchmark · original X500 CAD and PX4 v1.16\n1 ms MuJoCo integration · same keyboard sequence · independent PX4 runs',fontsize=16,fontweight='bold')
fig.savefig(out/'flight-comparison.png',dpi=160)
fig.savefig(out/'flight-comparison.pdf')
columns=['time_s','x_m','y_m','z_m','qw','qx','qy','qz','vx_m_s','vy_m_s','vz_m_s','wx_rad_s','wy_rad_s','wz_rad_s']
columns += [f'rotor_{i}_rad_s' for i in range(1,5)]+[f'command_{i}' for i in range(1,5)]+['pan_rad','tilt_rad','battery_v','current_a','charge_ah']
for label,data in [('reference',a),('tidewater',b)]:np.savetxt(out/(label+'.csv'),data,delimiter=',',header=','.join(columns),comments='',fmt='%.12g')
m=report['closed_loop'];repeat=report.get('reference_repeatability',{})
lines=['# X500 flight parity benchmark','',f"Reference model: **{report['model']}** (the local file names it X500 V2).",
    '', '## Method','',
    '- Original `Simulation.physics` and `Simulation.setpoints` are executed directly from the existing simulator source.',
    '- Reference rendering meshes/textures are omitted; collision shapes, inertias, joints, sensors and actuators are retained.',
    '- Tidewater uses its own combined boat/drone model; the benchmark adds the same launch floor and places the boat away from the flight path.',
    '- Body mass/inertia, joint axes/ranges/damping/armature, collision parameters, rotor inertia and solver settings are checked before running.',
    '- Motor replay exercises throttle steps, differential thrust, camera motion and seeded gusts at 1 kHz.',
    '- Independent PX4 processes exercise takeoff/hover, forward acceleration, braking, strafe, yaw, climb, descent and camera control.',
    '- Firmware binary SHA-256 and original parameter/source hashes are recorded in `report.json`.',
    '- A repeated original PX4 run measures reference repeatability. Runs are aligned in time at settled hover; displacement is measured from each actual hover start. Absolute-world errors and initial hover offsets are also retained in the JSON report.',
    '', '## Results','', '| Metric | Tidewater versus original | Original repeat |','|---|---:|---:|']
for key,label,scale in [('position_max_m','Maximum position difference (mm)',1000),('velocity_max_m_s','Maximum velocity difference (m/s)',1),('attitude_max_deg','Maximum attitude difference (degrees)',1),('camera_max_deg','Maximum camera difference (degrees)',1),('rotor_max_rpm','Maximum rotor difference (RPM)',1)]:
    lines.append(f"| {label} | {m[key]*scale:.6g} | {repeat.get(key,float('nan'))*scale:.6g} |")
if 'handling' in report:
    lines += ['', '## Handling measurements', '', '| Metric | Original | Tidewater |', '|---|---:|---:|']
    for key,label in [('arming_delay_sim_s','Arming delay (s)'),('takeoff_to_hover_sim_s','Takeoff to settled hover (s)'),
        ('forward_90_percent_rise_s','Time to 0.9 m/s (s)'),('forward_end_speed_m_s','Forward speed after 2 s (m/s)'),
        ('brake_settle_s','Braking to below 0.1 m/s (s)'),('brake_distance_m','Braking distance (m)'),
        ('climb_height_change_m','Climb over 2 s (m)'),('descend_height_change_m','Descent over 2 s (m)')]:
        values=[report['handling'][run].get(key) for run in ('reference','tidewater')]
        formatted=['not reached' if value is None else f'{value:.6g}' for value in values]
        lines.append(f'| {label} | {formatted[0]} | {formatted[1]} |')
    lines += ['', 'Times in this table are simulation seconds. Live game pacing is recorded separately in [live-game-verification.json](live-game-verification.json).']
lines += ['', '![Flight response comparison](flight-comparison.png)','',
    'Calm motor replay agrees to floating-point precision. Gust replay has its own measured error in the report; no percentage score hides individual metrics.',
    '', 'The flight laws, physics parameters and firmware are shared. Independent PX4 startup/estimator timing can produce different trajectories, so these runs are not claimed to be bitwise identical.',
    'This benchmark compares simulator behavior, not real-world X500 calibration. It does not measure browser FPS or radio hardware.',
    '', '## Reproduce','', '```bash',
    'OPENBLAS_NUM_THREADS=1 MUJOCO_GL=disable NUMBA_CACHE_DIR=simulation/runtime/native-cache-linux \\',
    '  ~/.cache/tidewater-game/python/bin/python simulation/tests/benchmark_flight.py', '```',
    '', 'Run from `tidewater-game` in WSL after preparing the collision model. Then run `simulation/tests/render_flight_benchmark.py` with Python/Matplotlib.',
    'The NPZ files preserve full-precision samples; CSV files are provided for analysis. The PDF figure is suitable for export.']
(out/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(out/'README.md')
