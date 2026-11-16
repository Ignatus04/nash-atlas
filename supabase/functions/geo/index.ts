// Which country is the visitor in? Answers {"c":"RU"} from the IP address of the request, using the free
// DB-IP Lite country database (CC BY 4.0, https://db-ip.com) on our own server (container `geo`).
// The IP address is only looked up in memory: it is not stored or sent anywhere.
// The site uses the answer to draw borders as the visitor's country officially sees them.

// our sites: the main one and the beta at beta.nash-atlas.ru (server/beta.sh)
const ORIGINS = ["https://nash-atlas.ru", "https://beta.nash-atlas.ru"];
const CORS: Record<string, string> = {
  "Access-Control-Allow-Origin": "https://nash-atlas.ru",  // set per request: the site or its beta copy
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Vary": "Origin",
};
// the lookup itself runs in the `geo` container next to this runtime (server/geo/lookup.ts): the edge runtime cannot read data files
async function lookup(ip: string): Promise<{ c: string | null; db?: boolean }> {
  try {
    const r = await fetch(`http://geo:8000/?ip=${encodeURIComponent(ip)}`, { signal: AbortSignal.timeout(1500) });
    return r.ok ? await r.json() : { c: null };
  } catch { return { c: null }; }
}

Deno.serve(async (req) => {
  { const o = req.headers.get("origin") ?? ""; CORS["Access-Control-Allow-Origin"] = ORIGINS.includes(o) ? o : ORIGINS[0]; }
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  // Caddy puts the visitor's address first in X-Forwarded-For
  const ip = (req.headers.get("x-forwarded-for") ?? req.headers.get("x-real-ip") ?? "").split(",")[0].trim();
  const r = ip ? await lookup(ip) : { c: null };
  const c = r.c ?? null;
  // ?debug: what the function sees (the caller's own address only), to check the server setup
  const body = new URL(req.url).searchParams.has("debug") ? { c, ip, db: r.db ?? false } : { c };
  return new Response(JSON.stringify(body), {
    headers: { ...CORS, "Content-Type": "application/json", "Cache-Control": "private, no-store" },
  });
});
