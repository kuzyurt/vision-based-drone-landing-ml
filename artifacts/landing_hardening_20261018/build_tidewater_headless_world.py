"""Reuse the verified scene-probe construction; preserve its prior sources."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
text=(ROOT/'tidewater_scene_probe.mjs').read_text().split('// Probe a known original-CAD pose',1)[0]
text=text.replace("'../../../tidewater_scene_v2/'","'../../../tidewater_flight_setup/'")
text+='''
const sensor=new PolicyCamera(bridge);app.camera=sensor.camera;G.exposure.value=.55;
export async function capture(state){
 bridge.state=state;if(state.geoms)bridge._applyTransforms(state.geoms);bridge._applyBodies(state.bodies);
 new E.Matrix4().set(...state.views.drone.matrix).decompose(app.camera.position,app.camera.quaternion,app.camera.scale);app.camera.updateMatrixWorld();
 GPU.beginFrame();G.time.value=state.time_s;G.dt.value=.04;app.updateSun();app.atmosphere.update(.04,app.camera.position.y);app.applyAtmosphereReadback();app.fft.update(.04);app.seaDetail.update(.04);app.caustics.update();app.underwaterLighting.update(app.camera);app.clouds.update(.04,app.camera);app.environment.update(.04);app.oceanLOD.update(app.camera);app.terrain.update(app.camera);app.rocks.update(app.camera);app.debris.update(app.camera);app.village.update(.04);app.vegetation.update(.04,app.camera);app.scene.updateMatrixWorld(true);app.shadows.render(app.scene,app.engine.meshRenderer,app.shadows.update(app.camera,G.sunDir.value));GPU.submit();await GPU.pipelinesReady();
 return sensor.capture(state);
}
export {app,map,bridge,sensor,errors,GPU,progress,assets};
'''
out=ROOT/'tidewater_headless_world.mjs';assert not out.exists();out.write_text(text)
print(out)
