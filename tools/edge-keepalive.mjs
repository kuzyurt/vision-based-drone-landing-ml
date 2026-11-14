const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find(item => item.type === 'page' && item.url.includes('127.0.0.1:5189'));
if (!page) throw new Error('Tidewater page not found');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
ws.addEventListener('message', event => { const message = JSON.parse(event.data); if (message.id) { const request = pending.get(message.id); pending.delete(message.id); message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result); } });
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve); ws.addEventListener('error', reject); });
const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, {resolve, reject}); ws.send(JSON.stringify({id: requestId, method, params})); });
try { await send('Emulation.setFocusEmulationEnabled', {enabled:true}); } catch {}
for (let i = 0; i < 1800; i++) {
  try { await send('Page.bringToFront'); } catch {}
  await new Promise(resolve => setTimeout(resolve, 2000));
}
ws.close();
