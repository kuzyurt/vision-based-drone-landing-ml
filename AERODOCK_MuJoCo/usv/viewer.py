"""Optional native MuJoCo viewer with the same water simulation and API."""
import time
import mujoco.viewer
from .boat_sim import BoatSim
from .world_render import WorldRenderer


def main():
    sim=BoatSim()
    sim.new_world('island')
    scenery=WorldRenderer(sim.model)
    print('Use the web server for browser controls, or import BoatSim for program control.')
    with mujoco.viewer.launch_passive(sim.model,sim.data) as viewer:
        viewer.opt.geomgroup[4]=0; viewer.opt.geomgroup[5]=0
        viewer.cam.distance=4.1; viewer.cam.elevation=-24; viewer.cam.azimuth=140
        while viewer.is_running():
            sim.model.vis.map.znear=(.0005 if viewer.cam.type==mujoco.mjtCamera.mjCAMERA_FIXED else .02)/sim.model.stat.extent
            started=time.perf_counter(); sim.step(4)
            viewer.cam.lookat[:]=sim.data.xpos[sim.boat]+[0,0,.35]
            with viewer.lock():
                viewer.user_scn.ngeom=0
                scenery.append(viewer.user_scn,sim.navigation.world,sim.data.xpos[sim.boat])
            viewer.sync()
            time.sleep(max(0,4*sim.model.opt.timestep-(time.perf_counter()-started)))


if __name__=='__main__': main()
