# Ownership Split: who does what, per stage

Project: nba-shot-selection-hot-hand
Purpose: this file is the working agreement between Massimo and Claude Code. It also goes in `docs/ownership.md` so the repo shows what was decided, delegated and verified.

## Instructions for Claude Code

Read this file at the start of every session, together with `docs/decisions.md`, `docs/hypotheses.md` and `config.yaml`.

1. For every item in a "Massimo writes or decides" cell, do not write the solution. Give hints, point to documentation, review what Massimo wrote, and explain trade-offs when asked.
2. For every item in a "Claude Code helps with" cell, you may write the code, but explain what it does in plain language and keep diffs small enough to review.
3. Never change a definition, threshold or hypothesis on your own. If you think one should change, say so and let Massimo decide and log it in `docs/decisions.md`.
4. After finishing work on a stage, list what Massimo should verify from the "Massimo verifies" cell. Do not declare a gate passed yourself. Massimo declares it.
5. Never use the previous shot's result as a feature in the xFG model. Never run the final analysis on the calibration half or tune on the analysis half.
6. Flag anything that looks like a mechanical artifact, an off-by-one error in streak logic, or a result that seems too good.
7. Keep co-authorship visible in commits. Do not rewrite history to hide it.

## Ownership table

| Stage | Massimo writes or decides | Claude Code helps with | Massimo verifies |
|---|---|---|---|
| 1 Setup | Folder choices, config values, predictions in `docs/hypotheses.md` (directional, with a reason) | Repo skeleton, pinned environment, `.gitignore`, Makefile or run_all script | A fresh clone installs and runs; predictions are committed before any data is collected |
| 2 Data acquisition | Season window, data route, exclusions, the All-Star source | Download loops with caching, timeouts and retries; manifest and file hashing | Row counts per season are in the expected range; hand-compare a sample of shots across both routes; read the NBA.com Terms of Use |
| 3 Audit and cleaning | Which checks matter, pass thresholds, every keep/drop/fix decision and its reason | Running each check per season and season type; attrition table code | Spot-check flagged rows in the raw data; re-running from raw reproduces the cleaned files exactly; every failed check has a `decisions.md` entry in his own words |
| 4 Definitions and features | **Hand-writes:** shot-pair logic, streak states, leave-one-out baseline, game-level calibration/analysis split, segment thresholds | Unit-test scaffolding, xFG model boilerplate, clustering plots and stability checks | His own hand-made test sequences pass; hand-check 5 real player-games against raw data; xFG model excludes the previous shot's result; definitions tagged `definitions-v1` |
| 5 Core test (H0) | **Hand-writes:** Models 0 to 3 and a first version of the permutation test; the interpretation in plain units | Clustered standard errors, speeding up permutations, the mixed-effects second method | Two methods agree in sign and rough size; reproduces one number by hand; result stated in feet and percentage points with intervals |
| 6 Segments (H1 to H4) | Applies only the pre-registered rows; compares results with his written predictions | Interaction models, Holm correction, forest plot, cluster heat map | Minimum-sample cells enforced; any extra comparison labelled exploratory; Result column of `hypotheses.md` filled in, including misses |
| 7 Robustness | **Writes the survival rule before running anything**; decides what counts as fragile | Loop over variations, specification curve, placebo tests | Placebo results make sense; fragility is reported plainly, not hidden |
| 8 Dashboard | What question each chart answers; all wording, including limitations | Streamlit code, pre-aggregated data loading | Displayed-vs-CSV check passes; two outside people can state the finding unaided; no leaderboard of individuals |
| 9 Repo and README | The README text, especially the limitations section | Makefile, linting, cold-clone troubleshooting | A cold clone reproduces the headline numbers from the README alone; every README number matches a committed table |
| 10 LinkedIn post or blog | Writes it himself | Proofreading and checking numbers against the README | Every claim matches a committed table; links work when logged out |

## Changes to this agreement

