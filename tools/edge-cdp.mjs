import fs from 'node:fs';

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = process.argv[2] === '--page' ? list.find(item => item.type === 'page' && item.url.includes('127.0.0.1:5189')) : null;
if (!page) throw new Error('Tidewater page not found');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const events = [];
ws.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.id) {
    const request = pending.get(message.id);
    pending.delete(message.id);
    if (request) message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
  } else events.push(message);
});
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve); ws.addEventListener('error', reject); });
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const requestId = ++id;
  pending.set(requestId, {resolve, reject});
  ws.send(JSON.stringify({id: requestId, method, params}));
});
const evaluate = async (expression, awaitPromise = true) => {
  const result = await send('Runtime.evaluate', {expression, awaitPromise, returnByValue: true});
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text + ': ' + (result.exceptionDetails.exception?.description || ''));
  return result.result?.value;
};
await send('Runtime.enable');
await send('Log.enable');
if (process.argv.includes('--text')) {
  console.log(await evaluate('document.body.innerText.slice(0,6000)'));
} else {
  const expression = fs.readFileSync(process.argv[3], 'utf8');
  const value = await evaluate(expression);
  console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 2));
}
const errors = events.filter(event => event.method === 'Runtime.exceptionThrown' || (event.method === 'Log.entryAdded' && ['error', 'warning'].includes(event.params.entry.level)));
for (const event of errors.slice(-20)) console.log('EVENT', JSON.stringify(event).slice(0, 1000));
ws.close();
