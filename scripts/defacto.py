# De facto control: carves territories whose real entry rules differ from the country that claims them.
#   XU  Ukraine's territory under Russian control (DeepStateMap line of the given day + Crimea)
#   XA  Abkhazia, XO South Ossetia (from Georgia), XT Transnistria (from Moldova)  — Natural Earth disputed areas
# Rewrites /tmp/c10c.geojson (countries) and /tmp/admin1c.geojson (regions); places/cities are reassigned elsewhere.
import json, sys
from shapely.geometry import shape, mapping, Point, box
from shapely.ops import unary_union

DS = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ds/f_20261114.geojson'
c = json.load(open('/tmp/c10b.geojson'))
da = json.load(open('/tmp/ne/da.geojson'))
adm = json.load(open('/tmp/admin1.geojson'))

def geo(k):
    return [f for f in c['features'] if f['properties']['k'] == k][0]
def g(f): return shape(f['geometry']).buffer(0)
def clean(x, min_area=1e-5):
    parts = [p for p in getattr(x, 'geoms', [x]) if p.geom_type == 'Polygon' and p.area > min_area]
    return unary_union(parts)

front = shape(json.load(open(DS))['features'][0]['geometry']).buffer(0)
UA, RU = geo('UA'), geo('RU')
ua, ru = g(UA), g(RU)
crimea_box = box(32.3, 44.3, 36.8, 46.3)
ru_crimea = clean(front.intersection(ru).intersection(crimea_box), 0.5)   # the peninsula only, not border slivers
xu = clean(unary_union([front.intersection(ua), ru_crimea]), 2e-4)
new = {'XU': (xu, 'Территории Украины под контролем России', 'Russian-controlled territories of Ukraine', 'UA')}
UA['geometry'] = mapping(clean(ua.difference(xu)))
RU['geometry'] = mapping(clean(ru.difference(ru_crimea)))

MUN = {f['properties']['shapeName']: shape(f['geometry']).buffer(0) for f in json.load(open('/tmp/gb/geo_ADM2.geojson'))['features']}
def brk(name): return unary_union([shape(f['geometry']).buffer(0) for f in da['features'] if f['properties']['BRK_NAME'] == name])
for k, name, ru_name, host in [('XA', 'Abkhazia', 'Абхазия', 'GE'), ('XO', 'South Ossetia', 'Южная Осетия', 'GE'), ('XT', 'Transnistria', 'Приднестровье', 'MD')]:
    H = geo(host); h = g(H); p = brk(name)
    # Georgia: Natural Earth outlines are coarse, so build from municipalities (geoBoundaries, OCHA)
    if k == 'XA':   # whole Abkhaz AR incl. upper Kodori, held by Abkhazia since 2008
        p = unary_union([MUN[m] for m in ('Gagra', 'Gudauta', 'Sokhumi', 'Gulripshi', 'Ochamchire', 'Gali')])
    if k == 'XO':   # Java and Akhalgori entirely; the Tskhinvali part of Gori/Kareli from NE
        p = unary_union([MUN['Java'], MUN['Akhalgori'], p.intersection(MUN['Gori']), p.intersection(MUN['Kareli'])])
    if k == 'XT':   # NE's left-bank units (Camenca, Grigoriopol, Bender…) are all PMR-held
        p = unary_union([p] + [shape(f['geometry']).buffer(0) for f in adm['features'] if f['properties']['k'] == 'MD' and f['properties']['ru'] in ('Каменка', 'Резина', 'левобережье Днестра', 'Григорио́поль', 'Бендеры', 'Приднестровье')])
    p = clean(p.intersection(h))
    H['geometry'] = mapping(clean(h.difference(p)))
    new[k] = (p, ru_name, name, host)


