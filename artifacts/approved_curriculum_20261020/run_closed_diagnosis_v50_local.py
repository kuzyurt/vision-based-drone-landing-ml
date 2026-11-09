import transport
try:print(transport.run('diagnose_closed_public_v50.py'))
except Exception as e:print(getattr(e,'stderr',str(e)));raise
