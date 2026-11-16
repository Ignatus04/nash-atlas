// Which country is the visitor in? Answers {"c":"RU"} from the IP address of the request, using the free
// DB-IP Lite country database (CC BY 4.0, https://db-ip.com) stored next to this file on our own server.
// The IP address is only looked up in memory: it is not stored or sent anywhere.
// The site uses the answer to draw borders as the visitor's country officially sees them.
import { Reader } from "npm:mmdb-lib@3.0.5";
import { Buffer } from "node:buffer";

// our sites: the main one and the beta at beta.nash-atlas.ru (server/beta.sh)
const ORIGINS = ["https://nash-atlas.ru", "https://beta.nash-atlas.ru"];
const CORS: Record<string, string> = {
  "Access-Control-Allow-Origin": "https://nash-atlas.ru",  // set per request: the site or its beta copy
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Vary": "Origin",
};
// both layouts: DB-IP's own file ({country:{iso_code}}) and the ip-location-db copy ({country_code})
// deno-lint-ignore no-explicit-any
let reader: Reader<any> | null = null;
// the edge runtime may bundle this file, so import.meta.url is not always its folder on disk: try the mounted folder too
const PATHS = [new URL("./country.mmdb", import.meta.url), "/home/deno/functions/geo/country.mmdb", "./geo/country.mmdb", "./country.mmdb"];
const errors: string[] = [];
for (const p of PATHS) {
  try { reader = new Reader(Buffer.from(await Deno.readFile(p))); break; }
  catch (err) { errors.push(`${p}: ${String(err).slice(0, 120)}`); }
}
if (!reader) console.error("geo: no database", errors.join(" | "));

Deno.serve((req) => {
  { const o = req.headers.get("origin") ?? ""; CORS["Access-Control-Allow-Origin"] = ORIGINS.includes(o) ? o : ORIGINS[0]; }
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  // Caddy puts the visitor's address first in X-Forwarded-For
  const ip = (req.headers.get("x-forwarded-for") ?? req.headers.get("x-real-ip") ?? "").split(",")[0].trim();
  let c: string | null = null;
  try { const r = ip ? reader?.get(ip) : null; c = r?.country?.iso_code || r?.country_code || null; } catch { c = null; }
  // ?debug: what the function sees (the caller's own address only), to check the server setup
  const body = new URL(req.url).searchParams.has("debug") ? { c, ip, db: Boolean(reader), errors, cwd: Deno.cwd(), url: import.meta.url } : { c };
  return new Response(JSON.stringify(body), {
    headers: { ...CORS, "Content-Type": "application/json", "Cache-Control": "private, no-store" },
  });
});
