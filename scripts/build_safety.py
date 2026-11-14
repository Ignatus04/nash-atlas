# Safety layer: country levels and "do not go" regions, taken first from the government that knows the place best.
# Sources (fetched 14.11.2026 through the user's browser into /tmp/sec):
#   US State Dept (cadataapi), Canada (data.international.gc.ca), UK FCDO (gov.uk content API),
#   Australia Smartraveller, France Diplomatie, Russian decree 757 response levels, ACLED via HDX.
import json, re, unicodedata, html, warnings
from collections import defaultdict
import country_converter as coco
import openpyxl
warnings.filterwarnings('ignore')
import logging; logging.getLogger('country_converter').setLevel(logging.CRITICAL)

S = '/tmp/sec/'
D = '/home/claude/site/data/'
meta = json.load(open(D + 'meta.json'))
OUR = set(meta)
cc = coco.CountryConverter()

def iso2(name):
    fix = {'Kosovo': 'XK', 'Côte d\'Ivoire': 'CI', "Cote d'Ivoire": 'CI', 'Micronesia': 'FM', 'Bonaire, Sint Eustatius, and Saba': 'BQ',
           'The Bahamas': 'BS', 'The Gambia': 'GM', 'Burma': 'MM', 'Burma (Myanmar)': 'MM', 'Mainland China': 'CN', 'China': 'CN',
           'Hong Kong': 'HK', 'Macau': 'MO', 'Macao': 'MO', 'North Korea': 'KP', 'South Korea': 'KR', 'Turkey': 'TR', 'Türkiye': 'TR',
           'The Occupied Palestinian Territories': 'PS', 'Israel, the West Bank and Gaza': 'IL', 'Israel, The West Bank and Gaza': 'IL',
           'Congo, Democratic Republic': 'CD', 'Democratic Republic of the Congo': 'CD', 'Republic of the Congo': 'CG', 'Congo': 'CG'}
    if name in fix: return fix[name]
    r = cc.convert(name, to='ISO2', not_found=None)
    return r if isinstance(r, str) else None

def clean(t):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t or ''))
    return re.sub(r'\s+', ' ', t).strip()

# ---------------- sources ----------------
US = {}
for x in json.load(open(S + 'atlas-sec-us.json')):
    name = x['Title'].split(' - Level')[0].split(' – Level')[0].strip()
    m = re.search(r'Level (\d)', x['Title'])
    k = iso2(name)
    if k and m: US[k] = {'lvl': int(m.group(1)), 'text': clean(x['Summary']), 'upd': x['Updated'][:10], 'name': name}
CA = {}
for k, v in json.load(open(S + 'atlas-sec-ca.json'))['data'].items():
    k = v.get('country-iso') or k
    CA[k] = {'lvl': {0: 1, 1: 2, 2: 3, 3: 4}[v['advisory-state']], 'regional': bool(v.get('has-regional-advisory')),
             'text': v['eng']['advisory-text'], 'upd': v['date-published']['date'][:10], 'slug': v['eng']['url-slug']}
UK = {}
for x in json.load(open(S + 'atlas-sec-uk.json')):
    k = iso2(x['country']['name']) if x.get('country') else None
    if not k: continue
    al = x.get('alert') or []
    lvl = 4 if 'avoid_all_travel_to_whole_country' in al else 3 if 'avoid_all_but_essential_travel_to_whole_country' in al else None
    UK[k] = {'lvl': lvl, 'parts': any('parts' in a for a in al), 'text': x['warn'] + ' ' + x.get('regional', ''), 'upd': x['upd'][:10], 'slug': x['slug']}
AU = {}
AUL = {'Exercise normal safety precautions': 1, 'Exercise a high degree of caution': 2, 'Reconsider your need to travel': 3, 'Do not travel': 4}
for x in json.load(open(S + 'atlas-sec-au.json')):
    k = iso2(x['name'])
    if k and x['level'] in AUL: AU[k] = {'lvl': AUL[x['level']], 'text': x.get('text', ''), 'upd': x['upd'], 'href': x.get('href')}
