#!/bin/bash
# «Наш атлас»: send login emails through the Postbox HTTPS API (auth-mail function) instead of SMTP.
# Run as root:  bash /opt/atlas/repo/server/mail-hook.sh
set -euo pipefail
APP=/opt/atlas/supabase
cd /opt/atlas/repo && git pull -q
cd $APP
setenv() { grep -v "^$1=" .env > .env.new || true; printf '%s=%s\n' "$1" "$2" >> .env.new; mv .env.new .env; chmod 600 .env; }
getenv() { grep "^$1=" .env | head -n1 | cut -d= -f2-; }
[ -n "$(getenv SEND_EMAIL_HOOK_SECRET)" ] || setenv SEND_EMAIL_HOOK_SECRET "v1,whsec_$(openssl rand -base64 32)"
setenv SEND_EMAIL_HOOK_ENABLED true
if [ -z "$(getenv POSTBOX_API_KEY)" ]; then
  read -r -s -p "Секретный ключ Postbox (не отображается при вводе): " P </dev/tty; echo; setenv POSTBOX_API_KEY "$P"
fi
cp /opt/atlas/repo/server/docker-compose.atlas.yml $APP/
cp /opt/atlas/repo/supabase/functions/auth-mail/index.ts volumes/functions/auth-mail/index.ts
docker compose up -d --force-recreate auth functions >/dev/null 2>&1
sleep 8
docker compose ps auth functions --format '{{.Service}}: {{.Status}}'
echo "Готово. Попробуйте войти по почте на nash-atlas.ru."
