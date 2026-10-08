"""Repeatable authored wind scenarios and dissipative relative-airflow drag.

OU turbulence is a correlated velocity process, not a validated atmospheric
spectrum. Coefficients and preset magnitudes are explicit scenario choices.
"""
from dataclasses import dataclass
import math
import numpy as np

PROFILES = {
    'steady10': dict(speed=10., sigma=0., tau=1.5, gust=0., period=12., duration=3.),
    'steady2': dict(speed=2., sigma=0., tau=1.5, gust=0., period=12., duration=3.),
    'steady6': dict(speed=6., sigma=0., tau=1.5, gust=0., period=12., duration=3.),
    'steady8': dict(speed=8., sigma=0., tau=1.5, gust=0., period=12., duration=3.),
    'calm': dict(speed=0., sigma=0., tau=1.5, gust=0., period=12., duration=3.),
    'breeze': dict(speed=2., sigma=.35, tau=1.5, gust=1., period=12., duration=3.),
    'gusty': dict(speed=4., sigma=.8, tau=1., gust=2., period=9., duration=3.),
}

@dataclass
class Wind:
    profile: str = 'calm'
    seed: int = 714
    direction_deg: float = 0.
    density: float = 1.225

    def __post_init__(self): self.reset()

    def reset(self):
        self.rng = np.random.default_rng(self.seed)
        self.fluctuation = np.zeros(3)
        self.velocity = np.zeros(3)

    def step(self, simulation_time, dt):
        p = PROFILES[self.profile]
        decay = math.exp(-dt / p['tau'])
        sigma = np.array([p['sigma'], p['sigma'], p['sigma'] * .5])
        self.fluctuation = decay * self.fluctuation + sigma * math.sqrt(1 - decay**2) * self.rng.normal(size=3)
        phase = simulation_time % p['period']
        gust = p['gust'] * math.sin(math.pi * phase / p['duration'])**2 if phase < p['duration'] else 0.
        angle = math.radians(self.direction_deg)
        self.velocity = np.array([math.cos(angle), math.sin(angle), 0.]) * (p['speed'] + gust) + self.fluctuation
        return self.velocity

    def description(self):
        return {'profile': self.profile, 'seed': self.seed, 'direction_deg': self.direction_deg,
                'velocity_m_s': self.velocity.tolist(), 'density_kg_m3': self.density,
                'parameters': PROFILES[self.profile], 'method': 'uniform_mean_smooth_gust_seeded_OU',
                'provenance': 'authored_scenarios_not_measured_weather'}


def directional_drag(relative_velocity, area, density=1.225, coefficient=1.):
    """One normal-axis force; quadratic and opposite to relative airflow."""
    return -.5 * density * coefficient * area * relative_velocity * abs(relative_velocity)
