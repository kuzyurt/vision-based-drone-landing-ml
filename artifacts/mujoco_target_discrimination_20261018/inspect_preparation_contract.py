from pathlib import Path
import sys,inspect
root=Path(__file__).resolve().parent;base=root.parents[2];sys.path.insert(0,str(base))
from landing_training.expert import Expert
from landing_training.run_episode import run_episode,NativePX4
print(inspect.getsource(Expert.prepare));print(inspect.getsource(NativePX4.observation))
s=inspect.getsource(run_episode).splitlines()
for i,line in enumerate(s):
 if'prepare'in line or'armed'in line or'preparation'in line:
  print('\n'.join(s[max(0,i-3):min(len(s),i+4)]))
