import json,re
S='/home/claude/site/'; B='/home/claude/build/node_modules/'
html=open(S+'index.html',encoding='utf-8').read()
libs={'https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js':B+'d3/dist/d3.min.js',
      'https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js':B+'topojson-client/dist/topojson-client.min.js',
      'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js':B+'jszip/dist/jszip.min.js'}
for url,path in libs.items():
    tag=f'<script src="{url}"></script>'
    assert tag in html,url
    code=open(path,encoding='utf-8').read().replace('</script','<\\/script')
    html=html.replace(tag,'<script>'+code+'</script>')
data={}
for n in ['countries','cities','meta','visa','lists','admin1','flags','descs','urban','safety','safezones','visa_all','passports','airports','areaplaces','admnames']:
    data[n]=json.load(open(S+f'data/{n}.json',encoding='utf-8'))
blob=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
marker='<script>\n"use strict";'
assert html.count(marker)==1
html=html.replace(marker,'<script>window.__DATA='+blob+';</script>\n'+marker)
open('/home/claude/out/nash-atlas.html','w',encoding='utf-8').write(html)
import os;print(os.path.getsize('/home/claude/out/nash-atlas.html')/1e6,'MB')
