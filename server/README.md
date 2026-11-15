# Наш сервер Supabase (Россия)

Самостоятельно размещённый Supabase для `api.nash-atlas.ru`: аккаунты и карты хранятся в России (ч. 5 ст. 18 152-ФЗ).

| Файл | Что делает |
| --- | --- |
| `install.sh` | Ставит Docker и официальный self-hosted Supabase в `/opt/atlas/supabase`, HTTPS через Caddy, файрвол, наши функции, ночные копии базы. Все секреты создаются на сервере. |
| `docker-compose.atlas.yml` | Наши настройки поверх официальных: шаблон письма с сайта, лимиты писем, функции без JWT, база закрыта снаружи. |
| `migrate.sh` | Переносит схему `public`, пользователей (`auth.users`, `auth.identities`) и данные из облачного Supabase. |
| `yandex.sh` | Создаёт провайдера входа `custom:yandex` (как в облаке), userinfo — функция `yandex-userinfo`. |
| `backup.sh` | Ночная копия базы в `/opt/atlas/backups`, хранится 14 дней. |

Порядок: `install.sh` → `migrate.sh` → `yandex.sh` → новый `supabaseUrl` и `supabaseKey` в `web-src/config.js`.

Обслуживание на сервере (`cd /opt/atlas/supabase`): `sh run.sh status`, `sh run.sh logs auth`, обновление — `sh update.sh && sh run.sh pull && sh run.sh recreate` (сначала копия базы). Пароли — `sh run.sh secrets`, в чат и в git не передаются.
