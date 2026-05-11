create table if not exists candidate_matches (
    id integer primary key autoincrement,
    candidate_id integer not null references candidates(id),
    is_in_baseline integer not null default 0,
    baseline_item_id integer references baseline_items(id),
    match_confidence text not null check (match_confidence in ('high', 'medium', 'low', 'no_match')),
    match_method text not null,
    match_score_detail real not null default 0.0,
    requires_human_review integer not null default 0,
    reason_text text,
    created_at text not null default current_timestamp
);

create unique index if not exists ux_candidate_matches_candidate
    on candidate_matches(candidate_id);

create index if not exists idx_candidate_matches_confidence
    on candidate_matches(match_confidence);

create index if not exists idx_candidate_matches_baseline
    on candidate_matches(baseline_item_id) where baseline_item_id is not null;
