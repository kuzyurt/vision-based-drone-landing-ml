"""Strict outcomes and complete denominators; independently testable offline."""
import math
from statistics import mean


def finite_number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def strict_landing(row):
    return (row.get('status') == 'completed' and row.get('outcome') == 'landed'
            and row.get('disarmed') is True and finite_number(row.get('stable_disarmed_contact_s'))
            and row['stable_disarmed_contact_s'] >= 2.
            and row.get('collision') is False and row.get('water_strike') is False
            and row.get('assistance_frames') == 0 and row.get('wrong_target_contacts') == 0)


def case_credit(case, row):
    if not row or row.get('status') != 'completed' or row.get('condition_valid') is not True:
        return None
    if not finite_number(row.get('mission_time_s')) or not 0 <= row['mission_time_s'] <= case['speed_deadline_s']+.08:
        return None
    landed = strict_landing(row)
    if case['category'] == 'acquisition':
        # A pad fit on a decoy is never a successful acquisition. Confirmation is
        # checked against scoring-only ground truth, continuously for 0.4 s.
        acquired = row.get('verified_acquisition_s')
        task = float(finite_number(acquired) and 0 <= acquired <= min(case['acquisition_deadline_s'],row['mission_time_s'])
                     and row.get('false_acquisition_events', 0) == 0
                     and row.get('collision') is False and row.get('water_strike') is False)
    else:
        task = float(landed)
    speed = 0.
    if landed:
        elapsed = row['mission_time_s']
        reference, deadline = case['speed_reference_s'], case['speed_deadline_s']
        speed = max(0., min(1., (deadline - elapsed) / (deadline - reference)))
    return dict(task=task, speed=speed, landed=landed)


def wilson(successes, count):
    if not count:
        return None
    z = 1.96
    p = successes / count
    den = 1 + z*z/count
    centre = (p + z*z/(2*count)) / den
    radius = z * math.sqrt(p*(1-p)/count + z*z/(4*count*count)) / den
    return [max(0., centre-radius), min(1., centre+radius)]


def aggregate(plan, rows):
    expected = {c['id']: c for c in plan['cases']}
    by_id = {}
    for row in rows:
        identifier = row['case_id']
        if identifier not in expected:
            raise ValueError('Result is not a member of this suite: ' + identifier)
        if identifier in by_id:
            raise ValueError('Duplicate result for ' + identifier)
        by_id[identifier] = row
    groups = {}
    for category in plan['categories']:
        source = [c for c in plan['cases'] if c['category'] == category] if category != 'speed' else plan['cases']
        credits = [(c, case_credit(c, by_id.get(c['id']))) for c in source]
        valid = [(c, credit) for c, credit in credits if credit is not None]
        values = [credit['speed' if category == 'speed' else 'task'] for _, credit in valid]
        complete = len(valid) == len(source)
        if category == 'speed' and values:
            buckets = [[v['speed'] for c, v in valid if c['category'] == group]
                       for group in plan['speed_source_categories']]
            score = mean(mean(b) for b in buckets if b) * 100
        else:
            score = mean(values) * 100 if values else None
        successes = sum(v['landed'] for _, v in valid)
        groups[category] = dict(score=score, complete=complete, planned=len(source), valid=len(valid),
                                recorded=sum(c['id'] in by_id for c in source),
                                landings=successes, landing_rate_ci95=wilson(successes, len(valid)))
    complete = all(v['complete'] for v in groups.values())
    total = sum(groups[k]['score'] * v['weight'] for k, v in plan['categories'].items()) if complete else None
    return dict(total=total, complete=complete, categories=groups,
                valid_cases=groups['speed']['valid'], planned_cases=len(expected),
                invalid_cases=sum(case_credit(expected[r['case_id']],r) is None for r in rows))
