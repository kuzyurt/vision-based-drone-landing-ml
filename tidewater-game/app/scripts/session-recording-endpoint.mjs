// Local-only endpoint for the in-game session recorder (dev key Z).
// The browser sends batches of JSON lines; they are appended to
// tidewater-game/recordings/<id>.jsonl. Shared by Vite (npm run dev) and the
// static server (npm start). Nothing is accepted from other origins.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export const RECORDINGS_DIR = path.resolve(fileURLToPath(new URL('../../recordings/', import.meta.url)));
const ROUTE = '/__session-recording';
const MAX_BATCH_BYTES = 64 * 1024 * 1024;
const ID = /^[A-Za-z0-9_-]{1,96}$/;

export async function handleSessionRecording(req, res, {dir = RECORDINGS_DIR} = {}) {
 const url = new URL(req.url, 'http://localhost');
 if (!url.pathname.endsWith(ROUTE)) return false;
 const reply = (code, text) => {res.statusCode = code; res.setHeader('Content-Type', 'text/plain; charset=utf-8'); res.end(text); return true;};
 if (req.method !== 'POST') return reply(405, 'POST only');
 const host = String(req.headers.host || '');
 if (!/^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/.test(host)) return reply(403, 'Local recordings only');
 const origin = req.headers.origin;
 if (origin && origin !== `http://${host}`) return reply(403, 'Same origin only');
 const id = url.searchParams.get('id') || '';
 if (!ID.test(id)) return reply(400, 'Invalid recording id');
 try {
  const chunks = []; let size = 0;
  for await (const chunk of req) {size += chunk.length; if (size > MAX_BATCH_BYTES) return reply(413, 'Batch too large'); chunks.push(chunk);}
  const body = Buffer.concat(chunks).toString('utf8');
  // Every line must be a JSON object; a corrupt batch is refused, never half-written.
  const lines = body.split('\n').filter(line => line.trim());
  for (const line of lines) {const value = JSON.parse(line); if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('not an object');}
  await fs.mkdir(dir, {recursive: true});
  const file = path.join(dir, id + '.jsonl');
  if (lines.length) await fs.appendFile(file, lines.join('\n') + '\n', 'utf8');
  return reply(200, path.relative(path.resolve(dir, '..'), file).split(path.sep).join('/'));
 } catch {
  return reply(400, 'Invalid recording batch');
 }
}
