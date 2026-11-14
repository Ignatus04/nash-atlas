import json, csv, sys
D='/home/claude/data/'
OUT='/home/claude/site/data/'
SPECIAL={'CYN':'XN','SOL':'XS','KOS':'XK'}
def key(p):
    a3=p.get('ADM0_A3') or p.get('adm0_a3')
    if a3 in SPECIAL: return SPECIAL[a3]
    k=p.get('ISO_A2_EH') or p.get('ISO_A2')
    if k in (None,'-99'): k=p.get('ISO_A2')
    return k if k and k!='-99' else 'Z'+a3
# visa
def load(fn):
    m={}
    for line in open(D+'visa/'+fn,encoding='utf-8'):
        line=line.rstrip('\n')
        if not line: continue
        cc,code,stay,note=line.split('|',3)
        m[cc]={'c':code,'s':stay,'n':note,'src':'wiki'}
    return m
ru=load('ru.txt'); by=load('by.txt')
PI={}
for r in csv.DictReader(open('/tmp/pid/passport-index-tidy-iso2.csv')):
    if r['Passport'] in ('RU','BY'): PI[(r['Passport'],r['Destination'])]=r['Requirement']
def pi(v):
    if v.lstrip('-').isdigit():
        n=int(v); 
        if n<0: return None
        return {'c':'F','s':f'{n} дней','n':'','src':'pi'}
    return {'c':{'visa free':'F','visa on arrival':'A','e-visa':'V','eta':'E','visa required':'R','no admission':'X'}.get(v,'R'),'s':'','n':'','src':'pi'}
# countries geo
c=json.load(open(D+'ne_50m_admin_0_countries.geojson'))
feats=[];names={}
for f in c['features']:
    p=f['properties'];k=key(p)
    f['properties']={'k':k,'ru':p.get('NAME_RU') or p['NAME'],'en':p['NAME'],'sov':p.get('SOV_A3')}
    names[k]=(f['properties']['ru'],p['NAME'])
    feats.append(f)
json.dump({'type':'FeatureCollection','features':feats},open('/tmp/countries.geojson','w'),ensure_ascii=False)
for k in names:
    for m,pp in ((ru,'RU'),(by,'BY')):
        if k not in m and (pp,k) in PI:
            v=pi(PI[(pp,k)])
            if v: m[k]=v
missing=[ (k,names[k][1]) for k in names if k not in ru or k not in by]
print('missing',missing)
json.dump({'updated':'2026-11-14','ru':ru,'by':by},open(OUT+'visa.json','w'),ensure_ascii=False,separators=(',',':'))
# cities
p=json.load(open(D+'ne_10m_populated_places.geojson'))
rows=[]
for f in p['features']:
    q=f['properties']
    iso=q.get('ISO_A2')
    a3=q.get('ADM0_A3')
    if a3 in SPECIAL: iso=SPECIAL[a3]
    if iso in (None,'-99'): iso = q.get('ADM0_A3')
    cap=1 if q.get('FEATURECLA','').startswith('Admin-0 capital') else 0
    rows.append([q.get('NAME_RU') or q['NAME'], q['NAME'], round(q['LATITUDE'],4), round(q['LONGITUDE'],4), iso, q.get('ADM1NAME') or '', int(q.get('POP_MAX') or 0), int(q.get('SCALERANK') or 10), cap])
rows.sort(key=lambda r:-r[6])
json.dump(rows,open(OUT+'cities.json','w'),ensure_ascii=False,separators=(',',':'))
print('cities',len(rows))
# admin1
a=json.load(open(D+'ne_10m_admin_1_states_provinces.geojson'))
af=[]
for f in a['features']:
    q=f['properties']
    iso=q.get('iso_a2')
    if q.get('adm0_a3') in SPECIAL: iso=SPECIAL[q['adm0_a3']]
    f['properties']={'id':q['adm1_code'],'ru':q.get('name_ru') or q.get('name'),'en':q.get('name_en') or q.get('name'),'k':iso,'t':q.get('type_en') or '','lat':q.get('latitude'),'lon':q.get('longitude')}
    af.append(f)
json.dump({'type':'FeatureCollection','features':af},open('/tmp/admin1.geojson','w'),ensure_ascii=False)
# meta
wc=json.load(open('/home/claude/build/node_modules/world-countries/countries.json'))
meta={}
for x in wc:
    meta[x['cca2']]={'cap':x.get('capital',[]),'cur':list((x.get('currencies') or {}).keys()),'lang':list((x.get('languages') or {}).items()),'reg':x.get('region'),'sub':x.get('subregion'),'flag':x.get('flag'),'ll':x.get('latlng'),'idd':(x.get('idd') or {}).get('root','')+((x.get('idd') or {}).get('suffixes') or [''])[0] if len((x.get('idd') or {}).get('suffixes') or [])==1 else (x.get('idd') or {}).get('root',''),'tld':(x.get('tld') or [''])[0],'side':x.get('car',{}).get('side') if x.get('car') else None,'ru':(x.get('translations',{}).get('rus') or {}).get('common')}
json.dump(meta,open(OUT+'meta.json','w'),ensure_ascii=False,separators=(',',':'))
print('meta',len(meta))
