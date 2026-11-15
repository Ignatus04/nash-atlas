#!/bin/bash
# «Наш атлас»: install Supabase on our own server in Russia (Ubuntu 24.04).
# Run as root:  curl -fsSL https://raw.githubusercontent.com/Ignatus04/nash-atlas/main/server/install.sh | bash
# Asks for the Postbox SMTP key (typed here, never sent anywhere else), generates all other secrets on the server.
set -euo pipefail
ROOT=/opt/atlas
APP=$ROOT/supabase
REPO=https://github.com/Ignatus04/nash-atlas
DOMAIN=api.nash-atlas.ru
ask() { local v; read -r -p "$1" v </dev/tty; printf '%s' "$v"; }
asks() { local v; read -r -s -p "$1" v </dev/tty; echo >/dev/tty; printf '%s' "$v"; }
say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }

[ "$(id -u)" = 0 ] || { echo "Запустите от root (sudo -i)."; exit 1; }
mkdir -p $ROOT $ROOT/backups && cd $ROOT

say "Проверяю, что $DOMAIN указывает на этот сервер"
MYIP=$(curl -fsS4 https://ifconfig.me || true)
DNSIP=$(getent ahostsv4 $DOMAIN | awk 'NR==1{print $1}' || true)
echo "IP сервера: ${MYIP:-?}   $DOMAIN → ${DNSIP:-нет записи}"
if [ -z "$DNSIP" ] || [ "$DNSIP" != "$MYIP" ]; then
  echo "Запись A для $DOMAIN ещё не указывает на этот сервер. Проверьте DNS в reg.ru и подождите 5–30 минут."
  [ "$(ask 'Продолжить всё равно? (да/нет) ')" = "да" ] || exit 1
fi

say "Обновления системы и защита"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get -y -qq upgrade && apt-get -y -qq install git curl jq openssl ufw unattended-upgrades fail2ban >/dev/null
ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443 >/dev/null; ufw --force enable >/dev/null
systemctl enable --now unattended-upgrades fail2ban >/dev/null 2>&1 || true
# swap: a 4 GB server is enough, swap protects from rare spikes
if ! swapon --show | grep -q .; then fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab; fi

say "Код сайта (функции, схема, настройки)"
rm -rf $ROOT/repo && git clone -q --depth 1 $REPO $ROOT/repo

if [ ! -f $APP/.env ]; then
  say "Supabase: официальная установка (несколько минут)"
  curl -fsSL https://raw.githubusercontent.com/supabase/supabase/master/docker/setup.sh -o /tmp/sb-setup.sh
  sh /tmp/sb-setup.sh -y --project-dir supabase
else
  echo "Supabase уже установлен в $APP, обновляю только наши настройки."
fi
cd $APP
# replace or add KEY=value in .env without sed (secrets may contain | or &)
setenv() { grep -v "^$1=" .env > .env.new || true; printf '%s=%s\n' "$1" "$2" >> .env.new; mv .env.new .env; chmod 600 .env; }
getenv() { grep "^$1=" .env | head -n1 | cut -d= -f2-; }

say "Адреса и почта"
setenv SUPABASE_PUBLIC_URL https://$DOMAIN
setenv API_EXTERNAL_URL https://$DOMAIN/auth/v1
setenv SITE_URL https://nash-atlas.ru
setenv ADDITIONAL_REDIRECT_URLS "https://nash-atlas.ru,https://nash-atlas.ru/**"
setenv PROXY_DOMAIN $DOMAIN
setenv DISABLE_SIGNUP false
setenv ENABLE_EMAIL_SIGNUP true
setenv ENABLE_EMAIL_AUTOCONFIRM false
setenv ENABLE_ANONYMOUS_USERS false
setenv ENABLE_PHONE_SIGNUP false
setenv FUNCTIONS_VERIFY_JWT false
setenv SMTP_HOST postbox.cloud.yandex.net
setenv SMTP_PORT 465
setenv SMTP_ADMIN_EMAIL noreply@nash-atlas.ru
setenv SMTP_SENDER_NAME '"Наш атлас"'
if [ "$(getenv SMTP_USER)" = "fake_mail_user" ] || [ -z "$(getenv SMTP_USER)" ]; then
  echo "Нужен API-ключ Postbox (сервисный аккаунт postbox-sender, область yc.postbox.send)."
  setenv SMTP_USER "$(ask 'Идентификатор API-ключа Postbox: ')"
  P=$(asks 'Секретный ключ Postbox (не отображается при вводе): ')
  setenv SMTP_PASS "$P"; setenv POSTBOX_API_KEY "$P"
fi
if [ -z "$(getenv SMARTCAPTCHA_SERVER_KEY)" ]; then
  setenv SMARTCAPTCHA_SERVER_KEY "$(asks 'Ключ сервера SmartCaptcha (Enter — пропустить): ')"
fi
setenv COMPOSE_FILE "docker-compose.yml:docker-compose.caddy.yml:docker-compose.atlas.yml"
cp $ROOT/repo/server/docker-compose.atlas.yml $APP/

say "Наши серверные функции"
for f in expand-link yandex-userinfo auth-mail; do
  mkdir -p volumes/functions/$f && cp $ROOT/repo/supabase/functions/$f/index.ts volumes/functions/$f/index.ts
done

say "Запуск (первый раз 3–10 минут)"
docker compose pull -q
docker compose up -d --wait || { docker compose ps; echo "Что-то не запустилось. Пришлите вывод выше."; exit 1; }

say "Резервная копия базы каждую ночь (хранятся 14 дней)"
cp $ROOT/repo/server/backup.sh $ROOT/backup.sh && chmod +x $ROOT/backup.sh
echo "17 3 * * * root $ROOT/backup.sh >> $ROOT/backups/backup.log 2>&1" > /etc/cron.d/atlas-backup

say "Проверка"
sleep 5
curl -fsS -o /dev/null -w "HTTPS $DOMAIN: %{http_code}\n" https://$DOMAIN/auth/v1/health -H "apikey: $(getenv SUPABASE_PUBLISHABLE_KEY)" || echo "HTTPS пока не отвечает: сертификат может выпускаться ещё пару минут."

cat <<MSG

Готово. Пришлите в чат эти две строки (они публичные):
  supabaseUrl: https://$DOMAIN
  supabaseKey: $(getenv SUPABASE_PUBLISHABLE_KEY)

Пароль от панели https://$DOMAIN (логин $(getenv DASHBOARD_USERNAME)) — сохраните у себя, в чат не присылайте:
  grep DASHBOARD_PASSWORD $APP/.env

Следующий шаг — перенос данных:  bash $ROOT/repo/server/migrate.sh
MSG
