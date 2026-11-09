from pathlib import Path
R=Path(__file__).parent;s=(R/'test_takeover_v48.py').read_text().replace('confirmed,False,None,None,None','confirmed,confirmed,None,None,None');assert s!=(R/'test_takeover_v48.py').read_text();(R/'test_takeover_v48b.py').write_text(s)
