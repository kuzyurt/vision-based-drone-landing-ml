// Assemble the Cloudflare Pages site in site/ (not tracked by git).
//
//   npm --prefix tidewater-game/app run build:web   # the game, once per change
//   node tools/build-site.mjs                       # website + game -> site/
//   node tools/serve-site.mjs                       # local test with the same headers
//
// site/          the project website (website/)
// site/play/     the realistic simulator (tidewater-game/app/dist-web/)
// site/_headers  cross-origin isolation for /play/ only; the game's PX4 and
//                MuJoCo workers need SharedArrayBuffer, the website does not
//
// Cloudflare Pages serves files up to 25 MiB and 20,000 files per site. The
// website's 1080p hero film is larger, so the site gets a 720p copy (cached in
// website/.cache/); the original in website/assets/ stays as it is.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const site = path.join(root, 'site'), website = path.join(root, 'website');
const game = path.join(root, 'tidewater-game/app/dist-web');
const LIMIT = 25 * 1024 * 1024, MAX_FILES = 20000;

try { await fs.access(path.join(game, 'index.html')); }
catch { throw new Error('No game build. Run: npm --prefix tidewater-game/app run build:web'); }

await fs.rm(site, {recursive: true, force: true});
await fs.cp(website, site, {recursive: true, filter: source => !/[\\/](\.cache|README\.md)$/.test(source)});
await fs.cp(game, path.join(site, 'play'), {recursive: true});

// 720p web copies of large videos (cached by content). The hero film plays in
// the background for every visitor, so it is always made smaller; a gameplay
// recording (assets/gameplay.mp4) only when it is over the file limit, and it
// keeps its sound.
async function webVideo(name, {always, crf, audio}) {
	const source = path.join(website, 'assets', name);
	let bytes;
	try { bytes = await fs.readFile(source); } catch { return; }
	if (!always && bytes.length <= LIMIT * 0.95) return;
	const cache = path.join(website, '.cache', `${path.parse(name).name}-720p-crf${crf}-${createHash('sha256').update(bytes).digest('hex').slice(0, 12)}.mp4`);
	try { await fs.access(cache); } catch {
		await fs.mkdir(path.dirname(cache), {recursive: true});
		execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', source, '-vf', 'scale=1280:-2', '-c:v', 'libx264', '-preset', 'slow', '-crf', String(crf),
			'-pix_fmt', 'yuv420p', ...(audio ? ['-c:a', 'aac', '-b:a', '128k'] : ['-an']), '-movflags', '+faststart', cache], {stdio: 'inherit'});
	}
	await fs.copyFile(cache, path.join(site, 'assets', name));
}
await webVideo('hero.mp4', {always: true, crf: 28, audio: false});
await webVideo('gameplay.mp4', {always: false, crf: 26, audio: true});

// Without a 404 page Cloudflare Pages answers unknown paths with index.html and
// status 200; a missing file must stay a real 404 (the video fallback relies on it).
await fs.writeFile(path.join(site, '404.html'), `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Not found · AERODOCK</title><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0d1b24;color:#e8f1f3;font:18px/1.5 system-ui,sans-serif}a{color:#3cc7b4}</style>
</head><body><p>This page does not exist. <a href="/">Back to AERODOCK</a></p></body></html>
`);

await fs.writeFile(path.join(site, '_headers'), `/play/*
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
  Cross-Origin-Resource-Policy: same-origin
`);

let count = 0, total = 0;
const big = [];
async function walk(dir) {
	for (const entry of await fs.readdir(dir, {withFileTypes: true})) {
		const file = path.join(dir, entry.name);
		if (entry.isDirectory()) { await walk(file); continue; }
		const {size} = await fs.stat(file);
		count++; total += size;
		if (size > LIMIT) big.push(`${path.relative(site, file)} (${(size / 1048576).toFixed(1)} MiB)`);
	}
}
await walk(site);
if (big.length) throw new Error('Files over 25 MiB: ' + big.join(', '));
if (count > MAX_FILES) throw new Error(`${count} files, more than ${MAX_FILES}`);
console.log(`site/: ${count} files, ${(total / 1048576).toFixed(1)} MiB, every file under 25 MiB. Test: node tools/serve-site.mjs`);
