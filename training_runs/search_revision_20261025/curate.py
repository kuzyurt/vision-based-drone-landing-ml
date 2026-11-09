"""Read-only historical replay and an explicit, lossless training-view manifest."""
import argparse
from collections import Counter
from dataclasses import fields
import json
import math
from pathlib import Path
import zlib

from common import HERE, REPO, sha, fingerprint, verify_sources, write_json, utc
from storage import open_read
from landing_training.privileged_teacher import SearchDecision as HistoricalSearch, BoatView
from revised_teacher import SearchDecision

ORIGINAL = HERE.parent/'search_110gb_20261025/data'
KEPT = {'001_training_beach', '057_training_city', '043_training_gravel'}
BOAT_FIELDS = {f.name for f in fields(BoatView)}


def audit():
    original = json.loads((ORIGINAL/'manifest.json').read_text())
    reports = []
    for e in original['entries']:
        if e['outcome'] == 'landed':
            continue
        old, new = HistoricalSearch(), SearchDecision()
        warning = None
        last_non_scan = -1
        target_detectable = 0
        target_max_extent = 0.
        turns = []
        last_coverage = 0.
        compared = 0
        db = open_read(ORIGINAL/e['database'])
        try:
            for i, packed in db.execute('SELECT i,row FROM frames ORDER BY i'):
                row = json.loads(zlib.decompress(packed))
                obs = row['observation']
                diag = row['supervision']['teacher_diagnostics']
                t = obs['mission']['elapsed_s']
                if diag['control_phase'] != 'scan':
                    last_non_scan = i
                if last_coverage > 350 and diag['coverage_deg'] < 5:
                    turns.append(dict(frame=i, time_s=t))
                last_coverage = diag['coverage_deg']
                boats = row['supervision']['boats']
                for v in boats:
                    if v['key'] == 'target':
                        target_detectable += bool(v['boat_detection_valid'])
                        target_max_extent = max(target_max_extent, v['extent_px'])
                if warning is not None:
                    continue
                views = [BoatView(**{k:v[k] for k in BOAT_FIELDS}) for v in boats]
                yaw = math.pi/2-obs['px4']['attitude_ned_rad'][2]
                pan, tilt = obs['gimbal_rad']
                settled = abs(pan)<math.radians(3) and abs(tilt-math.radians(6))<math.radians(3)
                old.decide(t, views, yaw+pan, settled)
                new.decide(t, views, yaw+pan, settled)
                # The pilot can reset search after decide() (view loss/stalled approach).
                # Reproduce only a reset actually recorded, then require exact state agreement.
                if diag['mode']=='scan_1' and diag['coverage_deg']==0 and old.mode!='scan_1':
                    old.restart(t, 'recorded_pilot_restart')
                    new.restart(t, 'recorded_pilot_restart')
                elif diag['selected'] is None and old.selected is not None:
                    old.restart(t, 'recorded_pilot_restart')
                    new.restart(t, 'recorded_pilot_restart')
                if (old.selected != diag['selected'] or old.confirmed != diag['confirmed'] or old.mode != diag['mode']
                    or abs(math.degrees(old.coverage)-diag['coverage_deg'])>1e-5):
                    raise ValueError(f'Historical replay diverged: {e["id"]} frame {i}')
                if (new.selected != old.selected or new.confirmed != old.confirmed
                    or abs(new.coverage-old.coverage)>1e-7):
                    raise ValueError(f'Revised replay changed decisions before warning: {e["id"]} frame {i}')
                compared += 1
                if new.warning is not None:
                    warning = dict(code=new.warning, frame=i, time_s=t,
                                   keep_frames=i+1, terminal=False,
                                   provenance='counterfactual_search_replay_not_original_warning',
                                   decisions_equivalent_through_warning=True)
        finally:
            db.close()
        report = dict(id=e['id'], retained=e['id'] in KEPT,
                      terminal_scan_start_frame=last_non_scan+1,
                      terminal_scan_start_s=(last_non_scan+1)/25,
                      full_turn_boundaries=turns, warning=warning,
                      replay_compared_frames=compared,
                      target_detectable_frames=target_detectable,
                      target_max_extent_px=target_max_extent)
        if e['id'] in KEPT and warning is None:
            raise ValueError('Retained episode has no verified exhaustion point: '+e['id'])
        reports.append(report)
        print(json.dumps(report), flush=True)
    write_json(HERE/'audit.json', dict(created_utc=utc(), original_manifest_sha256=sha(ORIGINAL/'manifest.json'), episodes=reports))


