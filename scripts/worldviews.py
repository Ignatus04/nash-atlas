# Borders as each country officially sees them.
# Input:  scripts/src/countries_defacto.topo.json (the de facto map the site always had), scripts/src/ne_10m_admin_0_disputed_areas.geojson + data/ne_10m_admin_0_countries.geojson (Natural Earth, not in the repo)
#         (Natural Earth: who owns each disputed area in 31 countries' points of view), site/data/admin1.json (Ukrainian regions).
# Output: site/data/countries.json — the same map with disputed areas cut out as separate pieces (key "~…"),
#         site/data/worldviews.json — for each viewer country, which pieces/territories go to which country.
# The site merges pieces into owners at load (topojson.mergeArcs), so a viewer never sees a piece on its own.
import json, subprocess, os
from shapely.geometry import shape, mapping, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

R = '/home/claude/'
BUILD = R + 'build/'
def topo2geo(path, objs=None):
    js = ("const t=require(%r),tc=require('topojson-client');const ks=%s||Object.keys(t.objects);"
          "const f=[];for(const k of ks)if(t.objects[k])f.push(...tc.feature(t,t.objects[k]).features);"
          "process.stdout.write(JSON.stringify({type:'FeatureCollection',features:f}))") % (path, json.dumps(objs))
    return json.loads(subprocess.run(['node', '-e', js], cwd=BUILD, capture_output=True, text=True, check=True).stdout)

base = topo2geo(R + 'scripts/src/countries_defacto.topo.json')['features']
G = {i: shape(f['geometry']).buffer(0) for i, f in enumerate(base)}
K = [f['properties']['k'] for f in base]
def idx(k): return [i for i in range(len(base)) if K[i] == k and not base[i]['properties'].get('small')][0]
KM2 = 111 * 111 * 0.75
pieces = []      # (key, geometry, host key, ru name)

def cut(host, geom, key, ru):
    i = idx(host); h = G[i]; p = h.intersection(geom)
    p = unary_union([g for g in getattr(p, 'geoms', [p]) if g.geom_type == 'Polygon' and g.area > 1e-5])
    if p.is_empty: return False
    rest = h.difference(p).buffer(0); near = p.buffer(1e-4)
    # slivers left along the cut (the two sources draw borders a little differently) are dropped; real islands are kept
    G[i] = unary_union([q for q in getattr(rest, 'geoms', [rest]) if q.geom_type == 'Polygon' and (q.area > 2e-3 or not q.intersects(near))])
    pieces.append((key, p, host, ru)); return True

# Ukraine: Russia's claim is the full Donetsk, Luhansk, Zaporizhzhia, Kherson regions + Crimea and Sevastopol.
ua = {f['properties']['id']: shape(f['geometry']).buffer(0) for f in topo2geo(R + 'site/data/admin1.json', ['UA', 'XU'])['features']}
# the whole claimed area, occupied parts included: the de facto Ukraine has slivers along the occupied regions' edges, and they must go with the claim
free_claim = unary_union([ua[i] for i in ua if i.split('-')[1] in ('327', '4827', '331', '329', '283', '5482')]).buffer(0.01)
cut('UA', free_claim, '~UA-claim', 'Подконтрольная Украине часть Донецкой, Запорожской и Херсонской областей')
cut('XU', ua['UKR-328-XU'].buffer(0.003), '~UA-kharkiv', 'Занятая часть Харьковской области')
# Russian islets off Crimea (Tuzla in the Kerch Strait) belong with Crimea
ri, xi = idx('RU'), idx('XU'); crimea = ua['RUS-283'].buffer(0.1)
isl = [q for q in G[ri].geoms if q.area < 0.02 and crimea.contains(q.representative_point())]
if isl: G[ri] = unary_union([q for q in G[ri].geoms if q not in isl]); G[xi] = unary_union([G[xi], *isl]); print('islets to Crimea', len(isl))

# Natural Earth disputed areas that some country assigns to a different country
ne = json.load(open(R + 'data/ne_10m_admin_0_countries.geojson'))['features']
SPECIAL = {'CYN': 'XN', 'SOL': 'XS', 'KOS': 'XK', 'SAH': 'EH', 'PSX': 'PS', 'TWN': 'TW'}
A3 = dict(SPECIAL)
for f in ne:
    p = f['properties']; a3 = p['ADM0_A3']
    if a3 in A3: continue
    k = p.get('ISO_A2_EH') if p.get('ISO_A2_EH') not in (None, '-99') else p.get('ISO_A2')
    if k and k != '-99': A3[a3] = k
