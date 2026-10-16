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
play-by-play: L. Markkanen). One 2025-26 case maps to a team "Heave" event.
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
**Finding (flagged by Claude in the Stage 3 spot-check).** In 2024-25 game 0022400002, I. Stewart misses
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

### D-030 · 2026-10-15 · Rookie = first season actually played (Massimo)
**Finding.** The player table's `FROM_YEAR` is the first season on a roster, not the first season
played: 23 players who debuted in the window are listed a year early (e.g. Kendrick Nunn and Michael
Porter Jr., whose rookie seasons were 2019-20). Also, the `PlayerIndex` "season" files are not
season rosters (each lists roughly the players whose last season it was); together they cover every
player once, so they are used as one player table, never per season.
**Decision (Massimo).** First NBA season = the player table's first season, moved to the first season
with a shot when the listed season is inside the window and the player took no shot in it. Before
2018-19 the shot data cannot correct it, so the listed season is kept (a known limitation for
veterans' season counts).
**Status.** Decided by Massimo, 2026-10-15.

### D-031 · 2026-10-15 · Playoff usage tier = regular-season tier (Massimo)
**Decision (Massimo).** A player's usage tier is computed from his regular season (official totals,
FGA per game, thirds among players with 100+ FGA) and carries into that season's playoffs.
**Reason.** Playoff samples are short and many players would fall below the 100-FGA minimum.
**Status.** Decided by Massimo, 2026-10-15.

### D-032 · 2026-10-15 · xFG model: logistic regression (Massimo)
**Finding.** On 20% of calibration-half games held out from fitting (172,568 shots): logistic
regression log loss 0.6378, AUC 0.654, max calibration error 2.2 points; gradient boosting 0.6360,
0.657, 1.7 points; no-model baseline log loss 0.6902. Plot: `reports/figures/stage4_xfg_calibration.png`.
**Decision (Massimo).** Logistic regression (distance and angle as splines; zone, shot type and
action type as categories; action types with fewer than 500 calibration shots pooled into
"Other"). The boosted model's 0.3% gain is not "clearly better" (playbook 4.6).
Fitted on all calibration-half analysis-population shots; never uses a shot result as a feature.
**Limitation.** No defender information, so xFG measures location-based difficulty only; predictions
mostly fall between 0.31 and 0.95.
**Status.** Decided by Massimo, 2026-10-15.

### D-033 · 2026-10-15 · Four playstyle clusters (Massimo)
**Finding.** k-means on the five zone shares of 1,640 player-seasons (calibration half, regular
season). Silhouette 0.26 (k=3), 0.25 (4), 0.22 (5), 0.22 (6), 0.22 (7). Stability (adjusted Rand
index vs the reference fit; 20 seeds, 100 bootstrap resamples): k=3 seeds min 0.97, bootstrap median
0.93; k=4 0.97 / 0.88; k=5 0.41 / 0.53; k=6 0.64 / 0.55; k=7 0.81 / 0.70. k >= 5 is not stable.
Full table: `reports/stage4_cluster_stability.csv`.
**Decision (Massimo).** k = 4, named from their average zone mix: rim bigs (204 player-seasons; 48%
restricted area), mid-range scorers (397; 22% mid-range), rim and corner (474; 32% rim, 12% corner
three), three-point shooters (565; 46% above-the-break three). Zone shares are not standardised.
**Status.** Decided by Massimo, 2026-10-15.

### D-034 · 2026-10-15 · Clustering minimum counted in the calibration half (Massimo)
**Decision (Massimo).** A player-season needs at least 200 calibration-half regular-season shots
(about 400 in a full season) to get a cluster; others are left out of H3 only.
**Reason.** Each zone mix then rests on at least 200 shots.
**Status.** Decided by Massimo, 2026-10-15.

### D-035 · 2026-10-15 · Playoff cluster = regular-season cluster (Massimo)
**Decision (Massimo).** A player's playoff shots carry his regular-season cluster of the same season,
matching the usage-tier rule (D-031).
**Status.** Decided by Massimo, 2026-10-15.

### D-036 · 2026-10-15 · Stage 5 outcomes are measured against the player's own baseline (Massimo)
**Decision (Massimo).** In every model (0 to 3), the distance outcome is next-shot distance minus the
player's leave-one-out baseline (D-027), and each zone outcome is the next-shot zone indicator minus
the player's baseline share of that zone (three-pointers: corner plus above-the-break share).
**Status.** Decided by Massimo, 2026-10-15, before any analysis-half estimate was computed.

### D-037 · 2026-10-15 · Model 2 context controls (Massimo)
**Decision (Massimo).** Score margin before the shot in 7 symmetric bins (<= -15, -14 to -6, -5 to -1,
0, 1 to 5, 6 to 14, >= 15); period as a category with all overtimes pooled; clock remaining in the
period, game-clock seconds since the previous shot, and the attempt number in the game (capped at
15) as linear terms; home or away; season and season type (absorbed by the fixed effects in
Model 3). Standard errors clustered by player in every model.
**Status.** Decided by Massimo, 2026-10-15.

