"""Second-chance (same-possession) flag on a hand-made play-by-play (D-047)."""

import pandas as pd

from hothand.robustness import same_possession

A, B = 100, 200  # team ids


def pbp(rows):
    """rows: (actionType, teamId, personId); file order = event order."""
    df = pd.DataFrame(rows, columns=["actionType", "teamId", "personId"])
    df["gameId"] = 22400001
    return df


def pair(prev_row, next_row, prev_made=0, team=A):
    return pd.DataFrame({"game_id": ["0022400001"], "team_id": [team], "prev_pbp_row": [prev_row],
                         "pbp_row": [next_row], "prev_made": [prev_made]})


def test_offensive_rebound_then_shot_is_same_possession():
    p = pbp([("Missed Shot", A, 1), ("Rebound", A, 2), ("Missed Shot", A, 1)])
    assert same_possession(pair(0, 2), p).tolist() == [True]


def test_team_rebound_counts_as_offensive():
    p = pbp([("Missed Shot", A, 1), ("Rebound", 0, A), ("Missed Shot", A, 1)])
    assert same_possession(pair(0, 2), p).tolist() == [True]


def test_defensive_rebound_ends_possession():
    p = pbp([("Missed Shot", A, 1), ("Rebound", B, 9), ("Missed Shot", B, 9),
             ("Rebound", A, 2), ("Missed Shot", A, 1)])
    assert same_possession(pair(0, 4), p).tolist() == [False]


def test_teammate_make_or_turnover_ends_possession():
    p = pbp([("Missed Shot", A, 1), ("Rebound", A, 2), ("Made Shot", A, 3),
             ("Missed Shot", A, 1)])
    assert same_possession(pair(0, 3), p).tolist() == [False]
    p = pbp([("Missed Shot", A, 1), ("Rebound", A, 2), ("Turnover", A, 2),
             ("Missed Shot", A, 1)])
    assert same_possession(pair(0, 3), p).tolist() == [False]


def test_after_a_make_is_never_same_possession():
    p = pbp([("Made Shot", A, 1), ("Rebound", A, 2), ("Missed Shot", A, 1)])
    assert same_possession(pair(0, 2, prev_made=1), p).tolist() == [False]


def test_period_end_ends_possession():
    p = pbp([("Missed Shot", A, 1), ("Rebound", A, 2), ("period", 0, 0), ("Missed Shot", A, 1)])
    assert same_possession(pair(0, 3), p).tolist() == [False]


def test_short_names_use_initials_and_full_names_for_clashes():
    from hothand.robustness import short_names
    full = pd.Series({1: "Lauri Markkanen", 2: "Marcus Morris", 3: "Markieff Morris",
                      4: "Amen Thompson", 5: "Klay Thompson"})
    assert short_names(full).to_dict() == {1: "L. Markkanen", 2: "Marcus Morris",
                                           3: "Markieff Morris", 4: "A. Thompson",
                                           5: "K. Thompson"}
