"""Small Windows OpenGL probe. No scene, flight, or training is started."""
from pathlib import Path
import ctypes, datetime, json, platform, subprocess, sys
import mujoco, psutil

ROOT=Path(__file__).resolve().parent
def main():
    c=mujoco.GLContext(64,64)
    try:
        c.make_current()
        lib=ctypes.WinDLL('opengl32.dll');lib.glGetString.restype=ctypes.c_char_p
        gl={k:lib.glGetString(v).decode() for k,v in [('vendor',0x1f00),('renderer',0x1f01),('version',0x1f02)]}
        model=mujoco.MjModel.from_xml_string('<mujoco><worldbody><light pos="0 0 3"/><geom type="plane" size="2 2 .1"/><body pos="0 0 .3"><freejoint/><geom type="sphere" size=".2" rgba="1 .2 .1 1"/></body></worldbody></mujoco>')
        data=mujoco.MjData(model);mujoco.mj_forward(model,data)
        with mujoco.Renderer(model,height=64,width=64) as renderer:
            renderer.update_scene(data);rgb=renderer.render()
            assert rgb.shape==(64,64,3) and rgb.max()>rgb.min()
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.free','--format=csv,noheader,nounits'],text=True).strip()
        result=dict(status='windows_native_small_opengl_render_passed',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),platform=platform.platform(),python=sys.version,mujoco=mujoco.__version__,gl=gl,nvidia=gpu,ram_available_bytes=psutil.virtual_memory().available,ram_total_bytes=psutil.virtual_memory().total,benchmark=False,physical_flight=False)
        (ROOT/'windows_probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    finally:c.free()

if __name__=='__main__':main()
