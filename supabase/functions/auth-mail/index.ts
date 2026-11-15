// Login emails with a CAPTCHA in front of them. One function, two jobs (deploy with JWT verification OFF):
//
// 1. POST /auth-mail?captcha  {email, token}  — the site asks for a login code. We check the Yandex SmartCaptcha
//    token and, if a person passed it, note «this address may get one code in the next 10 minutes».
// 2. POST /auth-mail  (Supabase Auth «Send Email» hook, signed)  — Supabase wants to send a login email. We send it
//    through Yandex Cloud Postbox only if step 1 let this address through. A script that calls Supabase directly,
//    without the captcha, gets no email.
//
// Secrets (Supabase → Edge Functions → Secrets): SMARTCAPTCHA_SERVER_KEY, POSTBOX_API_KEY (the secret part of the
// Postbox API key, the same one as the SMTP password), SEND_EMAIL_HOOK_SECRET (from the hook settings, "v1,whsec_…").
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are provided by Supabase itself.
import { Webhook } from "npm:standardwebhooks@1.0.0";

const URL_ = Deno.env.get("SUPABASE_URL")!;
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const FROM = "=?UTF-8?B?" + btoa(String.fromCharCode(...new TextEncoder().encode("Наш атлас"))) + "?= <noreply@nash-atlas.ru>";
const SUBJECT = "Код для входа в «Наш атлас»";
const CORS = {
  "Access-Control-Allow-Origin": "https://nash-atlas.ru",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Vary": "Origin",
};
const json = (b: unknown, status = 200, h: Record<string, string> = {}) =>
  new Response(JSON.stringify(b), { status, headers: { ...h, "Content-Type": "application/json" } });
const norm = (e: string) => String(e || "").trim().toLowerCase();

// the pass table, through the database REST API with the service key (RLS keeps everyone else out)
const db = (path: string, init: RequestInit = {}) =>
  fetch(`${URL_}/rest/v1/${path}`, { ...init, headers: { apikey: SERVICE, Authorization: `Bearer ${SERVICE}`, "Content-Type": "application/json", ...(init.headers || {}) } });

async function captcha(req: Request) {
  let body: { email?: string; token?: string } = {};
  try { body = await req.json(); } catch { /* empty */ }
  const email = norm(body.email ?? ""), token = String(body.token ?? "");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email) || email.length > 254 || !token) return json({ ok: false, error: "bad request" }, 400, CORS);
  const ip = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim();
  const r = await fetch("https://smartcaptcha.cloud.yandex.ru/validate", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ secret: Deno.env.get("SMARTCAPTCHA_SERVER_KEY") ?? "", token, ...(ip ? { ip } : {}) }),
  }).then((x) => x.json()).catch(() => null);
  if (r?.status !== "ok") return json({ ok: false, error: "captcha failed" }, 403, CORS);
  const until = new Date(Date.now() + 10 * 60_000).toISOString();
  const w = await db("captcha_pass", { method: "POST", headers: { Prefer: "resolution=merge-duplicates" }, body: JSON.stringify({ email, until }) });
  if (!w.ok) return json({ ok: false, error: "storage" }, 500, CORS);
  return json({ ok: true }, 200, CORS);
}

async function takePass(email: string) {
  const r = await db(`captcha_pass?email=eq.${encodeURIComponent(email)}&until=gt.${encodeURIComponent(new Date().toISOString())}`, {
    method: "DELETE", headers: { Prefer: "return=representation" },
  });
  if (!r.ok) return false;
  const rows = await r.json();
  return Array.isArray(rows) && rows.length > 0;
}

