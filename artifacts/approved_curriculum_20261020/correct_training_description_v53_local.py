from pathlib import Path
R=Path(__file__).parent;s=(R/'train_static_verifier_v53.py').read_text().replace('zero false assertions in BOTH groups','zero false assertions in ALL THREE groups').replace('new-close false reduced when present','new-negative false reduced when present');compile(s,'train_static_verifier_v53b.py','exec');(R/'train_static_verifier_v53b.py').write_text(s)
