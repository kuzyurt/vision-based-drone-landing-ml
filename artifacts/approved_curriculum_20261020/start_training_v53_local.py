import transport
try:print(transport.run('launch_training_v53b.py'))
except Exception as e:print(getattr(e,'stderr',str(e)));raise
