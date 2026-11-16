// «Наш атлас»: country by IP address, inside our server only (container `geo`, server/docker-compose.atlas.yml).
// The edge runtime cannot read data files, so the lookup lives in this small Deno service and the function
// supabase/functions/geo asks it: GET http://geo:8000/?ip=1.2.3.4 → {"c":"RU"}. Database: DB-IP Lite (CC BY 4.0).
// Addresses are looked up in memory only, never stored or logged.
import { Reader } from "npm:mmdb-lib@3.0.5";
import { Buffer } from "node:buffer";

const FILE = Deno.env.get("GEO_FILE") ?? "/app/country.mmdb";
// deno-lint-ignore no-explicit-any
let reader: Reader<any> | null = null;
let loaded = 0;
async function load() {
  try {
    const st = await Deno.stat(FILE);
    if (reader && st.mtime && st.mtime.getTime() === loaded) return;
    reader = new Reader(Buffer.from(await Deno.readFile(FILE)));
    loaded = st.mtime?.getTime() ?? Date.now();
  } catch (err) { console.error("geo: no database", String(err)); }
}
await load();
setInterval(load, 6 * 3600 * 1000);   // picks up the monthly update without a restart

Deno.serve({ port: 8000, hostname: "0.0.0.0" }, (req) => {
  const ip = new URL(req.url).searchParams.get("ip") ?? "";
  let c: string | null = null;
  try { const r = ip && reader ? reader.get(ip) : null; c = r?.country?.iso_code || r?.country_code || null; } catch { c = null; }
  return Response.json({ c, db: Boolean(reader) });
});
