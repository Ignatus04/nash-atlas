/* Наш атлас service worker: the app and data come from the cache, then refresh; map tiles are kept for offline use */
const VER="__VER__", CORE=__CORE__, APP="atlas-app-"+VER, ASSETS="atlas-assets-v1", TILES="atlas-tiles", TILE_MAX=3000;
self.addEventListener("install",e=>{e.waitUntil(caches.open(APP).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()))});
// Preserve unchanged resources across releases, including the previous worker's cache.
self.addEventListener("activate",e=>{e.waitUntil((async()=>{
  const assets=await caches.open(ASSETS);
  for(const k of await caches.keys())if(k.startsWith("atlas-app-")&&k!==APP){
    const old=await caches.open(k);
    for(const request of await old.keys()){
      const u=new URL(request.url);
      if(u.origin===location.origin&&(u.searchParams.has("v")||/\/(fonts|vendor|icons|passports)\//.test(u.pathname))&&!(await assets.match(request))){const response=await old.match(request);if(response)await assets.put(request,response)}
    }
    await caches.delete(k);
  }
  await self.clients.claim();
})())});
async function storeAsset(c,r,res){
  await c.put(r,res);
  // Bound the cache without discarding unrelated, still-current data and artwork.
  const u=new URL(r.url), versions=(await c.keys()).filter(k=>{const x=new URL(k.url);return x.pathname===u.pathname&&k.url!==r.url});
  for(const old of versions.slice(0,-1))await c.delete(old);
}
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
  const cacheable=u.searchParams.has("v")||/\/(fonts|vendor|icons|passports)\//.test(u.pathname);
  if(!cacheable)return;
  const response=caches.open(ASSETS).then(async c=>{const hit=await c.match(r);if(hit)return hit;const res=await fetch(r);if(res.ok)e.waitUntil(storeAsset(c,r,res.clone()));return res});
  e.respondWith(response);
});
