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
# Postbox's HTTPS API needs a static access key (not the API key used for SMTP)
if [ -z "$(getenv POSTBOX_KEY_ID)" ] || [ -z "$(getenv POSTBOX_KEY_SECRET)" ]; then
  echo "Нужен статический ключ доступа сервисного аккаунта postbox-sender."
  read -r -p "Идентификатор ключа (начинается с YCA): " KID </dev/tty
  read -r -s -p "Секретный ключ (не отображается при вводе): " KSEC </dev/tty; echo
  setenv POSTBOX_KEY_ID "$KID"; setenv POSTBOX_KEY_SECRET "$KSEC"
fi
read -r -p "На какую почту отправить пробное письмо: " TO </dev/tty
echo "Проверяю ключ: отправляю пробное письмо…"
CODE=$(curl -s -o /tmp/pb.out -w '%{http_code}' --aws-sigv4 "aws:amz:ru-central1:ses" --user "$(getenv POSTBOX_KEY_ID):$(getenv POSTBOX_KEY_SECRET)" \
  -H "Content-Type: application/json" -X POST https://postbox.cloud.yandex.net/v2/email/outbound-emails \
  -d '{"FromEmailAddress":"noreply@nash-atlas.ru","Destination":{"ToAddresses":["'"$TO"'"]},"Content":{"Simple":{"Subject":{"Data":"check"},"Body":{"Text":{"Data":"check"}}}}}')
if [ "$CODE" != "200" ]; then
  echo "Postbox ответил $CODE: $(head -c 300 /tmp/pb.out)"
  echo "Ключ не подошёл. Проверьте, что это статический ключ сервисного аккаунта с ролью postbox.sender."
  grep -v "^POSTBOX_KEY_ID=\|^POSTBOX_KEY_SECRET=" .env > .env.new; mv .env.new .env; chmod 600 .env
  exit 1
fi
echo "Ключ работает."
cp /opt/atlas/repo/server/docker-compose.atlas.yml $APP/
cp /opt/atlas/repo/supabase/functions/auth-mail/index.ts volumes/functions/auth-mail/index.ts
docker compose up -d --force-recreate auth functions >/dev/null 2>&1
sleep 8
docker compose ps auth functions --format '{{.Service}}: {{.Status}}'
echo "Готово. Попробуйте войти по почте на nash-atlas.ru."
