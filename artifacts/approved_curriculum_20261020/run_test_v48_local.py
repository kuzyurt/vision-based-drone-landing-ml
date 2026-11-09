import transport
try:print(transport.run('test_takeover_v48b.py'))
except Exception as e:print(getattr(e,'stderr',str(e)));raise
