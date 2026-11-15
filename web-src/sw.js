/* Наш атлас service worker: the app and data come from the cache, then refresh; map tiles are kept for offline use */
const VER="__VER__", CORE=__CORE__, APP="atlas-app-"+VER, TILES="atlas-tiles", TILE_MAX=3000;
self.addEventListener("install",e=>{e.waitUntil(caches.open(APP).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith("atlas-app-")&&k!==APP).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
async function trimTiles(){const c=await caches.open(TILES);const ks=await c.keys();for(let i=0;i<ks.length-TILE_MAX;i++)await c.delete(ks[i])}
self.addEventListener("fetch",e=>{
  const r=e.request; if(r.method!=="GET") return;
  const u=new URL(r.url);
  // page: network first, so a new version shows up at once; offline falls back to the cached page
  if(r.mode==="navigate"){const app=u.origin===location.origin&&/^\/(index\.html)?$/.test(u.pathname);e.respondWith(fetch(r).then(res=>{if(app&&res.ok){const cp=res.clone();caches.open(APP).then(c=>c.put("index.html",cp))}return res}).catch(()=>app?caches.match("index.html"):Response.error()));return}
  // map tiles: cache first, keep the most recent few thousand
  if(/tile\.opentopomap\.org$/.test(u.hostname)){
    e.respondWith(caches.open(TILES).then(async c=>{const hit=await c.match(r);if(hit)return hit;const res=await fetch(r);if(res.ok){c.put(r,res.clone());if(Math.random()<.02)trimTiles()}return res}));return}
  if(u.origin!==location.origin) return;
  // app files and data (versioned URLs): cache first
  e.respondWith(caches.open(APP).then(async c=>{const hit=await c.match(r);if(hit)return hit;const res=await fetch(r);if(res.ok&&(u.search.includes("v=")||/\/(fonts|vendor|icons)\//.test(u.pathname)))c.put(r,res.clone());return res}));
});
