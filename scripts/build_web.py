"""Build the website version of Наш атлас into /home/claude/web:
index.html + app.js + app.css, self-hosted libraries and fonts, data/*.json loaded on demand,
web app manifest and a service worker (works offline for what has been opened)."""
import json, re, os, shutil, hashlib
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
S=ROOT+'site/'; SRC=ROOT+'web-src/'; OUT=ROOT+'web/'
B=next(p for p in [ROOT+'node_modules/',ROOT+'build/node_modules/'] if os.path.isdir(p+'d3'))
if os.path.exists(OUT): shutil.rmtree(OUT)
for d in ['data','vendor','fonts','icons']: os.makedirs(OUT+d)
html=open(S+'index.html',encoding='utf-8').read()

# libraries: from CDNs to local files
libs={'https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js':('d3/dist/d3.min.js','d3.min.js'),
      'https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js':('topojson-client/dist/topojson-client.min.js','topojson-client.min.js'),
      'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js':('jszip/dist/jszip.min.js','jszip.min.js')}
for url,(src,name) in libs.items():
    shutil.copy(B+src,OUT+'vendor/'+name)
    tag=f'<script src="{url}"></script>'; assert tag in html
    html=html.replace(tag,f'<script src="vendor/{name}"' + (' defer' if name=='jszip.min.js' else '') + '></script>')
# accounts: Supabase client and the project settings
shutil.copy(B+'@supabase/supabase-js/dist/umd/supabase.js',OUT+'vendor/supabase.js')
shutil.copy(SRC+'config.js',OUT+'config.js')

# fonts: self-hosted (Google Fonts is not always reachable)
faces=[]
for fam,key,ws in [('Unbounded','unbounded',[500,700]),('Manrope','manrope',[400,500,600,700])]:
    for w in ws:
        for sub,rng in [('cyrillic','U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116'),('latin','U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD')]:
            f=f'{key}-{sub}-{w}-normal.woff2'; shutil.copy(B+f'@fontsource/{key}/files/'+f,OUT+'fonts/'+f)
            faces.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-display:swap;font-weight:{w};src:url(fonts/{f}) format('woff2');unicode-range:{rng}}}")
gf=re.search(r'<link rel="preconnect" href="https://fonts.googleapis.com">\s*<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\s*<link href="https://fonts.googleapis.com[^"]+" rel="stylesheet">',html)
assert gf; html=html.replace(gf.group(0),'')

# styles and the app script out of the page
st=re.search(r'<style>(.*?)</style>',html,re.S); css='\n'.join(faces)+'\n'+st.group(1)
m=re.search(r'<script>\n"use strict";(.*?)</script>',html,re.S); js='"use strict";'+m.group(1)
ver=hashlib.sha1((css+js+''.join(open(S+'data/'+f,'rb').read().hex()[:2000] for f in sorted(os.listdir(S+'data')))).encode()).hexdigest()[:10]
open(OUT+'app.css','w',encoding='utf-8').write(css)
open(OUT+'app.js','w',encoding='utf-8').write(js)
html=html.replace(st.group(0),f'<link rel="stylesheet" href="app.css?v={ver}">')
html=html.replace(m.group(0),f'<script src="vendor/supabase.js"></script>\n<script src="config.js?v={ver}"></script>\n<script>window.ATLAS_VER="{ver}"</script>\n<script src="app.js?v={ver}"></script>\n'
 '<script>if("serviceWorker" in navigator&&location.protocol==="https:")addEventListener("load",()=>navigator.serviceWorker.register("sw.js").catch(()=>{}))</script>')
head='''<meta name="theme-color" content="#13213a">
<meta name="description" content="Наша карта путешествий: где были, куда хотим, правила въезда и безопасность по странам.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="preload" href="data/countries.json?v=%s" as="fetch" crossorigin>
''' % ver
html=html.replace('<title>Наш атлас</title>','<title>Наш атлас</title>\n'+head)
open(OUT+'index.html','w',encoding='utf-8').write(html)

# data, minified
sizes={}
PRIVATE={'lists.json'}
for f in sorted(os.listdir(S+'data')):
    if f in PRIVATE: continue
    d=json.load(open(S+'data/'+f,encoding='utf-8'))
    out=json.dumps(d,ensure_ascii=False,separators=(',',':'))
    open(OUT+'data/'+f,'w',encoding='utf-8').write(out); sizes[f]=len(out.encode())

shutil.copy(SRC+'CNAME',OUT+'CNAME')  # custom domain for GitHub Pages
shutil.copy(SRC+'privacy.html',OUT+'privacy.html')
for f in ['icon.svg','icon-192.png','icon-512.png','icon-maskable-512.png','apple-touch-icon.png']: shutil.copy(SRC+f,OUT+'icons/'+f)
json.dump({"name":"Наш атлас","short_name":"Атлас","description":"Карта путешествий: места, правила въезда, безопасность.",
  "lang":"ru","start_url":"./","scope":"./","display":"standalone","orientation":"any","background_color":"#0f1a2e","theme_color":"#13213a",
  "icons":[{"src":"icons/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"icons/icon-512.png","sizes":"512x512","type":"image/png"},
           {"src":"icons/icon-maskable-512.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]},
  open(OUT+'manifest.webmanifest','w',encoding='utf-8'),ensure_ascii=False,indent=1)

core=['./','index.html',f'app.js?v={ver}',f'app.css?v={ver}','manifest.webmanifest']+['vendor/'+n for _,n in libs.values()]+\
     [f'data/{n}.json?v={ver}' for n in ['countries','cities','meta','visa','visa_all','areaplaces','flags','safety','safezones','urban']]+['vendor/supabase.js']+\
     ['fonts/'+f for f in sorted(os.listdir(OUT+'fonts'))]+['icons/icon-192.png','icons/icon.svg']
sw=open(SRC+'sw.js',encoding='utf-8').read().replace('__VER__',ver).replace('__CORE__',json.dumps(core))
open(OUT+'sw.js','w',encoding='utf-8').write(sw)
tot=sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fs in os.walk(OUT) for f in fs)
print('version',ver,'| total',round(tot/1e6,1),'MB | app.js',os.path.getsize(OUT+'app.js')//1024,'KB')