A3['KOR'] = 'KR'
da = json.load(open(R + 'scripts/src/ne_10m_admin_0_disputed_areas.geojson'))['features']
POV = {c[8:]: c for c in da[0]['properties'] if c.startswith('ADM0_A3_') and c[8:] not in ('UN', 'WB')}
VIEWER = {pov: ('KR' if pov == 'KO' else pov) for pov in POV}      # NE uses KO for South Korea
WHOLE = {'Kosovo': 'XK', 'Abkhazia': 'XA', 'South Ossetia': 'XO', 'N. Cyprus': 'XN', 'Somaliland': 'XS',
         'Taiwan': 'TW', 'Transnistria': 'XT', 'Falkland Is.': 'FK', 'S. Georgia': 'GS'}
SKIP = {'Crimea', "Donetsk People's Republic", "Luhansk People's Republic", 'Artsakh'}   # Ukraine handled above; Artsakh is Azerbaijan's since 2023
RU_NAMES = {'Jammu and Kashmir': 'Джамму и Кашмир', 'Aksai Chin': 'Аксайчин', 'Arunachal Pradesh': 'Аруначал-Прадеш',
            'Shaksam Valley': 'Шаксгам', 'Gilgit-Baltistan': 'Гилгит-Балтистан', 'Azad Kashmir': 'Азад Кашмир',
            'Golan Heights': 'Голанские высоты', 'W. Sahara': 'Западная Сахара', 'Kuril Is.': 'Южные Курилы',
            'Junagadh and Manavadar': 'Джунагадх', 'Olivenza': 'Оливенса', 'Siachen Glacier': 'Сиачен',
            'Demchok': 'Демчок', 'Tirpani Valleys': 'Долина Тирпани', 'Samdu Valleys': 'Долина Самду',
            'Bara Hotii Valleys': 'Бара-Хоти', 'Bhutan (northwest valleys)': 'Долины северо-запада Бутана',
            'Bhutan (Chumbi salient)': 'Чумби', 'Gaza': 'Газа', 'West Bank': 'Западный берег'}
owner = {}         # key -> {viewer: owner key}
for f in da:
    p = f['properties']; name = p['BRK_NAME'].strip('﻿')
    if name in SKIP: continue
    o = {v: A3.get(str(p[c])) for v, c in ((VIEWER[pv], c) for pv, c in POV.items())}
    o = {v: k for v, k in o.items() if k}
    if name in WHOLE or (name == 'W. Sahara' and p['ADM0_A3'] == 'SAH'):
        key = WHOLE.get(name, 'EH')
    else:
        g = shape(f['geometry']).buffer(0)
        if g.area * KM2 < 200 or name not in RU_NAMES: continue
        host = max(range(len(base)), key=lambda i: G[i].intersection(g).area)
        hk = K[host]
        if all(v == hk for v in o.values()): continue
        key = '~' + name
        if not cut(hk, g, key, RU_NAMES[name]): continue
    owner.setdefault(key, {}).update({v: k for v, k in o.items()})

# viewers: Natural Earth's 31, plus our own rules
# the international view (UN positions): occupied or breakaway areas go back to the recognized state
INTL = {'XU': 'UA', '~UA-kharkiv': 'UA', 'XA': 'GE', 'XO': 'GE', 'XT': 'MD', 'XN': 'CY', 'XS': 'SO', '~Golan Heights': 'SY', '~W. Sahara': 'EH'}
views = {}
for v in VIEWER.values():
    # start from the international view; Natural Earth says where this country differs (codes for "disputed" fall back)
    m = {**INTL, **{k: o[v] for k, o in owner.items() if v in o}}
    m.update({'XU': 'UA', '~UA-kharkiv': 'UA'})               # Ukraine's own borders for everyone but Russia
    views[v] = m
