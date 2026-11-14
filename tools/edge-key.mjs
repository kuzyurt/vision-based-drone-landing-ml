const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find(item => item.type === 'page' && item.url.includes('127.0.0.1:5189'));
if (!page) throw new Error('Tidewater page not found');
const code = process.argv[2] || 'KeyD';
const key = process.argv[3] || code.replace(/^Key/, '').toLowerCase();
const hold = Number(process.argv[4] || 1000);
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
try {
  await send('Page.bringToFront');
  await send('Emulation.setFocusEmulationEnabled', {enabled: true});
} catch {}
await send('Input.dispatchKeyEvent', {type: 'keyDown', code, key, text: key, unmodifiedText: key, windowsVirtualKeyCode: key.toUpperCase().charCodeAt(0), nativeVirtualKeyCode: key.toUpperCase().charCodeAt(0)});
await new Promise(resolve => setTimeout(resolve, hold));
await send('Input.dispatchKeyEvent', {type: 'keyUp', code, key, windowsVirtualKeyCode: key.toUpperCase().charCodeAt(0), nativeVirtualKeyCode: key.toUpperCase().charCodeAt(0)});
console.log(JSON.stringify({code, key, hold_ms: hold}));
ws.close();
