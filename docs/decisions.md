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
**Status.** Confirmed by Massimo, 2026-10-15.

### D-003 · 2026-10-14 · Special seasons are flagged, not excluded
**Decision.** 2019-20 (bubble playoffs, no fans) and 2020-21 (shortened schedule) stay in the sample with
a flag column. Their influence is tested in Stage 7 ("drop special seasons").
**Reason.** Excluding them up front throws away a quarter of the playoff data on a guess.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-004 · 2026-10-14 · Data routes
**Decision.** Primary source is the bulk dataset (shufinskiy/nba_data) for every season it covers;
nba_api fills any missing recent season. One season is pulled from both routes and compared.
**Reason.** Bulk is fast and includes play-by-play (needed for score margin); nba_api is current.
Agreement between two independent sources is a quality signal.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-005 · 2026-10-14 · Distance units
**Decision.** Distances are stored in feet (the unit NBA.com publishes) and reported in feet with a
metre conversion in brackets.
**Alternatives.** Convert everything to metres.
**Reason.** The playbook names metres for Primary 1 but feet in Stage 5.6. Keeping the source unit avoids
a conversion step in every table; the outcome itself is unchanged. Noted here so the inconsistency
is resolved on record, before any data is seen.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-006 · 2026-10-14 · Definition of consecutive shots
**Decision.** Two field-goal attempts form a pair if they are by the same player, in the same game, with
no other attempt by that player between them, and no more than 240 seconds of game clock apart.
Pairs may span a period break in the primary specification.
**Alternatives.** No gap limit; same-period only; 60-480 s gaps. All are run in Stage 7.
**Reason.** 240 s (4 game minutes) is long enough to keep most within-stint sequences and short
enough that a pair rarely spans a trip to the bench. Chosen before any data was opened.
**Known limitation.** Shot-chart data contains field-goal attempts only, so free throws are invisible
to the sequence (a shooting foul followed by free throws looks like nothing happened).
**Status.** Confirmed by Massimo, 2026-10-15.

### D-007 · 2026-10-14 · Random seed
**Decision.** One global seed, `20261014`, in `config.yaml`, used everywhere randomness appears
(half split, clustering, permutations, bootstraps).
**Status.** Confirmed by Massimo, 2026-10-15.

