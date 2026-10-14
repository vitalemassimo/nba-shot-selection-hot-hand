# Decision log

One dated entry for every choice that could change a result: the decision, the alternatives
considered, and the reason. Entries are never edited after the fact; a changed decision gets a new
entry that references the old one.

---

### D-001 · 2026-10-14 · Environment
**Decision.** Python 3.13 in a project virtual environment (`.venv`), core versions pinned in
`requirements.txt`, full transitive lock in `requirements-lock.txt`.
**Alternatives.** conda `environment.yml`; Colab.
**Reason.** nba_api needs Python 3.10+. A venv plus pip lock is the simplest thing a stranger can
reproduce. Colab is excluded because NBA.com reportedly blocks cloud IPs and files do not persist.

### D-002 · 2026-10-14 · Season window
**Decision.** Eight completed seasons, 2018-19 to 2025-26, regular season and playoffs.
**Alternatives.** A longer window (more data, but mixes the pre-2018 era of fewer threes); a shorter
window (cleaner era, too few rookie and playoff shots).
**Reason.** The three-point-heavy style is reasonably stable over this span, so playstyle clusters do not
mix eras, and eight seasons give enough shots for the rookie and playoff splits.

### D-003 · 2026-10-14 · Special seasons are flagged, not excluded
**Decision.** 2019-20 (bubble playoffs, no fans) and 2020-21 (shortened schedule) stay in the sample with
a flag column. Their influence is tested in Stage 7 ("drop special seasons").
**Reason.** Excluding them up front throws away a quarter of the playoff data on a guess.

### D-004 · 2026-10-14 · Data routes
**Decision.** Primary source is the bulk dataset (shufinskiy/nba_data) for every season it covers;
nba_api fills any missing recent season. One season is pulled from both routes and compared.
**Reason.** Bulk is fast and includes play-by-play (needed for score margin); nba_api is current.
Agreement between two independent sources is a quality signal.

### D-005 · 2026-10-14 · Distance units
**Decision.** Distances are stored in feet (the unit NBA.com publishes) and reported in feet with a
metre conversion in brackets.
**Alternatives.** Convert everything to metres.
**Reason.** The playbook names metres for Primary 1 but feet in Stage 5.6. Keeping the source unit avoids
a conversion step in every table; the outcome itself is unchanged. Noted here so the inconsistency
is resolved on record, before any data is seen.

### D-006 · 2026-10-14 · Definition of consecutive shots
**Decision.** Two field-goal attempts form a pair if they are by the same player, in the same game, with
no other attempt by that player between them, and no more than 240 seconds of game clock apart.
Pairs may span a period break in the primary specification.
**Alternatives.** No gap limit; same-period only; 60-480 s gaps. All are run in Stage 7.
**Reason.** 240 s (4 game minutes) is long enough to keep most within-stint sequences and short
enough that a pair rarely spans a trip to the bench. Chosen before any data was opened.
**Known limitation.** Shot-chart data contains field-goal attempts only, so free throws are invisible
to the sequence (a shooting foul followed by free throws looks like nothing happened).

### D-007 · 2026-10-14 · Random seed
**Decision.** One global seed, `20261014`, in `config.yaml`, used everywhere randomness appears
(half split, clustering, permutations, bootstraps).

### D-008 · 2026-10-14 · Rookie and veteran
**Decision.** Rookie = the player's first NBA season, taken from the player table (first season / draft
year), not from the first season in the window. Veteran = fifth NBA season or later. Seasons 2-4
remain in the full sample but are excluded from the H1 comparison.
**Reason.** Using the window's first season would label veterans as rookies in 2018-19.

### D-009 · 2026-10-14 · Usage tier
**Decision.** Tertiles of field-goal attempts per game within each season, among player-seasons with at
least 100 FGA. All-Stars are shown as a labelled subset, never used as the test variable.
**Reason.** All-Star status is partly an outcome of performing well.

### D-010 · 2026-10-14 · Calibration / analysis split
**Decision.** Each game is randomly assigned (seeded) to a calibration half or an analysis half, 50/50.
Clusters and the xFG model are fitted on calibration; every hypothesis test runs on analysis.
The assignment is saved to `data/processed/game_split.csv`.
**Reason.** Removes the circularity of building groups and testing on the same shots.

### D-011 · 2026-10-14 · Inference thresholds
**Decision.** 1,000 permutations; alpha 0.05; minimum 30 players and 2,000 shot pairs per segment cell
(otherwise reported as "too few shots to estimate"); Holm correction across H1-H4 on distance;
standard errors clustered by player.

### D-012 · 2026-10-14 · Robustness survival rule
**Decision.** The headline survives if its sign is unchanged and its 95% CI overlaps the baseline
estimate in at least 80% of the Stage 7 variations.
**Reason.** Fixed before running any variation, so the bar cannot move after seeing results.

### D-013 · 2026-10-15 · Bulk dataset covers the whole window
**Decision.** All 8 seasons (regular season and playoffs) of shot details and play-by-play
(`nbastatsv3`) come from the bulk dataset. nba_api is used for the player table and the cross-check.
**Reason.** The bulk index lists `shotdetail_2025` and `nbastatsv3_2025` (season 2025-26), so the
playbook's open item "does the bulk dataset cover 2025-26?" resolves to yes. One source for all
seasons avoids mixing collection methods.

### D-014 · 2026-10-15 · NBA.com league-wide shot requests are truncated
**Finding.** A league-wide `ShotChartDetail` request for 2024-25 regular season returned exactly
102,400 rows (the bulk file has 219,527). The endpoint silently caps responses.
**Decision.** Pull nba_api shots one team at a time and concatenate; fail loudly if any part hits the cap.

### D-015 · 2026-10-15 · Cross-check result and one disagreeing shot
**Finding.** 2024-25 (regular season and playoffs, 233,904 shots) matches one-to-one between routes
on game ID, event ID and player ID, with identical made flags. One shot differs in location:
game 22401194, event 653, Cam Spencer: bulk 26 ft / Above the Break 3, NBA.com 22 ft / Mid-Range.
**Decision.** Keep the bulk value, so every season comes from the same source. Effect on any
result is negligible (1 in 233,904 shots).

### D-016 · 2026-10-15 · All-Star source
**Decision.** All-Star selections come from the "Rosters" section of each Wikipedia
`<YEAR>_NBA_All-Star_Game` page (page revision ids stored in `data/reference/allstars.csv`).
Every selected player counts, including injured selections and their replacements.
**Reason.** Citable and versioned. All-Star status is only a labelled subset (D-009), never a test
variable, so small roster-definition differences cannot move a pre-registered result.
