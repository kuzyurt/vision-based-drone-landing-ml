const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find(item => item.type === 'page' && item.url.includes('127.0.0.1:5189'));
if (!page) throw new Error('Tidewater page not found');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.id) {
    const request = pending.get(message.id);pending.delete(message.id);
    if (request) message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
    return;
  }
  if (message.method === 'Runtime.consoleAPICalled') console.log('CONSOLE', message.params.type, message.params.args.map(arg => arg.value ?? arg.description).join(' '));
  else if (message.method === 'Runtime.exceptionThrown') console.log('EXCEPTION', JSON.stringify(message.params.exceptionDetails).slice(0, 2000));
  else if (message.method === 'Log.entryAdded') console.log('LOG', message.params.entry.level, message.params.entry.text, message.params.entry.url || '');
});
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve); ws.addEventListener('error', reject); });
const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, {resolve, reject}); ws.send(JSON.stringify({id: requestId, method, params})); });
const evaluate = async expression => (await send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true})).result?.value;
await send('Runtime.enable');await send('Log.enable');await send('Page.enable');
await send('Page.reload', {ignoreCache: true});
await new Promise(resolve => setTimeout(resolve, 25000));
console.log('STATE', JSON.stringify(await evaluate(`({app:!!window.__app, ui:!!window.__ui, text:document.body.innerText.slice(0,300), start:document.querySelector('#flight-start')?.hidden, loader:document.querySelector('#loader')?.innerText?.slice(0,300), error:document.querySelector('.error')?.innerText})`), null, 2));
ws.close();