### D-008 · 2026-10-14 · Rookie and veteran (revised by Massimo 2026-10-15)
**Decision (Massimo's wording).** Rookie = first NBA season, taken from the player table. Veteran =
10th season or later; seasons 2–9 are left out of H1.
**Replaces.** Claude's draft of 2026-10-14 (veteran = 5th season or later).
**Reason.** Using the window's first season would label veterans as rookies in 2018-19.
**Group sizes (regular season, 2018-19 to 2025-26, first season from the player table):**
rookies 816 player-seasons / 145,669 shots; seasons 2-4: 1,599 / 534,508; seasons 5-9: 1,331 /
663,271; season 10+: 720 player-seasons, 234 players / 346,438 shots.
**Status.** Revised and confirmed by Massimo, 2026-10-15 (seasons 2-9 stay in the full
sample but are left out of the H1 comparison).

### D-009 · 2026-10-14 · Usage tier
**Decision.** Tertiles of field-goal attempts per game within each season, among player-seasons with at
least 100 FGA. All-Stars are shown as a labelled subset, never used as the test variable.
**Reason.** All-Star status is partly an outcome of performing well.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-010 · 2026-10-14 · Calibration / analysis split
**Decision.** Each game is randomly assigned (seeded) to a calibration half or an analysis half, 50/50.
Clusters and the xFG model are fitted on calibration; every hypothesis test runs on analysis.
The assignment is saved to `data/processed/game_split.csv`.
**Reason.** Removes the circularity of building groups and testing on the same shots.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-011 · 2026-10-14 · Inference thresholds
**Decision.** 1,000 permutations; alpha 0.05; minimum 30 players and 2,000 shot pairs per segment cell
(otherwise reported as "too few shots to estimate"); Holm correction across H1-H4 on distance;
standard errors clustered by player.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-012 · 2026-10-14 · Robustness survival rule
**Decision.** The headline survives if its sign is unchanged and its 95% CI overlaps the baseline
estimate in at least 80% of the Stage 7 variations.
**Reason.** Fixed before running any variation, so the bar cannot move after seeing results.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-013 · 2026-10-15 · Bulk dataset covers the whole window
**Decision.** All 8 seasons (regular season and playoffs) of shot details and play-by-play
(`nbastatsv3`) come from the bulk dataset. nba_api is used for the player table and the cross-check.
**Reason.** The bulk index lists `shotdetail_2025` and `nbastatsv3_2025` (season 2025-26), so the
playbook's open item "does the bulk dataset cover 2025-26?" resolves to yes. One source for all
seasons avoids mixing collection methods.
**Status.** Confirmed by Massimo, 2026-10-15.

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
**Status.** Confirmed by Massimo, 2026-10-15.

### D-016 · 2026-10-15 · All-Star source
**Decision.** All-Star selections come from the "Rosters" section of each Wikipedia
`<YEAR>_NBA_All-Star_Game` page (page revision ids stored in `data/reference/allstars.csv`).
Every selected player counts, including injured selections and their replacements.
**Reason.** Citable and versioned. All-Star status is only a labelled subset (D-009), never a test
variable, so small roster-definition differences cannot move a pre-registered result.
**Check (2026-10-15, requested by Massimo).** From 2025 the game uses more than two teams (2026:
US and World teams). Wikipedia's "Rosters" section still lists every selection by conference; all 28
players in the 2026 team lineups and all 26 All-Stars in the 2025 lineups are in our list. The 2025
lineups also contain 8 Rising Stars players (e.g. Amen Thompson, Zach Edey), who joined as a fourth
team but were not All-Star selections, so they are correctly excluded.
**Status.** Checked and confirmed by Massimo, 2026-10-15.

### D-017 · 2026-10-15 · Shot order comes from the play-by-play file order, not event numbers
**Finding.** Sorting a player's shots by event number sends the game clock backwards 500-770 times per
regular season. Example: 2024-25 game 0022400002, event 329 (a missed tip at 1:39 of Q2) was
numbered after event 326 (0:03 of Q2). Event numbers are sometimes assigned late (corrections).
In the play-by-play file's row order, the clock never runs backwards (0 cases in all 16 files).
**Decision.** Order shots within a game by the play-by-play file position (`pbp_row`), which
agrees with the game clock. The clock (with tenths of a second) comes from the play-by-play.
**Why it matters.** The unit of analysis is a pair of consecutive shots; a wrong order would build
wrong pairs and attach wrong "previous shot" results.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-018 · 2026-10-15 · 2025-26 recording change for end-of-quarter heaves
**Finding.** In 2025-26 the play-by-play has 1,093 team-level "Heave" events (e.g. "NETS Heave"),
a type absent in earlier seasons, and player-credited shots from 36+ ft in the last 3 seconds of
Q1-Q3 fall from 500-650 per season to 49, of which 53% are makes (2-4% in earlier seasons).
Official box-score FGA totals still match the shot table exactly, so missed end-of-quarter heaves
are no longer counted as a player's field-goal attempt from 2025-26.
**Decision (Stage 3).** No change to the cleaned data: the shot table is kept as published.
**Decision (deferred to Stage 4, fixed before analysis).** Heaves must be treated identically in
every season, otherwise 2025-26 differs mechanically. Stage 4 excludes shots matching the
2025-26 pattern (36+ ft, last 3 s of Q1-Q3, made or missed) from every season, and a heave also
breaks a pair rather than being silently skipped. Exact thresholds go into config.yaml then.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-019 · 2026-10-15 · Drop 8 shots with conflicting shooter attribution
**Finding.** 8 shots out of 1,804,934 (all seasons) either have no play-by-play event with the same
game and event number, or the play-by-play names a different player (e.g. shot table: Rudy Gay,
play-by-play: Markkanen). One 2025-26 case maps to a team "Heave" event.
**Decision.** Drop them in structural cleaning (counted in the attrition table).
**Reason.** They cannot be placed in the event sequence with confidence, so any pair built on them
could be wrong. 8 shots cannot move any result.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-020 · 2026-10-15 · Shots on the three-point line: zone vs shot type
**Finding.** 1-210 shots per file (21.9-24.0 ft from the basket) have a location zone that disagrees
with the scorer's 2-or-3-point ruling (e.g. zone "Above the Break 3", shot type "2PT").
**Decision.** Keep both columns as published. Shot value (2 or 3) follows the scorer's ruling;
the zone outcome uses the published zone. Stated in the data dictionary.
**Reason.** Both are official; the disagreement is a line call, affects <0.1% of shots, and
relabelling would be a judgement made after looking at data.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-021 · 2026-10-15 · Games in scope
**Finding.** The data contains only regular-season (game ID type 2) and playoff (type 4) games:
no play-in games (type 5) and no NBA Cup final (type 6, which does not count in the standings).
Game counts match the real schedules (1,230 per season; 1,059 in 2019-20; 1,080 in 2020-21).
**Decision.** Keep this scope. Play-in games are neither regular season nor playoffs, so they are
out of scope for H4 anyway.
**Status.** Confirmed by Massimo, 2026-10-15.

### D-022 · 2026-10-15 · Garbage time (Massimo)
**Decision (Massimo's wording).** Garbage time in the 4th quarter is just to be considered if the
score is not close, like if a team is losing by 20+ points.
**Operationalised as.** A shot is in garbage time if it is in the 4th quarter, with 5 minutes or
less left, and the absolute score margin before the shot is 20 or more. Overtime is never garbage
time. Massimo kept the 5-minute condition: joining the two makes more sense.
Used only in the Stage 7 robustness variation "exclude heaves and garbage time".
**Status.** Confirmed by Massimo, 2026-10-15.

### D-023 · 2026-10-15 · Thresholds that were in config.yaml without an entry
**Decision.** Clustering: player-seasons need at least 200 field-goal attempts; k tested from 3 to
7; stability checked over 20 seeds and 100 bootstrap resamples. Robustness: pair-gap variants of
60, 120, 240 and 480 s and no limit; minimum-attempt variants 50, 100 and 200; heaves are shots in
the last 3 s of a period. Data sanity ranges: 150,000-240,000 attempts per regular season,
8,000-25,000 per playoffs. Proposed by Claude, reviewed by Massimo.
**Status.** Confirmed by Massimo, 2026-10-15.


### D-024 · 2026-10-15 · Leave out pairs where the next shot is a putback or tip (Massimo)
**Finding (flagged by Claude in the Stage 3 spot-check).** In 2024-25 game 0022400002, Stewart misses
a tip at 1:40 of Q2, rebounds, misses another tip at 1:39 and scores a putback at 1:36. With the D-006
pair definition each of these is "after a miss, the next shot is at the rim", which is the H0
prediction produced by rebounding mechanics rather than by a shot-selection decision.
**Decision (Massimo's wording).** Leave out pairs where the next shot is a putback or tip.
**Alternatives considered.** A minimum time between the two shots; requiring the next shot to come
from a new possession.
**Reason (Massimo).** Finding the right time between the two shots with good reasoning is basically
impossible; requiring a new possession takes away the importance of offensive rebounding and then
resetting the offense.
**Operationalised as.** A pair is left out when the next shot's `action_type` is one of: Tip Layup
Shot (38,559 shots), Putback Layup Shot (28,012), Tip Dunk Shot (6,489), Putback Dunk Shot (4,233).
Together 77,293 of 1,804,926 cleaned shots (4.3%), 8,261-10,553 per regular season. Counted before
any pair or outcome was computed.
**Putback as the previous shot (Massimo's wording, 2026-10-15).** The pair putback-jump shot
should not count because a putback is basically something that you have to take. You got the ball
under the basket, so as a basketball player, that is one of the easiest shots that you have,
without accounting for the defender in this statement, while a jump shot comes from a more
reasoned-out reading of the defence and what you, as a player, can do.
**Operationalised as.** A pair is left out when either shot is a putback or tip. The putback still
sits between the shots around it, so under D-006 (no other attempt in between) a miss, putback,
jump shot sequence produces no pair at all.
**Status.** Decided by Massimo, 2026-10-15.

### D-025 · 2026-10-15 · Game split drawn within each season and season type (Massimo)
**Finding.** One 50/50 draw over all 10,191 games gave individual playoff seasons 44-59% calibration
games (only 35 analysis games in the 2020-21 playoffs).
**Decision (Massimo).** Draw the seeded 50/50 split separately inside each season x season type.
Refines D-010; games, not shots, are still the unit. Saved to `data/processed/game_split.csv`.
**Status.** Decided by Massimo, 2026-10-15.

### D-026 · 2026-10-15 · Backcourt shots are left out (Massimo)
**Finding.** 274 backcourt shots are not heaves under D-018 (mostly 4th-quarter or mid-period
desperation shots); they have no zone in the five-zone scheme.
**Decision (Massimo).** Leave them out, like heaves: a backcourt shot is never analysed, and any pair
touching one is left out (it stays in the sequence, so it also breaks the pair around it).
**Status.** Decided by Massimo, 2026-10-15.

### D-027 · 2026-10-15 · Leave-one-out baseline (Massimo)
**Decision (Massimo).** A shot's baseline is the mean distance and zone mix of the same player's
other shots in the same season, the same season type (regular season and playoffs separate) and
the same calibration/analysis half. Baseline shots are the analysis population: no heaves,
putbacks, tips or backcourt shots. A player with one shot in a group has no baseline.
**Status.** Decided by Massimo, 2026-10-15.

### D-028 · 2026-10-15 · Distance measure (Massimo)
**Decision (Massimo).** Distance is computed from the court coordinates, sqrt(x² + y²) / 10, to
0.1 ft (`coord_distance_ft`), not the published distance, which is rounded down to whole feet.
The two agree within 1 ft on every shot (Stage 3 audit).
**Status.** Decided by Massimo, 2026-10-15.

### D-029 · 2026-10-15 · Putbacks and tips count in the streak state (Massimo)
**Decision (Massimo's wording).** I would count a putback in the streak because it brings energy and
confidence to the player, especially when it is not on your own miss: the player worked hard for
that rebound and got rewarded.
**Details (Massimo, 2026-10-15).** Tips count too. A missed putback or tip counts as a miss (it ends a
run of makes); a made one extends it.
**Operationalised as.** Putbacks and tips stay out of analysed pairs (D-024) but are links in the
streak chain, so they enter "last two shots" and "3+ makes in a row". Heaves, backcourt shots, the
gap rule and a new game still break the chain.
**Status.** Decided by Massimo, 2026-10-15.
