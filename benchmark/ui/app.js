/* Offline, dependency-free SVG plots. Missing observations are never zero bars. */
'use strict';
const data = window.BENCHMARK_DATA;
const $ = id => document.getElementById(id);
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const svgNode = (tag, attrs = {}, text) => { const n = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k,v] of Object.entries(attrs)) n.setAttribute(k,v); if (text !== undefined) n.textContent = text; return n; };
const pct = n => n === null || n === undefined ? 'Not scored' : `${n.toFixed(1)}%`;
const date = s => s ? s.replace('T',' ').replace(/\.\d+/, '').replace('+00:00',' UTC') : 'Not recorded';
let activeRun;

function overall(policies, scores) {
  const width = Math.max(760, policies.length * 94 + 74), height = 365;
  const left = 54, top = 24, plotH = 220, bottom = top + plotH;
  const svg = svgNode('svg', {viewBox:`0 0 ${width} ${height}`, width, height, role:'img', 'aria-label':'Overall mission score by policy. Vertical axis zero to one hundred percent. Unscored policies have empty dashed columns.'});
  for (const v of [0,25,50,75,100]) {
    const y = bottom - v / 100 * plotH;
    svg.append(svgNode('line',{x1:left,y1:y,x2:width-10,y2:y,stroke:'#dce7ed'}));
    svg.append(svgNode('text',{x:left-10,y:y+4,'text-anchor':'end',fill:'#536c7c','font-size':12},`${v}%`));
  }
  const step = (width-left-20)/Math.max(policies.length,1);
  policies.forEach((p,i) => {
    const x = left + step*(i+.5), score = scores[p.id]?.total;
    if (score === null || score === undefined) {
      svg.append(svgNode('rect',{x:x-23,y:top+1,width:46,height:plotH-1,fill:'#f7fafc',stroke:'#a0b7c5','stroke-dasharray':'3 5',rx:2}));
      svg.append(svgNode('text',{x,y:top+plotH/2,'text-anchor':'middle','font-size':11,fill:'#536c7c'},'—'));
    } else {
      const bar = svgNode('rect',{x:x-23,y:bottom-score/100*plotH,width:46,height:score/100*plotH,fill:'#087f98',rx:2});
      bar.append(svgNode('title',{},`${p.label}: ${pct(score)}`)); svg.append(bar);
      svg.append(svgNode('text',{x,y:bottom-score/100*plotH-8,'text-anchor':'middle','font-size':12,fill:'#14556c'},pct(score)));
    }
    const label = p.label.length>29 ? p.label.slice(0,27)+'…' : p.label;
    const text = svgNode('text',{x:x+2,y:bottom+18,transform:`rotate(42 ${x+2} ${bottom+18})`,'text-anchor':'start','font-size':11,fill:'#183345'},label);
    text.append(svgNode('title',{},p.label)); svg.append(text);
  });
  if (!policies.length) svg.append(svgNode('text',{x:width/2,y:140,'text-anchor':'middle',fill:'#536c7c'},'No policies match the filter.'));
  $('overall-chart').replaceChildren(svg);
}

function mini(p, score) {
  const svg = svgNode('svg',{viewBox:'0 0 340 178',class:'mini-chart',role:'img','aria-label':`${p.label} benchmark categories, zero to one hundred percent`});
  const left=145,right=306,span=right-left;
  for (const v of [0,50,100]) {
    const x=left+span*v/100;
    svg.append(svgNode('line',{x1:x,y1:18,x2:x,y2:170,stroke:'#e1eaf0'}));
    svg.append(svgNode('text',{x,y:11,'text-anchor':'middle','font-size':10,fill:'#536c7c'},`${v}%`));
  }
  Object.entries(data.suite.categories).forEach(([key,c],i)=>{
    const y=22+i*25, item=score?.categories[key], value=item?.score;
    const labels={landing:'Landing / boat speed',wind:'Wind',waves:'Waves',acquisition:'Find the boat',combined:'Combined',speed:'Mission speed'};
    svg.append(svgNode('text',{x:left-10,y:y+12,'text-anchor':'end','font-size':11,fill:'#183345'},labels[key]));
    svg.append(svgNode('rect',{x:left,y,width:span,height:15,fill:'#eef4f7',rx:2}));
    if(value!==null && value!==undefined){
      const bar=svgNode('rect',{x:left,y,width:span*value/100,height:15,fill:item.complete?'#087f98':'#87afbf',rx:2});
      bar.append(svgNode('title',{},`${c.label}: ${pct(value)}; ${item.valid}/${item.planned} valid cases${item.complete?'':' (partial, excluded from total)'}`));svg.append(bar);
      svg.append(svgNode('text',{x:311,y:y+12,'font-size':10,fill:'#14556c'},Math.round(value)));
    }else svg.append(svgNode('text',{x:left+span/2,y:y+11,'text-anchor':'middle','font-size':10,fill:'#758d9d'},'Not run'));
  });
  return svg;
}