def prefix_counts(database, frames):
    counts = Counter()
    db = open_read(database)
    try:
        for (packed,) in db.execute('SELECT row FROM frames WHERE i < ? ORDER BY i', (frames,)):
            row = json.loads(zlib.decompress(packed))
            for v in row['supervision']['boats']:
                if v['identity_supervision_valid']:
                    counts['target' if v['evidence']=='target_boat' else 'different'] += 1
    finally:
        db.close()
    return dict(target=counts['target'], different=counts['different'])


def build():
    audit_receipt = json.loads((HERE/'audit.json').read_text())
    if audit_receipt['original_manifest_sha256'] != sha(ORIGINAL/'manifest.json'):
        raise ValueError('Original manifest changed after audit')
    original = json.loads((ORIGINAL/'manifest.json').read_text())
    revised_root = HERE/'data'
    revised = json.loads((revised_root/'manifest.json').read_text())
    if revised['status'] != 'complete' or len(revised['entries'])!=8:
        raise ValueError('All eight replacement recordings must finish before training')
    if any(e['outcome']!='landed' or
           (revised_root/'episodes'/e['id']/'search_warning.json').exists()
           for e in revised['entries']):
        raise ValueError('Replacement attempts need review: at least one did not land; no silent success filtering')
    audits = {e['id']:e for e in audit_receipt['episodes']}
    entries = []
    contracts = []
    for root, source, revision in [(ORIGINAL, original, False), (revised_root, revised, True)]:
        contract_path = root/'collection.json'
        contract = json.loads(contract_path.read_text())
        contracts.append(dict(path=str(contract_path.resolve()), sha256=sha(contract_path), sources=contract['sources'],
                              manifest_path=str((root/'manifest.json').resolve()), manifest_sha256=sha(root/'manifest.json')))
        for entry in source['entries']:
            if not revision and entry['outcome']!='landed' and entry['id'] not in KEPT:
                continue
            e = dict(entry, database=str((root/entry['database']).resolve()),
                     source_manifest=str((root/'manifest.json').resolve()),
                     source_frames=entry['frames'])
            if not revision and e['id'] in KEPT:
                warning = audits[e['id']]['warning']
                e.update(frames=warning['keep_frames'], curation_warning=warning,
                         identity_labels=prefix_counts(Path(e['database']), warning['keep_frames']))
            entries.append(e)
    if len(entries)!=60 or Counter(e['role'] for e in entries)!=Counter(training=48,validation=6,test=6):
        raise ValueError('Curated role split differs from approved 48/6/6')
    sources = {c['path']:c['sha256'] for c in contracts}
    manifest = dict(schema='drone.search.curated.v1', status='complete', entries=entries,
                    source_contracts=contracts, source_fingerprint=fingerprint(sources),
                    audit_sha256=sha(HERE/'audit.json'), created_utc=utc(),
                    original_recordings_modified=False, policy_warning_terminates=False)
    (HERE/'curated').mkdir(exist_ok=True)
    write_json(HERE/'curated/manifest.json', manifest)
    verify_curated(HERE/'curated')
    print(json.dumps(dict(status='curated', episodes=60, frames=sum(e['frames'] for e in entries))))