const TEMPLATE = `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>Код для входа в «Наш атлас»</title>
</head>
<body style="margin:0;padding:0;background:#eef1f6;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">Код {{ .Token }} действует час. Введите его на сайте nash-atlas.ru</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#eef1f6;">
  <tr><td align="center" style="padding:32px 12px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden;">
      <tr><td style="background:#13213a;padding:22px 32px;">
        <span style="font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:18px;font-weight:700;color:#ffffff;letter-spacing:.2px;">Наш атлас</span>
      </td></tr>
      <tr><td style="padding:32px 32px 8px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#13213a;">
        <p style="margin:0 0 6px;font-size:15px;line-height:22px;color:#4a5568;">Код для входа</p>
        <p style="margin:0 0 20px;font-size:40px;line-height:48px;font-weight:700;letter-spacing:8px;color:#13213a;">{{ .Token }}</p>
        <p style="margin:0 0 28px;font-size:15px;line-height:22px;color:#13213a;">Введите его в окне входа на сайте. Код действует час и подходит для одного входа.</p>
      </td></tr>
      <tr><td style="padding:0 32px 8px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="border-radius:10px;background:#ff8a5c;">
            <a href="{{ .ConfirmationURL }}" style="display:inline-block;padding:13px 22px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:15px;font-weight:700;color:#1a0d06;text-decoration:none;border-radius:10px;">Войти без кода</a>
          </td></tr></table>
      </td></tr>
      <tr><td style="padding:10px 32px 28px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:13px;line-height:20px;color:#6b7686;">
        Кнопка сработает, если открыть письмо в том же браузере, где вы запросили вход. На другом устройстве введите код.
      </td></tr>
      <tr><td style="padding:18px 32px;border-top:1px solid #e5e9f0;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:12px;line-height:18px;color:#8a94a3;">
        Если вход запрашивали не вы, удалите письмо: без него в аккаунт никто не войдёт.<br>
        <a href="https://nash-atlas.ru/" style="color:#6b7686;">nash-atlas.ru</a>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
`;

async function hook(req: Request) {
  const payload = await req.text();
  const secret = (Deno.env.get("SEND_EMAIL_HOOK_SECRET") ?? "").replace(/^v1,whsec_/, "");
  let data: any;
  try {
    data = new Webhook(secret).verify(payload, Object.fromEntries(req.headers));
  } catch {
    return json({ error: { http_code: 401, message: "bad signature" } }, 401);
  }
  const email = norm(data?.user?.email ?? data?.user?.new_email ?? "");
  const e = data?.email_data ?? {};
  const type = String(e.email_action_type ?? "");
  // a login code (first or next login) needs a passed captcha; other emails come only from signed-in actions
  if ((type === "magiclink" || type === "signup") && !(await takePass(email)))
    return json({ error: { http_code: 429, message: "Пройдите проверку «я не робот» на сайте и запросите код снова." } }, 429);
  const link = `${URL_}/auth/v1/verify?token=${encodeURIComponent(e.token_hash ?? "")}&type=${encodeURIComponent(type)}&redirect_to=${encodeURIComponent(e.redirect_to ?? "https://nash-atlas.ru/")}`;
  const esc = (s: string) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
  const html = TEMPLATE.replaceAll("{{ .Token }}", esc(e.token ?? "")).replaceAll("{{ .ConfirmationURL }}", esc(link));
  const text = `Код для входа в «Наш атлас»: ${e.token}\n\nВведите его в окне входа на сайте nash-atlas.ru. Код действует час и подходит для одного входа.\nИли войдите по ссылке: ${link}\n\nЕсли вход запрашивали не вы, удалите письмо.`;
  const r = await fetch("https://postbox.cloud.yandex.net/v2/email/outbound-emails", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Api-Key ${Deno.env.get("POSTBOX_API_KEY") ?? ""}` },
    body: JSON.stringify({
      FromEmailAddress: FROM,
      Destination: { ToAddresses: [email] },
      Content: { Simple: {
        Subject: { Data: SUBJECT, Charset: "UTF-8" },
        Body: { Html: { Data: html, Charset: "UTF-8" }, Text: { Data: text, Charset: "UTF-8" } },
      } },
    }),
  });
  if (!r.ok) {
    console.error("postbox", r.status, (await r.text()).slice(0, 300));
    return json({ error: { http_code: 502, message: "Письмо не отправилось. Попробуйте через минуту." } }, 502);
  }
  await r.body?.cancel();
  return json({});
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  if (req.method !== "POST") return json({ error: "method" }, 405, CORS);
  if (new URL(req.url).searchParams.has("captcha")) return captcha(req);
  if (req.headers.get("webhook-signature")) return hook(req);
  return json({ error: "not found" }, 404, CORS);
});
