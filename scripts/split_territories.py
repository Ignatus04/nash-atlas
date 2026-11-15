# Overseas parts that Natural Earth keeps inside their country become countries of their own on the map,
# because their entry rules differ (French overseas departments, Caribbean Netherlands, Svalbard...).
# Also gives Clipperton its own key and folds tiny uninhabited Australian islands into Australia, so every
# key on the map belongs to exactly one shape. Safe to run more than once.
import json

D = '/home/claude/site/data/'
SPLIT = {  # sovereign key -> [(new key, lon0, lon1, lat0, lat1)]
    'FR': [('GF', -55, -51, 2, 6.5), ('GP', -62, -60.9, 15.8, 16.6), ('MQ', -61.3, -60.7, 14.3, 14.95),
           ('RE', 55, 56, -21.5, -20.8), ('YT', 44.9, 45.4, -13.1, -12.5)],
    'NL': [('BQ', -69, -62, 11, 18)],
    'NO': [('SJ', 0, 40, 74, 82), ('SJ', -9.5, -7, 70.5, 71.5), ('BV', 2, 5, -56, -53)],
}
SMALL = {'GF': 0}
NAMES = {'GF': 'French Guiana', 'GP': 'Guadeloupe', 'MQ': 'Martinique', 'RE': 'Réunion', 'YT': 'Mayotte',
         'BQ': 'Caribbean Netherlands', 'SJ': 'Svalbard and Jan Mayen', 'BV': 'Bouvet Island',
         'CX': 'Christmas Island', 'CC': 'Cocos (Keeling) Islands', 'CP': 'Clipperton Island'}

t = json.load(open(D + 'countries.json'))
sc, tr = t['transform']['scale'], t['transform']['translate']
arcs = []
for a in t['arcs']:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy; pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
    arcs.append(pts)

def centre(poly):
    pts = []
    for i in poly[0]:
        pts += arcs[i] if i >= 0 else arcs[~i][::-1]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

def polys(g):
    return [g['arcs']] if g['type'] == 'Polygon' else list(g['arcs'])

def setp(g, ps):
    if len(ps) == 1: g['type'], g['arcs'] = 'Polygon', ps[0]
    else: g['type'], g['arcs'] = 'MultiPolygon', ps

obj = next(iter(t['objects'].values()))
G = obj['geometries']
have = {g['properties']['k'] for g in G}
added = []
for sov, rules in SPLIT.items():
    g = next(x for x in G if x['properties']['k'] == sov and not x['properties'].get('small'))
    keep, out = [], {}
    for p in polys(g):
        lon, lat = centre(p)
        hit = next((r[0] for r in rules if r[1] <= lon <= r[2] and r[3] <= lat <= r[4]), None)
        if hit and hit not in have: out.setdefault(hit, []).append(p)
        else: keep.append(p)
    setp(g, keep)
    for k, ps in out.items():
        n = {'type': 'Polygon', 'arcs': [], 'properties': {**g['properties'], 'k': k, 'en': NAMES[k], 'ru': NAMES[k], 'small': SMALL.get(k, 1)}}
        setp(n, ps); G.append(n); added.append(k)

# Clipperton had France's key; the tiny Australian islands had Australia's
for g in G:
    if g['properties']['en'] == 'Clipperton I.': g['properties']['k'] = 'CP'; g['properties']['en'] = NAMES['CP']
au = next(x for x in G if x['properties']['k'] == 'AU' and not x['properties'].get('small'))
rest = []
for g in G:
    if g['properties']['k'] == 'AU' and g is not au:
        if g['properties']['en'] == 'Indian Ocean Ter.':
            for p in polys(g):
                lon, lat = centre(p); k = 'CX' if lon > 100 else 'CC'
                n = next((x for x in rest if x['properties']['k'] == k), None)
                if not n:
                    n = {'type': 'Polygon', 'arcs': [], 'properties': {**g['properties'], 'k': k, 'en': NAMES[k], 'ru': NAMES[k]}}
                    rest.append(n); added.append(k)
                setp(n, polys(n) + [p] if n['arcs'] else [p])
        else:
            setp(au, polys(au) + polys(g))
        g['drop'] = True
obj['geometries'] = [g for g in G if not g.get('drop')] + rest
json.dump(t, open(D + 'countries.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('countries: new', added)

# regions of the overseas parts move with them
a = json.load(open(D + 'admin1.json'))
moved = []
for sov, rules in SPLIT.items():
    o = a['objects'].get(sov)
    if not o: continue
    stay = []
    for g in o['geometries']:
        p = g['properties']
        hit = next((r[0] for r in rules if r[1] <= p['lon'] <= r[2] and r[3] <= p['lat'] <= r[4]), None)
        if hit:
            p['k'] = hit
            a['objects'].setdefault(hit, {'type': 'GeometryCollection', 'geometries': []})['geometries'].append(g)
            moved.append((hit, p['en']))
        else: stay.append(g)
    o['geometries'] = stay
json.dump(a, open(D + 'admin1.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('regions moved', moved)

# names, flags and entry rules for keys that had none
m = json.load(open(D + 'meta.json'))
m.setdefault('CP', {'cap': [], 'cur': ['EUR'], 'lang': [['fra', 'French']], 'reg': 'Americas', 'sub': 'Central America', 'flag': '🇫🇷', 'll': [10.3, -109.2], 'ru': 'Клиппертон'})
json.dump(m, open(D + 'meta.json', 'w'), ensure_ascii=False, separators=(',', ':'))
f = json.load(open(D + 'flags.json'))
f.setdefault('CP', f['FR'])
json.dump(f, open(D + 'flags.json', 'w'), ensure_ascii=False, separators=(',', ':'))
v = json.load(open(D + 'visa.json'))
for p, fn in (('ru', 'ru.txt'), ('by', 'by.txt')):
    for line in open('/home/claude/data/visa/' + fn, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line: continue
        cc, code, stay, note = line.split('|', 3)
        if cc in NAMES: v[p][cc] = {'c': code, 's': stay, 'n': note, 'src': 'wiki'}
json.dump(v, open(D + 'visa.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('visa', {k: (v['ru'].get(k, {}).get('c'), v['by'].get(k, {}).get('c')) for k in NAMES})
