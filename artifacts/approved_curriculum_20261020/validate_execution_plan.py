"""Read-only consistency check for the detailed plan; never authorizes execution."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT=Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    c=json.loads((ROOT/'EXECUTION_CHECKLIST.json').read_text())
    s=json.loads((ROOT/'EXECUTION_STATE.json').read_text())
    checks=[]
    def require(name,condition):
        assert condition,name
        checks.append(name)
    require('Originalplan byte-identisch',sha(ROOT/'PLAN.md')==c['original_plan_sha256']=='6057d01f86eafebbd54c94c43d2ecd14c0a0c4f6de7ecc435ea7ba6cb2efcb9a')
    require('Runbook ist genau die referenzierte Revision',sha(ROOT/'EXECUTION_RUNBOOK.md')==c['runbook_sha256']==s['runbook_sha256'])
    require('Zielmenge bleibt64',sum(q['total']for q in c['quotas'])==c['data']['new_target']==64)
    require('Rollen bleiben48/16',sum(q['training']for q in c['quotas'])==48 and sum(q['validation']for q in c['quotas'])==16)
    require('Quotenarithmetik',all(q['total']==q['training']+q['validation']for q in c['quotas']))
    require('Native Paare bleiben18/36',c['data']['native_test_scenarios']*2==c['data']['native_test_flights']==36)
    require('Kein neues E12/Home-Dataset',c['data']['e12_new_episodes']==0 and not c['data']['rerender_original_dataset'])
    require('Suchziel vorhanden und nicht ausgeblendet',c['data']['search_target_present']and not c['data']['hide_world_target']and c['data']['search_initial_view']=='outside_camera')
    require('Keine Tidewater Trainings-/Auswahldaten',not c['data']['tidewater_training']and not c['data']['tidewater_model_selection'])
    require('Ressourcen und Timer unverändert',c['resources']['workers']==8 and c['resources']['ram_reserve_gib']==4 and c['resources']['vram_reserve_gib']==1 and c['resources']['heartbeat_minutes']==30 and c['resources']['local_backup_interval_seconds']==300)
    start=datetime.datetime.fromisoformat(c['time']['origin_utc'])
    deadline=datetime.datetime.fromisoformat(c['time']['hard_deadline_utc'])
    require('17h-Grenze nicht verschoben',(deadline-start).total_seconds()==17*3600)
    require('Export vor Deadline',datetime.datetime.fromisoformat(c['time']['normal_local_delivery_utc'])<datetime.datetime.fromisoformat(c['time']['last_notional_export_utc'])<deadline)
    require('Fehler können ehrlichen Export nicht blockieren',c['failure_exit']['from_any_phase']and c['failure_exit']['missing_phases_must_not_be_marked_passed']and c['failure_exit']['no_fabricated_checkpoint_if_training_not_run'])
    seen=set()
    for p in c['phases']:
        require('Phasenabhängigkeiten '+p['id'],set(p['depends_on'])<=seen and p['id']not in seen)
        seen.add(p['id'])
    if not s['detailed_plan_approved']:
        require('Wartender Plan ohne erfundene Freigabe',c['approval_required']and s['phase']=='AWAITING_PLAN_APPROVAL'and not(ROOT/'PLAN_APPROVAL.json').exists())
    else:
        approval=json.loads((ROOT/'PLAN_APPROVAL.json').read_text())
        require('Referenz auf echte menschliche Freigabe erforderlich',approval.get('authority_origin')=='human_message'and bool(approval.get('trusted_message_reference'))and approval.get('approved')is True and approval.get('original_plan_sha256')==c['original_plan_sha256']and approval.get('runbook_sha256')==c['runbook_sha256']and approval.get('checklist_sha256')==sha(ROOT/'EXECUTION_CHECKLIST.json'))
    require('Benötigte bereits vorhandene Hilfen existieren',all((ROOT/f).is_file()for f in ['PLAN.md','STATUS.md','transport.py','backup_watcher.py','snapshot_policy.py','semantic_contract.py','run_semantic_collection_v32.py','queue_semantic_pilots.py','launch_semantic_pilots.py']))
    report={'schema':'approved.curriculum.plan.consistency.v1','status':'passed',
            'checks':checks,'this_check_grants_execution_authority':False,
            'approval_state':'approved_receipt_present'if s['detailed_plan_approved']else'pending',
            'scope':'Document consistency only; does not certify missing executors, data, masks, training, or model quality.'}
    (ROOT/'PLAN_CONSISTENCY_RECEIPT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':'passed','checks':len(checks),'this_check_grants_execution_authority':False,'original_plan_unchanged':True,'approval_state':report['approval_state']}))

if __name__=='__main__':
    main()
