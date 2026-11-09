from pathlib import Path
ROOT=Path(__file__).resolve().parent
dest=ROOT/'mission_helpers_v2';dest.mkdir(exist_ok=False)
text=(ROOT/'mission_helpers/mission_safety.py').read_text()
needle="            completing=diagnostics.get('control_phase') in ['touchdown_commit','confirm','disarmed'] or p.get('landed')"
assert text.count(needle)==1
text=text.replace(needle,"            recovery_live=(diagnostics.get('recovery_active',False) and now<=float(diagnostics.get('recovery_deadline_s',-1)) and remaining>15.)\n            if recovery_live:search_over=False\n            recovery_failed=bool(diagnostics.get('recovery_exhausted',False))\n"+needle)
needle='            if search_over or reserve_low or camera_failed:'
assert text.count(needle)==1;text=text.replace(needle,'            if search_over or reserve_low or camera_failed or recovery_failed:')
needle="self.trigger='camera_unavailable' if camera_failed else 'return_time_reserve' if reserve_low else 'search_timeout'"
assert text.count(needle)==1;text=text.replace(needle,"self.trigger='camera_unavailable' if camera_failed else 'bounded_recovery_exhausted' if recovery_failed else 'return_time_reserve' if reserve_low else 'search_timeout'")
(dest/'mission_safety.py').write_text(text)
print('Mission V2 honors only finite active recovery and retains camera/reserve failsafes.')