def verify_curated(root):
    m = json.loads((root/'manifest.json').read_text())
    if m['schema']!='drone.search.curated.v1' or m['status']!='complete':
        raise ValueError('Unknown/incomplete curated dataset')
    if sha(HERE/'audit.json')!=m['audit_sha256']:
        raise ValueError('Trim evidence changed')
    for c in m['source_contracts']:
        expected_roots={(ORIGINAL/'collection.json').resolve(),(HERE/'data/collection.json').resolve()}
        if Path(c['path']).resolve() not in expected_roots:
            raise ValueError('Unexpected source contract')
        if sha(Path(c['path']))!=c['sha256']:
            raise ValueError('Source collection contract changed')
        contract=json.loads(Path(c['path']).read_text())
        if contract['sources']!=c['sources']:raise ValueError('Source receipt differs')
        verify_sources(contract['sources'])
        if Path(c['manifest_path']).resolve()!=Path(c['path']).parent/'manifest.json' or sha(Path(c['manifest_path']))!=c['manifest_sha256']:
            raise ValueError('Source manifest changed')
    if m['source_fingerprint']!=fingerprint({c['path']:c['sha256'] for c in m['source_contracts']}):
        raise ValueError('Curated source identity changed')
    seen=set(); worlds=set(); labels={r:Counter() for r in ('training','validation')}
    for e in m['entries']:
        dbpath=Path(e['database']).resolve()
        if not any(dbpath.is_relative_to(p.resolve()) for p in (ORIGINAL,HERE/'data')):
            raise ValueError('Unexpected database root')
        source=json.loads(Path(e['source_manifest']).read_text())
        if str(Path(e['source_manifest']).resolve()) not in {c['manifest_path'] for c in m['source_contracts']}:
            raise ValueError('Unapproved source manifest')
        original=next(x for x in source['entries'] if x['id']==e['id'])
        if e['id'] in seen or e['scenario']['world_seed'] in worlds:
            raise ValueError('Duplicate world')
        seen.add(e['id']); worlds.add(e['scenario']['world_seed'])
        if sha(dbpath)!=original['database_sha256'] or e['database_sha256']!=original['database_sha256']:
            raise ValueError('Recording checksum differs')
        contract=json.loads((Path(e['source_manifest']).parent/'collection.json').read_text())
        plan=next(x for x in contract['plan'] if x['id']==e['id'])
        db=open_read(dbpath)
        try:
            info=json.loads(db.execute("SELECT value FROM info WHERE key='contract'").fetchone()[0])
            result=json.loads(db.execute("SELECT value FROM info WHERE key='result'").fetchone()[0])
            if (info['entry']!=plan or info['source_fingerprint']!=source['source_fingerprint']
                or info['schema']!='drone.search.fresh_episode.v1' or info['radio'] is not False
                or result['frames']!=original['frames'] or not result['condition_valid']):
                raise ValueError('Invalid recording contract')
        finally:db.close()
        for key in ('role','scenario','outcome','source_frames'):
            expected=original['frames'] if key=='source_frames' else original[key]
            if e[key]!=expected: raise ValueError('Curated scenario/role differs')
        expected_frames=original['frames']
        if e['id'] in KEPT:
            audits=json.loads((HERE/'audit.json').read_text())['episodes']
            w=next(x['warning'] for x in audits if x['id']==e['id'])
            if e['curation_warning']!=w:raise ValueError('Warning cutoff differs')
            expected_frames=w['keep_frames']
        elif original['outcome']!='landed':
            raise ValueError('Unapproved failed recording')
        if e['frames']!=expected_frames:raise ValueError('Invalid frame interval')
        expected_labels=prefix_counts(dbpath,e['frames']) if e['id'] in KEPT else result['identity_labels']
        if e['identity_labels']!=expected_labels:raise ValueError('Identity coverage differs')
        if e['role'] in labels:labels[e['role']].update(e['identity_labels'])
    if len(seen)!=60 or Counter(e['role'] for e in m['entries'])!=Counter(training=48,validation=6,test=6):
        raise ValueError('Incomplete curated split')
    for role,counts in labels.items():
        if min(counts['target'],counts['different'])<16:raise ValueError('Insufficient labels: '+role)
    return m


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','build']);args=p.parse_args()
    audit() if args.action=='audit' else build()
