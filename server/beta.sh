#!/bin/bash
# «Наш атлас»: the test copy of the site at https://beta.nash-atlas.ru, served by our own server.
# The copy is built from the `beta` branch of the repository and updates itself within 2 minutes of a push there.
# It uses the same accounts and data as the main site (api.nash-atlas.ru); it is hidden from search engines.
# Before running: DNS record A  beta.nash-atlas.ru → this server's IP (at reg.ru, like api.nash-atlas.ru).
# Run as root:  curl -fsSL https://raw.githubusercontent.com/Ignatus04/nash-atlas/main/server/beta.sh | bash
set -euo pipefail
ROOT=/opt/atlas
APP=$ROOT/supabase
B=$ROOT/beta
DOMAIN=beta.nash-atlas.ru
REPO=https://github.com/Ignatus04/nash-atlas
say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
[ "$(id -u)" = 0 ] || { echo "Запустите от root (sudo -i)."; exit 1; }

say "Проверяю, что $DOMAIN указывает на этот сервер"
MYIP=$(curl -fsS4 https://ifconfig.me || true)
DNSIP=$(getent ahostsv4 $DOMAIN | awk 'NR==1{print $1}' || true)
echo "IP сервера: ${MYIP:-?}   $DOMAIN → ${DNSIP:-нет записи}"
[ -n "$DNSIP" ] && [ "$DNSIP" = "$MYIP" ] || { echo "Сначала добавьте в reg.ru запись A: beta → $MYIP, подождите 5–30 минут и запустите снова."; exit 1; }
command -v rsync >/dev/null || apt-get install -y -qq rsync >/dev/null

say "Скрипт обновления беты"
mkdir -p $B/www
cat > $B/update.sh <<'UPD'
#!/bin/bash
# builds the beta branch into /opt/atlas/beta/www when it has changed
set -euo pipefail
B=/opt/atlas/beta
exec 9>$B/.lock; flock -n 9 || exit 0
[ -d $B/repo/.git ] || git clone -q --depth 1 --branch beta https://github.com/Ignatus04/nash-atlas $B/repo
cd $B/repo
git fetch -q --depth 1 origin beta
NEW=$(git rev-parse FETCH_HEAD)
[ "$NEW" = "$(cat $B/built 2>/dev/null || true)" ] && [ "${1:-}" != "force" ] && exit 0
git reset -q --hard FETCH_HEAD
docker run --rm -v $B/repo:/w -v $B/npm-cache:/root/.npm -w /w -e ATLAS_BETA=1 node:20-bookworm \
  sh -c 'npm install --no-audit --no-fund --silent && python3 scripts/build_web.py'
rsync -a --delete $B/repo/web/ $B/www/
echo "$NEW" > $B/built
echo "$(date '+%F %T') beta ${NEW:0:7}"
UPD
chmod +x $B/update.sh
$B/update.sh force

say "Сайт беты в Caddy"
cd $APP
SVC=$(docker compose config --format json | jq -r '.services|to_entries[]|select(.value.image|test("caddy"))|.key' | head -n1)
[ -n "$SVC" ] || { echo "Не нашёл Caddy в docker compose. Пришлите вывод: docker compose ps"; exit 1; }
CF=$(docker compose config --format json | jq -r --arg s "$SVC" '.services[$s].volumes[]|select(.target|test("Caddyfile$"))|.source' | head -n1)
if [ -z "$CF" ] || [ "$CF" = null ]; then   # the whole config folder may be mounted instead of the file
  D=$(docker compose config --format json | jq -r --arg s "$SVC" '.services[$s].volumes[]|select(.target=="/etc/caddy")|.source' | head -n1)
  [ -n "$D" ] && CF="$D/Caddyfile"
fi
[ -f "$CF" ] || { echo "Не нашёл Caddyfile. Пришлите вывод: docker compose config | grep -i caddy"; exit 1; }
if ! grep -q "$DOMAIN" "$CF"; then
  cp "$CF" "$CF.before-beta"
  cat >> "$CF" <<CADDY

$DOMAIN {
	root * /srv/beta
	encode zstd gzip
	header /sw.js Cache-Control "no-cache"
	header /index.html Cache-Control "no-cache"
	file_server
}
CADDY
fi
cat > $APP/docker-compose.beta.yml <<YML
services:
  $SVC:
    volumes:
      - $B/www:/srv/beta:ro
YML
grep -v '^COMPOSE_FILE=' .env > .env.new || true
CFILES=$(grep '^COMPOSE_FILE=' .env | cut -d= -f2-)
case ":$CFILES:" in *":docker-compose.beta.yml:"*) ;; *) CFILES="$CFILES:docker-compose.beta.yml";; esac
echo "COMPOSE_FILE=$CFILES" >> .env.new
# sign-in may return to the beta site as well
R=$(grep '^ADDITIONAL_REDIRECT_URLS=' .env | cut -d= -f2- || true)
grep -v '^ADDITIONAL_REDIRECT_URLS=' .env.new > .env.tmp; mv .env.tmp .env.new
case "$R" in *"$DOMAIN"*) ;; *) R="$R,https://$DOMAIN,https://$DOMAIN/**";; esac
echo "ADDITIONAL_REDIRECT_URLS=$R" >> .env.new
mv .env.new .env; chmod 600 .env

say "Серверные функции: разрешаю им отвечать бете"
[ -d $ROOT/repo/.git ] && (cd $ROOT/repo && git pull -q) || true
for f in expand-link auth-mail geo; do
  [ -f $ROOT/repo/supabase/functions/$f/index.ts ] && mkdir -p volumes/functions/$f && cp $ROOT/repo/supabase/functions/$f/index.ts volumes/functions/$f/index.ts
done
[ -f volumes/functions/geo/country.mmdb ] || curl -fsSL https://raw.githubusercontent.com/Ignatus04/nash-atlas/main/server/geo.sh | bash
docker compose up -d --wait >/dev/null
docker compose restart functions "$SVC" >/dev/null

say "Обновление каждые 2 минуты"
echo "*/2 * * * * root $B/update.sh >> $B/update.log 2>&1" > /etc/cron.d/atlas-beta

say "Проверка"
sleep 8
curl -fsS -o /dev/null -w "https://$DOMAIN: %{http_code}\n" https://$DOMAIN/ || echo "Пока не отвечает: сертификат выпускается 1–2 минуты, откройте https://$DOMAIN чуть позже."
echo -n "Определение страны: "; curl -s https://api.nash-atlas.ru/functions/v1/geo; echo
echo "Готово. Бета: https://$DOMAIN — обновляется сама после каждого изменения в ветке beta."
