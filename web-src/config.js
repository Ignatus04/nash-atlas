// Supabase project settings. The publishable key is meant to be public:
// what each person can see or change is enforced by the database rules in supabase/schema.sql.
window.ATLAS_CFG = {
  supabaseUrl: "https://hvqdjcpbevwuaymdrpye.supabase.co",
  supabaseKey: "sb_publishable_pVRfI-YUFLDwhTXSqoQhaw_0_bArhAB",
  // one-tap sign-in buttons; a provider is listed here only after it is set up in Supabase.
  // Google is switched off: Russian sites may not sign people in through foreign services (149-FZ as amended by 406-FZ).
  // It stays set up in Supabase and in the code as a backup; adding "google" back to this list turns the button on again.
  oauth: ["yandex"],
  // Yandex Metrica counter number; loaded only after the visitor agrees to analytics cookies. Empty: no counter.
  metrikaId: "",
  // Yandex Advertising Network (RSYA) block ids, e.g. "R-A-1234567-1"; shown only after the visitor agrees to ad cookies. Empty: no ads.
  ads: { country: "", places: "" },
  // iPhone shortcut that sends a shared map link to nash-atlas.ru/?add=… (iCloud link). Empty: the help shows copy-and-paste instead.
  iosShortcut: "",
  // Yandex SmartCaptcha client key (public). A login code is requested only after the captcha; the Send Email hook in
  // Supabase (auth-mail) enforces it. Empty: no captcha, and the hook must be off.
  captchaKey: "ysc1_j3MQfxoZouoo7Jud36S9ml3suQ7e2p9swOcxqdxtd9229339",
  // Google sign-in runs on our own page (shows nash-atlas.ru, not the Supabase address); same client as in Supabase
  googleClientId: "444988932037-ve1fbt66uu4vlmi6qkhmrjaq2761e594.apps.googleusercontent.com"
};
