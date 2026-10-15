"""The permutation machinery on synthetic shots with known answers."""

import numpy as np
import pandas as pd

from hothand.core import permutation_test


def synthetic(n_games=400, shots_per_game=8, p=0.5, streak=0.0, seed=1):
    """Independent shots (streak=0) or shots whose make probability rises after a make."""
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(n_games):
        prev = None
        for i in range(shots_per_game):
            q = p + (streak if prev == 1 else -streak if prev == 0 else 0)
            made = int(rng.random() < q)
            rows.append({"game_id": f"G{g}", "player_id": 1, "pbp_row": i, "shot_made": made,
                         "xfg": p, "zone": "mid_range", "baseline_corner_three": 0.0,
                         "baseline_above_break_three": 0.0, "distance_vs_baseline_ft": 0.0,
                         "in_analysis_population": True, "period": 1})
            prev = made
    shots = pd.DataFrame(rows)
    pairs = shots[shots.pbp_row > 0][["game_id", "player_id", "pbp_row"]].copy()
    pairs["prev_pbp_row"] = pairs.pbp_row - 1
    return shots, pairs


def test_independent_shots_bias_is_removed_by_the_shuffle():
    shots, pairs = synthetic()
    res, _ = permutation_test(shots, pairs, n_perm=200, seed=7, within=["game_id", "player_id"])
    r = res.set_index("outcome").loc["next_surprise"]
    # With independent shots the naive after-make minus after-miss difference is not zero: within a
    # game it is pulled down (Miller-Sanjurjo), and pooling games pulls it up (games with more makes
    # contribute more after-make pairs). The shuffled null reproduces both, so the bias-corrected
    # effect is close to zero and not significant.
    assert abs(r.null_mean) > 0.01
    assert abs(r.bias_corrected) < 0.03 and r.p_two_sided > 0.05


def test_a_real_streak_effect_is_detected():
    shots, pairs = synthetic(streak=0.15)
    res, _ = permutation_test(shots, pairs, n_perm=200, seed=7, within=["game_id", "player_id"])
    r = res.set_index("outcome").loc["next_surprise"]
    assert r.bias_corrected > 0.2 and r.p_two_sided < 0.01
