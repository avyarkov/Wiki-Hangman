-- Run this in the Supabase SQL Editor (Project > SQL Editor > New query) once per project.

create table if not exists completions (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  player_id uuid,
  difficulty text not null check (difficulty in ('easy', 'medium', 'hard', 'culture', 'science')),
  title text not null,
  won boolean not null,
  strikes int not null check (strikes between 0 and 6),
  letters_guessed text not null,
  duration_seconds int not null,
  origin text not null
);

-- RLS is default-deny once enabled. The policy below only allows INSERT from the
-- public anon key (used client-side) -- there is no select/update/delete policy,
-- so completed rows can't be read back or tampered with through the public API.
alter table completions enable row level security;

create policy "Allow anonymous inserts"
  on completions
  for insert
  to anon
  with check (true);

-- Needed if the project has "Automatically expose new tables" disabled
-- (Data API > Security): that setting controls the base table grant, which
-- Postgres checks before RLS policies even apply. Harmless no-op otherwise.
grant insert on completions to anon;


create table if not exists ratings (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  player_id uuid,
  topic text not null,
  difficulty text not null check (difficulty in ('easy', 'medium', 'hard', 'culture', 'science')),
  rating text not null check (rating in ('good', 'ok', 'bad')),
  origin text not null
);

alter table ratings enable row level security;

create policy "Allow anonymous inserts"
  on ratings
  for insert
  to anon
  with check (true);

grant insert on ratings to anon;