function card(p, score) {
  const card=node('article',undefined,`policy-card${score?.complete?' complete':''}`);
  const top=node('div',undefined,'card-top');top.append(node('h3',p.label),node('span',score?.total===null||score?.total===undefined?'Not scored':pct(score.total),`score${score?.complete?'':' pending'}`));card.append(top);
  card.append(node('p',`${p.role} · ${p.available?'Local assets available':'Incomplete local bundle'}`,'role-line'),mini(p,score));
  const coverage=score?`${score.valid_cases}/${score.planned_cases} valid cases · ${score.invalid_cases} invalid or infrastructure failures`:'No trials recorded for this suite.';
  card.append(node('p',coverage,'coverage-line'));
  const details=node('details');details.append(node('summary','Model, weights & timestamp'));
  const dl=node('dl');
  for(const [key,value] of [['Snapshot',p.identity_sha256],['Manifest time',date(p.file_modified_utc)],['Captured',date(p.captured_utc)],['Actor',p.actor],['Missing',p.missing.length?p.missing.join(', '):'None in inventory']]){dl.append(node('dt',key),node('dd',value));}
  details.append(dl);
  const a=node('a','Open architecture & source receipt');a.href=`../models/${encodeURIComponent(p.id)}/architecture.json`;details.append(a);
  const weights=node('p',`${Object.keys(p.weights).length} checkpoint components. Source and weights are hash-bound; runtime preflight is required.`);weights.style.marginTop='10px';details.append(weights);card.append(details);
  const trials=node('details');trials.append(node('summary','Inspect every planned test condition'));
  let expanded=false;
  trials.addEventListener('toggle',()=>{
    if(!trials.open||expanded)return;
    expanded=true;
    const byId=Object.fromEntries((score?.trials||[]).map(t=>[t.case_id,t]));
    const wrap=node('div',undefined,'table-scroll'),table=node('table'),head=node('thead'),heading=node('tr');
    for(const label of ['Case / conditions','Outcome','Acquired','Mission time'])heading.append(node('th',label));
    head.append(heading);table.append(head);const body=node('tbody');
    for(const c of data.suite.cases){const s=c.scenario,r=byId[c.id],tr=node('tr');
      const condition=`${c.id}: ${s.distance} m; boat ${s.boat_speed} m/s; wind ${s.wind_mean_m_s} m/s; waves ${s.wave_height} m; radio ${c.radio}; decoys ${c.decoys?'on':'off'}`;
      const outcome=!r?'Not run':r.status!=='completed'?r.status:!r.condition_valid?'Invalid conditions':r.outcome;
      for(const value of [condition,outcome,r?.verified_acquisition_s==null?'—':`${r.verified_acquisition_s.toFixed(2)} s`,r?.mission_time_s==null?'—':`${r.mission_time_s.toFixed(2)} s`])tr.append(node('td',value));
      body.append(tr);
    }
    table.append(body);wrap.append(table);trials.append(wrap);
  });
  card.append(trials);
  return card;
}

function render() {
  activeRun=data.runs.find(r=>r.id===$('run-select').value);
  const query=$('search').value.toLowerCase(),role=$('role').value;
  const policies=data.inventory.policies.filter(p=>(role==='all'||p.role===role)&&`${p.label} ${p.id}`.toLowerCase().includes(query));
  const scores=activeRun?.scores||{};
  overall(policies,scores);$('policy-grid').replaceChildren(...policies.map(p=>card(p,scores[p.id])));
  $('visible-count').textContent=`${policies.length} model configurations`;
  const complete=Object.values(scores).filter(s=>s.complete).length;
  $('coverage').textContent=`${complete} complete policy suites`;
  $('status-text').textContent=activeRun?`${activeRun.id}: ${complete} complete suites. Each chart uses this one run, machine, runtime and test plan. Partial category values are provisional.`:'Benchmarks have not been run. The real model inventory and test plan are ready; all result columns remain unscored.';
}

if(!data){$('status-text').textContent='Inventory data is missing. Run python -m benchmark prepare from the repository root; it does not launch benchmarks.';}
else {
  $('plan-count').textContent=`${data.suite.cases.length} planned flights per policy`;
  const option=node('option','Inventory only · No measured results');option.value='';$('run-select').append(option);
  for(const r of [...data.runs].reverse()){const opt=node('option',r.id);opt.value=r.id;$('run-select').append(opt);}
  if(data.runs.length)$('run-select').value=data.runs.at(-1).id;
  for(const id of ['run-select','role','search'])$(id).addEventListener(id==='search'?'input':'change',render);
  $('weights').replaceChildren(...Object.values(data.suite.categories).map(c=>node('span',`${c.label}: ${c.weight*100}%`)));
  $('inventory-count').textContent=`${data.inventory.weights.length} loose weight files · ${data.inventory.unique_weight_count} unique loose hashes · ${data.inventory.unique_weight_count_including_archives} unique weights including archives · ${data.inventory.policies.length} policy configurations`;
  for(const w of data.inventory.weights){const tr=node('tr');for(const value of [w.path,w.architecture,date(w.file_modified_utc),w.sha256])tr.append(node('td',value));$('weight-rows').append(tr);}
  for(const a of Object.values(data.inventory.architectures)){const article=node('article');article.append(node('h3',a.name));for(const [k,v]of Object.entries(a))if(k!=='name')article.append(node('p',`${k}: ${v}`));$('architectures').append(article);}
  for(const a of data.inventory.unweighted_architectures)$('architectures').append(node('p',`${a.name}. ${a.status}.`));
  for(const a of data.inventory.weight_archives){const details=node('details');details.append(node('summary',`${a.path}: ${a.members.length} archived weight members`));for(const m of a.members)details.append(node('p',`${m.path} · ${m.architecture} · SHA-256 ${m.sha256} · Entry time ${m.archive_timestamp.join('-')} · ${m.timestamp_basis}`));$('archives').append(details);}
  if(data.rejected.length){$('receipts').hidden=false;for(const r of data.rejected)$('rejected').append(node('li',`${r.path||r.run}: ${r.reason}`));}
  $('generated').textContent=`Inventory captured ${date(data.inventory.captured_utc)}`;
  render();
}
