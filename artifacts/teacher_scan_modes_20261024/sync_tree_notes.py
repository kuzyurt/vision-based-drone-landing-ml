"""Synchronize the editable tree's scan notes with the implemented contract."""
import datetime
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
tree=HERE.parents[1]/'artifacts/teacher_tree/tree.json'
before=HERE/'before/tree.json'
if not before.exists():before.write_bytes(tree.read_bytes())
doc=json.loads(tree.read_text(encoding='utf-8'))
doc['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
doc['subtitle']='Two-stage scan_1 / scan_2 search was implemented on 24 October 2026 in protocol_priority_v60.py and expert_adapter_v60.py. Remaining intent/code differences (colour preference and general overhead inspection) are stated in the relevant nodes. The observable teacher uses RGB and own telemetry; the older city80 scripted demonstration is a separate harness.'
nodes={}
def walk(n):
    nodes[n['id']]=n
    for child in n.get('children',[]):walk(child)
for root in doc['roots']:walk(root)
nodes['b1_4']['long']='IMPLEMENTED 24 OCTOBER 2026. The teacher explicitly stores scan_mode=scan_1 or scan_2. In scan_1, ordinary BOAT and WEAK candidates cannot initiate an approach; likely or confirmed target evidence can still interrupt. A full pass without target evidence switches to scan_2 and advances the camera elevation band. In scan_2, the first eligible fresh ordinary boat is inspected immediately; if no plausible boat is available, a fresh weak boat proposal can be inspected. The recognizer identity threshold is unchanged. Three empty completed passes still exhaust the bounded search. Rejection of the selected wrong/unresolved inspection starts a fresh scan_1 at the first elevation with coverage cleared. A lost view by itself is not a wrong-boat label. The explicit mode is recorded as expert_scan_mode and in expert_protocol_v60; the student neural input remains unchanged.'
nodes['b1_11']['sees']='During scan_2: a fresh camera-derived BOAT or better, not rejected and not a remembered inspected view. If no plausible boat is available, an eligible fresh WEAK proposal may be inspected. Established wrong designs are excluded. Colour-based candidate preference remains an unimplemented intent.'
nodes['b1_11']['does']='Inspect the first eligible boat encountered while scan_2 runs. Fresh plausible boats take precedence over weak proposals; first encounter in scan_2 orders candidates within that pool, with evidence class and visible extent breaking ties. Likely or confirmed target evidence always preempts ordinary inspection. Never approach an off-screen queue entry.'
nodes['b1_11']['long']='IMPLEMENTED 24 OCTOBER 2026. protocol_priority_v60.py now changes candidate acceptance explicitly by scan_mode. _pick_after_survey is invoked during the active relaxed scan, uses live candidates only, filters rejection/view memory, prefers plausible boats to weak blobs and uses relaxed_first_seen for encounter order. scan_1 records ordinary candidates for audit without chasing them. Rejection returns to strict scan_1. DEVIATION FROM COLOUR INTENT: appearance is still used for identity/view association, not a target-colour ranking of unknown boats. No target appearance is fabricated before visual identity has been established.'
nodes['b1_1111']['long']='IMPLEMENTED 24 OCTOBER 2026: rejecting the selected wrong design or an unresolved inspection restarts a complete strict scan_1 at the current viewpoint, clears survey coverage and resets the elevation to 18 degrees. Track rejection memory lasts 45 s; inspected-view association also suppresses revisiting the same estimated physical view. Strong repeated wrong-design evidence is not masked by selected-class hysteresis. Losing sight alone uses bounded reorientation and does not establish wrong identity. The generic far-candidate overhead-verification maneuver described in 1.111 is still only partially present; it is not claimed implemented by this scan change.'
nodes['b1_1']['long']+='\n\nIMPLEMENTATION UPDATE 24 OCTOBER 2026: ordinary BOAT/WEAK detections are recorded but not approached in strict scan_1. Only likely/confirmed target evidence interrupts that pass. After observed coverage completes, explicit scan_2 permits fresh ordinary/weak candidate inspection. The original interrupt-extent constants remain historical; the current priority branch uses the evidence classes.'
doc['roots'][0]['long']='UPDATE 24 OCTOBER 2026: the observable teacher has explicit strict scan_1 and relaxed scan_2 state, and records the active mode. Ordinary unknown boats wait for a full strict pass. Selected wrong/unresolved inspection restarts strict scan_1. The stock landing_training/expert.py remains a truth-based setup/legacy demonstration pilot; it is not the RGB-only IdentityExpertV60 action actor.\n\n'+doc['roots'][0]['long']
tree.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
