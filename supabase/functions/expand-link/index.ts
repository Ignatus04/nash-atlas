// Short map links → the full link they redirect to, so the site can read the place name and coordinates.
// Google Maps (maps.app.goo.gl, goo.gl/maps) and Yandex Maps (yandex.ru/maps/-/…) short links only.
// One request per link the person pasted or shared; only the redirect address is read, never the page.
// Deploy with JWT verification turned OFF: it is called before or without signing in.
const SHORT = [
  /^https:\/\/maps\.app\.goo\.gl\/[\w-]+/i,
  /^https:\/\/goo\.gl\/maps\/[\w-]+/i,
  /^https:\/\/(?:www\.)?yandex\.(?:ru|com|by|kz)\/maps\/-\/[\w-]+/i,
];
const FULL = /^https:\/\/(?:(?:www\.|maps\.)?google\.[a-z.]+\/maps|(?:www\.)?yandex\.(?:ru|com|by|kz)\/maps)/i;
const CORS = {
  "Access-Control-Allow-Origin": "https://nash-atlas.ru",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Vary": "Origin",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json", "Cache-Control": "public, max-age=86400" } });

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  const u = new URL(req.url).searchParams.get("u") ?? "";
  if (u.length > 300 || !SHORT.some((r) => r.test(u))) return json({ error: "not a short map link" }, 400);
  let cur = u;
  for (let hop = 0; hop < 4; hop++) {
    let r: Response;
    try {
      r = await fetch(cur, { redirect: "manual", headers: { "User-Agent": "Mozilla/5.0 (nash-atlas.ru link preview)" } });
    } catch {
      return json({ error: "could not reach the map service" }, 502);
    }
    await r.body?.cancel(); // the page itself is never read
    const loc = r.headers.get("location");
    if (!loc) break;
    cur = new URL(loc, cur).toString();
    if (FULL.test(cur)) return json({ url: cur });
    if (!SHORT.some((x) => x.test(cur)) && !/^https:\/\/(?:www\.)?google\.[a-z.]+\/|^https:\/\/consent\./i.test(cur)) break;
  }
  return FULL.test(cur) ? json({ url: cur }) : json({ error: "no map address behind this link" }, 404);
});