FR = {}
for x in json.load(open(S + 'atlas-sec-fr.json')):
    if not x.get('t'): continue
    k = {'republique-democratique-du-congo': 'CD', 'congo': 'CG', 'republique-centrafricaine': 'CF', 'cote-d-ivoire': 'CI', 'guinee-equatoriale': 'GQ',
         'cap-vert': 'CV', 'sao-tome-et-principe': 'ST', 'maurice': 'MU', 'comores': 'KM', 'tchad': 'TD', 'guinee': 'GN', 'gambie': 'GM',
         'liban': 'LB', 'syrie': 'SY', 'egypte': 'EG', 'libye': 'LY', 'maroc': 'MA', 'algerie': 'DZ', 'tunisie': 'TN', 'mauritanie': 'MR',
         'senegal': 'SN', 'mali': 'ML', 'burkina-faso': 'BF', 'niger': 'NE', 'benin': 'BJ', 'togo': 'TG', 'cameroun': 'CM', 'gabon': 'GA',
         'madagascar': 'MG', 'djibouti': 'DJ', 'haiti': 'HT', 'burundi': 'BI', 'rwanda': 'RW', 'seychelles': 'SC', 'vanuatu': 'VU',
         'sierra-leone': 'SL', 'liberia': 'LR', 'ghana': 'GH', 'nigeria': 'NG'}.get(x['s'])
    if k: FR[k] = {'text': x['t'], 'slug': x['s']}

# ---------------- who knows the place best ----------------
AMERICAS = {k for k, m in meta.items() if isinstance(m, dict) and m.get('reg') == 'Americas'}
FRANCO = set(FR) - {'GH', 'NG', 'SL', 'LR', 'EG', 'SY', 'LY'}          # anglophone and Arab-east countries go to the UK
ASIAPAC = {k for k in AU if (meta.get(k) or {}).get('reg') in ('Oceania',) or (meta.get(k) or {}).get('sub') in ('South-Eastern Asia', 'Eastern Asia')}
RUSSIA = {'RU', 'BY', 'XA', 'XO', 'XT', 'XU'}
def primary(k):
    if k in RUSSIA: return 'ru'
    if k in AMERICAS and k in US: return 'us'
    if k in FRANCO: return 'fr'
    if k in ASIAPAC: return 'au'
    if k in UK: return 'uk'
    if k in US: return 'us'
    if k in AU: return 'au'
    return None

def median(xs):
    xs = sorted(x for x in xs if x); return xs[len(xs) // 2] if xs else None

# ---------------- regions mentioned as dangerous ----------------
ne1 = json.load(open('/home/claude/data/ne_10m_admin_1_states_provinces.geojson'))['features']
ours = {f['properties']['id'] for f in json.load(open('/tmp/admin1c.geojson'))['features']}
def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9 ]+', ' ', s).strip()
GENERIC = {'north', 'south', 'east', 'west', 'central', 'capital', 'eastern', 'western', 'northern', 'southern', 'centre', 'center', 'north east', 'north west',
           'south east', 'south west', 'coast', 'lake', 'river', 'island', 'islands', 'city', 'national', 'federal', 'union', 'border', 'interior', 'littoral', 'sud', 'nord', 'est', 'ouest', 'centre est'}
STRIP = r'^(state of|province of|provincia de|provincia del|departamento de|departamento del|region de|region|region of|governorate of|estado de|estado|oblast|wilayah|province|department|district|county|municipality of)\s+'
ADM = defaultdict(list)
for f in ne1:
    p = f['properties']; k = p.get('iso_a2')
    if p['adm1_code'] not in ours or not k: continue
    names = set()
    for key in ('name', 'name_en', 'woe_name', 'gn_name', 'name_alt'):
        for v in (p.get(key) or '').split('|'):
            v = norm(v)
            v = re.sub(STRIP, '', v)
            v = re.sub(r'\s+(state|province|region|governorate|department|oblast|district|prefecture)$', '', v)
            if len(v) >= 4 and v not in GENERIC: names.add(v)
    cname = norm((meta.get(k) or {}).get('ru') and p.get('admin') or '')
    names.discard(cname)
    ADM[k].append((p['adm1_code'], names, p.get('name')))

MARK = {
    'us': [(r'do not travel to', 4), (r'reconsider travel to', 3), (r'exercise increased caution', 2), (r'exercise normal precautions', 1)],
    'uk': [(r'advises against all but essential travel', 3), (r'advises against all travel', 4)],
    'au': [(r'do not travel', 4), (r'reconsider your need to travel', 3), (r'exercise a high degree of caution', 2), (r'overview', 0)],
    'fr': [(r'formellement d[eé]conseill', 4), (r'd[eé]conseill[eé]e?s? sauf raison imp[eé]rative', 3), (r'vigilance renforc', 2)],
}
def segments(src, text):
    t = norm(text) if src != 'fr' else norm(text)
    pats = [(re.compile(norm(p) if src != 'fr' else norm(p).replace('[e ]', 'e')), lv) for p, lv in MARK[src]]
    hits = []
    for rx, lv in pats:
        for m in re.finditer(norm(rx.pattern) if False else rx, t): hits.append((m.start(), lv))
    hits.sort()
    out = []
    for i, (pos, lv) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else min(len(t), pos + 1500)
        out.append((lv, t[pos:min(end, pos + 1500)]))
    return out

