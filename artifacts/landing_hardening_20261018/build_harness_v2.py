"""New harness revision: explicit static-clearance prior and OWN gimbal command."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
text=(ROOT/'evaluate_hardening.py').read_text()
def replace(old,new):
 global text
 assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
replace('    class PreparationOnly(Original):',"    original_px4=getattr(episode,'_hardening_original_px4',episode.NativePX4)\n    episode._hardening_original_px4=original_px4\n    class CommandTelemetryPX4(original_px4):\n        def observation(self):\n            value=super().observation()\n            value['gimbal_commanded_rad']=[float(self.env.drone.pan),float(self.env.drone.tilt)]\n            value['gimbal_command_source']='own_last_issued_setpoint'\n            return value\n    episode.NativePX4=CommandTelemetryPX4\n    static_prior=None\n    class PreparationOnly(Original):\n        def __init__(self,env):\n            nonlocal static_prior\n            super().__init__(env)\n            from clearance_provider import StaticRecoveryPrior\n            static_prior=StaticRecoveryPrior(env,job['directory'])")
replace("            fault.before(rgb,observation)","            observation['mission']['recovery_clearance']=static_prior.certify(observation['px4'])\n            fault.before(rgb,observation)")
replace("    source_files={'evaluate_development.py':Path(__file__).resolve(),'faults.py':ROOT/'faults.py','mission_safety.py':ROOT/'mission_helpers/mission_safety.py','mission_integration.py':ROOT/'mission_helpers/mission_integration.py','mission_setup.py':ROOT/'mission_helpers/mission_setup.py'}", "    source_files={'evaluate_development.py':Path(__file__).resolve(),'faults.py':ROOT/'faults.py','clearance_provider.py':ROOT/'clearance_provider.py','recovery_clearance.py':ROOT/'recovery_clearance.py','mission_safety.py':ROOT/'mission_helpers_v2/mission_safety.py','mission_integration.py':ROOT/'mission_helpers/mission_integration.py','mission_setup.py':ROOT/'mission_helpers/mission_setup.py'}")
replace("    sh=source_fingerprint();rh=source_fingerprint(runtime_only=True)","    sh=source_fingerprint();rh=source_fingerprint(runtime_only=True)\n    candidate_config=json.loads((bundle/'policy.json').read_text())\n    for name,expected in candidate_config['file_hashes'].items():\n        if '__pycache__' not in name and sha(bundle/name)!=expected:raise RuntimeError('Changed frozen candidate source: '+name)")
(ROOT/'evaluate_hardening_v2.py').write_text(text)
print('Created separate V2 evaluator; original pilot harness remains frozen.')
