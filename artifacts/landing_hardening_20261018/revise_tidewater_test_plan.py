"""Separate observed initial-visibility difficulty from the speed question."""
from pathlib import Path
import datetime,hashlib,json,shutil
r=Path(__file__).resolve().parent
old=r/'tidewater_speed_20261018T152500Z'
out=r/'tidewater_limits_20261018T153300Z';out.mkdir()
shutil.copy2(old/'tidewater_speed_suite.mjs',out/'tidewater_speed_suite.mjs')
oldplan=json.loads((old/'plan.json').read_text())
base=dict(speed=.6,radio=False,timeOfDay=15.35,cloudCoverage=.62,wind=[0,0],height=4,backDistance=8,panDeg=0,tiltDeg=20)
cases=[]
for speed in [.6,1.4,2.2,2.8]:
    for radio in[False,True]:cases.append(dict(base,id='visible_'+str(speed).replace('.','p')+('_radio'if radio else'_visual'),group='visible_speed_ladder',speed=speed,radio=radio))
for case in oldplan['cases']:
    if case['group']=='harder_start':cases.append(case)
plan=dict(schema='tidewater.current_policy_exploratory_speed_test.v2',run=out.name,
    created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    candidate_policy_sha256=oldplan['candidate_policy_sha256'],
    driver_sha256=oldplan['driver_sha256'],workers=2,cases=cases,
    predecessor=old.name,
    reason='The actual first onboard RGB at8m/1.5m/35deg contains only water. Preserve the started difficult acquisition cases; do not spend remaining speed-ladder flights confounding search failure with motion capability. The dedicated ladder starts at4m with20deg tilt; verify actual RGB. No policy/physics modification.',
    followup='One midpoint between highest qualified success and next failed tested speed, then one changed-start confirmation of highest successful speed per radio mode; at most4followups.',
    speed_qualification='Physical stable disarmed boat landing plus final2.1s mean boat speed>=85%requested and minimum>=75%requested; always report actual speed. A slow-corner landing is a boat success but not proof of the requested speed.',
    current_policy_unchanged=True,no_training=True)
(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(run=out.name,initial_cases=len(cases),followups_max=4),indent=2))
