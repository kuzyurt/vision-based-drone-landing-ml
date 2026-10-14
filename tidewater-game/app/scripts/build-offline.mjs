import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const root=path.resolve('dist'),assets=[];
// Old developer checkouts may retain a test binary in public/. Remove only
// its generated distribution copy; keep the user's local reference intact.
await fs.rm(path.join(root,'landing/physics/vehicles.mjb.gz'),{force:true});
async function walk(dir){for(const entry of await fs.readdir(dir,{withFileTypes:true})){const file=path.join(dir,entry.name);if(entry.isDirectory())await walk(file);else if(!['offline-manifest.json','service-worker.js'].includes(entry.name)){const bytes=await fs.readFile(file);assets.push({url:path.relative(root,file).split(path.sep).map(encodeURIComponent).join('/'),sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length});}}}
await walk(root);assets.sort((a,b)=>a.url.localeCompare(b.url));
const version=createHash('sha256').update(JSON.stringify(assets)).digest('hex'),manifest={version,bytes:assets.reduce((n,a)=>n+a.bytes,0),assets};
await fs.writeFile(path.join(root,'offline-manifest.json'),JSON.stringify(manifest));
await fs.writeFile(path.join(root,'service-worker.js'),(await fs.readFile('scripts/service-worker.js','utf8')).replace('__BUILD_VERSION__',version));
console.log(`Offline manifest: ${assets.length} files, ${(manifest.bytes/1048576).toFixed(1)} MiB, version ${version.slice(0,12)}`);
