// Serve site/ locally the way Cloudflare Pages will: static files plus the
// headers from site/_headers (simple "/path/*" rules only).
//
//   node tools/serve-site.mjs [port] [latency_ms]   then open http://127.0.0.1:8788/
//
// latency_ms delays every response, to feel what loading is like over the internet.
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../site');
const port = Number(process.argv[2] || 8788), latency = Number(process.argv[3] || 0), log = process.env.SITE_LOG === '1', t0 = Date.now();
const types = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
	'.css': 'text/css; charset=utf-8', '.json': 'application/json', '.wasm': 'application/wasm', '.svg': 'image/svg+xml',
	'.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif', '.mp4': 'video/mp4', '.mp3': 'audio/mpeg',
	'.ogg': 'audio/ogg', '.txt': 'text/plain; charset=utf-8', '.ktx2': 'image/ktx2', '.glb': 'model/gltf-binary'};

const rules = [];
let current = null;
for (const line of (await fs.readFile(path.join(root, '_headers'), 'utf8')).split(/\r?\n/)) {
	if (!line.trim() || line.trim().startsWith('#')) continue;
	if (!/^\s/.test(line)) { current = {pattern: line.trim(), headers: []}; rules.push(current); continue; }
	const [name, ...value] = line.trim().split(':');
	current?.headers.push([name.trim(), value.join(':').trim()]);
}
const matches = (pattern, url) => pattern.endsWith('*') ? url.startsWith(pattern.slice(0, -1)) : url === pattern;

http.createServer(async (req, res) => {
	if (latency) await new Promise(resolve => setTimeout(resolve, latency));
	let url = decodeURIComponent(new URL(req.url, 'http://x').pathname);
	if (log) console.log(((Date.now() - t0) / 1000).toFixed(1), url);
	let file = path.join(root, url);
	if (!file.startsWith(root)) { res.writeHead(403).end(); return; }
	try {
		if ((await fs.stat(file)).isDirectory()) {
			if (!url.endsWith('/')) { res.writeHead(308, {Location: url + '/'}).end(); return; }
			file = path.join(file, 'index.html');
		}
		const body = await fs.readFile(file);
		for (const rule of rules) if (matches(rule.pattern, url)) for (const [name, value] of rule.headers) res.setHeader(name, value);
		res.setHeader('Content-Type', types[path.extname(file).toLowerCase()] || 'application/octet-stream');
		res.end(body);
	} catch {
		console.log('404', url);
		res.writeHead(404, {'Content-Type': 'text/plain'}).end('Not found');
	}
}).listen(port, '127.0.0.1', () => console.log(`site/ on http://127.0.0.1:${port}/`));
