-- Migration 010: multi-source structured fields (P1.8-E)
-- Adds structured columns to flixpatrol_top10 and trakt_trending.

-- FlixPatrol additions
alter table flixpatrol_top10 add column updated_at text;
alter table flixpatrol_top10 add column country_id text;
alter table flixpatrol_top10 add column company_id text;

-- Trakt additions
alter table trakt_trending add column genres_json text;
alter table trakt_trending add column trakt_status text;
alter table trakt_trending add column country text;
alter table trakt_trending add column network text;
alter table trakt_trending add column runtime integer;
alter table trakt_trending add column overview text;
alter table trakt_trending add column first_aired text;
alter table trakt_trending add column aired_episodes integer;
alter table trakt_trending add column certification text;
alter table trakt_trending add column updated_at text;

insert or ignore into schema_migrations(version) values (10);
