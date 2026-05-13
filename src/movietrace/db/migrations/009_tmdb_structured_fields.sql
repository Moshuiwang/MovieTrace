-- Migration 009: TMDb structured fields (P1.8-C)
-- Adds structured columns to tmdb_trending for trending/popular and detail fields.

alter table tmdb_trending add column adult integer;
alter table tmdb_trending add column softcore integer;
alter table tmdb_trending add column backdrop_path text;
alter table tmdb_trending add column poster_path text;
alter table tmdb_trending add column overview text;
alter table tmdb_trending add column genre_ids_json text;
alter table tmdb_trending add column origin_country_json text;
alter table tmdb_trending add column first_air_date text;
alter table tmdb_trending add column movie_release_date text;
alter table tmdb_trending add column original_name text;

alter table tmdb_trending add column last_air_date text;
alter table tmdb_trending add column next_air_date text;
alter table tmdb_trending add column last_episode_air_date text;
alter table tmdb_trending add column last_episode_season_number integer;
alter table tmdb_trending add column last_episode_number integer;
alter table tmdb_trending add column number_of_seasons integer;
alter table tmdb_trending add column number_of_episodes integer;
alter table tmdb_trending add column tmdbtv_status text;
alter table tmdb_trending add column in_production integer;
alter table tmdb_trending add column genres_json text;
alter table tmdb_trending add column seasons_json text;
alter table tmdb_trending add column last_episode_to_air_json text;
alter table tmdb_trending add column next_episode_to_air_json text;
alter table tmdb_trending add column networks_json text;
alter table tmdb_trending add column production_companies_json text;
alter table tmdb_trending add column spoken_languages_json text;
alter table tmdb_trending add column created_by_json text;

insert or ignore into schema_migrations(version) values (9);
