"""Normalize generated geometry onto a common 1 mm grid and verify every feature."""
import argparse,json,subprocess
from pathlib import Path
from shapely import make_valid,set_precision
from shapely.geometry import shape
from shapely.geometry.polygon import orient

ROOT=Path(__file__).resolve().parents[1]
def polygons(g):
    if g.geom_type=='Polygon':return [g]
    return [p for child in getattr(g,'geoms',[]) for p in polygons(child)]

def run(node,server,work):
    script="const fs=require('fs'),tc=require('./node_modules/topojson-client'),t=JSON.parse(fs.readFileSync(process.argv[1]));process.stdout.write(JSON.stringify(tc.feature(t,t.objects.countries)));"
    for level in ('countries','countries-detail'):
        path=ROOT/'site/data'/(level+'.json')
        d=json.loads(subprocess.check_output([node,'-e',script,str(path)],cwd=ROOT))
        for f in d['features']:
            g=set_precision(make_valid(shape(f['geometry'])),1e-8)
            assert not g.is_empty and g.is_valid,f['properties']['k']
            ps=[orient(p,sign=-1) for p in polygons(g)]
            f['geometry']={'type':'MultiPolygon','coordinates':[[[[round(x*1e8),round(y*1e8)] for x,y in ring.coords] for ring in [p.exterior,*p.interiors]] for p in ps]}
        integer=work/(level+'-integer.geojson');integer.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
        subprocess.run([node,'--max-old-space-size=6000',str(ROOT/'scripts/finalize_osm_topology.cjs'),str(integer),str(path),server],cwd=ROOT,check=True)
        final=json.loads(subprocess.check_output([node,'-e',script,str(path)],cwd=ROOT))['features']
        invalid=[f['properties']['k'] for f in final if not f['geometry'] or not shape(f['geometry']).is_valid]
        assert not invalid,(level,invalid)
        print(json.dumps({'level':level,'validFeatures':len(final),'bytes':path.stat().st_size}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--node',default='node');p.add_argument('--topo-server',default=str(ROOT/'scripts/geodata-tools/node_modules/topojson-server'));p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.node,a.topo_server,a.work)
