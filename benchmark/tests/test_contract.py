import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from benchmark.common import fingerprint, sha, write
from benchmark.scoring import aggregate, case_credit, strict_landing, wilson
from benchmark.suite import build_plan


def success(case, seconds=80.):
    return dict(case_id=case['id'], status='completed', condition_valid=True, outcome='landed',
                disarmed=True, stable_disarmed_contact_s=2.01, collision=False, water_strike=False,
                assistance_frames=0, wrong_target_contacts=0, verified_acquisition_s=30.,
                false_acquisition_events=0, mission_time_s=seconds)


class DesignTests(unittest.TestCase):
    def test_frozen_design_is_complete_and_deterministic(self):
        plan = build_plan()
        self.assertEqual(plan, build_plan())
        self.assertEqual(len(plan['cases']), 20)
        self.assertEqual(plan['max_flights_per_policy'], 20)
        self.assertEqual({key:sum(c['category']==key for c in plan['cases']) for key in plan['categories']},
                         {'landing':4,'wind':2,'waves':2,'acquisition':10,'combined':2,'speed':0})
        self.assertAlmostEqual(sum(c['weight'] for c in plan['categories'].values()), 1.)
        unsigned = {k:v for k,v in plan.items() if k != 'plan_sha256'}
        self.assertEqual(fingerprint(unsigned), plan['plan_sha256'])

    def test_compact_acquisition_covers_range_radio_and_scene_distractors(self):
        cases = [c for c in build_plan()['cases'] if c['category'] == 'acquisition']
        self.assertEqual({c['scenario']['distance'] for c in cases}, {30.,100.})
        self.assertEqual({c['radio'] for c in cases}, {'on','off'})
        self.assertEqual({c['decoys'] for c in cases}, {True,False})
        self.assertEqual(len(cases),10)
        self.assertTrue(all(c['initial_view']=='outside' for c in cases))

    def test_far_radio_decoy_comparisons_share_environment_and_start(self):
        for repeat in (0,1):
            cases=[c for c in build_plan()['cases'] if c['category']=='acquisition'
                   and c['scenario']['distance']==100. and c['repeat']==repeat]
            for key in ['world_seed','path_seed','world_rotation_deg','reverse','seed','bearing_deg']:
                self.assertEqual(len({c['scenario'][key] for c in cases}),1)

    def test_fast_boat_case_explicitly_uses_extended_speed_envelope(self):
        for c in build_plan()['cases']:
            if c['scenario']['boat_speed']>1.:
                self.assertTrue(c['scenario']['stress_test'])


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_plan()
        self.case = self.plan['cases'][0]

    def test_no_runs_does_not_mean_zero(self):
        result = aggregate(self.plan, [])
        self.assertIsNone(result['total'])
        self.assertEqual(result['valid_cases'],0)
        self.assertTrue(all(g['score'] is None for g in result['categories'].values()))

    def test_complete_failure_suite_is_real_zero(self):
        rows = [dict(success(c), outcome='timeout', verified_acquisition_s=None) for c in self.plan['cases']]
        self.assertEqual(aggregate(self.plan, rows)['total'],0.)

    def test_complete_success_suite_stays_bounded(self):
        rows = [success(c,c['speed_reference_s']) for c in self.plan['cases']]
        result = aggregate(self.plan,rows)
        self.assertTrue(result['complete'])
        self.assertAlmostEqual(result['total'],100.)

    def test_partial_suite_has_no_rankable_total(self):
        result = aggregate(self.plan,[success(self.case)])
        self.assertIsNone(result['total'])
        self.assertFalse(result['complete'])

    def test_contact_armed_home_or_assistance_is_not_landing(self):
        for fields in [dict(disarmed=False),dict(outcome='home_landed'),dict(assistance_frames=1),
                       dict(stable_disarmed_contact_s=1.99),dict(wrong_target_contacts=1),
                       dict(collision=True),dict(water_strike=True)]:
            row = dict(success(self.case),**fields)
            self.assertFalse(strict_landing(row))
            self.assertEqual(case_credit(self.case,row)['speed'],0.)

    def test_wrong_or_late_acquisition_has_no_credit(self):
        case = next(c for c in self.plan['cases'] if c['category']=='acquisition')
        for fields in [dict(verified_acquisition_s=120.1),dict(verified_acquisition_s=None),
                       dict(false_acquisition_events=1),dict(collision=True)]:
            self.assertEqual(case_credit(case,dict(success(case),**fields))['task'],0.)

    def test_infrastructure_and_misconfigured_motion_are_unscored(self):
        self.assertIsNone(case_credit(self.case,dict(success(self.case),condition_valid=False)))
        self.assertIsNone(case_credit(self.case,dict(success(self.case),status='infrastructure_error')))

    def test_malformed_time_cannot_create_a_score(self):
        for value in [float('nan'),float('inf'),-1.,300.,'80',None]:
            self.assertIsNone(case_credit(self.case,dict(success(self.case),mission_time_s=value)))

    def test_policy_error_is_a_failure_not_missing_infrastructure(self):
        case=next(c for c in self.plan['cases'] if c['category']=='landing')
        credit=case_credit(case,dict(success(case),outcome='policy_error'))
        self.assertEqual(credit['task'],0.)
        self.assertEqual(credit['speed'],0.)

    def test_duplicate_or_foreign_case_rejected(self):
        row=success(self.case)
        with self.assertRaises(ValueError):aggregate(self.plan,[row,row])
        with self.assertRaises(ValueError):aggregate(self.plan,[dict(row,case_id='foreign')])

    def test_speed_macro_average_does_not_overweight_search(self):
        rows=[]
        for case in self.plan['cases']:
            # 100% speed in acquisition, zero elsewhere: one of five equally
            # weighted source categories, independent of its case count.
            rows.append(success(case,case['speed_reference_s'] if case['category']=='acquisition' else 240.))
        self.assertAlmostEqual(aggregate(self.plan,rows)['categories']['speed']['score'],20.)

    def test_confidence_interval_not_overconfident_for_small_samples(self):
        low,high=wilson(3,3)
        self.assertLess(low,.5)
        self.assertAlmostEqual(high,1.)


