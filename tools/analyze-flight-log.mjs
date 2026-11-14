import fs from 'node:fs';
import path from 'node:path';

const input = process.argv[2] || 'tidewater-game/app/diagnostics/student-flight-nudged-20261112.json';
const output = process.argv[3] || input.replace(/\.json$/, '-compact.json');
const digestPath = process.argv[4] || input.replace(/\.json$/, '-digest.txt');
const raw = JSON.parse(fs.readFileSync(input, 'utf8'));
const rows = raw.rows.map(({route, ...row}) => row);
const compact = {...raw, rows};
fs.writeFileSync(output, JSON.stringify(compact));

const policyRows = rows.filter(row => row.diagnostics);
const phaseKey = row => row.diagnostics?.control_phase || row.phase || 'unknown';
const targetStats = row => {
  const proposals = row.diagnostics?.search_proposals || [];
  const targets = proposals.filter(item => item.evidence === 'target_boat');
  const best = targets.reduce((best, item) => item.confidence > (best?.confidence || -Infinity) ? item : best, null);
  return {targets, best, count: targets.length};
};
const segments = [];
for (const row of policyRows) {
  const phase = phaseKey(row);
  const last = segments.at(-1);
  if (!last || last.phase !== phase) {
    segments.push({phase, start_s: row.sim_s, end_s: row.sim_s, frames: 0, target_proposals: 0, target_at_or_above_05: 0, target_max: 0, best: null, first_wall: row.wall_ms, clearance_min: Infinity, clearance_max: -Infinity, recovery: 0, handoff: false, metric: false, pre360: row.diagnostics?.pre360_phase, search: `${row.diagnostics?.search_mode || '?'}/${row.diagnostics?.search_phase || '?'}`});
  }
  const segment = segments.at(-1);
  segment.end_s = row.sim_s;
  segment.frames++;
  const {targets, best, count} = targetStats(row);
  segment.target_proposals += count;
  segment.target_at_or_above_05 += targets.filter(item => item.confidence >= .5).length;
  if (best && best.confidence > segment.target_max) { segment.target_max = best.confidence; segment.best = {sim_s: row.sim_s, ...best}; }
  const d = row.diagnostics;
  if (Number.isFinite(d.estimated_clearance_m)) {
    segment.clearance_min = Math.min(segment.clearance_min, d.estimated_clearance_m);
    segment.clearance_max = Math.max(segment.clearance_max, d.estimated_clearance_m);
  }
  if (d.recovery_active) segment.recovery++;
  if (d.handoff_latched) segment.handoff = true;
  if (d.metric_confirmed) segment.metric = true;
}
const lines = [];
lines.push('Tidewater student flight — 1 s right nudge before policy enable');
lines.push(`captured ${raw.final?.captured_at || '?'}; raw ${raw.rows.length} rows; policy ${policyRows.length} rows`);
lines.push(`final: ${JSON.stringify(raw.final?.state)}`);
lines.push('');
lines.push('phase segments (policy rows):');
for (const s of segments) {
  lines.push(`${s.phase.padEnd(18)} ${s.start_s?.toFixed(2).padStart(8)}s -> ${s.end_s?.toFixed(2).padStart(8)}s  ${String(s.frames).padStart(4)}f  target:${s.target_proposals} >=.50:${s.target_at_or_above_05} max:${s.target_max.toFixed(3)}${s.best ? ` @${s.best.pixel.map(v=>v.toFixed(0)).join(',')}` : ''}  handoff:${s.handoff} metric:${s.metric} recovery:${s.recovery}${Number.isFinite(s.clearance_min) ? ` clearance:${s.clearance_min.toFixed(2)}-${s.clearance_max.toFixed(2)}` : ''}`);
}
lines.push('');
lines.push('first/last policy rows:');
for (const row of [policyRows[0], policyRows.at(-1)].filter(Boolean)) {
  lines.push(`${row.sim_s?.toFixed(2)}s ${phaseKey(row)} pre360=${row.diagnostics?.pre360_phase}/${row.diagnostics?.pre360_done} search=${row.diagnostics?.search_mode}/${row.diagnostics?.search_phase} handoff=${row.diagnostics?.handoff_latched} metric=${row.diagnostics?.metric_confirmed} proposals=${JSON.stringify((row.diagnostics?.search_proposals || []).map(p => [p.evidence, +p.confidence.toFixed(3), +p.identity_target_probability.toFixed(3)]))}`);
}
fs.writeFileSync(digestPath, lines.join('\n') + '\n');
console.log(JSON.stringify({input, compact: output, digest: digestPath, compact_bytes: fs.statSync(output).size, segments}, null, 2));
