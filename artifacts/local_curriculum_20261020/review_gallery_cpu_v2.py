"""Generate a local-only index of closed actual review videos."""
import html,json
from pathlib import Path
R=Path(__file__).resolve().parent;B=R/'review_batch_v1'

def update(state):
    plan=json.loads((B/'cpu_continuation_plan_v2.json').read_text());complete={r['name']:r for r in state.get('completed',[])};active={r['name']for r in state.get('active',[])};cards=[]
    for j in plan['jobs']:
        name=j['name'];r=complete.get(name);status='running'if name in active else'pending';video=''
        if r:
            status='purpose passed — human review pending'if(r.get('audit')or{}).get('status')=='passed'else'FAILED / missing purpose coverage — excluded'
            if r.get('video_ready'):video=f'<video controls preload="metadata" src="{name}/review.mp4"></video>'
            else:video='<p>No completed video. Setup/runtime failure is recorded, not replaced by a fabricated clip.</p>'
            detail=f'<pre>{html.escape(json.dumps({k:r.get(k)for k in ["exit_code","result","error"]},indent=2))}</pre>'
        else:detail='<p>The case has not closed yet.</p>'
        label='EXPERT drives'if j['name']not in ['E09_terminal_handoff','E10_natural_rescue','E11_expired_memory']else'Ownership is shown frame by frame: expert prefix / learner / expert / fault'
        cards.append(f'<article><h2>{html.escape(name)}</h2><p class="state">{html.escape(status)}</p><p>{label}</p>{video}<details><summary>Actual outcome / limits</summary>{detail}</details></article>')
    extra=B/'E04a_detail.mp4'
    if extra.exists():cards.insert(4,'<article><h2>E04a — detail of the SAME actual E04 flight</h2><video controls preload="metadata" src="E04a_detail.mp4"></video></article>')
    text='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Windows MuJoCo expert review</title><style>body{margin:24px auto;max-width:1300px;padding:0 18px;font:16px system-ui;background:#121820;color:#e5edf7}h1{font-size:28px}header{padding-bottom:20px;border-bottom:1px solid #455365}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px}article{background:#1c2733;padding:18px;border:1px solid #405063;border-radius:8px}video{width:100%;background:#05080b}.state{color:#ffd18b}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}a{color:#a8d5ff}.note{color:#bfcbd9}</style><header><h1>Actual Windows MuJoCo expert review</h1><p>No training eligibility granted. No synthetic replacement videos. E12 return-home is excluded.</p><p class="note">Each video uses actual recorded onboard RGB at 25 fps / normal task speed. Owners and evaluation faults are labelled. Assisted landings are never independent learner successes. Refresh to see newly closed cases.</p><p>All task rendering and physics: Windows Python MuJoCo. Flight controller: real pinned PX4 WebAssembly in Windows Node. No Tidewater world/images and no Linux runner.</p>'''
    text+=f'<p>Batch status: <strong>{html.escape(state["status"])}</strong>; closed {len(complete)}/{len(plan["jobs"])}</p></header><div class="grid">'+''.join(cards)+'</div></html>'
    p=B/'index.html';q=p.with_suffix('.tmp');q.write_text(text,encoding='utf-8');q.replace(p)

if __name__=='__main__':update(json.loads((B/'state.json').read_text()))

