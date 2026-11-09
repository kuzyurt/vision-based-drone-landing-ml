from pathlib import Path
p=Path(__file__).parent
s=(p/'render_static_repair_v36.py').read_text().replace('from usv.quaternion import quaternion','quaternion=environment.quaternion').replace("ROOT/'static_repair_v36'","ROOT/'static_repair_v37'").replace('from landing_training.observation import camera_image','from landing_training.run_episode import camera_image\n    from types import SimpleNamespace').replace('rgb=camera_image(rgb,**effect);','rgb=camera_image(rgb,SimpleNamespace(image_brightness=effect["brightness"],image_contrast=effect["contrast"],image_blur_px=effect["blur_radius"]));')
(p/'render_static_repair_v37.py').write_text(s)
for name in ['queue','launch']:(p/f'{name}_static_repair_v37.py').write_text((p/f'{name}_static_repair_v36.py').read_text().replace('static_repair_v36','static_repair_v37'))
