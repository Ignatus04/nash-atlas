#!/bin/bash
# «Наш атлас»: visitor-country lookup (function `geo`) with the free DB-IP Lite country database (CC BY 4.0).
# Run as root once:  bash /opt/atlas/repo/server/geo.sh   — it also installs a monthly update (cron).
set -euo pipefail
APP=/opt/atlas/supabase
DIR=$APP/volumes/functions/geo
[ -d /opt/atlas/repo ] && (cd /opt/atlas/repo && git pull -q) || true
mkdir -p $DIR
cp /opt/atlas/repo/supabase/functions/geo/index.ts $DIR/index.ts
get() { curl -fsSL "https://download.db-ip.com/free/dbip-country-lite-$1.mmdb.gz" -o /tmp/dbip.mmdb.gz; }
get "$(date +%Y-%m)" || get "$(date -d '-1 month' +%Y-%m)"
gunzip -c /tmp/dbip.mmdb.gz > $DIR/country.mmdb.new && mv $DIR/country.mmdb.new $DIR/country.mmdb && rm -f /tmp/dbip.mmdb.gz
echo "База DB-IP: $(du -h $DIR/country.mmdb | cut -f1)"
cp /opt/atlas/repo/server/geo.sh /opt/atlas/geo.sh
echo "23 4 3 * * root bash /opt/atlas/geo.sh >> /opt/atlas/backups/geo.log 2>&1" > /etc/cron.d/atlas-geo
cd $APP && docker compose restart functions >/dev/null 2>&1
sleep 6
echo -n "Проверка: "; curl -s https://api.nash-atlas.ru/functions/v1/geo; echo
