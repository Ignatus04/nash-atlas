// Shared arcs are simplified once, never separately for the two neighbouring countries.
const fs=require('fs'),path=require('path'),os=require('os'),cp=require('child_process');
const server=require(process.argv[3]||'./geodata-tools/node_modules/topojson-server');
const mapshaper=process.argv[4]||require.resolve('./geodata-tools/node_modules/mapshaper/bin/mapshaper');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-borders-'));
const client=require('../node_modules/topojson-client');
const root=path.resolve(__dirname,'..');
const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const quantized=input.type==='Topology'?input:server.topology({countries:input},1e12);
const decode=client.transform(quantized.transform);
const topo={...quantized,arcs:quantized.arcs.map(a=>a.map(decode))};delete topo.transform;
const uses=new Uint16Array(topo.arcs.length);
function visit(g,fn){if(g.type==='GeometryCollection')return g.geometries.forEach(x=>visit(x,fn));const walk=a=>{if(typeof a==='number')fn(a<0?~a:a);else a.forEach(walk)};if(g.arcs)walk(g.arcs)}
for(const g of topo.objects.countries.geometries){const seen=new Set();visit(g,a=>seen.add(a));for(const a of seen)uses[a]++}
function area(ring){let sum=0;for(const id of ring){const a=topo.arcs[id<0?~id:id];let s=0;for(let i=1;i<a.length;i++)s+=a[i-1][0]*a[i][1]-a[i][0]*a[i-1][1];sum+=id<0?-s:s}return Math.abs(sum/2)}
function filtered(minArea){
  const attached=r=>r.some(a=>uses[a<0?~a:a]>1);
  const geometries=topo.objects.countries.geometries.map(g=>{
    const polygons=g.type==='Polygon'?[g.arcs]:g.arcs;
    const areas=polygons.map(p=>area(p[0])),largest=areas.indexOf(Math.max(...areas));
    const kept=polygons.filter((p,i)=>i===largest||attached(p[0])||areas[i]>=minArea).map(p=>[p[0],...p.slice(1).filter(r=>attached(r)||area(r)>=minArea)]);
    return {...g,type:'MultiPolygon',arcs:kept};
  });
  return {countries:{type:'GeometryCollection',geometries}};
}
for(const [name,minArea] of [['countries-detail',1e-5],['countries',.01]]){
  const objects=filtered(minArea),used=new Set();visit(objects.countries,a=>used.add(a));
  const order=[...used].sort((a,b)=>a-b),ids=new Map(order.map((a,i)=>[a,i]));
  const remap=a=>typeof a==='number'?(a<0?~ids.get(~a):ids.get(a)):a.map(remap);
  for(const g of objects.countries.geometries)g.arcs=remap(g.arcs);
  const arcs=order.map(i=>topo.arcs[i]);
  const raw=path.join(temp,name+'-raw.json'),clean=path.join(temp,name+'-clean.json');
  fs.writeFileSync(raw,JSON.stringify(client.quantize({...topo,objects,arcs},1e12)));
  const args=['--max-old-space-size=6000',mapshaper,raw,'-clean','allow-overlaps','snap-interval=0.00000000001'];
  if(name==='countries')args.push('-simplify','dp','interval=1000','keep-shapes','-clean','allow-overlaps','snap-interval=0.00000000001');
  args.push('-rename-layers','countries','-o',clean,'format=topojson','quantization=1000000000000');
  cp.execFileSync(process.execPath,args,{stdio:'inherit'});
  const result=JSON.parse(fs.readFileSync(clean,'utf8'));
  const codes=result.objects.countries.geometries.map(g=>g.properties.k);
  if(codes.length!==objects.countries.geometries.length||result.objects.countries.geometries.some(g=>!g.arcs))throw Error('Geometry cleaning lost a territory');
  result.license='ODbL-1.0';result.licenseUrl='https://opendatacommons.org/licenses/odbl/1-0/';
  result.attribution='© OpenStreetMap contributors; Terrae';result.source='Terrae ADM0 2026.10, OSM 2026-09-28; site adaptations documented in boundary-sources.json';
  const content=JSON.stringify(result);
  fs.writeFileSync(path.join(root,'site/data',name+'.json'),content);
  console.log(JSON.stringify({name,arcs:arcs.length,vertices:result.arcs.reduce((n,a)=>n+a.length,0),bytes:Buffer.byteLength(content)}));
}
