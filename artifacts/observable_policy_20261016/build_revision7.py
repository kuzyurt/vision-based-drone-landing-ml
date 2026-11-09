"""Use the full observed edge cloud for reverse registration distances."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    b=ROOT/'bundle_spatial_r7';shutil.copytree(ROOT/'bundle_spatial_r5',b);package=b/'code/landing_training/radio_robust_20261015'
    shutil.copy2(ROOT/'bundle_spatial_r6/code/landing_training/radio_robust_20261015/controller/observable_acquisition.py',package/'controller/observable_acquisition.py')
    p=package/'marker_kernel.cpp';s=p.read_text()
    edits={
      'std::array<int,MAX_Q> nearestOrder{};':'std::vector<int> nearestOrder;\nstd::vector<Point> nearestObserved;',
      'observed[a][axis]<observed[b][axis]':'nearestObserved[a][axis]<nearestObserved[b][axis]',
      'const Point&p=observed[nearestOrder[mid]]':'const Point&p=nearestObserved[nearestOrder[mid]]',
      'nearestSquared(q,nearest,0,count)':'nearestSquared(q,nearest,0,int(nearestObserved.size()))',
      'for(int i=0;i<count;i++)nearestOrder[i]=i;buildNearest(0,count);':'''// Keep the original representative forward residual samples. Reverse
 // template-to-observation distances use EVERY observed border pixel, avoiding
 // a scale-dependent distance floor from the sparse240-point forward subset.
 nearestObserved.clear();
 for(const Point& pixel:border){Point q;if(rayCoordinates(pixel[0],pixel[1],q))nearestObserved.push_back(q);}
 nearestOrder.resize(nearestObserved.size());
 for(int i=0;i<int(nearestObserved.size());i++)nearestOrder[i]=i;
 buildNearest(0,int(nearestObserved.size()));'''}
    for old,new in edits.items():assert s.count(old)==1,old;s=s.replace(old,new)
    s=s.replace('// No pixel/sample is dropped.','// Full reverse edge cloud; forward sampling and acceptance gates retained.')
    p.write_text(s)
    subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC',str(p),'-o',str(package/'marker_kernel.so')],check=True,cwd=package)
    c=json.loads((b/'policy.json').read_text());c.update(runtime_revision='dense_reverse_edge_r7_20261017',closed_loop_evaluated=False,closed_loop_results={})
    c['controller_changes']+=['reject above-horizon coarse targets before locking camera or authorizing movement',
        'reverse template-to-edge distances query full observed border cloud rather than sparse240 forward samples; solver, residual threshold, precision/recall and physical landing gates unchanged']
    c['file_hashes']={str(p.relative_to(b)):sha(p) for p in (b/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for f in ['pose.pt','acquisition.pt','spatial_acquisition.pt']:c['file_hashes'][f]=sha(b/f)
    (b/'policy.json').write_text(json.dumps(c,indent=2));print(json.dumps(dict(bundle=str(b),pose_weights_unchanged=sha(b/'pose.pt')==sha(ROOT/'bundle_spatial_r3/pose.pt'))))
if __name__=='__main__':main()
