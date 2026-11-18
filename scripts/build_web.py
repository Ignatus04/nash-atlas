"""Build the website version of Наш атлас into /home/claude/web:
index.html + app.js + app.css, self-hosted libraries and fonts, data/*.json loaded on demand,
web app manifest and a service worker (works offline for what has been opened)."""
import json, re, os, shutil, hashlib, base64, html as htmltools
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
S=ROOT+'site/'; SRC=ROOT+'web-src/'; OUT=ROOT+'web/'
B=next(p for p in [ROOT+'node_modules/',ROOT+'build/node_modules/'] if os.path.isdir(p+'d3'))
if os.path.exists(OUT): shutil.rmtree(OUT)
for d in ['data','vendor','fonts','icons']: os.makedirs(OUT+d)
if os.path.isdir(SRC+'patterns'): shutil.copytree(SRC+'patterns',OUT+'patterns')
html=open(S+'index.html',encoding='utf-8').read()
# ATLAS_BETA=1: the test copy at beta.nash-atlas.ru (server/beta.sh). Hidden from search engines, marked «бета» on screen.
BETA=os.environ.get('ATLAS_BETA')=='1'

# libraries: from CDNs to local files
libs={'https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js':('d3/dist/d3.min.js','d3.min.js'),
      'https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js':('topojson-client/dist/topojson-client.min.js','topojson-client.min.js'),
      'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js':('jszip/dist/jszip.min.js','jszip.min.js')}
for url,(src,name) in libs.items():
    shutil.copy(B+src,OUT+'vendor/'+name)
    tag=f'<script src="{url}"></script>'; assert tag in html
    html=html.replace(tag,('' if name=='jszip.min.js' else f'<script src="vendor/{name}" defer></script>'))
# accounts: Supabase client and the project settings
shutil.copy(B+'@supabase/supabase-js/dist/umd/supabase.js',OUT+'vendor/supabase.js')
shutil.copy(SRC+'config.js',OUT+'config.js')
shutil.copy(SRC+'support-sbp.png',OUT+'support-sbp.png')

# fonts: self-hosted (Google Fonts is not always reachable)
faces=[]
for fam,key,ws in [('Unbounded','unbounded',[500,700]),('Manrope','manrope',[400,500,600,700])]:
    for w in ws:
        for sub,rng in [('cyrillic','U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116'),('latin','U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD')]:
            f=f'{key}-{sub}-{w}-normal.woff2'; shutil.copy(B+f'@fontsource/{key}/files/'+f,OUT+'fonts/'+f)
            faces.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-display:swap;font-weight:{w};src:url(fonts/{f}) format('woff2');unicode-range:{rng}}}")
gf=re.search(r'<link rel="preconnect" href="https://fonts.googleapis.com">\s*<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\s*<link href="https://fonts.googleapis.com[^"]+" rel="stylesheet">',html)
assert gf; html=html.replace(gf.group(0),'')

# data, minified
sizes={}
PRIVATE={'lists.json'}
for f in sorted(os.listdir(S+'data')):
    if f in PRIVATE: continue
    d=json.load(open(S+'data/'+f,encoding='utf-8'))
    if f=='passports.json':
        # Keep attribution in the small index; fetch only visible covers.
        os.makedirs(OUT+'passports',exist_ok=True)
        for k,c in d.items():
            src=c.get('img','')
            if src.startswith('data:image/webp;base64,'):
                raw=base64.b64decode(src.split(',',1)[1],validate=True)
                name=k.lower()+'-'+hashlib.sha256(raw).hexdigest()[:12]+'.webp'
                open(OUT+'passports/'+name,'wb').write(raw)
                c['img']='passports/'+name
    out=json.dumps(d,ensure_ascii=False,separators=(',',':'))
    open(OUT+'data/'+f,'w',encoding='utf-8').write(out); sizes[f]=len(out.encode())


# Only world-view labels are needed before the visitor explores the map.
all_cities=json.load(open(OUT+'data/cities.json',encoding='utf-8'))
world_cities=set(re.search(r'const WORLD_CITIES=new Set\(\[(.*?)\]\)',html,re.S).group(1).replace('"','').replace("'",'').split(','))
world_cities={x.strip() for x in world_cities}
startup_cities=[c for c in all_cities if c[8] or c[7]<=2 or c[4]+'|'+c[1] in world_cities]
open(OUT+'data/cities-start.json','w',encoding='utf-8').write(json.dumps(startup_cities,ensure_ascii=False,separators=(',',':')))
os.makedirs(OUT+'data/cities',exist_ok=True)
for k in sorted({c[4] for c in all_cities}):
    rows=[c for c in all_cities if c[4]==k]
    open(OUT+'data/cities/'+k+'.json','w',encoding='utf-8').write(json.dumps(rows,ensure_ascii=False,separators=(',',':')))

