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
| H0 | All players, after make vs after miss | Within-player shift in distance and zone | After a make, the next shot is similar in distance and zone to the previous one. After a miss, players move toward the basket, because a miss pushes them to look for an easier shot. | Partly correct; see [H0 result](#h0-result) |
| H1 | Rookies vs veterans | Size of the H0 shift in each group | After a miss, rookies shift their shots more than veterans do, because veterans follow a stable routine and rookies react strongly to the last result. | I was wrong; see [H1 result](#h1-result) |
| H2 | High-usage vs low-usage players (All-Stars shown as a labelled subset) | Size of the H0 shift in each tier | After a miss, low-usage players move toward easier shots (closer to the basket), while high-usage players show little or no shift. A low-usage role is replaceable, so a bad shot costs them minutes, and a high-usage player's role is secure. | I was wrong (opposite direction); see [H2 result](#h2-result) |
| H3 | Playstyle clusters from baseline shot-zone mix | Size and direction of the H0 shift per cluster | After a miss, the three-point shooter cluster shows no shift in zone mix, while the other clusters move toward the basket for an easier shot. | Partially correct; see [H3 result](#h3-result) |
| H4 | Regular season vs playoffs | Size of the H0 shift in each context | The post-miss shift in H0 is smaller in the playoffs than in the regular season, because tighter coaching, game plans and higher stakes keep players closer to their roles. | Cannot be told apart from no difference; see [H4 result](#h4-result) |

**Descriptive check (H4 note, not a test):** the high-usage tier's share of all shot attempts is higher in
the playoffs than in the regular season, which would fit the idea that stars take over.

**Rule for every row.** The prediction states a direction and a reason. A prediction with no direction
cannot be wrong, so it cannot be a finding.

## Results

### H0 result

Numbers from `data/processed/results_core.csv` (analysis half,
535,659 pairs, 1,199 players; `notebooks/04_core_test.ipynb`).

After a missed shot, most players will move closer to the basket on their next attempt to try and find an easier shot, and after a made shot, they move farther out, probably moved by confidence. These reasons are my reading as a long-time player and fan of the game; the data shows the change in shot choice, not the motive behind it. Compared with each player's own usual shot, the next shot after a miss comes around 0.9 ft (27 cm) closer, with 3.2 points more at the rim, while the next attempt after a make comes around 0.6 ft (18 cm) farther out, with 2.4 points more on threes. Put together, the next shot after a make is 1.5 ft (46 cm) farther than after a miss (95% interval 1.4 to 1.6 ft), and its shot mix holds 5.4 points more threes and 5.2 points fewer rim attempts. When I adjust for the location of the previous shot and the game scenario, a mixed-effects model yields the same 1.5 feet. It also withstands a shuffle test that eliminates the bias of comparing shots within brief sequences, though it decreases to roughly 1.0 feet when shots are only shuffled within the same quarter. I was partially correct: I predicted that players would search for closer shots following a miss, which they do, but I also predicted that after a make they would keep shooting from the same location, while they move farther out instead. The data reveals no hot hand: a player is not more likely to make his subsequent shot after a make if the difficulty of the shot and the sequence bias are taken into consideration. The result describes how shot choices change, not whether they are good choices, and it does not prove that a miss causes the change: part of it may come from second-chance shots in the same possession, which tend to be closer to the rim (tested in Stage 7), and the data has no information on defenders.

### H1 result

Numbers from `data/processed/results_segments.csv` (analysis half; `notebooks/05_segments.ipynb`).

I predicted that rookies would adjust their shot choice more than veterans, because they have less experience and I expected them to react more to the last shot. The data shows no difference. Rookies’ next shot is 1.56 ft (48 cm) farther after a make than after a miss, and veterans’ is 1.55 ft (47 cm). The gap between them is +0.07 ft (2 cm), with a 95% interval of -0.28 to +0.41 ft and a Holm-adjusted p of 0.95, so the interval is compatible with no difference at all. After a miss, rookies move 0.99 ft (30 cm) closer and veterans 0.90 ft (28 cm) closer. I was wrong on this one: I found no evidence that experience changes how much players adjust.

### H2 result

Numbers from `data/processed/results_segments.csv` (analysis half; `notebooks/05_segments.ipynb`).

I predicted that low-usage players would shift and high-usage players would shift little or not at all, and the data shows a clear difference in the opposite direction. High-usage players shift the most, 1.66 ft (50 cm), and low-usage players the least, 1.15 ft (35 cm). The difference between low and high usage is -0.47 ft (14 cm), with a 95% interval of -0.73 to -0.21 ft and a Holm-adjusted p of 0.001. After a miss, both groups move closer by about the same amount (0.84 ft for low usage, 0.92 ft for high). The difference sits after a make: high-usage players step out 0.71 ft (22 cm), low-usage players 0.31 ft (10 cm). All-Stars, shown only as a labelled group, shift 1.80 ft (55 cm), with an interval of 1.43 to 2.17 ft. I was wrong on this one. My explanation, to be tested later and not a conclusion, is that high-usage players are the first option of their offense, so after a make they are the ones given the freedom to take a harder, farther shot.

### H3 result

Numbers from `data/processed/results_segments.csv` (analysis half; `notebooks/05_segments.ipynb`).

I was partially correct. The shifts differ across the four playstyles (joint test, Holm-adjusted p = 0.0001), and the first half of my prediction failed: three-point shooters shift the most, 1.83 ft (56 cm), against 1.60 ft (49 cm) for rim-and-corner players, 1.43 ft (43 cm) for mid-range scorers and 0.81 ft (25 cm) for rim bigs. Their share of above-the-break threes swings the most, -4.4 points after a miss and +4.2 after a make. The second half held in part: all four groups take more rim attempts after a miss (+2.1 to +3.8 points). Compared with three-point shooters, rim bigs shift 1.03 ft (31 cm) less and mid-range scorers 0.42 ft (13 cm) less, while the rim-and-corner gap (-0.25 ft, p = 0.11) is uncertain. My explanation, to be tested later and not a conclusion, is that three-point shooters have the widest range to move across, from the rim to the arc, so their shot choice has the most room to change after each result.

### H4 result

Numbers from `data/processed/results_segments.csv` (analysis half; `notebooks/05_segments.ipynb`).

I predicted that the shift would be smaller in the playoffs, and the point estimate points that way, but it cannot be told apart from no difference. For the same 576 players, the shift is 1.33 ft (41 cm) in the playoffs against 1.49 ft (45 cm) in the regular season. The difference is -0.08 ft (2 cm), with a 95% interval of -0.29 to +0.13 ft and a Holm-adjusted p of 0.95; it is smaller than the simple subtraction (1.33 - 1.49 = -0.16 ft) because the test holds the game-context controls equal across the two contexts. The version with all players gives the same picture (-0.11 ft, p = 0.31). I can’t say the playoffs change the shift, only that the data does not rule out a small one.
