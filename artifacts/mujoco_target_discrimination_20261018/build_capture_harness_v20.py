"""Prepare a separate annotated development harness, not a launched collector.

V19 frozen sources are never edited. Observe exact existing segmentation pass;
binding happens after final camera_image effects and before the delivery queue.
"""
from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'run_expert_review_v19.py').read_text()
s=s.replace("p.add_argument('--prefix',action='store_true');", "p.add_argument('--annotation-probe-seconds',type=float,default=0.);p.add_argument('--prefix',action='store_true');")
s=s.replace('    class ActualReviewRenderer(original_renderer):', '''    from collection_pipeline.live_capture_bridge import ObserverCaptureBridge,declared_specs
    from landing_training.expert import camera_projection
    observer_holder={}
    original_camera_effects=episode.camera_image
    def annotated_camera_effects(rgb,scenario):
        final=original_camera_effects(rgb,scenario)
        bridge=observer_holder['bridge'];env=observer_holder['env']
        bridge.bind_final_rgb(final,current_capture_s=float(env.data.time))
        return final
    episode.camera_image=annotated_camera_effects
    class ActualReviewRenderer(original_renderer):''')
s=s.replace('            self.external_rows=0;self.last_external=-math.inf', '''            self.external_rows=0;self.last_external=-math.inf''') # original follows super on same line
needle="            self.glare_frames=0;self.max_glare_pixels=0;self.total_onboard_frames=0"
replace=needle+'''
            self.observer=ObserverCaptureBridge(out,declared_specs(env.model,annotation_groups(env.model)),
                geom_object_type=int(mujoco.mjtObj.mjOBJ_GEOM),provenance=dict(
                    cached_model_sha256=cached['sha256'],scenario_arguments=vars(a),harness_source_sha256=sha(__file__),
                    image_effects=dict(brightness=scenario.image_brightness,contrast=scenario.image_contrast,blur_px=scenario.image_blur_px,delay_steps=scenario.camera_delay_steps),
                    observer_source_sha256=sha(ROOT/'collection_pipeline/live_capture_bridge.py'),
                    annotation_source_sha256=sha(ROOT/'collection_pipeline/capture_annotations.py'),
                    original_camera_effects_module=original_camera_effects.__module__,
                    annotation_only=True,does_not_drive_actions=True))
            observer_holder.update(bridge=self.observer,env=env)'''
assert needle in s;s=s.replace(needle,replace)
needle="            seg=super().onboard_image();self.onboard.disable_segmentation_rendering()"
replace=needle+'''
            observer_pad,_=camera_projection(self.env,self.env.pad_position)
            self.observer.cache_geometry(seg,capture_s=float(self.env.data.time),
                target_pad_center_px=observer_pad[0].tolist(),retained_pixels=np.ones((360,640),dtype=bool))'''
assert needle in s;s=s.replace(needle,replace)
needle='            self.external_file.close();super().close()'
assert needle in s;s=s.replace(needle,'            self.observer.close();self.external_file.close();super().close()')
needle="    assert bound['ReviewRenderer']is ActualReviewRenderer"
assert needle in s;s=s.replace(needle,needle+"\n    assert bound['camera_image']is annotated_camera_effects")
s=s.replace("            elapsed=float(m['elapsed_s'])", "            elapsed=float(m['elapsed_s'])\n            if a.annotation_probe_seconds and elapsed>=a.annotation_probe_seconds:\n                progress['diagnostic_stop_reason']='bounded_actual_annotation_contract_probe';cancel.set()")
s=s.replace("        initial_tilt_deg=35.,yaw_offset_deg=0.,duration=a.duration)", "        initial_tilt_deg=35.,yaw_offset_deg=0.,duration=a.duration,\n        image_brightness=.93 if a.annotation_probe_seconds else 1.,image_contrast=1.05 if a.annotation_probe_seconds else 1.,\n        image_blur_px=.3 if a.annotation_probe_seconds else 0.,camera_delay_steps=2 if a.annotation_probe_seconds else 0)")
(root/'run_annotated_development_v20.py').write_text(s)
compile(s,'run_annotated_development_v20.py','exec')
print('Prepared separate V20 annotation harness; not launched or training eligible')
