from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
import sys,inspect
sys.path.insert(0,'/home/hxhshsh7gyg/vision-based-drone-landing-ml')
from landing_training import paths,environment
print(inspect.getsource(environment.DronePhysics))
"""
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
