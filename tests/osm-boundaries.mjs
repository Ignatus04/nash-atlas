import fs from 'node:fs';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import vm from 'node:vm';import * as d3 from 'd3';
const require=createRequire(import.meta.url),tc=require('topojson-client');
const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const overview=load('site/data/countries.json'),index=load('site/data/border-index.json');
assert.equal(overview.license,'ODbL-1.0');assert.equal(index.license,'ODbL-1.0');assert(fs.statSync('site/data/countries.json').size<6000000);
const feature=k=>{const id=Object.keys(index.groups).find(id=>index.groups[id].countries.includes(k));assert(id,k);const t=load('web/data/borders/'+id+'.json');assert.equal(t.license,'ODbL-1.0');return tc.feature(t,t.objects.countries).features.find(f=>f.properties.k===k)};
function segments(f){const ps=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates,out=[];for(const p of ps)for(const r of p)for(let i=1;i<r.length;i++)out.push([r[i-1],r[i]]);return out}
const key=s=>s.map(p=>p.map(x=>x.toFixed(7)).join(',')).sort().join('|');
const pl=new Map(segments(feature('PL')).map(s=>[key(s),s]));const common=segments(feature('SK')).filter(s=>pl.has(key(s)));
assert(common.length>1000,'Neighbours must retain their shared, detailed edges');
const fixture=load('tests/fixtures/pieniny-osm-20260928.geojson');const points=fixture.geometry.type==='LineString'?fixture.geometry.coordinates:fixture.geometry.coordinates.flat();
const near=common.filter(s=>s.some(p=>p[0]>20.20&&p[0]<20.60&&p[1]>49.30&&p[1]<49.52));assert(near.length>50);
function error(points,lines){let max=0;for(const p of points){let best=Infinity;for(const [a,b] of lines){const sx=111320*Math.cos(p[1]*Math.PI/180),sy=111320,dx=(b[0]-a[0])*sx,dy=(b[1]-a[1])*sy,x=(p[0]-a[0])*sx,y=(p[1]-a[1])*sy,len=dx*dx+dy*dy,t=len?Math.max(0,Math.min(1,(x*dx+y*dy)/len)):0;best=Math.min(best,Math.hypot(x-t*dx,y-t*dy))}max=Math.max(max,best)}return max}
const current=error(points,near);
const old=load('scripts/src/countries_legacy.topo.json'),o=old.objects[Object.keys(old.objects)[0]],mesh=tc.mesh(old,o,(a,b)=>a!==b&&[a.properties.k,b.properties.k].sort().join()==='PL,SK');
const oldLines=mesh.coordinates.flatMap(r=>r.slice(1).map((p,i)=>[r[i],p])).filter(s=>s.some(p=>p[0]>20&&p[0]<21&&p[1]>49&&p[1]<50));const previous=error(points,oldLines);
assert(current<25,`Detailed border deviates ${current.toFixed(1)}m from the native OSM sample`);assert(current<previous/5,'Must improve source geometry, not just rendering');
assert(fs.existsSync('web/borders-odbl.zip'));assert(fs.readFileSync('web/map-data.html','utf8').includes('ODbL'));
const source=fs.readFileSync('site/index.html','utf8'),fn=source.slice(source.indexOf('function applyWorldview('),source.indexOf('\nfunction viewNote()'));
const apply=new vm.Script('('+fn+')(ct,wv,cc,state)'),wv=load('site/data/worldviews.json');
for(const cc of ['XX','RU','BY','US','TR','CN','IN','JP','RS']){
  const keys=[old,overview].map(raw=>{const ct=structuredClone(raw);apply.runInNewContext({ct,wv,cc,state:{},d3,topojson:tc});return [...new Set(Object.values(ct.objects)[0].geometries.map(g=>g.properties.k))].sort()});assert.deepEqual(keys[0],keys[1],'Preserve territory identities in '+cc);
}
const occupied=load('web/data/borders/'+Object.keys(index.groups).find(id=>index.groups[id].countries.includes('XU'))+'.json');
const kharkiv=tc.feature(occupied,occupied.objects.countries.geometries.find(g=>g.properties.k==='~UA-kharkiv'));
const area=d3.geoArea(kharkiv)*6371**2;assert(area>100&&area<10000,'Preserve the existing Kharkiv control mask');
console.log(JSON.stringify({pass:true,sharedSegments:common.length,nativeSamplePoints:points.length,maxErrorMetres:Math.round(current*10)/10,previousErrorMetres:Math.round(previous*10)/10,detailGroups:Object.keys(index.groups).length}));
// Every European land-neighbour pair must use identical native edges, including
// microstates and the three-country junctions around Andorra.
const europePairs='ES-PT ES-FR ES-AD FR-AD FR-IT FR-MC FR-CH FR-DE FR-LU FR-BE IT-CH IT-AT IT-SI IT-SM IT-VA PT-ES BE-NL BE-DE BE-LU NL-DE DE-LU DE-CH DE-AT DE-CZ DE-PL DE-DK CH-AT CH-LI AT-LI AT-CZ AT-SK AT-HU AT-SI CZ-PL CZ-SK SK-PL SK-HU SK-UA PL-UA PL-BY PL-LT PL-RU LT-RU LT-BY LT-LV LV-BY LV-RU LV-EE EE-RU FI-RU FI-NO NO-RU NO-SE SE-FI BY-RU BY-UA UA-RU UA-MD UA-RO UA-HU MD-RO HU-RO HU-RS HU-HR HU-SI SI-HR HR-BA HR-RS HR-ME BA-RS BA-ME ME-RS ME-XK ME-AL RS-XK RS-MK RS-BG RS-RO XK-AL XK-MK AL-MK AL-GR MK-GR MK-BG GR-BG GR-TR BG-TR BG-RO TR-GE TR-AM TR-AZ GE-RU GE-AM GE-AZ AM-AZ AZ-RU'.split(' ').map(p=>p.split('-'));
const edges=new Map(),features=new Map();
for(const cc of new Set(europePairs.flat())){const f=feature(cc);features.set(cc,f);edges.set(cc,new Set(segments(f).map(key)))}
for(const [a,b] of europePairs){const shared=[...edges.get(a)].filter(e=>edges.get(b).has(e));assert(shared.length>0,`Native shared border missing: ${a}-${b}`)}
const vertices=f=>new Set(segments(f).flat().map(p=>p.map(x=>x.toFixed(7)).join(',')));
const es=vertices(features.get('ES')),fr=vertices(features.get('FR')),ad=vertices(features.get('AD'));
assert([...ad].filter(p=>es.has(p)&&fr.has(p)).length>=2,'Both Spain–France–Andorra junctions must coincide');
const policy=source.slice(source.indexOf('const EUROPE_BORDER_COUNTRIES='),source.indexOf('\nfunction scheduleDetailedBorders()'));
function requested(k,ids){return new vm.Script(policy+'; [...requestedBorderGroups(new Set(ids),k,index)]').runInNewContext({ids,k,index,Set})}
const group=cc=>Object.keys(index.groups).find(id=>index.groups[id].countries.includes(cc));
const selected=['ES','PT','FR','AD','IT','DE','CH','NO','PL','GR'].map(group),us=group('US');
assert.equal(requested(1,[...selected,us]).length,0,'No detailed download on world overview');
assert.equal(requested(2,[...new Set(selected),us]).length,new Set(selected).size,'All European groups load at regional zoom');
assert.equal(requested(2,[us]).length,0,'Keep distant non-European data deferred');
assert.equal(requested(12,[us]).length,1,'Close-up detail remains available worldwide');
console.log(JSON.stringify({europePass:true,sharedBorders:europePairs.length,andorraJunctions:2,regionalZoom:2}));
