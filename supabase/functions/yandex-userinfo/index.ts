// Yandex ID → standard OpenID fields, for the Supabase custom OAuth provider "custom:yandex".
// Supabase Auth calls this URL with the user's Yandex token (Authorization: Bearer …);
// we ask Yandex who it is and answer with sub / email / name, which Supabase understands.
// Deploy with JWT verification turned OFF: the caller is Supabase Auth, not a signed-in user.
Deno.serve(async (req) => {
  const token = (req.headers.get("authorization") ?? "").replace(/^(Bearer|OAuth)\s+/i, "").trim();
  if (!token) return Response.json({ error: "missing token" }, { status: 401 });

  const r = await fetch("https://login.yandex.ru/info?format=json", {
    headers: { Authorization: `OAuth ${token}` },
  });
  if (!r.ok) return Response.json({ error: "yandex rejected the token" }, { status: r.status });

  const y = await r.json();
  const email: string = y.default_email || (Array.isArray(y.emails) ? y.emails[0] : "") || "";
  const picture = y.default_avatar_id && !y.is_avatar_empty
    ? `https://avatars.yandex.net/get-yapic/${y.default_avatar_id}/islands-200`
    : undefined;

  return Response.json({
    sub: String(y.id),
    email,
    email_verified: Boolean(email), // Yandex only returns confirmed addresses
    name: y.real_name || y.display_name || y.login,
    preferred_username: y.login,
    picture,
  });
});
