from pathlib import Path
R=Path(__file__).parent;p=R/'encode_rescue_v48.py';s=p.read_text().replace('<=29.or55.','<=29. or 55.');compile(s,str(p),'exec');p.write_text(s)
