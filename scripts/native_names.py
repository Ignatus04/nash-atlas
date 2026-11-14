# adds the city's name in the country's state language as field 9 of each cities.json row
import json, math, unicodedata, sys
from collections import defaultdict
SITE='/home/claude/site/data/'
rows=json.load(open(SITE+'cities.json'))
csc=json.load(open('/tmp/csc/cities.json'))
ne={}
for f in json.load(open('/home/claude/data/ne_10m_populated_places.geojson'))['features']:
    q=f['properties']; ne[(q['NAME'],round(q['LATITUDE'],4),round(q['LONGITUDE'],4))]=q
LANG={'JP':'JA','CN':'ZH','TW':'ZHT','KR':'KO','GR':'EL','CY':'EL','HU':'HU','IL':'HE','IR':'FA','PK':'UR','TR':'TR','PL':'PL','SE':'SV','NL':'NL','IT':'IT','DE':'DE','AT':'DE','FR':'FR','ES':'ES','PT':'PT','BR':'PT','VN':'VI','ID':'ID','UA':'UK','BD':'BN','IN':'HI',
      **{c:'AR' for c in 'SA AE QA KW BH OM YE IQ SY JO LB EG LY TN DZ MA SD PS MR'.split()},
      **{c:'ES' for c in 'MX AR CL CO PE VE EC BO PY UY CU DO GT HN SV NI CR PA'.split()}}
def norm(s):
    s=unicodedata.normalize('NFKD',s or '').lower()
    return ''.join(ch for ch in s if ch.isalnum())
by=defaultdict(list)
for x in csc:
    try: by[x['country_code']].append((float(x['latitude']),float(x['longitude']),x))
    except: pass
def km(a,b,c,d):
    return math.hypot((c-a)*111,(d-b)*111*math.cos(math.radians(a)))
stats=defaultdict(int)
for r in rows:
    ru,en,lat,lon,iso=r[:5]
    best=None;bs=1e9
    for (la,lo,x) in by.get(iso,()):
        if abs(la-lat)>0.4 or abs(lo-lon)>0.6: continue
        d=km(lat,lon,la,lo)
        if d>30: continue
        tr=x.get('translations') or {}
        names={norm(x['name'])}|{norm(v) for v in tr.values()}
        match= norm(en) in names or (tr.get('ru') and tr['ru']==ru)
        sc=d if match else (d*4+15)
        if sc<bs: bs=sc;best=(x,match,d)
    nat=''
    if best and best[1] and best[0].get('native'):
        nat=best[0]['native'].strip(); stats['csc']+=1
    else:
        q=ne.get((en,lat,lon))
        if q:
            l=LANG.get(iso)
            nat=(q.get('NAME_'+l) if l else None) or q.get('NAMEPAR') or q['NAME']
            stats['ne']+=1
    # one line is enough when it already reads the same as the Russian name
    if norm(nat)==norm(ru): nat=''
    r[8:]=[r[8],nat]
json.dump(rows,open(SITE+'cities.json','w'),ensure_ascii=False,separators=(',',':'))
print(dict(stats),len(rows))
for r in rows[:40]: print(r[0],'|',r[9])

# --- clean-ups -----------------------------------------------------------
import re
rows=json.load(open(SITE+'cities.json'))
NONLATIN={'MM','KP','AF','ET','KH','KZ','GE','RS','JO','NP','MN','LA','TJ','KG','RU','BY','UA','BG','MK','GR','CY','AM','IL','TH','LK','JP','CN','TW','KR','IN','BD','PK','IR','IQ','SY','LB','EG','SA','AE','QA','KW','BH','OM','YE','LY','SD','ER','BT','MV'}
SR=[('Lj','Љ'),('lj','љ'),('Nj','Њ'),('nj','њ'),('Dž','Џ'),('dž','џ')]+list(zip('ABVGDĐEŽZIJKLMNOPRSTĆUFHCČŠabvgdđežzijklmnoprstćufhcčš','АБВГДЂЕЖЗИЈКЛМНОПРСТЋУФХЦЧШабвгдђежзијклмнопрстћуфхцчш'))
def sr(s):
    for a,b in SR: s=s.replace(a,b)
    return s
FIX={'Катманду':'काठमाडौं','Гонконг':'香港','Макао':'澳門','Кишинёв':'Chișinău','Подгорица':'Podgorica'}
def norm2(s): return re.sub(r'[\W_]','',(s or '').lower())
for r in rows:
    ru,iso,nat=r[0],r[4],r[9]
    if r[0] in FIX: nat=FIX[r[0]]
    elif iso=='RU': nat=''
    elif iso=='RS' and re.search('[A-Za-zČćĆčŠšŽžĐđ]',nat or ''): nat=sr(nat)
    elif iso=='SS' and nat and not re.search('[A-Za-z]',nat): nat=''
    elif iso in NONLATIN and nat and re.search('[A-Za-z]',nat): nat=''
    if norm2(nat)==norm2(ru): nat=''
    r[9]=nat
json.dump(rows,open(SITE+'cities.json','w'),ensure_ascii=False,separators=(',',':'))
