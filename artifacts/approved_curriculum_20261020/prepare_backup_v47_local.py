from pathlib import Path
R=Path(__file__).parent;s=(R/'backup_selected_models_now.py').read_text().replace("['perception_training_v38','spatial_training_v3']","['perception_training_v47']").replace("DEST/'VERIFIED.json'","DEST/'VERIFIED_V47.json'")
(R/'backup_selected_models_v47_now.py').write_text(s)
