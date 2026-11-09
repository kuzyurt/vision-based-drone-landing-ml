"""Offline task-purpose admission; annotations never enter the actor."""
import math

EXCLUDED_PHASES = {'return_home', 'land_home', 'home_landed', 'home_land', 'return_to_home'}

def initial_view(receipt, contract):
    if not receipt['target_present'] or receipt.get('target_removed'):
        raise ValueError('Search requires a target physically present in the world')
    pixels = receipt['target_pixels']
    if contract['initial_target'] == 'outside_camera' and pixels != 0:
        raise ValueError('Search task skipped: target visible in the first delivered image')
    if contract['initial_target'] == 'visible' and pixels <= 0:
        raise ValueError('Visible-start task is actually a search task')
    lo, hi = contract['actual_initial_distance_band_m']
    if not lo <= receipt['horizontal_distance_m'] <= hi:
        raise ValueError('Distance task did not execute its declared starting range')

def discovery(trace, contract):
    if not trace:
        raise ValueError('No actual camera trace')
    if contract['initial_target'] != 'outside_camera':
        return
    first = trace[0]
    seen = next((r for r in trace[1:] if r['target_pixels'] > 0), None)
    if seen is None:
        raise ValueError('Target never discovered; configured search is not coverage')
    delta = abs(math.atan2(math.sin(seen['view_bearing_rad']-first['view_bearing_rad']),
                          math.cos(seen['view_bearing_rad']-first['view_bearing_rad'])))
    if delta < math.radians(20) or min(first['horizontal_ray_norm'], seen['horizontal_ray_norm']) < .2:
        raise ValueError('No demonstrated useful change of camera search bearing before discovery')

def purpose(result, audit, contract):
    if result['outcome'] != 'landed':
        raise ValueError('No physical target touchdown; home/diagnostic stops are not success')
    if contract.get('requires_fault') and not audit['actual_fault_rows']:
        raise ValueError('Requested disturbance did not execute')
    if contract.get('requires_metric_loss') and not contract.get('measured_metric_loss_frames', 0):
        raise ValueError('Recovery task skipped actual target loss')
    if contract.get('requires_teacher_rescue'):
        if not contract.get('measured_struggle_before_takeover') or not contract.get('measured_post_takeover_expert_rows'):
            raise ValueError('No observed struggle followed by expert intervention')
    if audit['command_history_mismatches'] or audit['unsupported_descent'] or audit['metric_wrong']:
        raise ValueError('Unsafe or inconsistent actual trajectory')

def test_regressions():
    hidden = {'initial_target':'outside_camera','actual_initial_distance_band_m':[5,20]}
    visible = {'target_present':True,'target_removed':False,'target_pixels':6131,'horizontal_distance_m':8}
    for bad in [visible, dict(visible,target_pixels=0,target_removed=True), dict(visible,target_pixels=0,horizontal_distance_m=2)]:
        try: initial_view(bad, hidden)
        except ValueError: pass
        else: raise AssertionError('Invalid search accepted')
    initial_view(dict(visible,target_pixels=0),hidden)
    discovery([{'target_pixels':0,'view_bearing_rad':0.,'horizontal_ray_norm':.8},
               {'target_pixels':20,'view_bearing_rad':1.,'horizontal_ray_norm':.8}],hidden)
    try:
        discovery([{'target_pixels':0,'view_bearing_rad':0.,'horizontal_ray_norm':.8},
                   {'target_pixels':20,'view_bearing_rad':.01,'horizontal_ray_norm':.8}],hidden)
    except ValueError: pass
    else: raise AssertionError('Immediate FOV-edge appearance counted as search')
    print('PASS: initial-visible E06 regression rejected; removed target rejected; distance mismatch rejected; real search movement required')

if __name__ == '__main__':
    test_regressions()
