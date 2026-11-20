import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const origin='https://atlas.test';const cachesMap=new Map();let fetched=0,claimed=0;
const key=r=>new URL(typeof r==='string'?r:r.url,origin).href;
const caches={async keys(){return [...cachesMap.keys()]},async delete(k){return cachesMap.delete(k)},async open(k){if(!cachesMap.has(k))cachesMap.set(k,new Map());const m=cachesMap.get(k);return {async keys(){return [...m.keys()].map(url=>({url}))},async match(r){return m.get(key(r))?.clone()},async put(r,res){m.set(key(r),res.clone())},async delete(r){return m.delete(key(r))},async addAll(){}}},async match(r){for(const k of cachesMap.keys()){const hit=await (await this.open(k)).match(r);if(hit)return hit}}};
function worker(version,scope='/'){const events={};vm.runInNewContext(readFileSync('web-src/sw.js','utf8').replace('__VER__',version).replace('__CORE__','[]'),{URL,Response,caches,location:{origin},fetch:async()=>{fetched++;return new Response('fresh')},self:{registration:{scope:origin+scope},addEventListener:(n,f)=>events[n]=f,clients:{claim:async()=>{claimed++}},skipWaiting:async()=>{}},Math,Promise});return events}
async function activate(w){const jobs=[];w.activate({waitUntil:p=>jobs.push(p)});await Promise.all(jobs)}
async function get(w,path,options={}){const jobs=[];let response;w.fetch({request:{url:origin+path,method:'GET',mode:'cors',...options},waitUntil:p=>jobs.push(p),respondWith:p=>response=p});if(!response)return;const r=await response;await Promise.all(jobs);return r.text()}
const old=await caches.open('atlas-app-old');await old.put('/data/countries.json?v=content-a',new Response('saved map'));await old.put('index.html',new Response('old page'));
const first=worker('release-1');await activate(first);assert.equal(await get(first,'/data/countries.json?v=content-a'),'saved map');assert.equal(fetched,0);assert.equal(cachesMap.has('atlas-app-old'),false);
const second=worker('release-2');await activate(second);assert.equal(await get(second,'/data/countries.json?v=content-a'),'saved map');assert.equal(fetched,0,'unchanged map must survive a release');
assert.equal(await get(second,'/data/countries.json?v=content-b'),'fresh');assert.equal(fetched,1);await get(second,'/data/countries.json?v=content-b');assert.equal(fetched,1,'warm request must not hit network');await get(second,'/data/countries.json?v=content-c');assert.equal((await (await caches.open('atlas-assets-v1')).keys()).length,2,'keep at most two versions of each resource');assert.equal(await get(second,'/functions/v1/geo'),undefined,'unversioned live requests must bypass asset cache');assert.equal(claimed,2);
console.log('PASS: migration, reuse across releases, changed data, warm loads, bounded cache, live requests');

await caches.open('atlas-app-release-2');
const beta=worker('beta-release','/beta/');await activate(beta);assert(cachesMap.has('atlas-app-release-2'),'beta activation must preserve the main app cache');
assert.equal(await get(beta,'/beta/',{mode:'navigate'}),'fresh');await new Promise(r=>setTimeout(r,0));
const betaCache='atlas-subapp-%2Fbeta%2F-beta-release';assert.equal(await (await (await caches.open(betaCache)).match('/beta/index.html')).text(),'fresh');
await activate(worker('release-3'));assert(cachesMap.has(betaCache),'main activation must preserve beta cache');
console.log('PASS: main and beta cache isolation and beta navigation cache');