views['RU'].update({'XU': 'RU', '~UA-claim': 'RU', '~UA-kharkiv': 'UA', 'XA': 'XA', 'XO': 'XO'})   # Russia recognizes Abkhazia and South Ossetia
views['BY'] = {**{k: v for k, v in views['RU'].items() if k not in ('XU', '~UA-claim', '~UA-kharkiv')}, 'XA': 'GE', 'XO': 'GE'}
for v in ('RS',): views[v] = {**INTL, 'XK': 'RS'}
# Slivers: the source map has small bits of one country lying along another's border (Russian bits in Crimea,
# Ukrainian bits along the occupied areas). Under the fill of the neighbour they were invisible; once areas merge they show.
# A small part whose outline mostly runs along one neighbour joins that neighbour; real islands along a coast stay.
from shapely.strtree import STRtree
units = [(('f', i), G[i]) for i in G if not G[i].is_empty and not base[i]['properties'].get('small')] + [(('p', n), pieces[n][1]) for n in range(len(pieces))]
tree = STRtree([g for _, g in units])
moved = 0
for ui, (uid, g) in enumerate(units):
    parts = list(getattr(g, 'geoms', [g]))
    if len(parts) < 2: continue
    keep = []
    for q in parts:
        if q.area > 0.02 or q.area == max(x.area for x in parts): keep.append(q); continue
        ring = q.exterior; best, bl = None, 0
        for j in tree.query(q.buffer(0.003)):
            if j == ui: continue
            l = ring.intersection(units[j][1].buffer(0.003)).length
            if l > bl: best, bl = j, l
        if best is not None and bl > 0.5 * ring.length:
            units[best] = (units[best][0], unary_union([units[best][1], q.buffer(0.0005)]).buffer(0)); moved += 1
        else: keep.append(q)
    units[ui] = (uid, unary_union(keep))
for (kind, n), g in units:
    if kind == 'f': G[n] = g
    else: pieces[n] = (pieces[n][0], g, pieces[n][2], pieces[n][3])
print('slivers moved', moved)
# write the map. d3 draws on a sphere and reads a counter-clockwise ring as "everything except this", so every outer ring goes clockwise
def cw(g): return MultiPolygon([orient(q, -1.0) for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon']) if g.geom_type == 'MultiPolygon' else orient(g, -1.0)
G = {i: (cw(g) if not g.is_empty else g) for i, g in G.items()}
pieces = [(k, cw(g), h, ru) for k, g, h, ru in pieces]
feats = []
for i, f in enumerate(base):
    if G[i].is_empty: continue
    f['geometry'] = mapping(G[i]); feats.append(f)
for key, g, host, ru in pieces:
    feats.append({'type': 'Feature', 'properties': {'k': key, 'host': host, 'ru': ru, 'en': key[1:], 'sov': '', 'area': 0, 'small': 0}, 'geometry': mapping(g)})
json.dump({'type': 'FeatureCollection', 'features': feats}, open('/tmp/wv.geojson', 'w'))
# mapshaper snaps nearly-equal vertices and fixes slivers, so a piece and its neighbours share one border line;
# otherwise a merged country keeps a hairline where the piece was
subprocess.run([BUILD + 'node_modules/.bin/mapshaper', '-i', '/tmp/wv.geojson', 'snap', 'snap-interval=0.002', '-clean', 'gap-fill-area=20km2', 'allow-overlaps',
                '-rename-layers', 'c10b', '-o', R + 'site/data/countries.json', 'format=topojson', 'quantization=1000000', 'force'], check=True)
# Ukrainian names for cities in the occupied areas (Natural Earth NAME_UK): shown when the city is in Ukraine in this view
import math
places = json.load(open(R + 'data/ne_10m_populated_places.geojson'))['features']
cityUk = {}
for c in json.load(open(R + 'site/data/cities.json')):
    if c[4] != 'XU': continue
    q = min(places, key=lambda f: math.hypot(f['properties']['LATITUDE'] - c[2], f['properties']['LONGITUDE'] - c[3]))['properties']
    if math.hypot(q['LATITUDE'] - c[2], q['LONGITUDE'] - c[3]) < 0.1 and q.get('NAME_UK'): cityUk[c[1]] = q['NAME_UK']
# region names as the owner calls them, by region id without the "-XU" suffix
regionNames = {'RU': {'UKR-327': 'Донецкая Народная Республика', 'UKR-329': 'Луганская Народная Республика',
                      'RUS-283': 'Республика Крым', 'RUS-5482': 'Севастополь'}}
json.dump({'intl': INTL, 'views': views, 'cityUk': cityUk, 'regionNames': regionNames, 'source': 'Natural Earth disputed areas (public domain), DB-IP Lite'},
          open(R + 'site/data/worldviews.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('pieces', [(k, h, round(g.area * KM2)) for k, g, h, _ in pieces])
print('views', len(views), 'RU', views['RU'])
