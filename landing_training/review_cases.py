"""Ten explicit review flights spanning the production collection envelope."""
from dataclasses import replace

from .collect import planned_scenarios
from .config import Scenario


def diverse_review_scenarios():
    # Keep real production map/path seeds and both traversals of each world.
    # Clear pre-existing faults, then place the three production fault types
    # in three reverse flights: seven nominal and three fault configurations.
    pairs = (9, 175, 343, 473, 551)
    plan = planned_scenarios()['episodes']
    cases = []
    for family, pair in enumerate(pairs):
        for reverse in (False, True):
            original = next(item['scenario'] for item in plan
                            if item['pair'] == pair and item['scenario']['reverse'] == reverse)
            scenario = Scenario(**original)
            updates = dict(name=f'{len(cases)+1:02d}_{scenario.kind}_{"reverse" if reverse else "forward"}',
                           camera_blind_seconds=0., beacon_dropout_start_s=-1.,
                           beacon_dropout_duration_s=0., dock_unavailable_seconds=0.,
                           initial_camera_target=(family + int(reverse)) % 2 == 0)
            if family == 0 and not reverse: updates['height'] = 2.2
            if family == 4 and reverse: updates['height'] = 8.
            if reverse and family == 1:
                updates.update(beacon_dropout_start_s=3., beacon_dropout_duration_s=3.)
            if reverse and family == 2: updates['camera_blind_seconds'] = 2.5
            if reverse and family == 3: updates['dock_unavailable_seconds'] = 5.
            scenario = replace(scenario, **updates)
            scenario.validate()
            cases.append(scenario)
    return cases
