"""One-off city scenario: target 80 m out, six labelled false boats, real search.

The production Scenario envelope caps distance at 60 m.  This subclass keeps
every other validation rule and extends only the review distance, so the run is
still a real Environment, not a mocked one.

The target boat is held stationary (boat_speed = 0) so the 80 m start geometry
and the six static decoys stay valid for the whole episode instead of drifting
out of frame as the boat runs its route.

The aircraft starts broadside to the target with the camera looking along the
first search leg, so the target is outside the first frame.  The search legs
sweep the seaward sector and only turn in towards the boat at the end; see
``SEARCH_LEGS`` for the geometry and ``build_scene.py`` for the clearance
checks that keep the lanes and the final corridor free of decoys.
"""
from dataclasses import dataclass, replace

from landing_training.config import Scenario


@dataclass(frozen=True)
class Scenario80(Scenario):
    def validate(self):
        if not 0 <= float(self.distance) <= 80:
            raise ValueError("Extended distance envelope exceeded")
        # Validate every other field with the production 60 m cap.
        Scenario.validate(replace(self, distance=min(float(self.distance), 60.0)))


MAP = dict(
    name="city80_search",
    kind="city",
    world_seed=401,
    path_seed=501,
    seed=701,
    distance=80.0,
    bearing_deg=270.0,
    height=6.0,
    boat_speed=0.0,
    wave_height=0.02,
    wave_period=3.0,
    wind_profile="calm",
    # The gimbal starts on the first search leg, not on the target.  The
    # takeoff preparation must not aim the camera at the boat either.
    initial_camera_target=False,
    initial_pan_deg=0.0,
    initial_tilt_deg=18.0,
    duration=140.0,
)

# (along, lateral) metres in the approach frame: +along points from the target
# pad toward the 80 m airborne start, +lateral is 90 deg left of that axis.
#
# The decoys sit along the two search legs and the turn-in, not on the clear
# final corridor at lateral 0, so the aircraft meets false boats first and the
# target last.
DECOYS = [
    dict(label="false_boat_similar",   along=72.0, lateral=16.0, colour=(0.88, 0.88, 0.84), yaw=0.35, mast=True,  scale=(1.00, 1.00, 1.00)),
    dict(label="false_boat_similar",   along=63.0, lateral=27.0, colour=(0.82, 0.83, 0.80), yaw=1.20, mast=False, scale=(0.92, 0.96, 1.00)),
    dict(label="false_boat_unsimilar", along=52.0, lateral=32.0, colour=(0.70, 0.05, 0.03), yaw=0.80, mast=False, scale=(1.05, 0.90, 0.95)),
    dict(label="false_boat_similar",   along=39.0, lateral=25.0, colour=(0.90, 0.89, 0.85), yaw=2.10, mast=True,  scale=(1.08, 1.00, 1.00)),
    dict(label="false_boat_unsimilar", along=29.0, lateral=11.0, colour=(0.04, 0.10, 0.20), yaw=1.70, mast=True,  scale=(0.95, 1.10, 1.00)),
    dict(label="false_boat_unsimilar", along=18.0, lateral=21.0, colour=(0.64, 0.32, 0.05), yaw=2.60, mast=False, scale=(1.15, 1.00, 1.05)),
]

# Search legs in the same (along, lateral) frame.  Nothing here is target
# state: the mission only declares the seaward sector that has to be searched.
SEARCH_LEGS = [
    dict(name="search_sweep_1", along=80.0, lateral=40.0),
    dict(name="search_sweep_2", along=50.0, lateral=50.0),
]
SEARCH_START = dict(along=80.0, lateral=0.0)
