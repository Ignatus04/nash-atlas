# Письма входа

`login.html` вставляется в два шаблона Supabase (Authentication → Emails → Templates):

- **Confirm signup** — первое письмо новому человеку;
- **Magic link** — письмо при каждом следующем входе.

Тема для обоих: `Код для входа в «Наш атлас»`.

Шаблоны можно менять только после подключения своей почты (SMTP).

## Почта через Yandex Cloud Postbox

Supabase → Authentication → Emails → SMTP Settings:
host `postbox.cloud.yandex.net`, port `465`, username — идентификатор API-ключа, password — секретная часть ключа
(ключ сервисного аккаунта с ролью `postbox.sender`, область действия `yc.postbox.send`).
Sender email `noreply@nash-atlas.ru`, sender name `Наш атлас`.

## Вход через Яндекс ID

Функция `supabase/functions/yandex-userinfo` переводит ответ Яндекса в стандартные поля (`sub`, `email`).
Провайдер в Supabase: `custom:yandex`, тип OAuth2,
Authorization URL `https://oauth.yandex.ru/authorize`, Token URL `https://oauth.yandex.ru/token`,
UserInfo URL `https://hvqdjcpbevwuaymdrpye.supabase.co/functions/v1/yandex-userinfo`.
Кнопка на сайте появляется, когда в `web-src/config.js` в `oauth` добавлен `"yandex"` (для Google — `"google"`).
