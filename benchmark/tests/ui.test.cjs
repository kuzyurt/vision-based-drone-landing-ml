/* Offline DOM contract tests. No browser, model, renderer or simulator starts. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
class Element {
  constructor(tag) { this.tagName=tag; this.children=[]; this.attributes={}; this.textContent=''; this.value=''; this.style={}; this.listeners={}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children=children; }
  setAttribute(k,v) { this.attributes[k]=String(v); }
  addEventListener(k,v) { this.listeners[k]=v; }
}
const html=fs.readFileSync(path.join(root,'ui/index.html'),'utf8');
const elements=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element('div')]));
elements.role.value='all';
const context={window:{},document:{getElementById:id=>{assert.ok(elements[id],`Missing HTML id ${id}`);return elements[id];},createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'ui/data.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'ui/app.js'),'utf8'),context);
const inventory=context.window.BENCHMARK_DATA.inventory;
assert.equal(elements['policy-grid'].children.length,inventory.policies.length);
assert.equal(elements['weight-rows'].children.length,inventory.weights.length);
assert.match(elements['status-text'].textContent,/have not been run/);
assert.equal(elements['run-select'].children.length,1);
assert.match(JSON.stringify(elements['overall-chart'].children),/stroke-dasharray/);
assert.doesNotMatch(JSON.stringify(elements['overall-chart'].children),/NaN|undefined/);
elements.role.value='observable teacher';elements.role.listeners.change();
assert.equal(elements['policy-grid'].children.length,4);
elements.search.value='v61';elements.search.listeners.input();
assert.equal(elements['policy-grid'].children.length,1);
elements.search.value='no-such-policy';elements.search.listeners.input();
assert.equal(elements['policy-grid'].children.length,0);
assert.match(JSON.stringify(elements['overall-chart'].children),/No policies match/);
elements.role.value='all';elements.search.value='';elements.search.listeners.input();
assert.equal(elements['policy-grid'].children.length,inventory.policies.length);
console.log(`UI contract passed: ${inventory.policies.length} unscored policy charts; role/search filters; ${inventory.weights.length} weight rows; offline data and empty states.`);
