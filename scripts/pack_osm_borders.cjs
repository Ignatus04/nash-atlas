// Package connected worldview components separately; browsers fetch only nearby countries.
const fs=require('fs'),path=require('path'),zlib=require('zlib'),tc=require('../node_modules/topojson-client');
const root=path.resolve(__dirname,'..'),topo=JSON.parse(fs.readFileSync(path.join(root,'site/data/countries-detail.json'),'utf8'));
const wv=JSON.parse(fs.readFileSync(path.join(root,'site/data/worldviews.json'),'utf8'));
const object=topo.objects[Object.keys(topo.objects)[0]],parent=new Map();
const host=g=>g.properties.k.startsWith('~')?g.properties.host:g.properties.k;
const find=k=>{if(!parent.has(k))parent.set(k,k);const p=parent.get(k);if(p!==k)parent.set(k,find(p));return parent.get(k)};
const join=(a,b)=>{a=find(a);b=find(b);if(a!==b)parent.set(a,b)};
for(const g of object.geometries){const h=host(g),k=g.properties.k;find(h);for(const m of [wv.intl,...Object.values(wv.views)])if(m[k])join(h,m[k])}
const members=new Map();for(const k of parent.keys()){const p=find(k);if(!members.has(p))members.set(p,[]);members.get(p).push(k)}
const groups=new Map();for(const g of object.geometries){const id=members.get(find(host(g))).sort()[0];if(!groups.has(id))groups.set(id,[]);groups.get(id).push(g)}
const out=path.join(root,'site/geodata/borders');fs.mkdirSync(out,{recursive:true});
for(const f of fs.readdirSync(out))if(f.endsWith('.json.gz'))fs.unlinkSync(path.join(out,f));
const index={license:'ODbL-1.0',attribution:topo.attribution,cellDegrees:5,cells:{},groups:{}};
function scan(a,fn){if(typeof a==='number')fn(a<0?~a:a);else a.forEach(x=>scan(x,fn))}
for(const [id,geometries] of groups){
  const used=new Set();geometries.forEach(g=>scan(g.arcs,a=>used.add(a)));
  const order=[...used].sort((a,b)=>a-b),map=new Map(order.map((a,i)=>[a,i]));
  const remap=a=>typeof a==='number'?(a<0?~map.get(~a):map.get(a)):a.map(remap);
  const chunk={...topo,objects:{countries:{type:'GeometryCollection',geometries:geometries.map(g=>({...g,arcs:remap(g.arcs)}))}},arcs:order.map(a=>topo.arcs[a])};
  const json=JSON.stringify(chunk);fs.writeFileSync(path.join(out,id+'.json.gz'),zlib.gzipSync(json,{level:9}));
  const cells=new Set();
  for(const g of geometries){if(g.properties.k==='AQ')continue;const geo=tc.feature(topo,g).geometry;
    for(const p of geo.type==='Polygon'?[geo.coordinates]:geo.coordinates){let a=180,b=90,c=-180,d=-90;for(const [x,y] of p[0]){a=Math.min(a,x);b=Math.min(b,y);c=Math.max(c,x);d=Math.max(d,y)}
      for(let x=Math.max(0,Math.floor((a+180)/5));x<=Math.min(71,Math.floor((c+180)/5));x++)for(let y=Math.max(0,Math.floor((b+90)/5));y<=Math.min(35,Math.floor((d+90)/5));y++)cells.add(`${x}:${y}`)}
  }
  for(const cell of cells){if(!index.cells[cell])index.cells[cell]=[];index.cells[cell].push(id)}
  index.groups[id]={countries:members.get(find(host(geometries[0]))).sort(),vertices:chunk.arcs.reduce((n,a)=>n+a.length,0),bytes:Buffer.byteLength(json)};
}
fs.writeFileSync(path.join(root,'site/data/border-index.json'),JSON.stringify(index));
console.log(JSON.stringify({groups:groups.size,totalBytes:Object.values(index.groups).reduce((n,g)=>n+g.bytes,0),largest:Object.entries(index.groups).sort((a,b)=>b[1].bytes-a[1].bytes).slice(0,5)}));
