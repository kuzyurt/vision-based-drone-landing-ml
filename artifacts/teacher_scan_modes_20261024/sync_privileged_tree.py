"""Update the decision-tree explanation for the simulator-assisted teacher."""
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
path=HERE.parents[1]/'artifacts/teacher_tree/tree.json'
backup=HERE/'before_privileged_tree.json'
if not backup.exists(): backup.write_bytes(path.read_bytes())
tree=json.loads(path.read_text(encoding='utf-8'))
tree['subtitle']='Current no-radio teacher: landing_training/privileged_teacher.py. Simulator labels and exact ranges are allowed; actions are gated by actual camera visibility and identifiability. No neural detector or boat-correctness percentage.'
tree['updated_utc']=datetime.now(timezone.utc).isoformat()
rules={
'root':('Student sensors: RGB 640x360, own PX4 telemetry and camera encoders. Teacher additionally has simulator truth for annotation and control after visibility gates.',
        'Send six bounded commands: forward/right/down velocity, yaw rate, camera pan/tilt rates. Only an actually visible boat may become a search destination.',
        'The active review entry is run_privileged_review.py. VisibleBoatOracle reads exact visible pixels from a second segmentation render of the same camera. SearchDecision receives only visible BoatViews. PrivilegedTeacher controls search and calls SmoothLandingExpert only for an identified target with visible pad, or on physical contact. Hidden identity labels never rank unknown boats. The previous IdentityExpertV60 neural teacher remains a historical experiment. This change implements the no-radio branch; the existing radio branch is documented separately.'),
'b1':('No radio: beacon valid=False, age_s=3.1. Camera, own state, and teacher-only visible annotations are available.',
       'Scan, select a visibly supported candidate, inspect, reject false boats, and land on the identified target.',
       'Ground truth is allowed for labeling, range and precise control. Segmentation visibility prevents hidden boats from affecting selection. Student observations contain no boat truth, segmentation, instance ids, ranges or identities.'),
'b1_1':('No identifiable target or similar boat in recognition range. Far visible boats remain unknown.',
        'Hold survey altitude. Center camera pan, set 6 degree downward tilt, then yaw at 0.35 rad/s through a complete circle. Keep checking the higher-priority mid/close branches.',
        'Coverage accumulates actual unwrapped camera heading only while pan and tilt are within 3 degrees of their goals. Back-and-forth rotation does not count as a full circle. Ordinary unknown boats cannot interrupt scan_1.'),
'b1_1_1':('Exact visible pixels, bbox, category and horizontal range. Identity labels are masked when visually unsupported.',
          'Use not_resolved, unknown_boat, target_or_similar, different_boat, or target_boat as teaching evidence. These are rules, not neural probabilities.',
          'Detection requires at least 24 visible pixels and 8 pixel extent. Recognition additionally requires 80 pixels and 24 pixel extent. Above 35m all classes are unknown. At 27..35m, target and similar false boats are indistinguishable; dissimilar boats may be rejected. At <=27m a similar false boat may be rejected. Target identification also requires the actual pad visible with at least 6 pixels in its smaller projected dimension. Decisions require at least 0.16s sustained visibility. These thresholds are explicit teaching assumptions, not a measured guarantee of student recognition accuracy.'),
'b1_1_2':('The selected boat leaves the actual camera image.',
          'Stop translation/descent. Point toward its last observed location for at most 3s; then restart scan_1 without declaring it false.',
          'No new hidden boat position is used for reacquisition. Stationary decoys use instance-associated rejection memory for this episode; this is not a tested moving-boat reidentification system.'),
'b1_2':('A resolved visible target or similar false boat at 27..35m, or a closer target whose marker is not yet resolved.',
        'Approach it at survey height, keep it in view, and inspect. A confirmed target preempts it.',
        'True range selects the band; target identity and similar-false identity are deliberately merged until close. Limit horizontal speed to 2m/s. Unresolved inspection restarts scan_1 after 12s without 0.5m range progress or 90s overall.'),
'b1_3':('At <=27m, enough boat pixels and a visible target marker at least 6 pixels across its smaller dimension, sustained for 0.16s.',
        'Confirm and prioritize this target, then approach, match deck motion and descend through the stock Expert.',
        'No probability head is required. Teacher truth generates categorical labels, with identity_supervision_valid masking frames that cannot support identity. Descent additionally requires a current visible marker.'),
'b1_4':('A full scan_1 completed without selecting mid/close evidence.',
        'Enter scan_2 and accept the first currently visible eligible boat.',
        'The current implementation does not chase a remembered off-screen boat when the sweep ends. It continues turning until an eligible boat is live, with image order breaking simultaneous first-sighting ties.'),
'b1_11':('An actual visible generic boat passes the detection gate, even above 35m.',
         'Approach the first eligible boat without ranking by hidden identity or hidden target distance.',
         'Already rejected boats are excluded. Mid-band plausible evidence and close confirmed targets retain priority.'),
'b1_111':('The selected boat is farther than 35m and cannot yet be identified.',
          'Close at survey height while keeping the camera pointed at it. Use the same mid/close recognition gates as range falls.',
          'There is no mandatory 75-degree overflight in this version. Identification can finish earlier if close visual evidence is sufficient; otherwise the camera becomes progressively more downward-looking as the drone closes. This is an explicit difference from the older tree intent.'),
'b1_1111':('Close resolved inspection identifies a false boat or the visible target marker.',
           'False boat: remember rejection and restart scan_1. Target: run landing sequence.',
           'A single distant glimpse or simulator category alone cannot determine this verdict.'),
'b1_112':('A mid-band target-or-similar boat becomes visible during scan_2 or an unknown approach.',
          'Inspect using branch 1.2. Do not hop between equally plausible selected candidates.',
          'The same 35m and 27m range gates and image-resolution requirements apply in both scan modes.'),
'b1_113':('A close target passes the actual marker visibility and resolution gate.',
          'Preempt the current inspection and enter landing.',
          'Identical confirmation rule to branch 1.3; no learned confidence score is involved.'),
'b1_5':('Confirmed target and currently visible pad, or physical touchdown already happened.',
        'Align heading early, approach with bounded acceleration, settle for 0.6s, then descend continuously through SmoothLandingExpert.',
        'Choose the front/back heading branch as soon as identity is confirmed. Optical camera aiming uses actual camera and joint geometry with damping near vertical, avoiding atan2 pan spin. Tight descent-entry thresholds and wider exit thresholds prevent mode chatter; descent speed changes continuously with height. Exact pad geometry is allowed behind the visibility gate. Marker occlusion arrests descent; reacquisition uses the last observed location. Physical contact and PX4/disarm checks are unchanged.'),
'b1_6':('Own estimator validity/age, action limits and physical terminal state.',
        'Zero translation/yaw on invalid state or state older than 0.25s; stop sending commands on collision, water strike or landing.',
        'Bounds: horizontal speed 2m/s, down velocity -1..0.7m/s, yaw +/-0.5rad/s, pan +/-50deg/s, tilt +/-40deg/s. Contact-based disarm is termination only. This review does not use the historical neural MissionSafety return-home wrapper.'),
}
def update(node):
    key=node.get('id')
    if key in rules:
        node['sees'],node['does'],node['long']=rules[key]
        node['phases']=[]
    if key=='b1_111': node['title']='1.111 · Far candidate (>35m): approach until visual inspection is possible'
    if key=='b1_1111': node['title']='1.1111 · Inspection verdict: target → land · false boat → back to 360scan_1'
    for child in node.get('children',[]): update(child)
for root in tree['roots']: update(root)
path.write_text(json.dumps(tree,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
