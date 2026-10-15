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

## Feature table (`data/processed/features.parquet`)

One row per analysed pair (D-006, D-024, D-026), built by `hothand.features`. The row is the
**next shot**: every column of the cleaned shot table describes it, plus the columns below.
Not committed (large); rebuilt by `make features`.

| Column | Type | Definition |
|--------|------|------------|
| half | str | "calibration" or "analysis" (D-010, D-025); hypothesis tests use "analysis" only |
| is_putback_tip, is_heave, is_backcourt | bool | Shot flags (D-024, D-018, D-026); always False for analysed pairs |
| in_analysis_population | bool | Not a heave, putback, tip or backcourt shot |
| zone | str | Five analysis zones: restricted_area, paint, mid_range, corner_three, above_break_three |
| xfg | float | Expected make probability of the next shot from location and type only (D-032) |
| baseline_n | int | Number of the player's other shots behind the baseline |
| baseline_distance_ft | float | Leave-one-out mean distance of the player's other shots in the same season, season type and half (D-027) |
| baseline_{zone} | float | Leave-one-out share of the player's other shots in each zone (D-027) |
| distance_vs_baseline_ft | float | Next-shot distance (`coord_distance_ft`, D-028) minus baseline_distance_ft. **Primary 1** |
| next_is_{zone}, next_is_three | int8 | Next shot in that zone / a three-pointer. **Primary 2** |
| shot_number | int | Next shot's attempt number for this player in the game |
| gap_s | float | Game-clock seconds since the previous shot |
| same_period | bool | Previous shot in the same period |
| prev_pbp_row, prev_shot_made, prev_coord_distance_ft, prev_shot_distance_ft, prev_zone, prev_shot_value, prev_action_type, prev_game_elapsed_s | | The previous shot's values |
| prev_made | int8 | Previous shot made (1) or missed (0). The condition of every test |
| prev_xfg | float | Previous shot's xFG |
| prev_surprise | float | prev_made minus prev_xfg (playbook 5.2) |
| prev_make_run | float | Consecutive makes ending at the previous shot, along the streak chain (putbacks and tips count, D-029) |
| prev2_made | float | Result of the shot before the previous one in the chain (NaN if the chain is shorter) |
| last_two | str | "made-made", "made-miss", "miss-made", "miss-miss", or "" if no second shot in the chain |
| three_plus_makes | bool | prev_make_run >= 3 |
| season_no | int | NBA season number (1 = rookie), from the first season actually played (D-030) |
| experience_group | str | "rookie", "veteran" (10th season+), or empty (seasons 2-9, out of H1; D-008) |
| usage_tier | str | low / mid / high third of regular-season FGA per game (D-009, D-031); empty below 100 FGA |
| all_star | bool | Selected for that season's All-Star Game (D-016); labelled subset only |
| cluster | str | rim_bigs, mid_range_scorers, rim_and_corner, three_point_shooters (D-033 to D-035); empty if not clustered |

Supporting tables (committed, small): `data/processed/game_split.csv` (game -> half),
`data/processed/player_seasons.csv` (segment labels), `data/processed/player_clusters.csv`
(zone shares and cluster per clustered player-season).
