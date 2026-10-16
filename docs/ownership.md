# Ownership: who did what, per stage

Project: nba-shot-selection-hot-hand

This file records what I decided, wrote and verified in this project, and what I delegated to
Claude Code. Every definition, threshold, interpretation and gate is mine; the code for Stages 4 to 8
was written by Claude Code from my decisions, and every commit shows that co-authorship.

## Ownership table

| Stage | I write or decide | Claude Code helps with | I verify |
|---|---|---|---|
| 1 Setup | Folder choices, config values, the predictions in `docs/hypotheses.md` (directional, with a reason) | Repo skeleton, pinned environment, `.gitignore`, Makefile and run_all script | A fresh clone installs and runs; the predictions are committed before any data is collected |
| 2 Data acquisition | Season window, data route, exclusions, the All-Star source | Download loops with caching, timeouts and retries; manifest and file hashing | Row counts per season are in the expected range; a sample of shots matches across both routes; the NBA.com Terms of Use |
| 3 Audit and cleaning | Which checks matter, pass thresholds, every keep/drop/fix decision and its reason | Running each check per season and season type; attrition table code | Flagged rows in the raw data; re-running from raw reproduces the cleaned files exactly; every failed check has a `decisions.md` entry |
| 4 Definitions and features | Every definition and threshold: shot pairs, streak states, leave-one-out baseline, calibration/analysis split, segments, xFG model, number of clusters | All Stage 4 code (pairs, streak states, baseline, split, xFG, clusters, segment labels), unit tests, plots and stability checks | Hand-made test sequences pass; 5 real player-games hand-checked against the raw data; the xFG model excludes every shot result; definitions tagged `definitions-v1` |
| 5 Core test (H0) | Model specifications before the final run; the interpretation in plain units | Models 0 to 3, the permutation test, the mixed-effects second method | The two methods agree in sign and size; one number reproduced by hand; the result stated in feet and percentage points with intervals |
| 6 Segments (H1 to H4) | The comparison rules before the run; the comparison with my predictions; the Result column | Interaction models, Holm correction, forest plot, cluster heat map | Minimum-sample cells enforced; any extra comparison labelled exploratory; the Result column filled in, including misses |
| 7 Robustness | The survival rule before anything runs; what counts as fragile; the README robustness paragraph | Variation loop, second-chance flag, specification curve, placebo tests | The placebo results make sense; fragility is reported plainly, not hidden |
| 8 Dashboard | What question each chart answers; every dashboard rule; all wording, including limitations | Streamlit code, pre-aggregated data, the displayed-vs-CSV check | The displayed-vs-CSV check passes; two outside people state the finding unaided; no leaderboard of individuals |
| 9 Repo and README | The README text, especially the limitations; going public; deploying the dashboard | Reproduce and repo-structure sections, Makefile, linting, cold-clone test | A cold clone reproduces the results; every README number matches a committed table |
| 10 LinkedIn post or blog | The post | Proofreading and checking numbers against the README | Every claim matches a committed table; links work when logged out |

## Always mine (never delegated)

- Hypotheses and predictions
- Definitions (consecutive shot, streak state, baseline, segments)
- Interpretation of results and the limitations
- The LinkedIn post or blog text
- Declaring a gate passed

## Verification log