class ReportReceiptTests(unittest.TestCase):
    def test_changed_trace_is_excluded(self):
        from benchmark.report import build_report
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            plan=build_plan()
            write(root/'environments/suite.json',plan)
            write(root/'environments/runtime.json',{'fixture':'unit-test-only'})
            policy=dict(id='test-policy',identity_sha256='abc')
            write(root/'models/inventory.json',dict(policies=[policy]))
            context=dict(plan_sha256=plan['plan_sha256'],runtime_sha256=sha(root/'environments/runtime.json'))
            case=plan['cases'][0]
            write(root/'runs/unit/run.json',dict(id='unit',created_utc='test',context=context,policies=[policy['id']],cases=[case['id']]))
            result=root/'runs/unit'/policy['id']/case['id']/'result.json'
            write(result,dict(success(case),context=context,policy_id=policy['id'],policy_identity_sha256='abc',trace_sha256='changed'))
            (result.parent/'steps.jsonl').write_text('changed trace')
            with patch('benchmark.report.ROOT',root):payload=build_report()
            self.assertEqual(len(payload['rejected']),1)
            self.assertEqual(payload['runs'][0]['scores'][policy['id']]['valid_cases'],0)


class LegacyGuardCompatibilityTests(unittest.TestCase):
    def test_explicit_confirmation_is_preserved_without_mutating_actor_diagnostics(self):
        from benchmark.actors import LegacyMetricAdapter
        from types import SimpleNamespace
        d=dict(metric_valid=True,metric_confirmed=False)
        wrapped=LegacyMetricAdapter(SimpleNamespace(act=lambda *a:([0]*6,d)))
        _,result=wrapped.act(None,{})
        self.assertFalse(result['metric_confirmed'])
        self.assertEqual(d,dict(metric_valid=True,metric_confirmed=False))

    def test_accepted_legacy_fit_prevents_false_search_timeout_in_common_guard(self):
        import importlib.util
        from benchmark.common import REPO
        from benchmark.actors import LegacyMetricAdapter
        from types import SimpleNamespace
        source=REPO/'artifacts/landing_hardening_20261018/r15_native_completion_verified/r15_fresh_E60/mission_sources/mission_safety.py'
        spec=importlib.util.spec_from_file_location('guard_contract_fixture',source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        original=dict(metric_valid=True,estimated_clearance_m=.4,estimated_lateral_error_m=.01,control_phase='descend')
        actor=SimpleNamespace(reset=lambda:None,act=lambda *a:([0]*6,original))
        safe=module.MissionSafety(LegacyMetricAdapter(actor),[.1]*6)
        obs=dict(image_valid=True,image_delivery_time_s=130.,image_capture_time_s=130.,gimbal_rad=[0.,1.5],
            px4=dict(valid=True,position_enu_m=[0.,0.,2.],attitude_ned_rad=[0.,0.,0.],armed=True,landed=False),
            mission=dict(home_position_enu_m=[0.,0.,0.],home_authorized_for_landing=True,
                elapsed_s=130.,budget_s=240.,search_timeout_s=120.,home_source='own telemetry'))
        _,diagnostics=safe.act(None,obs)
        self.assertFalse(diagnostics['mission_fallback_active'])
        self.assertTrue(diagnostics['metric_confirmed'])
        self.assertNotIn('metric_confirmed',original)


if __name__=='__main__':
    unittest.main()
