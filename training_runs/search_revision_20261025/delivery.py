"""Privileged scenario qualification; never supplies actor observations/actions."""
import math
import numpy as np
import mujoco


def visibility_probe(env, renderer, oracle):
    saved = env.data.qpos[env.drone.camera_qpos].copy()
    count = 0
    maximum = 0.
    try:
        for pan in np.linspace(-math.pi, math.pi, 72, endpoint=False):
            env.data.qpos[env.drone.camera_qpos] = [pan, math.radians(6)]
            mujoco.mj_forward(env.model, env.data)
            renderer.onboard_image()
            renderer.onboard.enable_segmentation_rendering()
            try: views = oracle.observe(renderer.onboard.render().copy())
            finally: renderer.onboard.disable_segmentation_rendering()
            for view in views:
                if view.key == 'target':
                    count += int(view.detectable)
                    maximum = max(maximum, view.extent_px)
    finally:
        env.data.qpos[env.drone.camera_qpos] = saved
        mujoco.mj_forward(env.model, env.data)
    return dict(headings=72, detectable_headings=count,
                maximum_target_extent_px=maximum, actor_input=False,
                initial_camera_restored=True, physics_steps=0)
