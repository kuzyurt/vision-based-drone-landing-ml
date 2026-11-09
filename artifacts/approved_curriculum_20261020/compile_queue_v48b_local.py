from pathlib import Path
R=Path(__file__).parent
s=(R/'queue_affected_v48.py').read_text().replace('else181','else 181');compile(s,'queue_affected_v48b.py','exec');(R/'queue_affected_v48b.py').write_text(s)
s=(R/'launch_affected_v48.py').read_text().replace('queue_affected_v48.py','queue_affected_v48b.py');compile(s,'launch_affected_v48b.py','exec');(R/'launch_affected_v48b.py').write_text(s)
