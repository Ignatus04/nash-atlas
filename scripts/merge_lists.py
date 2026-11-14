import json, collections
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
c=json.load(open('/tmp/c10.geojson',encoding='utf-8'))
geoms=[shape(f['geometry']) for f in c['features']]; keys=[f['properties']['k'] for f in c['features']]
tree=STRtree(geoms)
def country(lat,lng):
    p=Point(lng,lat)
    for i in tree.query(p):
        if geoms[i].contains(p): return keys[i]
    # nearest within ~30km for coastal points
    i=tree.nearest(p); 
    return keys[i] if geoms[i].distance(p)<0.3 else None
def fnv(s):
    h=0x811c9dc5
    for ch in s: h^=ord(ch); h=(h*0x01000193)&0xffffffff
    return h
def b36(n):
    a='0123456789abcdefghijklmnopqrstuvwxyz';r=''
    while True:
        n,m=divmod(n,36);r=a[m]+r
        if n==0:return r
lists=json.load(open('site/data/lists.json',encoding='utf-8'))
base=[L for L in lists if not L.get('batch')]  # keep the first 15 lists
seen={it[0] for L in base for it in L['items']}
new=json.load(open('data/atlas-lists-2.json',encoding='utf-8'))
out=list(base); miss=0
for name,items in new.items():
    L={'name':name,'items':[],'batch':2}
    for row in items:
        nm,lat,lng=row[0],row[1],row[2]
        if lat is None or lng is None: miss+=1; continue
        pid='g'+b36(fnv(name+'|'+nm))
        while pid in seen: pid+='x'
        seen.add(pid)
        k=country(lat,lng) or ''
        L['items'].append([pid,nm,round(lat,5),round(lng,5),k])
    L['k']=collections.Counter(it[4] for it in L['items'] if it[4]).most_common(1)[0][0] if L['items'] else ''
    out.append(L)
json.dump(out,open('site/data/lists.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(len(out),'lists',sum(len(L['items']) for L in out),'places; missing coords',miss)
for L in out[15:]: print(L['name'],L['k'],len(L['items']),collections.Counter(it[4] for it in L['items']).most_common(3))