# Each resource keeps its cache key until its own bytes change.
assets={}
for folder in ("data","patterns","vendor"):
    for dp,ds,fs in os.walk(OUT+folder):
        for f in sorted(fs):
            path=os.path.join(dp,f); assets[os.path.relpath(path,OUT)]=hashlib.sha256(open(path,"rb").read()).hexdigest()[:12]
assets["config.js"]=hashlib.sha256(open(OUT+"config.js","rb").read()).hexdigest()[:12]

# styles and the app script out of the page
st=re.search(r'<style>(.*?)</style>',html,re.S); css='\n'.join(faces)+'\n'+st.group(1)
m=re.search(r'<script>\n"use strict";(.*?)</script>',html,re.S); js='"use strict";'+m.group(1)
pattern_hash=''.join(hashlib.sha1(open(os.path.join(dp,f),'rb').read()).hexdigest() for dp,ds,fs in os.walk(SRC+'patterns') for f in sorted(fs))
ver=hashlib.sha1((css+js+pattern_hash+open(SRC+'config.js').read()+''.join(hashlib.sha1(open(S+'data/'+f,'rb').read()).hexdigest() for f in sorted(os.listdir(S+'data')))).encode()).hexdigest()[:10]
open(OUT+'app.css','w',encoding='utf-8').write(css)
open(OUT+'app.js','w',encoding='utf-8').write(js)
html=html.replace(st.group(0),f'<link rel="stylesheet" href="app.css?v={ver}">')
html=html.replace(m.group(0),f'<script defer src="vendor/supabase.js"></script>\n<script defer src="config.js?v={assets["config.js"]}"></script>\n<script>window.ATLAS_VER="{ver}";window.ATLAS_ASSETS={json.dumps(assets,separators=(",",":"))}</script>\n<script defer src="app.js?v={ver}"></script>\n'
 '<script>if("serviceWorker" in navigator&&location.protocol==="https:")addEventListener("load",()=>navigator.serviceWorker.register("sw.js").catch(()=>{}))</script>')
head='''<meta name="theme-color" content="#13213a">
<meta name="description" content="Наша карта путешествий: где были, куда хотим, правила въезда и безопасность по странам.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
'''
# Discover startup requests from the head instead of waiting for app execution.
head+=''.join(f'<link rel="preload" href="data/{name}.json?v={assets["data/"+name+".json"]}" as="fetch" crossorigin>\n' for name in ('countries','cities-start','meta','visa','visa_all','worldviews','areaplaces'))
for name in ('d3.min.js','topojson-client.min.js','supabase.js'):
    html=html.replace(f'src="vendor/{name}"',f'src="vendor/{name}?v={assets["vendor/"+name]}"')
html=html.replace('<title>Наш атлас</title>','<title>Наш атлас</title>\n'+head)
if BETA:
    html=html.replace('<title>Наш атлас</title>','<title>Наш атлас · бета</title>\n<meta name="robots" content="noindex,nofollow">')
    css+='\n.beta-badge{position:fixed;left:50%;top:2px;transform:translateX(-50%);z-index:9999;pointer-events:none;font:700 10px/1 Manrope,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#13213a;background:#ffb547;border-radius:0 0 6px 6px;padding:3px 8px}'
    open(OUT+'app.css','w',encoding='utf-8').write(css)
    html=html.replace('<body>','<body>\n<div class="beta-badge">бета</div>',1)
# Content-Security-Policy: the browser runs only our own scripts (plus the hashed inline ones and, after consent,
# Yandex Metrika / ads). A missed escape somewhere then cannot run injected code. New outside hosts go here.
import hashlib,base64
hashes=' '.join("'sha256-%s'"%base64.b64encode(hashlib.sha256(b.encode()).digest()).decode() for b in re.findall(r'<script>([\s\S]*?)</script>',html))
SC='https://smartcaptcha.yandexcloud.net https://smartcaptcha.cloud.yandex.ru'
YA='https://yandex.ru https://*.yandex.ru https://*.yandex.net https://yastatic.net https://*.yandexadexchange.net https://yandexadexchange.net'
CSP=("default-src 'self'; "
  f"script-src 'self' {hashes} https://mc.yandex.ru {YA} {SC} https://accounts.google.com/gsi/client; "
  "style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style https://smartcaptcha.yandexcloud.net; "
  "img-src 'self' data: blob: https:; font-src 'self' data:; media-src 'self' data: blob:; "
  f"connect-src 'self' {SC} https://api.nash-atlas.ru wss://api.nash-atlas.ru https://*.supabase.co wss://*.supabase.co https://*.wikipedia.org https://commons.wikimedia.org https://nominatim.openstreetmap.org https://mc.yandex.ru {YA} https://accounts.google.com; "
  f"frame-src {YA} {SC} https://accounts.google.com; worker-src 'self' blob:; manifest-src 'self'; "
  "object-src 'none'; base-uri 'self'; form-action 'self'")
html=html.replace('<meta charset="utf-8">','<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="%s">'%CSP,1)
open(OUT+'index.html','w',encoding='utf-8').write(html)

