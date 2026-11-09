import math
import numpy as np
def numeric_observation(row):
    """Fixed 32-value deployable contract. Privileged fields are inaccessible."""
    observation = row['observation']
    p = observation['px4']
    b = observation['beacon']
    yaw = p.get('attitude_ned_rad', [0, 0, 0])[2]
    east, north, up = p.get('velocity_enu_m_s', [0, 0, 0])
    velocity = [math.cos(yaw) * north + math.sin(yaw) * east, -math.sin(yaw) * north + math.cos(yaw) * east, -up]
    values = [*velocity, *p.get('attitude_ned_rad', [0, 0, 0]), *p.get('angular_rate_frd_rad_s', [0, 0, 0]), *observation['gimbal_rad'], *b.get('relative_heading_m', [0, 0, 0]), *b.get('velocity_heading_m_s', [0, 0, 0]), p.get('position_age_s', 10), p.get('attitude_age_s', 10), b['age_s'], float(p['valid']), float(b['valid']), float(b['dock_ready']), observation['image_age_s'], *observation['previous_executed_action'], observation['decision_dt_s'], float(observation['image_valid'])]
    if len(values) != 32:
        raise AssertionError('Observation schema changed')
    return np.array(values, dtype=np.float32)
