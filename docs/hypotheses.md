# Pre-registered hypotheses

Committed before any data was collected (see the git log for this file's commit date).
The Prediction column is final. The Result column is filled in Stage 6, including predictions that miss.

**Core question.** After a made or missed shot, how does an NBA player's next shot change in distance,
zone and difficulty compared with that same player's own baseline?

**Outcome measures (fixed now):**

1. Primary 1: distance of the next shot attempt relative to the player's baseline average
   (stored in feet as published by NBA.com; reported in feet with a metre conversion, see D-005).
2. Primary 2: shot-zone mix of the next attempt (restricted area, paint, mid-range, corner three,
   above-the-break three).
3. Secondary: probability the next shot goes in, after adjusting for shot difficulty (xFG).
   This is the classic hot-hand test.

**Pre-registered test family:** H1-H4 on next-shot distance, Holm-corrected. Zone and xFG outcomes are
described, not used for additional significance claims. Anything not in this table is exploratory.

| ID | Comparison | What is compared | Prediction (written before data) | Result (fill after) |
|----|-----------|------------------|----------------------------------|---------------------|
| H0 | All players, after make vs after miss | Within-player shift in distance and zone | After a make, the next shot is similar in distance and zone to the previous one. After a miss, players move toward the basket, because a miss pushes them to look for an easier shot. | |
| H1 | Rookies vs veterans | Size of the H0 shift in each group | After a miss, rookies shift their shots more than veterans do, because veterans follow a stable routine and rookies react strongly to the last result. | |
| H2 | High-usage vs low-usage players (All-Stars shown as a labelled subset) | Size of the H0 shift in each tier | After a miss, low-usage players move toward easier shots (closer to the basket), while high-usage players show little or no shift. A low-usage role is replaceable, so a bad shot costs them minutes, and a high-usage player's role is secure. | |
| H3 | Playstyle clusters from baseline shot-zone mix | Size and direction of the H0 shift per cluster | After a miss, the three-point shooter cluster shows no shift in zone mix, while the other clusters move toward the basket for an easier shot. | |
| H4 | Regular season vs playoffs | Size of the H0 shift in each context | The post-miss shift in H0 is smaller in the playoffs than in the regular season, because tighter coaching, game plans and higher stakes keep players closer to their roles. | |

**Descriptive check (H4 note, not a test):** the high-usage tier's share of all shot attempts is higher in
the playoffs than in the regular season, which would fit the idea that stars take over.

**Rule for every row.** The prediction states a direction and a reason. A prediction with no direction
cannot be wrong, so it cannot be a finding.