| Stage | Date verified | What I checked | What I changed or fixed | Open questions |
|---|---|---|---|---|
| 1 | 2026-10-15 | Checked config.yaml values and the Stage 1 decisions (D-005 to D-012, D-023) in chat; confirmed that the predictions commit (0e843c9, 23:51) precedes the first download (about 23:54). The fresh-clone install was run by Claude Code on 2026-10-14 (setup, 3 tests and the empty pipeline passed) | D-008 veteran threshold changed to 10th season; seasons 2-9 left out of H1. D-022 garbage time redefined (4th quarter, 20+ margin, 5 minutes or less) | None |
| 2 | 2026-10-15 | Checked reports/stage2_acquisition.md and the Stage 2 decisions (D-002 to D-004, D-013 to D-016); hand-compared 10 random 2024-25 shots from both routes side by side (all fields identical); asked for and accepted the check that the 2025 and 2026 multi-team All-Star formats are fully covered | All-Star name cleaner fixed (Booker, Conley in 2020-21) | Read the NBA.com Terms of Use at the end of the project, before the repo goes public |
| 3 | 2026-10-15 | Checked reports/stage3_data_quality.md and D-017 to D-021; spot-checked in the raw data the 8 dropped shots, the event-329 ordering example and five 2025-26 Heave rows; re-run from raw reproduces the committed content hashes (run by Claude after fixing the notebook environment bug) | Decided D-024: pairs whose next shot is a putback or tip are left out | None (putback as previous shot settled in D-024) |
| 4 | 2026-10-15 | Decided every Stage 4 definition (D-024 to D-035); checked the pair attrition, split balance, xFG model comparison and calibration plot, cluster stability and profiles, and segment cell sizes; hand-checked 5 real player-games against the raw play-by-play (J. Freeman-Liberty, M. Potter, T. Eason, C. Payne, J. Grant), including putbacks, a heave, gaps over 240 s and pairs across quarter breaks; confirmed the xFG model excludes every shot result (enforced in code and tests); tagged definitions-v1 | Putbacks and tips count in the streak (D-029); rookie season = first season played (D-030); split drawn within each season and season type (D-025) | Playoff rookies (865 analysis pairs) fall below the 2,000-pair minimum for H1 |
| 5 | 2026-10-15 | Decided the Stage 5 specifications before any analysis-half estimate (D-036 to D-040); checked the single analysis-half run: Model 3 (1.50 ft) and the mixed-effects model (1.49 ft) agree in sign and size; reproduced Model 0 by hand (0.58 - (-0.88) = 1.46 ft); stated the result in feet and percentage points with intervals in the H0 result | Wrote the H0 result in docs/hypotheses.md | Second-chance shots in the same possession as a possible mechanical source of the shift (Stage 7); report make probability from the permutation test, not the fixed-effects regression |
| 6 | 2026-10-15 | Decided the Stage 6 comparison rules before the run (D-041 to D-044); checked that the minimum-cell rule was applied to every group (all cells met it in the pooled analysis); checked that the joint rookie/usage/cluster model is labelled secondary and not a finding; compared every result with my written predictions and filled the Result column for H1-H4, including the misses (H1, H2, the first half of H3) | Wrote the H1-H4 results in docs/hypotheses.md | Whether usage or playstyle drives the larger shift (they overlap); my explanations for H2 and H3 are to be tested |
| 7 | 2026-10-15 | Wrote the survival rule and the counting rules before any variation ran (D-045 to D-048); checked the automated result (positive in 24 of 24 counted variations, interval contains 1.50 ft in 20 of 24); checked that the placebo makes sense (+0.07 ft, small but not zero) and that the second-chance check removes almost none of the shift; reported the fragility plainly in the README | Wrote the README robustness paragraph; verdict: robust in direction, size depends on the consecutive-shot definition | Small leftover confounding suggested by the placebo; H2 does not hold in 2025-26 alone; specification-curve labels to fix in Stage 9 |
| 8 | 2026-10-16 | Decided what each view answers and every dashboard rule (D-049 to D-058); wrote or approved every word in dashboard/text.yaml; checked the displayed-vs-CSV script (109 numbers match); two outside viewers stated the finding unaided; confirmed there is no leaderboard (player list is alphabetical) | Asked for descriptive hovers, a ft/m switch, season menus and a square map per player; limitations as one bullet list | Public URL comes with the public repo in Stage 9 |
| 9 | 2026-10-16 | Wrote the README text (finding, question, key results, data, method, limitations, author); read the NBA.com Terms of Use and added the non-commercial statement and NBA.com citation; checked that a cold clone reproduces every results table byte for byte (D-059); deployed the dashboard on Streamlit Community Cloud and checked it works logged out | Made the repo public with description and topics; tagged results-v1 | NBA.com's live player index can drift slightly over time (no effect on results) |
| 10 | | | | |
