import fs from 'node:fs';
import path from 'node:path';

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find(item => item.type === 'page' && item.url.includes('127.0.0.1:5189'));
if (!page) throw new Error('Tidewater page not found');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (!message.id) return;
  const request = pending.get(message.id);
  pending.delete(message.id);
  message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
});
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve); ws.addEventListener('error', reject); });
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const requestId = ++id;
  pending.set(requestId, {resolve, reject});
  ws.send(JSON.stringify({id: requestId, method, params}));
});
await send('Page.bringToFront');
await send('Emulation.setFocusEmulationEnabled', {enabled: true});
const evaluated = await send('Runtime.evaluate', {
  expression: `(() => {
    const log=window.__diagLog;
    if (!log) return null;
    if (log.timer) { clearInterval(log.timer); log.timer=null; }
    const ops=window.__app?.flightOps, p=ops?.bridge?.policy;
    log.final={captured_at:new Date().toISOString(),state:ops?.state?.ml,policy_status:p?.status,diagnostics:p?.latestDiagnostics,latest_timing:p?.latestTiming};
    return JSON.stringify(log);
  })()`,
  returnByValue: true,
  awaitPromise: true,
});
if (!evaluated.result?.value) throw new Error('Diagnostic log not installed');
const output = process.argv[2] || 'tidewater-game/app/diagnostics/student-flight.json';
fs.mkdirSync(path.dirname(output), {recursive: true});
fs.writeFileSync(output, evaluated.result.value);
const log = JSON.parse(evaluated.result.value);
const rows = log.rows;
const policyRows = rows.filter(row => row.diagnostics);
const phaseCounts = {};
const controlCounts = {};
let targetProposals = 0, targetAtOrAbove = 0, targetBelow = 0, targetMax = 0, targetBest = null;
let recoveryRows = 0, metricRows = 0, handoffRows = 0;
for (const row of rows) {
  const key = row.phase || 'none';
  phaseCounts[key] = (phaseCounts[key] || 0) + 1;
  const d = row.diagnostics;
  if (!d) continue;
  const control = d.control_phase || 'none';
  controlCounts[control] = (controlCounts[control] || 0) + 1;
  if (d.handoff_latched) handoffRows++;
  if (d.metric_confirmed) metricRows++;
  if (d.recovery_active) recoveryRows++;
  for (const proposal of d.search_proposals || []) {
    if (proposal.evidence !== 'target_boat') continue;
    targetProposals++;
    const confidence = Number(proposal.confidence) || 0;
    if (confidence >= 0.5) targetAtOrAbove++;
    else targetBelow++;
    if (confidence > targetMax) { targetMax = confidence; targetBest = {sim_s: row.sim_s, phase: row.phase, control_phase: control, proposal}; }
  }
}
const summary = {
  output,
  bytes: fs.statSync(output).size,
  rows: rows.length,
  policy_rows: policyRows.length,
  marks: log.marks,
  phase_counts: phaseCounts,
  control_phase_counts: controlCounts,
  target_boat_proposals: targetProposals,
  target_boat_confidence_at_or_above_0_5: targetAtOrAbove,
  target_boat_confidence_below_0_5: targetBelow,
  target_boat_confidence_max: targetMax,
  target_boat_best: targetBest,
  rows_with_handoff: handoffRows,
  rows_with_metric: metricRows,
  rows_with_recovery: recoveryRows,
  final: log.final,
};
console.log(JSON.stringify(summary, null, 2));
ws.close();
