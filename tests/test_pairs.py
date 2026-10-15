"""Hand-made shot sequences with known answers for the pair and streak logic (playbook 4.10)."""

import pandas as pd
import pytest

from hothand.config import load_config
from hothand.pairs import assign_game_split, build_pairs, flag_shots, loo_baseline


@pytest.fixture
def cfg():
    c = load_config()
    c["pairs"]["max_gap_game_seconds"] = 240
    c["pairs"]["same_period_only"] = False
    c["pairs"]["heave_breaks_pair"] = True
    return c


def seq(rows):
    """rows: (game, player, elapsed_s, made, action_type, period, distance_ft, clock_remaining_s)."""
    df = pd.DataFrame(rows, columns=["game_id", "player_id", "game_elapsed_s", "shot_made",
                                     "action_type", "period", "coord_distance_ft",
                                     "clock_remaining_s"])
    df["pbp_row"] = range(len(df))
    df["shot_distance_ft"] = df.coord_distance_ft.astype(int)
    df["shot_zone_basic"] = "Mid-Range"
    df["shot_value"] = 2
    return df


def shot(game, player, t, made, action="Jump Shot", period=1, dist=15.0, clock=300.0):
    return (game, player, t, made, action, period, dist, clock)


def pairs_of(rows, cfg):
    return build_pairs(flag_shots(seq(rows), cfg), cfg)


def test_make_miss_make_make(cfg):
    p = pairs_of([shot("G1", 1, 10, 1), shot("G1", 1, 40, 0), shot("G1", 1, 70, 1),
                  shot("G1", 1, 100, 1)], cfg)
    assert p.shot_number.tolist() == [2, 3, 4]          # first shot has no pair
    assert p.prev_made.tolist() == [1, 0, 1]
    assert p.last_two.tolist() == ["", "made-miss", "miss-made"]
    assert p.prev_make_run.tolist() == [1, 0, 1]


def test_three_makes_in_a_row(cfg):
    p = pairs_of([shot("G1", 1, t, 1) for t in (10, 40, 70)] + [shot("G1", 1, 100, 0)], cfg)
    assert p.prev_make_run.tolist() == [1, 2, 3]
    assert p.three_plus_makes.tolist() == [False, False, True]
    assert p.last_two.tolist() == ["", "made-made", "made-made"]


def test_gap_above_threshold_breaks_pair_and_streak(cfg):
    p = pairs_of([shot("G1", 1, 10, 1), shot("G1", 1, 40, 1), shot("G1", 1, 300, 0),
                  shot("G1", 1, 330, 1)], cfg)
    # 40 -> 300 is a 260 s gap: no pair, and the streak restarts after it
    assert p.game_elapsed_s.tolist() == [40, 330]
    assert p.prev_make_run.tolist() == [1, 0]
    # the shot before the gap is not in the same chain, so there is no "last two" state
    assert p.last_two.tolist() == ["", ""]


def test_gap_exactly_at_threshold_is_a_pair(cfg):
    p = pairs_of([shot("G1", 1, 0, 1), shot("G1", 1, 240, 0)], cfg)
    assert len(p) == 1


def test_new_game_resets_sequence(cfg):
    p = pairs_of([shot("G1", 1, 10, 1), shot("G1", 1, 40, 1), shot("G2", 1, 5, 0),
                  shot("G2", 1, 30, 1)], cfg)
    assert p.game_id.tolist() == ["G1", "G2"]
    assert p.prev_make_run.tolist() == [1, 0]


def test_interleaved_players_never_mix(cfg):
    p = pairs_of([shot("G1", 1, 10, 1), shot("G1", 2, 20, 0), shot("G1", 1, 30, 0),
                  shot("G1", 2, 40, 1)], cfg)
    by_player = p.set_index("player_id")
    assert by_player.loc[1, "prev_made"] == 1 and by_player.loc[2, "prev_made"] == 0


def test_putback_left_out_as_next_and_as_previous(cfg):
    # miss, putback, jump shot: no pair at all (D-024), then jump, jump forms a pair
    p = pairs_of([shot("G1", 1, 10, 0), shot("G1", 1, 12, 1, "Putback Layup Shot", dist=1),
                  shot("G1", 1, 60, 1), shot("G1", 1, 90, 0)], cfg)
    assert p.game_elapsed_s.tolist() == [90]
    assert p.prev_make_run.tolist() == [1]  # the streak chain restarted after the putback


def test_heave_breaks_pair_when_configured(cfg):
    rows = [shot("G1", 1, 700, 0, clock=20.0), shot("G1", 1, 719, 0, dist=60.0, clock=1.0),
            shot("G1", 1, 760, 1, period=2, clock=680.0)]
    assert len(pairs_of(rows, cfg)) == 0
    cfg["pairs"]["heave_breaks_pair"] = False
    p = pairs_of(rows, cfg)
    assert p.game_elapsed_s.tolist() == [760] and p.prev_made.tolist() == [0]


def test_heave_only_in_periods_1_to_3(cfg):
    rows = [shot("G1", 1, 2860, 0, period=4, clock=20.0),
            shot("G1", 1, 2879, 0, period=4, dist=60.0, clock=1.0)]
    assert len(pairs_of(rows, cfg)) == 1  # a 4th-quarter heave is a normal shot


def test_same_period_only(cfg):
    rows = [shot("G1", 1, 700, 1, clock=20.0), shot("G1", 1, 740, 0, period=2, clock=700.0)]
    assert len(pairs_of(rows, cfg)) == 1
    cfg["pairs"]["same_period_only"] = True
    assert len(pairs_of(rows, cfg)) == 0


def test_game_split_is_by_game_seeded_and_balanced(cfg):
    games = pd.Series([f"G{i}" for i in range(100)] * 3)
    a, b = assign_game_split(games, cfg), assign_game_split(games, cfg)
    assert a.equals(b) and len(a) == 100 and (a.half == "calibration").sum() == 50


def test_loo_baseline_excludes_the_shot_itself():
    shots = pd.DataFrame({"player_id": [1, 1, 1, 2], "coord_distance_ft": [3.0, 15.0, 27.0, 10.0],
                          "zone": ["restricted_area", "mid_range", "above_break_three", "paint"]})
    b = loo_baseline(shots, ["player_id"])
    assert b.baseline_distance_ft.tolist()[:3] == [21.0, 15.0, 9.0]
    assert b.baseline_restricted_area.tolist()[:3] == [0.0, 0.5, 0.5]
    assert pd.isna(b.baseline_distance_ft.iloc[3])  # a player with one shot has no baseline
