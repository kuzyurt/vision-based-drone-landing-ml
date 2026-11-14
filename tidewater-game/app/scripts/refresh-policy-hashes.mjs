// Recompute the SHA-256 of every reference adapter file listed in
// public/policy/manifest.json (the browser refuses files whose hash differs).
// Only the hash strings are edited; the rest of the manifest text is untouched.
// Run after editing anything in public/policy/reference/:
//   node scripts/refresh-policy-hashes.mjs [--add new_file.py ...]
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const policy = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public/policy');
const manifestPath = path.join(policy, 'manifest.json');
let text = fs.readFileSync(manifestPath, 'utf8');
const table = JSON.parse(text).reference_adapter_sha256;
const sha = name => createHash('sha256').update(fs.readFileSync(path.join(policy, 'reference', name))).digest('hex');
const escape = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const args = process.argv.slice(2);
let changed = 0;
for (let i = 0; i < args.length; i++) {
	if (args[i] !== '--add' || !args[i + 1]) continue;
	const name = args[++i];
	if (name in table) continue;
	// Insert as the first entry of the table, with the indentation of the existing entries.
	const head = /("reference_adapter_sha256"\s*:\s*\{)(\r?\n)([ \t]*)/.exec(text);
	if (!head) throw new Error('reference_adapter_sha256 table not found');
	text = text.replace(head[0], `${head[1]}${head[2]}${head[3]}"${name}": "${sha(name)}",${head[2]}${head[3]}`);
	table[name] = sha(name); changed++; console.log(`${name}: added`);
}
for (const name of Object.keys(table)) {
	const now = sha(name);
	if (table[name] === now) continue;
	const pattern = new RegExp(`("${escape(name)}"\\s*:\\s*")${table[name]}(")`);
	if (!pattern.test(text)) throw new Error('hash entry not found: ' + name);
	text = text.replace(pattern, `$1${now}$2`);
	console.log(`${name}: ${table[name]} -> ${now}`); changed++;
}
JSON.parse(text);
fs.writeFileSync(manifestPath, text);
console.log(changed ? `${changed} change(s)` : 'all hashes current');
