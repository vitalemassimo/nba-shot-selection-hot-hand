# Data dictionary

Every column in the cleaned and feature tables, and every derived variable. Filled in during
Stages 3 and 4, then frozen with the `definitions-v1` tag.

## Shot table (`data/interim/`)

Cleaned shot table, one file per season and season type: `data/interim/shots_{rs|po}_{season}.parquet`.
One row per field-goal attempt, sorted by `game_id`, then `pbp_row` (chronological).
Built by `hothand.clean`; sources are the bulk shot table (S) and play-by-play (P).

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| game_id | str | S | 10-digit NBA game ID; 3rd digit 2 = regular season, 4 = playoffs |
| game_date | date | S | Game date |
| season | str | config | e.g. "2024-25" |
| season_type | str | config | "Regular Season" or "Playoffs" |
| season_flag | str | config | "bubble_playoffs" (2019-20), "shortened_schedule" (2020-21), else empty (D-003) |
| home_team, away_team | str | S | Team abbreviations |
| game_event_id | int | S | Event number in the game; NOT always chronological (D-017) |
| pbp_row | int | P | Position of the event in the game's play-by-play; defines shot order (D-017) |
| period | int | S | 1-4 regulation, 5+ overtime |
| clock_remaining_s | float | P | Seconds left in the period, to 0.1 s |
| game_elapsed_s | float | derived | Game-clock seconds since tip-off (12-min quarters, 5-min overtimes) |
| player_id, player_name | int, str | S | Shooter (the shot table's attribution; agrees with official FGA totals) |
| team_id, team_name | int, str | S | Shooter's team |
| is_home | bool | P | Shooter's team is the home team |
| score_home_before, score_away_before | int | P | Score immediately before the shot (a made shot is not included in its own row) |
| score_margin_before | int | derived | Shooter's team score minus opponent's, before the shot |
| action_type | str | S | e.g. "Jump Shot", "Driving Layup Shot" |
| shot_type | str | S | "2PT Field Goal" / "3PT Field Goal" (scorer's ruling) |
| shot_value | int | derived | 2 or 3, from shot_type (D-020) |
| shot_zone_basic | str | S | Restricted Area, In The Paint (Non-RA), Mid-Range, Left/Right Corner 3, Above the Break 3, Backcourt |
| shot_zone_area | str | S | Side of the court, e.g. "Left Side Center(LC)" |
| shot_zone_range | str | S | Distance band, e.g. "8-16 ft." |
| shot_distance_ft | int | S | Distance from the basket in feet, rounded down |
| coord_distance_ft | float | derived | sqrt(loc_x² + loc_y²) / 10, in feet |
| loc_x, loc_y | int | S | Court position in tenths of a foot, basket at (0, 0) |
| shot_made | int8 | S | 1 made, 0 missed |

## Feature table (`data/processed/`)

| Column | Type | Definition |
|--------|------|------------|
| _filled in Stage 4_ | | |
