from pathlib import Path
R=Path(__file__).parent;s=(R/'launch_training_v53.py').read_text().replace('Background camera faces away; no task-world target hiding/removed target or failed-camera-pose copying','Camera azimuth faces away in background-intent samples, but near downward views can still contain the boat: actual segmentation labels remain positive/unknown accordingly, never inferred background from the sampler name. No task-world target hiding or failed-pose copying')
compile(s,'launch_training_v53b.py','exec');(R/'launch_training_v53b.py').write_text(s)
