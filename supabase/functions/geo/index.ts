// Which country is the visitor in? Answers {"c":"RU"} from the IP address of the request, using the free
// DB-IP Lite country database (CC BY 4.0, https://db-ip.com) stored next to this file on our own server.
// The IP address is only looked up in memory: it is not stored or sent anywhere.
// The site uses the answer to draw borders as the visitor's country officially sees them.
import { Reader } from "npm:mmdb-lib@3.0.5";
import { Buffer } from "node:buffer";

const CORS = {
  "Access-Control-Allow-Origin": "https://nash-atlas.ru",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Vary": "Origin",
};
// both layouts: DB-IP's own file ({country:{iso_code}}) and the ip-location-db copy ({country_code})
let reader: Reader<{ country?: { iso_code?: string }; country_code?: string }> | null = null;
try {
  reader = new Reader(Buffer.from(await Deno.readFile(new URL("./country.mmdb", import.meta.url))));
} catch (err) {
  console.error("geo: no database", String(err));
}

Deno.serve((req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  // Caddy puts the visitor's address first in X-Forwarded-For
  const ip = (req.headers.get("x-forwarded-for") ?? req.headers.get("x-real-ip") ?? "").split(",")[0].trim();
  let c: string | null = null;
  try { const r = ip ? reader?.get(ip) : null; c = r?.country?.iso_code || r?.country_code || null; } catch { c = null; }
  return new Response(JSON.stringify({ c }), {
    headers: { ...CORS, "Content-Type": "application/json", "Cache-Control": "private, no-store" },
  });
});
