"""Paired GPU timings, byte equality and FP32 objective/gradient checks."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import time
import psutil

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1]
sys.path[:0] = [str(HERE), str(RUN / 'operations/training_optimization_20261025'), str(RUN)]
import torch
from torch.utils.data import DataLoader, Subset
import train_optimized as trainer
from input_pipeline import ParallelFrames as OldFrames, BufferedLoader
from fast_input import ParallelFrames as FastFrames, unpack
from cheap_loss import loss as cheap_loss
from model import load_backbone, SearchHead, loss as old_loss, encode_maps, targets
from common import config, utc, write_json, sha
from storage import pack_rgb, unpack_rgb


def main():
    if psutil.virtual_memory().available < 2_400_000_000:
        raise RuntimeError('Need 2.4 GB free after imports for isolated GPU comparison')
    c = config()
    torch.set_num_threads(2)
    m = json.loads((RUN / 'curated/manifest.json').read_text())
    entries = [e for e in m['entries'] if e['role'] == 'training']
    n = sum(e['frames'] for e in entries)
    indices = torch.randperm(n, generator=torch.Generator().manual_seed(c['seed']))[:2048].tolist()
    report = dict(created_utc=utc(), original_sources={n: sha(RUN/n) for n in ('model.py','storage.py')},
                  implementation={p.name: sha(p) for p in (HERE/'cheap_loss.py',HERE/'fast_input.py')},
                  measured_frames=len(indices), batch_size=8, precision='float32', cases=[], timings=[])
    # Exercise both supported codecs and exact RGB channels without file writes.
    import numpy as np
    for pixels in [np.zeros((360,640,3),np.uint8),np.full((360,640,3),255,np.uint8),
                   np.random.default_rng(99).integers(0,256,(360,640,3),dtype=np.uint8)]:
        codec, blob = pack_rgb(pixels)
        if not np.array_equal(unpack(codec,blob),unpack_rgb(codec,blob)):
            raise AssertionError('Codec or RGB channel order differs')
    report['raw_and_png_rgb_checks'] = True
    base = load_backbone('cuda')
    head = SearchHead().cuda()
    snapshot = torch.load(RUN/'output_optimized/latest.pt',map_location='cpu',weights_only=False)
    head.load_state_dict(snapshot['model'])
    original = OldFrames(RUN/'curated',entries,2)
    try:
        image, actual = next(iter(DataLoader(Subset(original,indices[:8]),batch_size=8)))
        fine,context = encode_maps(base,image.cuda())
        output = head(fine,context)
        empty = {k: torch.stack([targets([])[k] for _ in range(8)]) for k in actual}
        one = dict(bbox=[250,120,300,190],boat_detection_valid=True,evidence='target_boat',identity_supervision_valid=True)
        one_class = {k: torch.stack([targets([one])[k] for _ in range(8)]) for k in actual}
        for name,target in [('actual',actual),('empty',empty),('one_class',one_class)]:
            target={k:v.cuda()for k,v in target.items()}
            refs={k:v.detach().clone().requires_grad_(True)for k,v in output.items()}
            value,parts=old_loss(refs,target)
            grads=torch.autograd.grad(value,tuple(refs.values()))
            newer={k:v.detach().clone().requires_grad_(True)for k,v in output.items()}
            new_value,new_parts=cheap_loss(newer,target)
            new_grads=torch.autograd.grad(new_value,tuple(newer.values()))
            part_difference=max(float((parts[k]-new_parts[k]).abs())for k in parts)
            gradient_difference=max(float((a-b).abs().max())for a,b in zip(grads,new_grads))
            row=dict(case=name,loss_difference=float((value-new_value).abs()),part_difference=part_difference,
                     gradient_max_difference=gradient_difference)
            if max(row['loss_difference'],part_difference,gradient_difference)>1e-5:
                raise AssertionError(row)
            report['cases'].append(row)
    finally:original.close()
    reference_parameters=None
    reference_digest=None
    checked_decoders=set()
    for decoder,math in [('old','old'),('old','cheap'),('fast','old'),('fast','cheap'),('old','old')]:
        dataset=(OldFrames if decoder=='old' else FastFrames)(RUN/'curated',entries,2)
        loader=DataLoader(Subset(dataset,indices),batch_size=8,num_workers=0,pin_memory=True)
        try:
            digest=hashlib.sha256()
            if decoder not in checked_decoders:
                with BufferedLoader(loader)as batches:
                    for image,target in batches:
                        for tensor in [image,*[target[k]for k in sorted(target)]]:
                            digest.update(tensor.contiguous().numpy().tobytes())
                if reference_digest is None:reference_digest=digest.hexdigest()
                if digest.hexdigest()!=reference_digest:raise AssertionError('Actual image/target/order differs')
                checked_decoders.add(decoder)
            trainer.loss=old_loss if math=='old' else cheap_loss
            head.load_state_dict(snapshot['model'])
            opt=torch.optim.AdamW(head.parameters(),lr=c['learning_rate'],weight_decay=c['weight_decay'])
            opt.load_state_dict(copy.deepcopy(snapshot['optimizer']))
            torch.cuda.synchronize()
            began=time.perf_counter()
            metrics=trainer.run_epoch(head,base,loader,'cuda',opt)
            torch.cuda.synchronize()
            elapsed=time.perf_counter()-began
            parameters={k:v.detach().cpu().clone()for k,v in head.state_dict().items()}
            if reference_parameters is None:reference_parameters=parameters
            delta=max(float((v-reference_parameters[k]).abs().max())for k,v in parameters.items())
            row=dict(decoder=decoder,math=math,seconds=elapsed,frames_per_second=len(indices)/elapsed,
                     parameter_max_difference=delta,metrics=metrics,rgb_targets_digest=reference_digest,
                     rss_bytes=psutil.Process().memory_info().rss)
            if delta>1e-5:raise AssertionError(row)
            report['timings'].append(row)
            print(json.dumps(row),flush=True)
        finally:dataset.close()
    report['passed']=True
    write_json(HERE/'measurement.json',report)
    print(json.dumps(dict(passed=True,checks=report['cases'])),flush=True)


if __name__=='__main__':main()