# --- other de facto fixes (Wikipedia: List of territorial disputes, checked 14.11.2026) ---
gm = json.load(open('/home/claude/build/node_modules/@geo-maps/countries-land-100m/map.geo.json'))
osm_tw = [shape(f['geometry']).buffer(0) for f in gm['features'] if f['properties']['A3'] == 'TWN'][0]
TW = geo('TW')   # Matsu and Pratas are held by the ROC but were missing
TW['geometry'] = mapping(unary_union([g(TW), osm_tw.intersection(box(119.8, 25.9, 120.6, 26.45)), osm_tw.intersection(box(116.6, 20.6, 116.8, 20.8))]))
CY, XN = geo('CY'), geo('XN')   # the island outline of Cyprus covered the north too
nc = unary_union([shape(f['geometry']).buffer(0) for f in da['features'] if f['properties']['BRK_NAME'] == 'N. Cyprus'])
c10 = json.load(open('/tmp/c10.geojson'))
south = unary_union([shape(f['geometry']).buffer(0) for f in c10['features'] if f['properties']['k'] == 'CY'])
bz = unary_union([shape(f['geometry']).buffer(0) for f in da['features'] if 'Buffer Zone' in f['properties']['BRK_NAME']])
mask = nc.buffer(0.06).difference(south.buffer(0.003)).difference(bz)   # reach out to the precise coastline, but never south of the Green Line
xn = clean(unary_union([g(CY), g(XN)]).intersection(mask))
from shapely.geometry import Polygon, MultiPolygon
# keep the main north and the Kokkina exclave; specks near Dhekelia go back to the south
xn = unary_union([q for q in getattr(xn, 'geoms', [xn]) if q.area > 0.01 or q.centroid.x < 32.7])
def fill_holes(geom, max_area=0.002):
    out = []
    for q in getattr(geom, 'geoms', [geom]):
        out.append(Polygon(q.exterior, [r for r in q.interiors if Polygon(r).area > max_area]))
    return unary_union(out)
XN['geometry'] = mapping(xn); CY['geometry'] = mapping(fill_holes(clean(g(CY).difference(xn))))
IN = geo('IN')   # Siachen glacier and Saltoro ridge: held by India since 1984, was a hole
sia = unary_union([shape(f['geometry']).buffer(0) for f in da['features'] if f['properties']['BRK_NAME'] == 'Siachen Glacier'])
IN['geometry'] = mapping(unary_union([g(IN), sia]))

for k, (p, ru_name, en, host) in new.items():
    c['features'].append({'type': 'Feature', 'properties': {'k': k, 'ru': ru_name, 'en': en, 'sov': geo(host)['properties']['sov'], 'area': 0, 'small': 0}, 'geometry': mapping(p)})
    print(k, round(p.area, 3))
geo('TW')['properties']['ru'] = 'Тайвань (Китайская Республика)'
json.dump(c, open('/tmp/c10c.geojson', 'w'))

# regions: cut the host's regions along the same lines
out = []
for f in adm['features']:
    k = f['properties']['k']
    cuts = [(nk, v[0]) for nk, v in new.items() if v[3] == k]
    if not cuts: out.append(f); continue
    s = shape(f['geometry']).buffer(0); rest = s
    for nk, p in cuts:
        i = clean(s.intersection(p), 1e-3)
        rest = rest.difference(p)
        if nk != 'XU': continue   # small entities get one region of their own below
        if not i.is_empty and (i.area > 0.25 * s.area or i.area > 0.1):
            pr = dict(f['properties']); pr['k'] = nk; pr['id'] = pr['id'] + '-' + nk
            c_ = i.representative_point(); pr['lat'], pr['lon'] = round(c_.y, 4), round(c_.x, 4)
            out.append({'type': 'Feature', 'properties': pr, 'geometry': mapping(i)})
    rest = clean(rest, 1e-3)
    if not rest.is_empty and (rest.area > 0.25 * s.area or rest.area > 0.1):
        f['geometry'] = mapping(rest); out.append(f)
for nk in ('XA', 'XO', 'XT'):
    p, ru_name, en, host = new[nk]; c_ = p.representative_point()
    out.append({'type': 'Feature', 'properties': {'id': 'DF-' + nk, 'ru': ru_name, 'en': en, 'k': nk, 't': 'Territory', 'lat': round(c_.y, 4), 'lon': round(c_.x, 4)}, 'geometry': mapping(p)})
# Crimea / Sevastopol were Russian regions in this data: hand them to XU
for f in out:
    if f['properties']['k'] == 'RU' and shape(f['geometry']).representative_point().within(new['XU'][0]):
        f['properties']['k'] = 'XU'
adm['features'] = out
json.dump(adm, open('/tmp/admin1c.geojson', 'w'))
json.dump({k: mapping(v[0]) for k, v in new.items()}, open('/tmp/defacto_polys.json', 'w'))
print('regions', len(out))