def zones_for(k, src, text):
    found = {}
    if not text: return found
    for lv, seg in segments(src, text):
        if lv < 3: continue
        for aid, names, nm in ADM.get(k, []):
            if any(re.search(r'\b' + re.escape(n) + r'\b', seg) for n in names):
                found[aid] = max(found.get(aid, 0), lv)
    return found

# ---------------- Russia: official response levels (decree 757 of 19.10.2022) + KTO/federal emergency ----------------
RU_LV = {4: ['Белгородская', 'Курская', 'Брянская'],
         3: ['Воронежская', 'Ростовская', 'Краснодарский'],
         2: ['Москва', 'Московская', 'Владимирская', 'Ивановская', 'Калужская', 'Костромская', 'Липецкая', 'Орловская', 'Рязанская', 'Смоленская',
             'Тамбовская', 'Тверская', 'Тульская', 'Ярославская', 'Адыгея', 'Калмыкия', 'Астраханская', 'Волгоградская']}
RU_NOTE = {4: 'режим КТО и ЧС федерального характера, обстрелы и атаки дронов', 3: 'средний уровень реагирования: возможны ограничения въезда и передвижения',
           2: 'уровень повышенной готовности: усиленная охрана, возможны проверки транспорта', 1: 'базовый уровень готовности'}
adm_c = json.load(open('/tmp/admin1c.geojson'))['features']
ru_z = {}
for f in adm_c:
    p = f['properties']
    if p['k'] != 'RU': continue
    lv = next((l for l, names in RU_LV.items() if any((p['ru'] or '').startswith(n) for n in names)), 1)
    ru_z[p['id']] = lv

# ---------------- ACLED: political violence, last 3 full months ----------------
wb = openpyxl.load_workbook(S + 'pv.xlsx', read_only=True)
MON = ['August', 'September', 'October']
ac_c = defaultdict(lambda: [0, 0]); ac_a = defaultdict(lambda: [0, 0])
for sh in wb.sheetnames[1:]:
    ws = wb[sh]; head = None
    for r in ws.iter_rows(values_only=True):
        if head is None: head = r; continue
        row = dict(zip(head, r))
        if str(row.get('Year')) != '2026' or row.get('Month') not in MON: continue
        k = iso2(row['Country'])
        if not k: continue
        ac_c[k][0] += row['Events'] or 0; ac_c[k][1] += row['Fatalities'] or 0
        if row.get('Admin1'): a = ac_a[(k, norm(row['Admin1']))]; a[0] += row['Events'] or 0; a[1] += row['Fatalities'] or 0
pop = {}
for f in json.load(open('/home/claude/data/ne_10m_admin_0_countries.geojson'))['features']:
    p = f['properties']; k = p.get('ISO_A2_EH') or p.get('ISO_A2')
    if k and k != '-99' and p.get('POP_EST'): pop[k] = p['POP_EST']
acled_z = {}
for (k, an), (ev, fat) in ac_a.items():
    for aid, names, nm in ADM.get(k, []):
        if an in names or norm(nm) == an: acled_z[aid] = [ev, fat]; break

