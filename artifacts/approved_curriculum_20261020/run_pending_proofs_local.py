import transport
for script in ['test_survey_v51.py','audit_terminal_repair_v49.py']:
 try:print(transport.run(script))
 except Exception as e:print(getattr(e,'stderr',str(e)));raise
