"""Initialize annotation identities on manually appended MuJoCo render geoms.

MuJoCo3.14 Renderer.render indexes its segid table directly. mjv_initGeom does
not initialize the object's identity fields for appended scenery. These fields
are not RGB material, geometry, physics or task-input channels.
"""
import mujoco


def install(rendering):
    if getattr(rendering,'_discrimination_segmentation_ids',False):return
    original=rendering.append_scenery
    def append(world_renderer,scene,world,position,renderer=None):
        first=scene.ngeom
        original(world_renderer,scene,world,position,renderer=renderer)
        for g in scene.geoms[first:scene.ngeom]:
            g.segid=-1;g.objid=-1;g.objtype=int(mujoco.mjtObj.mjOBJ_UNKNOWN)
    rendering.append_scenery=append
    rendering._discrimination_segmentation_ids=True


def identify_water(scene,env):
    g=scene.geoms[scene.ngeom-1]
    g.segid=scene.ngeom-1;g.objtype=int(mujoco.mjtObj.mjOBJ_GEOM)
    g.objid=env.model.geom('water_surface').id
