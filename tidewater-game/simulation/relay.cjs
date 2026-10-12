// Forward HTTP and WebSocket traffic; PX4 lockstep stays entirely inside WSL.
const net = require('node:net');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const host = process.argv[2];
if (!net.isIPv4(host) || host === '0.0.0.0') throw new Error('Expected a WSL IPv4 address');
const sockets = new Set();
const started = process.hrtime.bigint();
// Windows time is the same time base used by the browser. WSL's virtual
// monotonic clock can advance at a different rate on this host.
const clock = setInterval(() => {
  const body = JSON.stringify({elapsed_s: Number(process.hrtime.bigint()-started)/1e9});
  const request = http.request({host, port:5195, path:'/api/clock', method:'POST',
    headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(body)}, timeout:1000}, response => response.resume());
  request.on('error', () => {});
  request.on('timeout', () => request.destroy());
  request.end(body);
}, 500);
const server = net.createServer(client => {
  const upstream = net.connect({host, port: 5195});
  for (const socket of [client, upstream]) {
    sockets.add(socket);
    socket.setNoDelay(true);
    socket.on('error', () => { client.destroy(); upstream.destroy(); });
    socket.on('close', () => { sockets.delete(socket); client.destroy(); upstream.destroy(); });
  }
  client.pipe(upstream); upstream.pipe(client);
});
server.listen(5195, '127.0.0.1', () => {
  fs.writeFileSync(path.join(__dirname, 'runtime', 'relay.pid'), String(process.pid));
  console.log(`Tidewater localhost relay ready: ${host}:5195`);
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => {
  clearInterval(clock);
  for (const socket of sockets) socket.destroy();
  server.close(() => process.exit(0));
});
