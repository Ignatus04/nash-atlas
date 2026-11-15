#!/bin/bash
# «Наш атлас»: Yandex ID login on our server (custom OAuth provider "custom:yandex", as in the cloud project).
# Before: in oauth.yandex.ru add the Redirect URI https://api.nash-atlas.ru/auth/v1/callback
set -euo pipefail
APP=/opt/atlas/supabase; cd $APP
getenv() { grep "^$1=" .env | head -n1 | cut -d= -f2-; }
KEY=$(getenv SUPABASE_SECRET_KEY)
read -r -s -p "Client secret приложения Яндекс ID (oauth.yandex.ru, ввод не отображается): " SECRET </dev/tty; echo
BODY=$(jq -n --arg s "$SECRET" '{provider_type:"oauth2",identifier:"custom:yandex",name:"Яндекс ID",
  client_id:"384227b54f1b431b9bf604dbf1ef4be0",client_secret:$s,
  authorization_url:"https://oauth.yandex.ru/authorize",token_url:"https://oauth.yandex.ru/token",
  userinfo_url:"https://api.nash-atlas.ru/functions/v1/yandex-userinfo",scopes:["login:email","login:info","login:avatar"]}')
U=https://api.nash-atlas.ru/auth/v1/admin/custom-providers
if curl -fsS "$U/custom:yandex" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" >/dev/null 2>&1; then
  curl -fsS -X PUT "$U/custom:yandex" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "$BODY" >/dev/null
else
  curl -fsS -X POST "$U" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "$BODY" >/dev/null
fi && echo "Вход через Яндекс ID настроен." || echo "Не получилось. Пришлите вывод выше."
