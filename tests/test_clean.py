import pandas as pd

from hothand.clean import pbp_context
from hothand.rawio import game_seconds_elapsed, parse_iso_clock


def test_parse_iso_clock():
    s = pd.Series(["PT12M00.00S", "PT00M03.50S", "PT05M00.00S"])
    assert parse_iso_clock(s).tolist() == [720.0, 3.5, 300.0]


def test_game_seconds_elapsed_regulation_and_overtime():
    period = pd.Series([1, 4, 5, 6])
    remaining = pd.Series([720.0, 0.0, 300.0, 0.0])
    # start of Q1, end of Q4, start of OT1, end of OT2
    assert game_seconds_elapsed(period, remaining).tolist() == [0, 2880, 2880, 3480]


def _pbp(rows):
    cols = ["gameId", "actionNumber", "personId", "period", "clock", "scoreHome", "scoreAway",
            "isFieldGoal", "location"]
    return pd.DataFrame(rows, columns=cols)


def test_score_before_excludes_the_shot_itself_and_resets_per_game():
    pbp = _pbp([
        (1, 2, 0, 1, "PT12M00.00S", 0, 0, 0, None),          # period start
        (1, 4, 10, 1, "PT11M40.00S", 2, None, 1, "h"),       # home makes a 2
        (1, 5, 20, 1, "PT11M20.00S", None, None, 1, "v"),    # away misses
        (1, 9, 20, 1, "PT11M00.00S", 2, 3, 1, "v"),          # away makes a 3
        (2, 3, 30, 1, "PT11M50.00S", None, None, 1, "h"),    # new game: score resets
    ])
    ctx = pbp_context(pbp).set_index(["gameId", "actionNumber"])
    assert ctx.loc[(1, 4), ["score_home_before", "score_away_before"]].tolist() == [0, 0]
    assert ctx.loc[(1, 5), ["score_home_before", "score_away_before"]].tolist() == [2, 0]
    assert ctx.loc[(1, 9), ["score_home_before", "score_away_before"]].tolist() == [2, 0]
    assert ctx.loc[(2, 3), ["score_home_before", "score_away_before"]].tolist() == [0, 0]


def test_file_order_not_event_number_defines_position():
    # event 9 was numbered late but happened first; file order is the truth
    pbp = _pbp([
        (1, 9, 10, 1, "PT11M50.00S", None, None, 1, "h"),
        (1, 4, 10, 1, "PT11M30.00S", None, None, 1, "h"),
    ])
    ctx = pbp_context(pbp).set_index("actionNumber")
    assert ctx.loc[9, "pbp_row"] < ctx.loc[4, "pbp_row"]
