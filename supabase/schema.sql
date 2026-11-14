-- Наш атлас: accounts, maps, sharing. Run once in Supabase → SQL Editor.
-- Every account gets its own map; a map can be shared by link to read only or to edit.

create extension if not exists pgcrypto;

create table if not exists public.maps (
  id         uuid primary key default gen_random_uuid(),
  owner      uuid not null references auth.users(id) on delete cascade default auth.uid(),
  name       text not null default 'Мой атлас' check (char_length(name) between 1 and 80),
  created_at timestamptz not null default now()
);

create table if not exists public.map_members (
  map_id  uuid not null references public.maps(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role    text not null check (role in ('owner','editor','viewer')),
  email   text,
  joined_at timestamptz not null default now(),
  primary key (map_id, user_id)
);

create table if not exists public.map_invites (
  token      text primary key default encode(gen_random_bytes(16),'hex'),
  map_id     uuid not null references public.maps(id) on delete cascade,
  role       text not null check (role in ('editor','viewer')),
  created_by uuid not null references auth.users(id) on delete cascade default auth.uid(),
  created_at timestamptz not null default now(),
  revoked    boolean not null default false
);

-- one row per saved thing: places/<id>, notes/<id>, photos/<id>, assets/<id>, meta/seed …
create table if not exists public.docs (
  map_id     uuid not null references public.maps(id) on delete cascade,
  path       text not null check (char_length(path) between 3 and 200),
  data       jsonb not null,
  updated_at timestamptz not null default now(),
  updated_by uuid default auth.uid(),
  primary key (map_id, path)
);
create index if not exists docs_map_idx on public.docs(map_id);

-- helpers (security definer, so policies do not recurse)
create or replace function public.map_role(m uuid) returns text
language sql stable security definer set search_path = public as $$
  select role from map_members where map_id = m and user_id = auth.uid()
$$;
create or replace function public.can_read(m uuid) returns boolean
language sql stable security definer set search_path = public as $$ select public.map_role(m) is not null $$;
create or replace function public.can_edit(m uuid) returns boolean
language sql stable security definer set search_path = public as $$ select public.map_role(m) in ('owner','editor') $$;
create or replace function public.is_owner(m uuid) returns boolean
language sql stable security definer set search_path = public as $$ select public.map_role(m) = 'owner' $$;

-- the creator of a map becomes its owner
create or replace function public.add_owner() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into map_members(map_id,user_id,role,email)
  values (new.id, new.owner, 'owner', (select email from auth.users where id = new.owner))
  on conflict do nothing;
  return new;
end $$;
drop trigger if exists maps_add_owner on public.maps;
create trigger maps_add_owner after insert on public.maps for each row execute function public.add_owner();

alter table public.maps        enable row level security;
alter table public.map_members enable row level security;
alter table public.map_invites enable row level security;
alter table public.docs        enable row level security;

drop policy if exists maps_read   on public.maps;
drop policy if exists maps_insert on public.maps;
drop policy if exists maps_update on public.maps;
drop policy if exists maps_delete on public.maps;
create policy maps_read   on public.maps for select using (owner = auth.uid() or public.can_read(id));
create policy maps_insert on public.maps for insert with check (owner = auth.uid());
create policy maps_update on public.maps for update using (public.is_owner(id)) with check (public.is_owner(id));
create policy maps_delete on public.maps for delete using (public.is_owner(id));

drop policy if exists members_read   on public.map_members;
drop policy if exists members_update on public.map_members;
drop policy if exists members_delete on public.map_members;
create policy members_read   on public.map_members for select using (public.can_read(map_id));
create policy members_update on public.map_members for update using (public.is_owner(map_id) and role <> 'owner') with check (role in ('editor','viewer'));
-- the owner removes anyone but themselves; anyone can leave a map they do not own
create policy members_delete on public.map_members for delete using ((public.is_owner(map_id) and role <> 'owner') or (user_id = auth.uid() and role <> 'owner'));

drop policy if exists invites_owner on public.map_invites;
create policy invites_owner on public.map_invites for all using (public.is_owner(map_id)) with check (public.is_owner(map_id) and created_by = auth.uid());

drop policy if exists docs_read  on public.docs;
drop policy if exists docs_write on public.docs;
drop policy if exists docs_update on public.docs;
drop policy if exists docs_delete on public.docs;
create policy docs_read   on public.docs for select using (public.can_read(map_id));
create policy docs_write  on public.docs for insert with check (public.can_edit(map_id));
create policy docs_update on public.docs for update using (public.can_edit(map_id)) with check (public.can_edit(map_id));
create policy docs_delete on public.docs for delete using (public.can_edit(map_id));

-- accept a link: signed-in users join the map with the link's role (never lowering an existing role)
create or replace function public.accept_invite(t text) returns uuid
language plpgsql security definer set search_path = public as $$
declare inv map_invites; cur text;
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  select * into inv from map_invites where token = t and not revoked;
  if not found then raise exception 'invite not found'; end if;
  select role into cur from map_members where map_id = inv.map_id and user_id = auth.uid();
  if cur is null then
    insert into map_members(map_id,user_id,role,email) values (inv.map_id, auth.uid(), inv.role, (select email from auth.users where id = auth.uid()));
  elsif cur = 'viewer' and inv.role = 'editor' then
    update map_members set role = 'editor' where map_id = inv.map_id and user_id = auth.uid();
  end if;
  return inv.map_id;
end $$;

-- read-only links also work without an account
create or replace function public.shared_map(t text) returns json
language sql stable security definer set search_path = public as $$
  select json_build_object('map', json_build_object('id', m.id, 'name', m.name), 'role', i.role,
    'docs', coalesce((select json_agg(json_build_object('path', d.path, 'data', d.data)) from docs d where d.map_id = m.id and d.path not like 'assets/%'), '[]'::json))
  from map_invites i join maps m on m.id = i.map_id
  where i.token = t and not i.revoked
$$;
create or replace function public.shared_asset(t text, p text) returns jsonb
language sql stable security definer set search_path = public as $$
  select d.data from map_invites i join docs d on d.map_id = i.map_id
  where i.token = t and not i.revoked and d.path = p and p like 'assets/%'
$$;

grant execute on function public.accept_invite(text) to authenticated;
grant execute on function public.shared_map(text), public.shared_asset(text,text) to anon, authenticated;

-- live updates between devices
do $$ begin
  alter publication supabase_realtime add table public.docs;
exception when duplicate_object then null; when undefined_object then null; end $$;
