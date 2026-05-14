-- Migration 011: TMDb external_id namespace prefix (P1.9-hotfix-E)
-- TMDb movie and TV IDs are separate namespaces that can collide.
-- Prefix external_id with "tv:" or "movie:" to prevent cross-type matches.

-- Update existing records: derive prefix from external_granularity or canonical_items.content_type
update external_ids
set external_id = 'movie:' || external_id
where source = 'tmdb'
  and external_id not like 'tv:%'
  and external_id not like 'movie:%'
  and external_granularity = 'movie';

update external_ids
set external_id = 'tv:' || external_id
where source = 'tmdb'
  and external_id not like 'tv:%'
  and external_id not like 'movie:%'
  and external_granularity in ('tv', 'series', 'season', 'episode');

-- For records without granularity, derive from canonical_items
update external_ids
set external_id = 'movie:' || external_id
where source = 'tmdb'
  and external_id not like 'tv:%'
  and external_id not like 'movie:%'
  and external_granularity is null
  and canonical_item_id in (
    select id from canonical_items where content_type = 'movie'
  );

update external_ids
set external_id = 'tv:' || external_id
where source = 'tmdb'
  and external_id not like 'tv:%'
  and external_id not like 'movie:%'
  and external_granularity is null
  and canonical_item_id in (
    select id from canonical_items where content_type = 'tv'
  );

-- Any remaining unprefixed tmdb records default to 'movie:'
update external_ids
set external_id = 'unknown:' || external_id
where source = 'tmdb'
  and external_id not like 'tv:%'
  and external_id not like 'movie:%'
  and external_id not like 'unknown:%';

insert or ignore into schema_migrations(version) values (11);
