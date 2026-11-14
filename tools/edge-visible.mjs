const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find(item => item.type === 'page' && item.url.includes('127.0.0.1:5189'));
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
ws.addEventListener('message', event => { const message = JSON.parse(event.data); if (message.id) { const request = pending.get(message.id); pending.delete(message.id); message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result); } });
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve); ws.addEventListener('error', reject); });
const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, {resolve, reject}); ws.send(JSON.stringify({id: requestId, method, params})); });
for (const [method, params] of [['Page.bringToFront', {}], ['Emulation.setFocusEmulationEnabled', {enabled:true}], ['Emulation.setPageVisibilityOverride', {visibility:'visible'}]]) {
  try { console.log(method, await send(method, params)); } catch (error) { console.log(method, 'FAILED', error.message); }
}
await new Promise(resolve => setTimeout(resolve, 500));
const result = await send('Runtime.evaluate', {expression:'({visibility:document.visibilityState,focused:document.hasFocus(),hidden:document.hidden})',returnByValue:true});
console.log(result.result.value);
await send('Page.reload', {ignoreCache:true});
await new Promise(resolve => setTimeout(resolve, 15000));
const state = await send('Runtime.evaluate', {expression:'({visibility:document.visibilityState,app:!!window.__app,text:document.body.innerText.slice(0,260)})',returnByValue:true});
console.log(state.result.value);
ws.close();
