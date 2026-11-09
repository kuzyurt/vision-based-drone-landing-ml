import transport
code="""
from pathlib import Path
import json,psutil,signal,datetime
R=Path(__ROOT__);s=R/'terminal_handoff_v46/state.json';d=json.loads(s.read_text());assert d['status']=='waiting_actual_spare_slot','Terminal already active: do not interrupt or duplicate'
p=psutil.Process(670892);assert p.username()=='hxhshsh7gyg'and 'queue_terminal_v46.py'in ' '.join(p.cmdline());p.send_signal(signal.SIGTERM)
(R/'terminal_handoff_v46/REPLACED_BEFORE_FLIGHT.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason='Same healthy terminal case will test corrected DAgger V48; queued V46 never started native',native_flight_started=False),indent=2));print('retired idle terminal waiter670892; no native terminal flight interrupted')
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