# Human-readable attribution for cover images, including derivative licence links.
covers=json.load(open(OUT+'data/passports.json',encoding='utf-8'))
e=htmltools.escape
rows=[]
for k,c in sorted(covers.items()):
    page=c.get('page',''); licurl=c.get('licenseUrl','')
    if not page.startswith('https://commons.wikimedia.org/wiki/'): continue
    licence=f'<a href="{e(licurl,quote=True)}">{e(c.get("lic",""))}</a>' if licurl.startswith('https://') else e(c.get('lic',''))
    rows.append(f'<article><img src="{e(c["img"],quote=True)}" alt="Обложка {e(k)}" loading="lazy"><div><h2>{e(k)}</h2><p>{e(c.get("by",""))}</p><p>{licence} · <a href="{e(page,quote=True)}">Источник и условия использования</a></p><p>{e(c.get("changes","Уменьшено и перекодировано в WebP"))}</p></div></article>')
credits='<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Источники обложек — Наш атлас</title><style>body{margin:0 auto;padding:24px;max-width:850px;background:#101c30;color:#eef1f6;font:15px/1.5 system-ui}a{color:#9cd3ff}article{display:flex;gap:24px;padding:20px 0;border-bottom:1px solid #33445f}img{width:90px;height:130px;object-fit:contain}h2{margin:0}p{margin:8px 0}</style><a href="/">← На карту</a><h1>Источники обложек паспортов</h1><p>Автор, исходное изображение и лицензия каждого файла. Для отсутствующих обложек используется условное изображение без фотографии. Указанная лицензия относится и к подготовленной версии изображения.</p>'+''.join(rows)+'</html>'
open(OUT+'passport-sources.html','w',encoding='utf-8').write(credits)

if BETA: open(OUT+'robots.txt','w').write('User-agent: *\nDisallow: /\n')
else: shutil.copy(SRC+'CNAME',OUT+'CNAME')  # custom domain for GitHub Pages
# the login email template: our own Supabase server fetches it from here (server/docker-compose.atlas.yml)
os.makedirs(OUT+'email',exist_ok=True); shutil.copy(ROOT+'supabase/email/login.html',OUT+'email/login.html')
for f in ('privacy.html','terms.html','consent.html'):
  t=open(SRC+f,encoding='utf-8').read()
  t=t.replace('<meta charset="utf-8">','<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; script-src \'none\'; object-src \'none\'; base-uri \'self\'; form-action \'none\'">',1)
  open(OUT+f,'w',encoding='utf-8').write(t)
for f in ['icon.svg','icon-192.png','icon-512.png','icon-maskable-512.png','apple-touch-icon.png']: shutil.copy(SRC+f,OUT+'icons/'+f)
json.dump({"id":"./","name":"Наш атлас"+(" · бета" if BETA else ""),"short_name":"Атлас β" if BETA else "Атлас","description":"Карта путешествий: места, правила въезда, безопасность.",
  "lang":"ru","categories":["travel","navigation"],"start_url":"./","scope":"./","display":"standalone","orientation":"any","background_color":"#0f1a2e","theme_color":"#13213a",
  "share_target":{"action":"./","method":"GET","params":{"title":"addtitle","text":"addtext","url":"add"}},
  "icons":[{"src":"icons/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"icons/icon-512.png","sizes":"512x512","type":"image/png"},
           {"src":"icons/icon-maskable-512.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]},
  open(OUT+'manifest.webmanifest','w',encoding='utf-8'),ensure_ascii=False,indent=1)

# Android app (TWA): Digital Asset Links tie the app to this site. The fingerprint is the SHA-256 of the app signing key (android/README.md); it is public.
fp=ROOT+'android/fingerprint.txt'
if os.path.exists(fp):
  fps=[l.strip() for l in open(fp,encoding='utf-8') if l.strip() and not l.lstrip().startswith('#')]
  if fps:
    os.makedirs(OUT+'.well-known',exist_ok=True)
    json.dump([{"relation":["delegate_permission/common.handle_all_urls"],"target":{"namespace":"android_app","package_name":"ru.nashatlas.app","sha256_cert_fingerprints":fps}}],
      open(OUT+'.well-known/assetlinks.json','w',encoding='utf-8'),indent=1)

# Cache files when actually requested. Eagerly downloading every font and data set
# on each update competes with the visible map and doubles cold-load requests.
core=['manifest.webmanifest','icons/icon-192.png','icons/icon.svg']
sw=open(SRC+'sw.js',encoding='utf-8').read().replace('__VER__',ver).replace('__CORE__',json.dumps(core))
open(OUT+'sw.js','w',encoding='utf-8').write(sw)
tot=sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fs in os.walk(OUT) for f in fs)
print('version',ver,'| total',round(tot/1e6,1),'MB | app.js',os.path.getsize(OUT+'app.js')//1024,'KB')

