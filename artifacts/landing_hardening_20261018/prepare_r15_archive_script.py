from pathlib import Path
r=Path(__file__).resolve().parent
s=(r/'archive_r14_controller.py').read_text().replace('r14','r15').replace('34845b34dc9490fddcc411738bd25b83e0d52bf4ab3564bf4aa22c931004c473','5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35')
(r/'archive_r15_controller.py').write_text(s)