### D-038 · 2026-10-15 · H0 pools the regular season and playoffs (Massimo)
**Decision (Massimo).** The core test uses all analysis-half pairs, with season type as a control.
H4 compares the two contexts separately.
**Status.** Decided by Massimo, 2026-10-15.

### D-039 · 2026-10-15 · Permutation test shuffles analysed shots only (Massimo)
**Decision (Massimo).** Within each player-game (check: player-game-period), only analysis-population
shots are shuffled between their time slots. Putbacks, tips, heaves and backcourt shots stay where
they happened, so the same slots form pairs in every shuffle. Statistic: mean outcome of the next
shot after a make minus after a miss; bias-corrected effect = observed minus the mean of 1,000
shuffles (seed from config); two-sided p-value from the shuffled distribution.
**Validation.** On synthetic independent shots the correction removes the pooled bias (corrected
effect 0.002, p = 0.90); on synthetic streaky shots it detects the effect (tests/test_core.py).
**Status.** Decided by Massimo, 2026-10-15.

### D-040 · 2026-10-15 · Stage 5 run protocol (playbook 5.3, 5.5, 5.7)
**Protocol.** Code was developed and debugged on the calibration half only; no estimate from it was
shown to Massimo before D-036 to D-039 were decided. The final analysis runs once on the analysis
half via `notebooks/04_core_test.ipynb`. The headline is Model 3's previous-shot-made coefficient
on distance vs baseline; the second method is a mixed model with a random intercept per player and
the Model 2 covariates. Any rerun of the final analysis gets a dated entry here with its reason.
**Run log.** Final analysis-half run: 2026-10-15, notebook committed unrun at e89be31, specifications at
abc1c9c. One run, no reruns.

### D-041 · 2026-10-15 · H1-H4 test the size of the H0 shift (Massimo)
**Decision (Massimo).** Each segment hypothesis compares the H0 shift (Model 3's after-make minus
after-miss gap in distance vs baseline) between groups, through an interaction of "previous shot
made" with the group in Model 3 (playbook 6.1). Each group's own Model 3 estimate is shown for display,
and the after-miss and after-make moves vs each player's baseline are shown as a description.
**Status.** Decided by Massimo, 2026-10-15.

### D-042 · 2026-10-15 · H1-H3 pool the regular season and playoffs (Massimo)
**Decision (Massimo).** As in H0 (D-038): all analysis-half pairs, season type absorbed by the
player-season fixed effects.
**Status.** Decided by Massimo, 2026-10-15.

### D-043 · 2026-10-15 · H2 test = high vs low usage tier (Massimo)
**Decision (Massimo).** The pre-registered H2 test is the difference in the H0 shift between the high
and low usage tiers. The mid tier and the All-Star subset are shown as labelled estimates.
**Status.** Decided by Massimo, 2026-10-15.

### D-044 · 2026-10-15 · H4 test = players in both contexts (Massimo)
**Decision (Massimo).** The pre-registered H4 test uses only player-seasons with analysis-half pairs in
both the regular season and the playoffs, so the same players are compared in two contexts. The
all-players version is reported next to it (playbook 6.2).
**Also fixed by the playbook (6.2-6.5).** H3: one joint test that the shift is equal across the four
clusters; pairwise differences only if it rejects. Holm correction across the four pre-registered
p-values (H1 interaction, H2 high-vs-low interaction, H3 joint test, H4 both-contexts interaction);
adjusted and unadjusted p-values side by side. Cells below 30 players or 2,000 pairs are "too few
shots to estimate". A joint model with the rookie, usage and cluster interactions together is a
labelled secondary analysis. Anything else is exploratory.
**Status.** Decided by Massimo, 2026-10-15.
**Run log (Stage 6).** Final analysis-half run: 2026-10-15, notebook committed unrun at a9c3abf. One run,
no reruns.
**Rerun 2026-10-15 (cosmetic).** Figure layout only (axis labels); `results_segments.csv` verified
byte-identical before and after.

### D-045 · 2026-10-15 · Survival rule (Massimo; replaces D-012)
**Decision (Massimo).** The headline (H0 distance shift, Model 3, analysis half: 1.50 ft) survives if
(a) its sign stays positive in every counted variation, and (b) each variation's 95% interval
contains the baseline estimate in at least 80% of the counted variations. A single sign flip makes
it fragile. Written before any Stage 7 variation was run.
**Status.** Decided by Massimo, 2026-10-15.

### D-046 · 2026-10-15 · What the survival rule judges and how variations are counted (Massimo)
**Decision (Massimo).** The rule judges the headline only. H2 (low minus high usage) and the H3
rim-bigs gap get the same variations in the sensitivity table, reported plainly without a verdict.
Every estimate counts once (each season, each gap value, ...), except "drop each of the 10 most
influential players", which counts as one variation judged on its worst case. The longer-streak
variations (last two shots, 3+ makes) and the cluster-count variations estimate a different quantity,
so they are reported in their own section and do not count.
**Status.** Decided by Massimo, 2026-10-15.

