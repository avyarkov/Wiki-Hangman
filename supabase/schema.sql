-- Run this in the Supabase SQL Editor (Project > SQL Editor > New query) once per project.

create table if not exists completions (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  player_id uuid,
  difficulty text not null check (difficulty in ('easy', 'medium', 'hard', 'culture', 'science')),
  title text not null,
  won boolean not null,
  strikes int not null check (strikes between 0 and 6),
  letters_guessed text not null
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

-- Migration: adds a per-browser player id (see PLAYER_ID in index.html) so
-- completions can be grouped by player. Safe to re-run against a table created
-- by an earlier version of this file; no-ops if already applied.
alter table completions add column if not exists player_id uuid;
create index if not exists completions_player_id_idx on completions (player_id);

-- Migration: replaces the letters_used count with the actual guess sequence,
-- stored as a plain string of letters in guess order (e.g. 'EART').
-- Left nullable/unconstrained here (unlike the column definition above) so this
-- doesn't fail against any rows already logged under the old column.
alter table completions drop column if exists letters_used;
alter table completions add column if not exists letters_guessed text;
