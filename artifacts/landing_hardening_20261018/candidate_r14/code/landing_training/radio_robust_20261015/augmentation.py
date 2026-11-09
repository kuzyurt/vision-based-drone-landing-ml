"""Episode-coherent radio noise, age, outages and receiver-quality metadata."""
import hashlib
import math
import numpy as np


class RadioAugmentation:
    def __init__(self, epoch, mode='mixed'):
        self.epoch = epoch
        self.mode = mode
        self.lanes = {}

    def apply(self, spec, values):
        x = values.numpy().copy()
        token = spec['token']
        if token not in self.lanes:
            seed = int.from_bytes(hashlib.sha256((spec['path'] + ':' + str(self.epoch) + ':' + self.mode).encode()).digest()[:8], 'little')
            rng = np.random.default_rng(seed)
            mode = self.mode if self.mode != 'mixed' else rng.choice(['clean', 'noisy', 'missing'], p=[.25, .35, .40])
            sigma_p = float(np.exp(rng.uniform(np.log(.5), np.log(8.)))) if mode == 'noisy' else .25
            sigma_v = float(np.exp(rng.uniform(np.log(.05), np.log(.8)))) if mode == 'noisy' else .025
            self.lanes[token] = dict(rng=rng, mode=mode, sigma_p=sigma_p, sigma_v=sigma_v,
                                     bias=rng.normal(0, sigma_p * .65, 3), drift=np.zeros(3),
                                     packet_p=np.zeros(3), packet_v=np.zeros(3), next_packet=0.,
                                     outage_until=-1., outage_at=float(rng.uniform(2., 12.)),
                                     latency=float(rng.uniform(0., 1.5)) if mode == 'noisy' else 0.)
        state = self.lanes[token]
        rng = state['rng']
        quality = np.empty((len(x), 2), dtype=np.float32)
        # Dataset decisions are 25 Hz; schedules continue across 64-frame chunks.
        for j, row in enumerate(x):
            t = (spec['start'] + j) * .04
            mode = state['mode']
            missing = mode == 'missing'
            if mode == 'noisy':
                if t >= state['outage_at']:
                    state['outage_until'] = t + float(rng.uniform(.5, 6.))
                    state['outage_at'] = state['outage_until'] + float(rng.uniform(5., 20.))
                missing |= t < state['outage_until']
                if t >= state['next_packet']:
                    state['next_packet'] = t + 1.
                    state['packet_p'] = rng.normal(0, state['sigma_p'] * .3, 3)
                    state['packet_v'] = rng.normal(0, state['sigma_v'], 3)
                    state['drift'] = .94 * state['drift'] + rng.normal(0, state['sigma_p'] * .12, 3)
                yaw = math.pi / 2 - float(row[5])
                c, s = math.cos(yaw), math.sin(yaw)
                def heading(v):
                    return np.array([c * v[0] + s * v[1], s * v[0] - c * v[1], -v[2]])
                row[11:14] -= row[14:17] * state['latency']
                row[11:14] += heading(state['bias'] + state['drift'] + state['packet_p'])
                row[14:17] += heading(state['packet_v'])
                row[19] += state['latency']
            if missing or row[19] >= 3. or row[21] < .5:
                row[11:17] = 0.
                row[21] = 0.
                row[19] = max(3.1, float(row[19]))
                quality[j] = [100., 10.]
            else:
                quality[j] = [state['sigma_p'], state['sigma_v']]
        mode = state['mode']
        if spec['end']:
            self.lanes.pop(token)
        return x, quality, mode
