from pathlib import Path
r=Path(__file__).resolve().parent
s=(r/'queue_r12_browser_gate.py').read_text().replace('r12','r14').replace('433276','439795').replace('cfae2590824b63296a370e199b7e832a7eee3c34ae0bdd3dc4c5f5d2515deea4','34845b34dc9490fddcc411738bd25b83e0d52bf4ab3564bf4aa22c931004c473')
start=s.index("    save(dict(status='running_one_production_browser_stack_flight'))")
end=s.index('\nexcept BaseException',start)
block='''    moving=json.loads((ROOT/'vm_r14_moving_driver_receipt.json').read_text())
    assert sha(app/moving['file'])==moving['sha256']
    assert portability['frames']==1810 and portability['near_velocity_frames']>=100 and portability['stopping_limited_frames']>=12
    game_results=[]
    for label,script,folder in [
        ('unpowered_boat','tidewater_landing_r14_browser.mjs','tidewater_stationary_r14_browser'),
        ('moving_boat_0p6','tidewater_landing_r14_moving_browser.mjs','tidewater_moving_r14_browser')]:
        assert not(ROOT/folder).exists(),folder
        command[-1]=str(app/'test'/script)
        save(dict(status='running_bounded_actual_production_stack_flight',scenario=label,completed=game_results))
        with(ROOT/(folder+'.log')).open('x')as log:
            subprocess.run(command,cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=360,check=True)
        report=json.loads((ROOT/folder/'report.json').read_text())
        assert report['physical_assessment']['landed']and not report['gpu_errors'],report
        assert report['policy']['policy_sha256']=='34845b34dc9490fddcc411738bd25b83e0d52bf4ab3564bf4aa22c931004c473'
        if label=='moving_boat_0p6':
            motion=report['boat_motion_assessment']
            assert motion['displacement_m']>5 and .3<motion['mean_speed_m_s']<1.,motion
        game_results.append(dict(scenario=label,flight_seconds=report['flight_seconds'],physical_assessment=report['physical_assessment'],boat_motion=report.get('boat_motion_assessment')))
    save(dict(status='native_and_two_actual_game_flights_passed_requires_export_review',game_results=game_results,qualification_export_still_required=True))'''
s=s[:start]+block+s[end:]
out=r/'queue_r14_browser_gate.py';assert not out.exists();compile(s,str(out),'exec');out.write_text(s)
