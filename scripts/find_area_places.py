# Saved Google places that are a city, region or country themselves (not a place inside one)
import json, math, re, unicodedata
def nz(t):
    t=(t or '').lower().replace('ё','е').replace('й','\x01')
    t=unicodedata.normalize('NFKD',t); t=''.join(ch for ch in t if not unicodedata.combining(ch)).replace('\x01','й')
    t=re.sub(r"[«»\"'’().,!?:;·—–\-]+",' ',t); return re.sub(r'\s+',' ',t).strip()
def km(a,b,c,d):
    p=math.pi/180; return 6371*2*math.asin(math.sqrt(math.sin((c-a)*p/2)**2+math.cos(a*p)*math.cos(c*p)*math.sin((d-b)*p/2)**2))
lists=json.load(open('site/data/lists.json')); cities=json.load(open('site/data/cities.json')); meta=json.load(open('site/data/meta.json'))
adm=json.load(open('site/data/admin1.json'))
regs=[g['properties'] for o in adm['objects'].values() for g in o['geometries']]
ct=json.load(open('site/data/countries.json')); cn={}
for o in ct['objects'].values():
    for g in o['geometries']: p=g['properties']; cn.setdefault(p['k'],set()).update(nz(p.get(x)) for x in ('ru','en') if p.get(x))
STRIP=re.compile(r'\s+(город|city|province|провинция|область|регион|region|остров|island|state|штат)$')
byK={}
for c in cities: byK.setdefault(c[4],[]).append(c)
out={}
for L in lists:
    for it in L['items']:
        pid,name,lat,lng,k=it[:5]; n=nz(name); n2=STRIP.sub('',n); n2=re.split(r' (?=,)|,',n2)[0].strip()
        # "Стамбул, Турция" -> "стамбул"
        n3=nz(name.split(',')[0])
        cand={n,n2,n3}
        hit=None
        for c in byK.get(k,[]):
            names={nz(c[0]),nz(c[1]),nz(c[9] if len(c)>9 else '')}-{''}
            lim=40 if c[6]>1e6 else 25
            if cand&names and km(lat,lng,c[2],c[3])<lim: hit=('city',c[0]);break
        if not hit:
            for r in regs:
                if r['k']!=k: continue
                names={nz(r.get('ru')),nz(r.get('en'))}-{''}
                if cand&names and r.get('lat') is not None and km(lat,lng,r['lat'],r['lon'])<250: hit=('region',r.get('ru') or r.get('en'));break
        if not hit and cand&cn.get(k,set()): hit=('country',name)
        if hit: out['g'+pid if not pid.startswith('g') else pid]=hit
json.dump({k:v[0] for k,v in out.items()},open('site/data/areaplaces.json','w'),ensure_ascii=False)
print(len(out)); 
for k,v in list(out.items())[:400]: print(v)
