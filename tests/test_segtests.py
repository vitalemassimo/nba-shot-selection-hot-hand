import pandas as pd

from hothand.segtests import both_contexts, holm


def test_both_contexts_keeps_player_seasons_with_regular_season_and_playoff_pairs():
    d = pd.DataFrame({"player_id": [1, 1, 2, 3, 3],
                      "season": ["2020-21", "2020-21", "2020-21", "2020-21", "2021-22"],
                      "season_type": ["Regular Season", "Playoffs", "Regular Season",
                                      "Regular Season", "Playoffs"]})
    # player 3 has RS and playoffs only in different seasons: not the same player-season
    assert both_contexts(d).tolist() == [True, True, False, False, False]


def test_holm_adjustment():
    out = holm({"H1": 0.01, "H2": 0.04, "H3": 0.03, "H4": 0.5}, alpha=0.05).set_index("hypothesis")
    assert round(out.loc["H1", "p_holm"], 3) == 0.04      # 0.01 x 4
    assert round(out.loc["H3", "p_holm"], 3) == 0.09      # 0.03 x 3
    assert round(out.loc["H2", "p_holm"], 3) == 0.09      # max(0.04 x 2, previous)
    assert out.loc["H1", "reject_at_alpha"] and not out.loc["H2", "reject_at_alpha"]
