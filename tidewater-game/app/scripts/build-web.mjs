// Build the game for static web hosting (Cloudflare Pages) into dist-web/.
//
//   npm run build:web
//
// Differences from `npm run build` (which stays the offline/local build):
// - VITE_WEB_HOSTED=1: no offline service worker (it would download every file
//   for every visitor) and an in-game hint on slow devices.
// - The 27 MiB WebGPU runtime of onnxruntime-web is over the 25 MiB per-file
//   limit, so it is replaced by remote-jsep-wasm.json: the jsDelivr URL of the
//   same file in the pinned npm version plus its SHA-256, checked at load time.
// - Unused copies are left out: the rollback policy folder, Vite's duplicate
//   ORT wasm files (ORT loads them from policy/ort/ via wasmPaths) and an old
//   developer test binary.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {build} from 'vite';

const LIMIT = 25 * 1024 * 1024, MAX_FILES = 20000;
const out = path.resolve('dist-web');
const version = JSON.parse(await fs.readFile(path.resolve('node_modules/onnxruntime-web/package.json'), 'utf8')).version;

process.env.VITE_WEB_HOSTED = '1';
await build({mode: 'production', logLevel: 'warn', build: {outDir: out, emptyOutDir: true}});

const remove = async rel => fs.rm(path.join(out, rel), {recursive: true, force: true});
await remove('policy-legacy-vision-first');
await remove('landing/physics/vehicles.mjb.gz');
for (const name of await fs.readdir(path.join(out, 'assets')))
	if (/^ort-wasm.*\.wasm$/.test(name)) await remove(path.join('assets', name));

const jsep = path.join(out, 'policy/ort/ort-wasm-simd-threaded.jsep.wasm');
const bytes = await fs.readFile(jsep);
const local = await fs.readFile(path.resolve('node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.jsep.wasm'));
if (!bytes.equals(local)) throw new Error('policy/ort jsep wasm differs from onnxruntime-web ' + version + '; run tools/vendor-policy-runtime.mjs');
await fs.writeFile(path.join(out, 'policy/ort/remote-jsep-wasm.json'), JSON.stringify({
	url: `https://cdn.jsdelivr.net/npm/onnxruntime-web@${version}/dist/ort-wasm-simd-threaded.jsep.wasm`,
	sha256: createHash('sha256').update(bytes).digest('hex'),
	bytes: bytes.length,
}, null, 1));
await fs.rm(jsep);

let count = 0, total = 0;
const big = [];
async function walk(dir) {
	for (const entry of await fs.readdir(dir, {withFileTypes: true})) {
		const file = path.join(dir, entry.name);
		if (entry.isDirectory()) { await walk(file); continue; }
		const {size} = await fs.stat(file);
		count++; total += size;
		if (size > LIMIT) big.push(`${path.relative(out, file)} (${(size / 1048576).toFixed(1)} MiB)`);
	}
}
await walk(out);
if (big.length) throw new Error('Files over 25 MiB: ' + big.join(', '));
if (count > MAX_FILES) throw new Error(`${count} files, more than ${MAX_FILES}`);
console.log(`dist-web: ${count} files, ${(total / 1048576).toFixed(1)} MiB, largest file under 25 MiB; WebGPU runtime from jsDelivr (onnxruntime-web ${version})`);
