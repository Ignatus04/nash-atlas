#!/bin/bash
# «Наш атлас»: copy accounts and maps from the cloud Supabase (France) into our server.
# Run as root after install.sh:  bash /opt/atlas/repo/server/migrate.sh
# The cloud database password is typed here and goes only to the cloud database.
set -euo pipefail
APP=/opt/atlas/supabase
W=/opt/atlas/migrate; mkdir -p $W; chmod 700 $W; cd $W
say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
PSQL="docker exec -i supabase-db psql -v ON_ERROR_STOP=1 -U supabase_admin -d postgres -q"

echo "Нужен пароль облачной базы Supabase (Project Settings → Database). Ввод не отображается."
read -r -s -p "Пароль облачной базы: " PGPW </dev/tty; echo
[ -n "$PGPW" ] || { echo "Пароль пустой."; exit 1; }
# the pooler address and user of the cloud project; the password goes in an environment variable, not in a URL
CLOUD="host=aws-1-eu-west-3.pooler.supabase.com port=5432 dbname=postgres user=postgres.hvqdjcpbevwuaymdrpye sslmode=require"
DUMP="docker run --rm -i --network host -e PGPASSWORD postgres:17 pg_dump"
export PGPASSWORD="$PGPW"
echo "Проверяю пароль…"
docker run --rm --network host -e PGPASSWORD postgres:17 psql "$CLOUD" -tAc "select 1" >/dev/null || { echo "Пароль не подошёл. Сбросьте его в Supabase (Project Settings → Database → Reset database password) и запустите снова."; exit 1; }

say "Выгружаю из облака (схема public, пользователи, данные)"
$DUMP "$CLOUD" --schema=public --schema-only --no-owner > schema.sql
$DUMP "$CLOUD" --data-only --table=auth.users --table=auth.identities > auth.sql
$DUMP "$CLOUD" --data-only --schema=public > data.sql
grep -c "^COPY\|^INSERT" auth.sql data.sql || true

say "Резервная копия нового сервера перед загрузкой"
/opt/atlas/backup.sh || true

say "Загружаю на наш сервер"
# a schema that already exists on the new server is dropped first so the cloud one is copied exactly
$PSQL <<'SQL'
drop schema if exists public cascade;
create schema public;
grant usage on schema public to anon, authenticated, service_role;
grant all on schema public to postgres, service_role;
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant all on functions to anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to anon, authenticated, service_role;
SQL
grep -v '^CREATE SCHEMA public;$\|^COMMENT ON SCHEMA public' schema.sql | $PSQL
# triggers off while copying rows, otherwise «add owner on new map» would duplicate members
( echo "set session_replication_role = replica;"; cat auth.sql; cat data.sql ) | $PSQL
# realtime for the shared maps, and the functions that may not have been run in the cloud
$PSQL <<'SQL'
do $$ begin
  begin alter publication supabase_realtime add table public.docs; exception when others then null; end;
end $$;
create table if not exists public.captcha_pass (email text primary key, until timestamptz not null);
alter table public.captcha_pass enable row level security;
revoke all on public.captcha_pass from anon, authenticated;
notify pgrst, 'reload schema';
SQL
grep -q "delete_my_account" schema.sql || sed -n '/create or replace function public.delete_my_account/,/grant execute on function public.delete_my_account() to authenticated;/p' /opt/atlas/repo/supabase/schema.sql | $PSQL

say "Сверка"
$PSQL -t <<'SQL'
select 'пользователей: '||(select count(*) from auth.users)||', карт: '||(select count(*) from public.maps)||', записей: '||(select count(*) from public.docs);
SQL
rm -f $W/*.sql
echo "Готово. Дальше: bash /opt/atlas/repo/server/yandex.sh (вход через Яндекс ID)."
