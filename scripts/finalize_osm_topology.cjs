// Infer topology on a common integer grid, without rescaling the grid to a bbox.
// This avoids re-introducing microscopic crossings while encoding TopoJSON.
const fs=require('fs'),server=require(process.argv[4]||'./geodata-tools/node_modules/topojson-server');
const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const t=server.topology({countries:input});
t.arcs=t.arcs.map(a=>{let x=0,y=0;return a.map(p=>{const d=[p[0]-x,p[1]-y];x=p[0];y=p[1];return d})});
t.transform={scale:[1e-8,1e-8],translate:[0,0]};if(t.bbox)t.bbox=t.bbox.map(x=>x*1e-8);
t.license='ODbL-1.0';t.licenseUrl='https://opendatacommons.org/licenses/odbl/1-0/';t.attribution='© OpenStreetMap contributors; Terrae';
t.source='Terrae ADM0 2026.10, OSM 2026-09-28; site adaptations documented in boundary-sources.json';
fs.writeFileSync(process.argv[3],JSON.stringify(t));
