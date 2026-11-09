"""Exercise unchanged batching, gradients, metrics and full optimizer continuation."""
from pathlib import Path
import io
import json
import sys
import copy
import torch
from torch.utils.data import DataLoader, Dataset, Subset

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1]
sys.path.insert(0, str(RUN))
import train as original
import train_optimized as optimized
from common import config, write_json, utc
from model import SearchHead, targets


class Numbers(Dataset):
    def __len__(self): return 101
    def __getitem__(self, index): return index


class Features(Dataset):
    def __init__(self):
        self.values = torch.randn(32, 24 * 45 * 80 + 48 * 23 * 40,
                                  generator=torch.Generator().manual_seed(2468)) * .1

    def __len__(self): return len(self.values)

    def __getitem__(self, index):
        boat = dict(bbox=[250., 120., 320., 185.], boat_detection_valid=True,
                    evidence=('unknown_boat', 'target_or_similar', 'different_boat', 'target_boat')[index % 4],
                    identity_supervision_valid=index % 4 >= 2)
        return self.values[index], targets([boat])


def encode_unused_base(base, values):
    split = 24 * 45 * 80
    return values[:, :split].reshape(-1, 24, 45, 80), values[:, split:].reshape(-1, 48, 23, 40)


def main():
    torch.set_num_threads(2)
    c = config()
    report = dict(created_utc=utc())
    old = DataLoader(Numbers(), batch_size=c['batch_size'], shuffle=True, num_workers=0,
                     generator=torch.Generator().manual_seed(c['seed']))
    expected = torch.cat(list(old))
    for skip in (0, 1, 5, 12, 13):
        batches = list(optimized.make_loader(Numbers(), True, c, 'cpu', skip))
        got = torch.cat(batches) if batches else torch.tensor([], dtype=torch.int64)
        if not torch.equal(got, expected[skip * c['batch_size']:]):
            raise AssertionError(f'Shuffle/cursor differs at batch {skip}')
    report['same_shuffle_and_resume_order'] = True
    data = Features()
    base = torch.nn.Identity()
    # The encoder is unchanged in the optimization. Isolate the actual spatial
    # head/AdamW update math on fixed full-sized feature maps for this check.
    original.encode_maps = encode_unused_base
    optimized.encode_maps = encode_unused_base
    torch.manual_seed(c['seed'])
    head = SearchHead()
    initial = copy.deepcopy(head.state_dict())
    opt = torch.optim.AdamW(head.parameters(), lr=c['learning_rate'], weight_decay=c['weight_decay'])
    baseline = original.epoch(head, base, optimized.make_loader(data, False, c, 'cpu'), 'cpu', opt)
    end = copy.deepcopy(head.state_dict())
    end_optimizer = copy.deepcopy(opt.state_dict())
    head.load_state_dict(initial)
    opt = torch.optim.AdamW(head.parameters(), lr=c['learning_rate'], weight_decay=c['weight_decay'])
    cursor = []
    optimized.run_epoch(head, base, optimized.make_loader(Subset(data, range(16)), False, c, 'cpu'),
                        'cpu', opt, callback=lambda p: cursor.append(copy.deepcopy(p)))
    buffer = io.BytesIO()
    torch.save(dict(model=head.state_dict(), optimizer=opt.state_dict(), cursor=cursor[-1]), buffer)
    buffer.seek(0)
    saved = torch.load(buffer, map_location='cpu', weights_only=False)
    resumed = SearchHead()
    resumed.load_state_dict(saved['model'])
    resumed_optimizer = torch.optim.AdamW(resumed.parameters(), lr=c['learning_rate'], weight_decay=c['weight_decay'])
    resumed_optimizer.load_state_dict(saved['optimizer'])
    metrics = optimized.run_epoch(resumed, base, optimized.make_loader(data, False, c, 'cpu', skip=2),
                                 'cpu', resumed_optimizer, saved['cursor'])
    parameter_difference = max(float((end[k] - resumed.state_dict()[k]).abs().max()) for k in end)
    metric_difference = max(abs(metrics[k] - baseline[k]) for k in baseline)
    resumed_state = resumed_optimizer.state_dict()
    optimizer_difference = max(float((v - resumed_state['state'][i][key]).abs().max())
        for i, state in end_optimizer['state'].items() for key, v in state.items() if torch.is_tensor(v))
    report.update(parameter_max_difference=parameter_difference, metric_max_difference=metric_difference,
                  optimizer_max_difference=optimizer_difference, actual_updates=4,
                  split_after_updates=2, batch_size=c['batch_size'], encoder_changed=False)
    if max(parameter_difference, metric_difference, optimizer_difference) != 0:
        raise AssertionError(report)
    report['passed'] = True
    write_json(HERE / 'continuation_checks.json', report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
