from pathlib import Path
r=Path(__file__).resolve().parent
old='34845b34dc9490fddcc411738bd25b83e0d52bf4ab3564bf4aa22c931004c473';new='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
s=(r/'stage_and_probe_r14_browser.py').read_text().replace('r14','r15').replace('60eae669686d55ad84434c59dbc6f3e327c542ab054a238297bf4a6f6cbf4996','044c09b8b4b1e228b8658b9e6e0f1791847adffea226cb8d9483629e570251d2')
(r/'stage_and_probe_r15_browser.py').write_text(s)
s=(r/'queue_r14_browser_gate.py').read_text().replace('r14','r15').replace(old,new).replace('439795','443764')
a="    assert portability['frames']==1810 and portability['near_velocity_frames']>=100 and portability['stopping_limited_frames']>=12";assert a in s
s=s.replace(a,a+"\n    assert portability['terminal_budget_frames']>=100")
(r/'queue_r15_browser_gate.py').write_text(s)
s=(r/'launch_r14_browser_gate.py').read_text().replace('r14','r15');(r/'launch_r15_browser_gate.py').write_text(s)
for name in ['stage_and_probe_r15_browser.py','queue_r15_browser_gate.py','launch_r15_browser_gate.py']:compile((r/name).read_text(),name,'exec')
