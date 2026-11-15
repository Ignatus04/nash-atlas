# For every region (admin-1) the city that is its administrative centre, and the list of all centres
# (national capitals and region capitals) that get a written description. Output: site/data/centers.json
import json
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
D = '/home/claude/site/data/'
t = json.load(open(D + 'admin1.json'))
sc, tr = t['transform']['scale'], t['transform']['translate']
arcs = []
for a in t['arcs']:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy; pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
    arcs.append(pts)
def ring(r):
    pts = []
    for i in r:
        seg = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts += seg if not pts else seg[1:]
    return pts
def geom(g):
    if g['type'] == 'Polygon': return {'type': 'Polygon', 'coordinates': [ring(r) for r in g['arcs']]}
    if g['type'] == 'MultiPolygon': return {'type': 'MultiPolygon', 'coordinates': [[ring(r) for r in p] for p in g['arcs']]}
regs = []
for o in t['objects'].values():
    for g in o['geometries']:
        if g.get('type') in ('Polygon', 'MultiPolygon'):
            try: regs.append((g['properties'], shape(geom(g)).buffer(0)))
            except Exception: pass
tree = STRtree([s for _, s in regs])
cities = json.load(open(D + 'cities.json'))
key = {(c[4], c[1]): c for c in cities}
pp = json.load(open('/home/claude/data/ne_10m_populated_places.geojson'))
fix = {'CYN': 'XN', 'SOL': 'XS', 'KOS': 'XK'}
centres, by_reg = [], {}
for f in pp['features']:
    q = f['properties']; cl = q.get('FEATURECLA') or ''
    if not (cl.startswith('Admin-1') or cl.startswith('Admin-0 capital')): continue
    iso = fix.get(q.get('ADM0_A3'), q.get('ISO_A2'))
    c = key.get((iso, q['NAME']))
    if not c: continue
    ck = iso + '|' + c[1]
    centres.append(ck)
    pt = Point(c[3], c[2])
    for i in tree.query(pt):
        p, s = regs[i]
        if s.contains(pt) or s.distance(pt) < 0.02:
            if p['k'] == iso or p['k'] in ('GF','GP','MQ','RE','YT','BQ','SJ'):
                old = by_reg.get(p['id'])
                if not old or (cl.startswith('Admin-0') or key[(old.split('|')[0], old.split('|',1)[1])][6] < c[6]): by_reg[p['id']] = ck
json.dump({'reg': by_reg, 'all': sorted(set(centres))}, open(D + 'centers.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('centres', len(set(centres)), 'regions with a centre', len(by_reg), 'of', len(regs))