### D-047 · 2026-10-15 · Second-chance variation (Massimo)
**Decision (Massimo).** Add a variation that leaves out pairs where the next shot comes in the same
possession after the previous miss: after the miss, the shooter's team gets the offensive rebound,
and no opponent field-goal attempt, defensive rebound or turnover happens before the next shot
(built from the play-by-play). Tests the possession-mechanics explanation in the H0 result.
**Status.** Decided by Massimo, 2026-10-15.

### D-048 · 2026-10-15 · Stage 7 estimator and placebo (Massimo)
**Decision (Massimo).** Each variation re-runs Model 3 (D-036, D-037). The future-result placebo
replaces "previous shot made" with "the shot after the next one was made" and controls for that
later shot's distance, zone and xFG, mirroring how Model 3 controls for the previous shot.
**Status.** Decided by Massimo, 2026-10-15.
**Run log (Stage 7).** First analysis-half run, 2026-10-15, crashed while drawing the specification
curve (a matplotlib colour argument); nbconvert does not save a failed notebook, so no Stage 7 result
was seen. Plot code fixed (no analysis change) and the notebook run again.

### D-049 · 2026-10-16 · Dashboard: make probability for all players only (Massimo)
**Decision (Massimo).** The dashboard shows the make-probability (hot-hand) result only for all
players, from the bias-corrected permutation test (Stage 5). No per-group make-probability shifts.
**Status.** Decided by Massimo, 2026-10-16.

### D-050 · 2026-10-16 · Dashboard: player lookup with 100+ pairs each side (Massimo)
**Decision (Massimo).** The player lookup shows only player-seasons with at least 100 analysis-half
pairs after a make and 100 after a miss, next to the player's group, with intervals and a noise
warning. No ranking or sorting by size.
**Status.** Decided by Massimo, 2026-10-16.

### D-051 · 2026-10-16 · Dashboard: shot map as a difference map (Massimo)
**Decision (Massimo).** One half-court map per group: share of next shots in each court bin after a
make minus after a miss (analysis half, pre-computed bins).
**Status.** Decided by Massimo, 2026-10-16.

### D-052 · 2026-10-16 · Dashboard hosting: Streamlit Community Cloud (Massimo)
**Decision (Massimo).** Deploy from the GitHub repo to Streamlit Community Cloud when the repo goes
public (Stage 9); built and tested locally until then.
**Status.** Decided by Massimo, 2026-10-16.

### D-053 · 2026-10-16 · Headline make-probability card shows both shuffles (Massimo)
**Decision (Massimo).** The dashboard's make-probability card shows both bias-corrected permutation
results with their p-values: -0.4 pp (shuffle within game, p = 0.002) and +0.1 pp (shuffle within
quarter, p = 0.464), so the card matches the "no hot hand" finding instead of showing one number
that could read as a negative streak effect.
**Status.** Decided by Massimo, 2026-10-16.

### D-054 · 2026-10-16 · Shot map can switch between feet and metres (Massimo)
**Decision (Massimo).** The shot map has a ft / m switch: court positions, court lines and hover
labels convert (1 ft = 0.3048 m); the colours are percentage points and do not change. Feet stay the
default, consistent with D-005.
**Status.** Decided by Massimo, 2026-10-16.

### D-055 · 2026-10-16 · Player lookup gets a zone map (Massimo)
**Decision (Massimo).** The player lookup shows a court map of the five shot zones for the chosen
player-season, each coloured by the share of next shots in that zone after a make minus after a
miss (percentage points), with the shot counts on each side. Zones rather than squares, because a
player-season has only ~200-300 shots on each side (median ~30 per zone and side).
**Status.** Decided by Massimo, 2026-10-16.

### D-056 · 2026-10-16 · Player comparison chart stays under the map (Massimo)
**Decision (Massimo).** The chart comparing the player's overall shift with his usage tier, playstyle
and all players stays, below the zone map, with clearer labels.
**Status.** Decided by Massimo, 2026-10-16.

### D-057 · 2026-10-16 · Player map uses squares like the group map (Massimo; replaces D-055)
**Decision (Massimo).** The player map uses the same square design as the group map, with bigger
squares: 6 x 6 ft, centred on the basket, showing only squares with at least 5 shots on each side.
**Finding behind the size.** On 120 sampled player-seasons, 4 ft squares with 10+ shots showed a
median of 2 squares (22% of the player's shots); 6 ft with 5+ showed 8 squares (58%), the most of
the options compared (4 ft/5+: 5, 38%; 5 ft/5+: 6, 49%; 6 ft/10+: 3, 34%; 8 ft/10+: 4, 50%).
Squares can rest on 5 shots per side, so the counts are on hover and the noise warning stays.
**Status.** Decided by Massimo, 2026-10-16.

### D-058 · 2026-10-16 · Season menus on both maps (Massimo)
**Decision (Massimo).** The group map has a season menu ("All seasons" or one of the 8 seasons; per
season, squares still need 50+ shots on each side). The player lookup has separate menus for the
player and the season (only seasons where he has 100+ pairs on each side).
**Status.** Decided by Massimo, 2026-10-16.
**Rerun 2026-10-16 (cosmetic, Stage 7).** Specification-curve labels were clipped; figure export fixed
(`bbox_inches="tight"`), notebook rerun, `results_robustness.csv` verified byte-identical.
