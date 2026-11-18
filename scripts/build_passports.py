# Any passport: entry rules from Passport Index (Feb 2026, MIT) and real cover photos from Wikimedia Commons (free licences).
import json, csv, logging, re
import country_converter as coco
logging.getLogger('country_converter').setLevel(logging.CRITICAL)
D = '/home/claude/site/data/'
meta = json.load(open(D + 'meta.json'))
rows = list(csv.DictReader(open('/tmp/pi/tidy26.csv')))
P = sorted({r['Passport'] for r in rows}); DEST = sorted({r['Destination'] for r in rows})
CODE = {'visa free': 'F', 'visa on arrival': 'A', 'eta': 'E', 'e-visa': 'V', 'visa required': 'R', 'no admission': 'X', '-1': 'H'}
m = {}
for r in rows:
    q = r['Requirement']; c = 'F' if q.isdigit() else CODE.get(q, 'U')
    m.setdefault(r['Passport'], {})[r['Destination']] = (c, int(q) if q.isdigit() else 0)
# territories missing from the matrix: follow whoever controls entry there
FOLLOW = {'XU': 'RU', 'XT': 'MD', 'PR': 'US', 'GU': 'US', 'VI': 'US', 'AS': 'US', 'MP': 'US', 'AX': 'FI', 'SJ': 'NO', 'VA': 'IT', 'SM': 'IT', 'MC': 'FR', 'GG': 'GB', 'JE': 'GB', 'IM': 'GB'}
dests = [k for k in meta if isinstance(meta[k], dict)]
codes, days = {}, {}
for p in P:
    s, d = [], []
    for k in dests:
        src = k if k in m[p] else FOLLOW.get(k)
        c, n = m[p].get(src, ('U', 0)) if src else ('U', 0)
        if p == k: c = 'H'
        if src and src != k and p == src: c = 'M'   # own country's territory (e.g. RU→XU): free movement
        s.append(c); d.append(n)
    codes[p] = ''.join(s); days[p] = d
# cover photos
cov = {}
FIX = {'Taiwan': 'TW', 'Kosovo': 'XK', 'Palestine': 'PS', 'State of Palestine': 'PS', 'Hong Kong': 'HK', 'Macau': 'MO', 'Macao': 'MO', 'Vatican City': 'VA',
       'Sahrawi Arab Democratic Republic': None, 'Somaliland': 'XS', 'Northern Cyprus': 'XN', 'Transnistria': 'XT', 'Abkhazia': 'XA', 'South Ossetia': 'XO', 'Republic of the Congo': 'CG', 'Congo': 'CG'}
for x in json.load(open('/tmp/ppd/atlas-passports.json')):
    name = re.sub(r'\s*\(.*?\)', '', x['country']).strip()
    k = FIX[name] if name in FIX else coco.convert(name, to='ISO2', not_found=None)
    if not isinstance(k, str) or not x.get('img'): continue
    if k in cov: continue
    cov[k] = {'img': x['img'], 'lic': x.get('lic'), 'by': (x.get('artist') or x.get('credit') or '').strip(), 'page': x.get('page')}
for x in json.load(open('/tmp/ppd/atlas-passports-2.json')):
    cov.setdefault(x['k'], {'img': x['img'], 'lic': x.get('lic'), 'by': x.get('artist', ''), 'page': x.get('page')})
json.dump({'updated': '2026-02-17', 'dest': dests, 'p': codes, 'd': days}, open(D + 'visa_all.json', 'w'), separators=(',', ':'))
# Identity pages and unclear attribution-only files must never be restored.
for k in ('PY','UY','GL','FO'): cov.pop(k,None)
# Preserve the separately reviewed CC0 cover; never restore the former identity page.
try:
    reviewed=json.load(open(D+'passports.json')).get('PY')
    if reviewed and reviewed.get('page')=='https://commons.wikimedia.org/wiki/File:PARAGUAY_PASSPORT_PIC.webp' and reviewed.get('lic')=='CC0': cov['PY']=reviewed
except (OSError,ValueError): pass
json.dump(cov, open(D + 'passports.json', 'w'), separators=(',', ':'))
import os
print('passports', len(P), 'covers', len(cov), 'missing covers', sorted(set(P) - set(cov)))
print('sizes', os.path.getsize(D + 'visa_all.json'), os.path.getsize(D + 'passports.json'))
