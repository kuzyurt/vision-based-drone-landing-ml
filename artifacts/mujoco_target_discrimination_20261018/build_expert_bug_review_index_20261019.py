"""Verify delivered media and publish explicit expert coverage / quarantine index."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent;MEDIA=ROOT/'vm_results'
def main():
    new=json.loads((MEDIA/'manifest.json').read_text())
    for r in new:
        p=MEDIA/r['video'];assert p.stat().st_size==r['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    cases=[
      ('E01','Basic search, approach and touchdown','v18_actual_expert_review','Expert throughout; full flight accelerated.'),
      ('E02','Hard distractors and landing','v15_hard_actual_expert_review','Expert throughout; full flight accelerated. Previously shown.'),
      ('E03','Yaw disturbance and resynchronization','v16_actual_expert_review','Expert throughout except injected camera fault; no actual target-loss recovery in this run.'),
      ('E04','Near-deck target loss, climb and reacquisition','v17_actual_expert_review','Expert throughout except injected tilt fault. Full flight accelerated.'),
      ('E04a','Same recovery, normal-speed detail','v17_recovery_normal_speed','Same E04 flight, task55–78; 1x. Does not include touchdown.'),
      ('E05','Failed acquisition; intended recovery never triggered','v15_recovery_actual_expert_review','Expert throughout. Diagnostic stop: no confirmed identity and no injected recovery fault.'),
      ('E06','Earlier failed scan / candidate inspection','v13c_actual_expert_review','Legacy expert-mode review; older rows lack explicit ownership tags. Diagnostic stop, not completed landing.'),
      ('E07','Earlier identity acquired but metric landing pose missing','v13b_actual_expert_review','Legacy expert-mode review; older rows lack explicit ownership tags. Diagnostic stop.'),
      ('E08','Earlier basic landing before later search revisions','v14_actual_expert_review','Legacy expert-mode review; older rows lack explicit ownership tags. Historical comparison, not a fix.'),
    ]
    lines=['# Rejected expert demonstrations — review set','',
      '**All recordings below are rejected for training reuse. No fixes are claimed.**',
      'The original recordings, failed revisions and evaluation sources remain unchanged. Root quarantine also rejects the experimental perception derivatives and checkpoint; it cannot undo their earlier training.',
      '', '## What this set covers', '',
      'This gathers the available teacher demonstrations and expert-only portions of mixed flights. It does not prove all requested curriculum situations were demonstrated. Accelerated videos show the full recorded flight; normal-speed detail is identified separately. Use the ID and task/video timestamp when reporting a bug.',
      '', 'Recent candidate-only evaluations use the same observable expert-derived controller internally, but remain candidate tests; they are not separate successful teacher rescues. They are excluded from this teacher gallery. The four exact held-out failures have no separately recorded teacher counterpart.', '']
    verified=[]
    for ident,title,stem,note in cases:
        receipt=json.loads((MEDIA/(stem+'_video_receipt.json')).read_text());p=MEDIA/(stem+'.mp4')
        assert p.stat().st_size==receipt['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==receipt['video_sha256']
        lines += ['## '+ident+' — '+title,'',note+f' Playback {receipt["playback_speed"]:.2f}x.', '',f'![{ident} {title}]({p.as_posix()})','']
        verified.append(dict(id=ident,video=p.name,sha256=receipt['video_sha256']))
    titles=[('E09','Late terminal takeover: already on deck, not a rescue'),('E10','Failed expert rescue after learner tilt-loss struggle — V19'),('E11','Failed expert rescue after learner tilt-loss struggle — V21'),('E12','No target: search followed by physical home landing')]
    for (ident,title),r in zip(titles,new):
        p=MEDIA/r['video'];lines += ['## '+ident+' — '+title,'',
          f'Only the uninterrupted expert-controlled segment is shown; zero learner frames. Task {r["first_task_s"]:.2f}–{r["last_task_s"]:.2f}s, playback {r["playback_speed"]:.2f}x. '+('A learner flew earlier; this is not an expert-only whole flight.'if r['selection']=='post_takeover'else'Expert controls the entire flight.'),
          '',f'![{ident} {title}]({p.as_posix()})',''];verified.append(dict(id=ident,**r))
    lines += ['## Missing or insufficient demonstrated coverage','',
      '- Systematic isolated glare rejection, red-boat early rejection, ambiguous nearest-object inspection, rejection and over-object rescan are not separately established by the hard-scene landing.',
      '- Original boat with hidden marker versus wrong boat with copied cross: no complete dedicated teacher demonstration set.',
      '- Robust overland-to-water transition, long-range search across all five maps and all weather/speed conditions: not demonstrated by these previews.',
      '- Genuine learner struggle followed by a consistently successful expert rescue: not established. E10/E11 show failures; E09 is a false educational takeover. E04 is expert-only disturbance recovery, not learner rescue.',
      '- Continuous camera orientation during descent remains a reported bug, not fixed or approved.',
      '', 'No new trajectories will be generated from this rejected teacher merely to fill these gaps. Review and repair the existing behavior before generating replacement demonstrations.',
      '', '## Complete recording inventory','',
      'All 59 recordings are listed in TRAINING_QUARANTINE_20261019.json with ownership, phases and source trace hashes. Short annotation/throughput probes, repeated development flights, candidate tests and original-policy baselines are not additional successful teacher situations.',
      '', 'The six current admission/cache/training entry points have fail-closed quarantine guards. Frozen historical sources and originals were not rewritten. Future consumers must honor the quarantine; sidecars are not a universal filesystem access restriction.','']
    (ROOT/'EXPERT_BUG_REVIEW_20261019.md').write_text('\n'.join(lines),encoding='utf-8')
    (ROOT/'expert_bug_review_media_verified_20261019.json').write_text(json.dumps(dict(verified=verified,training_allowed=False),indent=2))
    print(json.dumps(dict(verified_videos=len(verified),index=str(ROOT/'EXPERT_BUG_REVIEW_20261019.md'))))
if __name__=='__main__':main()
