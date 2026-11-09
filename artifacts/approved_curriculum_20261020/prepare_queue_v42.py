from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
def main():
    s=(ROOT/'queue_semantic_pilots.py').read_text().replace("OUT = ROOT / 'semantic_pilots'","OUT = ROOT / 'search_v42/pilots'").replace("'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only'","'EXPERT_RECOGNIZER_ROOT':'approved_curriculum_20261020/perception_training_v38'").replace("'EXPERT_RUNTIME_GATE':'expert_fix_review_20261019/v31/runtime_probe.json'","'EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v42/runtime_probe.json'").replace("str(V31/'sources')+':'+str(OLD)","str(ROOT/'search_v42/sources')+':'+str(OLD)").replace("str(ROOT/'run_semantic_collection_v32.py')","str(ROOT/'search_v42/sources/run_semantic_collection_v42.py')").replace("'approved_curriculum_20261020/semantic_pilots/'+name","'approved_curriculum_20261020/search_v42/pilots/'+name").replace('instance=230+i','instance=120+i').replace('>3000','>2200')
    s=s.replace("('learner_struggle',8.,0.,'hard','visible','tilt',True)]","('learner_struggle',12.,0.,'hard','visible',None,True),\n           ('expired_memory',8.,0.,'hard','visible','tilt',True)]")
    s=s.replace("        scenario_file=OUT/(name+'_scenario.json');", "        if name=='expired_memory':scenario.update(boat_speed=.9,wave_height=.05,camera_delay_steps=2)\n        scenario_file=OUT/(name+'_scenario.json');")
    s=s.replace("grants_training_eligibility=False)","grants_training_eligibility=False,foreground_cross_board_for_observable_pursuit=name=='learner_struggle',requires_expired_memory=name=='expired_memory',purpose_detail='Natural learner wrong-object pursuit before latched expert'if name=='learner_struggle'else'Actual post-prefix moving-boat tilt loss with expired-memory rescue'if name=='expired_memory'else name)")
    s=s.replace("scene=scene,fault=fault,dagger=dagger,instance=120+i)","scene=scene,fault=fault,dagger=dagger,prefix=dagger and name!='learner_struggle',instance=120+i)")
    s=s.replace("if job['fault']=='tilt':args+=['--tilt-fault']","if job['fault']=='tilt':args+=['--tilt-fault','--fault-duration','2.0'if name=='expired_memory'else'1.6']")
    s=s.replace("if job['dagger']:args+=['--mode','dagger','--prefix']","if job['dagger']:args+=['--mode','dagger']\n                if job['prefix']:args+=['--prefix']")
    s=s.replace("                active.remove(t)","                active.remove(t)\n                if results[-1]['result'] and results[-1]['result']['outcome'] in ['collision_failure','water_strike']:raise RuntimeError('Physical safety stop '+t['name'])")
    # Safe rolling slots: ninth job may reuse a COMPLETED slot, not MAVLink ID255.
    s=s.replace("p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,","p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,")
    s=s.replace('def main():','def run_flights():',1).replace("if __name__=='__main__':\n    main()", """if __name__=='__main__':
    assert json.loads((ROOT/'search_v42/source_test_receipt.json').read_text())['status']=='passed'
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'PYTHONPATH':str(ROOT/'search_v42/sources')+':'+str(OLD),'PYTHONDONTWRITEBYTECODE':'1'}
    with(ROOT/'search_v42/runtime_probe.log').open('x')as log:
        subprocess.run([sys.executable,str(ROOT/'search_v42/sources/probe_expert_v42.py'),'--recognizer-root','approved_curriculum_20261020/perception_training_v38','--output','approved_curriculum_20261020/search_v42/runtime_probe.json'],cwd=OLD,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    assert json.loads((ROOT/'search_v42/runtime_probe.json').read_text())['status']=='runtime_hook_probe_passed'
    run_flights()""")
    (ROOT/'queue_search_v42.py').write_text(s);compile(s,'queue_search_v42.py','exec');print('prepared_nine_purposes_not_launched',flush=True)
if __name__=='__main__':main()