# ---------------- assemble ----------------
import importlib.util, sys
sys.path.insert(0, '/home/claude/scripts'); from zones_curated import Z as CUR
ADM_EN = defaultdict(list)
for f in adm_c: ADM_EN[f['properties']['k']].append((f['properties']['id'], f['properties']['en']))
C, Z = {}, {}
for k in sorted(OUR):
    if not isinstance(meta.get(k), dict): continue
    src = primary(k)
    by = {'us': US.get(k, {}).get('lvl'), 'ca': CA.get(k, {}).get('lvl'), 'uk': UK.get(k, {}).get('lvl') or (2 if UK.get(k, {}).get('parts') else (1 if k in UK else None)),
          'au': AU.get(k, {}).get('lvl')}
    if src == 'us': lvl = US[k]['lvl']
    elif src == 'au': lvl = AU[k]['lvl']
    elif src == 'uk': lvl = UK[k]['lvl'] or CA.get(k, {}).get('lvl') or median(by.values())
    elif src == 'fr': lvl = CA.get(k, {}).get('lvl') or median(by.values())
    else: lvl = median(by.values())
    note = None
    if k == 'RU': lvl, note = 2, 'Уровни по регионам — по указу о режимах реагирования (2022) и режимам КТО/ЧС; западные МИДы не советуют ездить в Россию целиком, в том числе из-за рисков для своих граждан.'
    if k == 'BY': lvl, note = 1, 'Для граждан РФ и РБ — обычные меры. Западные МИДы не советуют ехать в Беларусь своим гражданам по политическим причинам и из-за риска задержания.'
    if k == 'XU': lvl, note = 4, 'Идут боевые действия, обстрелы и атаки дронов; у линии фронта опасно.'
    if k in ('XA', 'XO', 'XT'): lvl, note = 2, 'Официальных оценок для граждан РФ и РБ нет; западные МИДы не советуют туда ехать, в том числе потому, что не могут там помочь своим гражданам.'
    # regions: hand-checked list read from the primary source (zones_curated.py); Russia from the decree levels
    cur = CUR.get(k, {})
    if cur.get('country'): lvl = cur['country']
    if k == 'RU':
        for a, l in ru_z.items():
            if l >= 2: Z[a] = {'l': l, 's': 'ru', 'n': RU_NOTE[l]}
    for names, l, part, nt in cur.get('z', []):
        hit = [aid for aid, en in ADM_EN.get(k, []) if en in names]
        miss = set(names) - {en for aid, en in ADM_EN.get(k, []) if aid in hit}
        if miss: print('  no region', k, miss)
        for aid in hit: Z[aid] = {'l': l, 's': src, 'p': part, 'n': nt}
    ev, fat = ac_c.get(k, (None, None)) if k in ac_c else (None, None)
    pm = round(ev / max(pop.get(k, 0), 1) * 1e6, 1) if ev is not None and pop.get(k) else None
    C[k] = {'l': lvl, 's': src, 'zn': cur.get('n'), 'by': {s: v for s, v in by.items() if v}, 'a': [ev, fat, pm] if ev is not None else None, 'n': note,
            'u': {'us': US.get(k, {}).get('upd'), 'uk': UK.get(k, {}).get('upd'), 'au': AU.get(k, {}).get('upd'), 'ca': CA.get(k, {}).get('upd')},
            'lk': {'us': f"https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html", 'uk': f"https://www.gov.uk/foreign-travel-advice/{UK[k]['slug']}" if k in UK else None,
                   'au': f"https://www.smartraveller.gov.au{AU[k]['href']}" if k in AU and AU[k].get('href') else None,
                   'ca': f"https://travel.gc.ca/destinations/{CA[k]['slug']}" if k in CA else None,
                   'fr': f"https://www.diplomatie.gouv.fr/fr/information-par-pays/{FR[k]['slug']}/conseils-aux-voyageurs-securite" if k in FR else None}}
for a, (ev, fat) in acled_z.items():
    Z.setdefault(a, {})['a'] = [ev, fat]
# territories without their own advice follow the country that runs them
PARENT = {'VA': 'IT', 'FO': 'DK', 'GG': 'GB', 'JE': 'GB', 'IM': 'GB', 'AX': 'FI', 'SJ': 'NO', 'CC': 'AU', 'CX': 'AU', 'NF': 'AU', 'XN': 'CY'}
for k, par in PARENT.items():
    if k in C and C[k]['l'] is None and par in C: C[k]['l'] = C[par]['l']; C[k]['s'] = C[par]['s']
if 'XS' in C: C['XS'].update({'l': 3, 's': 'uk', 'n': 'Британский МИД не советует ездить в Сомалиленд без крайней необходимости; в районах Сул и Санааг — не ехать.'})
if 'XN' in C: C['XN']['n'] = 'Оценки — как для Кипра в целом.'
RU_NAME = {f['properties']['id']: f['properties']['ru'] or f['properties']['en'] for f in adm_c}
for a, v in Z.items(): v['r'] = RU_NAME.get(a)
out = {'updated': '2026-11-14', 'acled': '2026-08..2026-10', 'c': C, 'z': Z}
json.dump(out, open(D + 'safety.json', 'w'), ensure_ascii=False, separators=(',', ':'))
from collections import Counter
print('countries', len(C), Counter(v['l'] for v in C.values()), Counter(v['s'] for v in C.values()))
print('zones', sum(1 for v in Z.values() if 'l' in v), 'acled zones', len(acled_z))

# zone outlines for the map: only the regions that carry a level
import subprocess
feats = [f for f in adm_c if f['properties']['id'] in Z and 'l' in Z[f['properties']['id']]]
for f in feats: f['properties'] = {'id': f['properties']['id'], 'k': f['properties']['k']}
json.dump({'type': 'FeatureCollection', 'features': feats}, open('/tmp/safezones.geojson', 'w'))
subprocess.run(['/home/claude/build/node_modules/.bin/mapshaper', '-i', '/tmp/safezones.geojson', 'name=z', '-simplify', '20%', 'keep-shapes',
                '-o', 'format=topojson', 'quantization=100000', D + 'safezones.json'], check=True, capture_output=True)
import os; print('safezones', os.path.getsize(D + 'safezones.json'), 'safety', os.path.getsize(D + 'safety.json'))