- 2026-10-15, Massimo: Stage 4 code is delegated to Claude Code, including the shot-pair logic,
  streak states, leave-one-out baseline and game split. Claude must present every decision and
  interpretation to Massimo before it is used, and Massimo still decides every definition and
  threshold (rule 3) and declares the gate.
- 2026-10-15, Massimo: Stage 5 code is delegated to Claude Code as well: Models 0 to 3, the
  permutation test and the mixed-effects second method. Claude must present every modelling
  decision before the final run and every result to Massimo, who writes the interpretation in
  plain units, reproduces one number himself and declares the gate.
- 2026-10-15, Massimo: the H0 interpretation in `docs/hypotheses.md` was written by Massimo.
- 2026-10-15, Massimo: Stage 6 code is delegated to Claude Code (interaction models, Holm correction,
  forest plot, cluster heat map). Massimo decides every comparison rule before the run, compares the
  results with his predictions, fills the Result column and declares the gate.

## Always Massimo's (never delegated)

- Hypotheses and predictions
- Definitions (consecutive shot, streak state, baseline, segments)
- Interpretation of results and the limitations
- The LinkedIn post or blog text
- Declaring a gate passed

## Verification log

Fill this in as you go. One row per stage once you have personally checked the "Massimo verifies" items.

| Stage | Date verified | What I checked | What I changed or fixed | Open questions |
|---|---|---|---|---|
| 1 | 2026-10-15 | Checked config.yaml values and the Stage 1 decisions (D-005 to D-012, D-023) in chat; confirmed that the predictions commit (0e843c9, 23:51) precedes the first download (about 23:54). The fresh-clone install was run by Claude on 2026-10-14 (setup, 3 tests and the empty pipeline passed), not by Massimo | D-008 veteran threshold changed to 10th season; seasons 2-9 left out of H1. D-022 garbage time redefined (4th quarter, 20+ margin, 5 minutes or less) | None |
| 2 | 2026-10-15 | Checked reports/stage2_acquisition.md and the Stage 2 decisions (D-002 to D-004, D-013 to D-016); hand-compared 10 random 2024-25 shots from both routes side by side (all fields identical); asked for and accepted the check that the 2025 and 2026 multi-team All-Star formats are fully covered | All-Star name cleaner fixed (Booker, Conley in 2020-21) | Read the NBA.com Terms of Use at the end of the project, before the repo goes public |
| 3 | 2026-10-15 | Checked reports/stage3_data_quality.md and D-017 to D-021; spot-checked in the raw data the 8 dropped shots, the event-329 ordering example and five 2025-26 Heave rows; re-run from raw reproduces the committed content hashes (run by Claude after fixing the notebook environment bug) | Decided D-024: pairs whose next shot is a putback or tip are left out | None (putback as previous shot settled in D-024) |
| 4 | 2026-10-15 | Decided every Stage 4 definition (D-024 to D-035); checked the pair attrition, split balance, xFG model comparison and calibration plot, cluster stability and profiles, and segment cell sizes; hand-checked 5 real player-games against the raw play-by-play (J. Freeman-Liberty, M. Potter, T. Eason, C. Payne, J. Grant), including putbacks, a heave, gaps over 240 s and pairs across quarter breaks; confirmed the xFG model excludes every shot result (enforced in code and tests); tagged definitions-v1 | Putbacks and tips count in the streak (D-029); rookie season = first season played (D-030); split drawn within each season and season type (D-025) | Playoff rookies (865 analysis pairs) fall below the 2,000-pair minimum for H1 |
| 5 | 2026-10-15 | Decided the Stage 5 specifications before any analysis-half estimate (D-036 to D-040); checked the single analysis-half run: Model 3 (1.50 ft) and the mixed-effects model (1.49 ft) agree in sign and size; reproduced Model 0 by hand (0.58 - (-0.88) = 1.46 ft); stated the result in feet and percentage points with intervals in the H0 result | Wrote the H0 result in docs/hypotheses.md | Second-chance shots in the same possession as a possible mechanical source of the shift (Stage 7); report make probability from the permutation test, not the fixed-effects regression |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |
| 10 | | | | |
