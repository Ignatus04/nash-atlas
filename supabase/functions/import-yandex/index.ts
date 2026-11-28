function allowed(url: URL) {
  return url.protocol === "https:" && /^(www\.)?yandex\.(ru|com|by|kz|eu)$/.test(url.hostname) &&
    !url.username && !url.password && (!url.port || url.port === "443") && /^\/maps(?:\/|$)/.test(url.pathname);
}
async function page(address: string) {
  let url = new URL(address);
  for (let hop = 0; hop < 6; hop++) {
    if (!allowed(url)) throw new Error("Яндекс перенаправил на недоступную страницу: " + url.hostname + url.pathname);
    const response = await fetch(url, { redirect: "manual", signal: AbortSignal.timeout(15000),
      headers: { "User-Agent": "Mozilla/5.0", "Accept-Language": "ru" } });
    const location = response.headers.get("location");
    if (location) { await response.body?.cancel(); url = new URL(location, url); continue; }
    if (!response.ok) throw new Error("Яндекс временно не отдаёт страницу");
    const reader = response.body!.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      size += value.length;
      if (size > 5000000) { await reader.cancel(); throw new Error("Страница слишком большая"); }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
    const html = new TextDecoder().decode(bytes);
    const match = html.match(/<script\b[^>]*class=["']state-view["'][^>]*>([\s\S]*?)<\/script>/);
    if (!match) throw new Error("Яндекс не открыл данные. Проверьте публичный доступ или повторите позже");
    return { state: JSON.parse(match[1]), url: url.href };
  }
  throw new Error("Слишком много перенаправлений");
}
function findPoint(value: any, uri: string): any {
  if (!value || typeof value !== "object") return null;
  if (value.uri === uri && Array.isArray(value.coordinates) && value.coordinates.length === 2 &&
      value.coordinates.every(Number.isFinite) && Math.abs(value.coordinates[0]) <= 180 && Math.abs(value.coordinates[1]) <= 90)
    return { lng: value.coordinates[0], lat: value.coordinates[1] };
  for (const child of Object.values(value)) {
    const point = findPoint(child, uri);
    if (point) return point;
  }
  return null;
}
Deno.serve(async req => {
  const origin = req.headers.get("origin") || "";
  const headers = { "Access-Control-Allow-Origin": ["https://nash-atlas.ru","https://beta.nash-atlas.ru"].includes(origin) ? origin : "https://nash-atlas.ru",
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Access-Control-Allow-Methods": "GET, OPTIONS", "Vary": "Origin", "Content-Type": "application/json", "Cache-Control": "no-store" };
  if (req.method === "OPTIONS") return new Response(null, {headers});
  try {
    const params = new URL(req.url).searchParams;
    const uri = params.get("uri");
    if (uri) {
      if (uri.length > 4000 || !/^ymapsbm1:\/\/(org|geo)\?/.test(uri)) throw new Error("Некорректное место");
      const address = "https://yandex.ru/maps/?uri=" + encodeURIComponent(uri);
      const {state} = await page(address);
      const point = findPoint(state, uri);
      if (!point) throw new Error("Координаты места пока недоступны");
      return Response.json({...point, url: address}, {headers});
    }
    const input = params.get("u") || "";
    if (input.length > 4000) throw new Error("Ссылка слишком длинная");
    const {state, url} = await page(input);
    const list = state.bookmarks?.publicList || state.config?.bookmarksPublicList;
    if (!list || !Array.isArray(list.children)) throw new Error("Нужна ссылка на публичный список мест Яндекс Карт");
    const items = list.children.map((item: any) => ({
      name: String(item.title || "Место"), note: String(item.description || ""),
      uri: String(item.uri || ""), ...findPoint(state, item.uri)
    }));
    return Response.json({title: String(list.title || "Яндекс Карты"), items, url}, {headers});
  } catch (error) {
    return Response.json({error: error instanceof Error ? error.message : "Не удалось загрузить список"}, {status: 400, headers});
  }
});
