import pandas as pd

from hothand.segments import experience_group, first_season_played, name_key, usage_tiers


def test_name_key_handles_suffix_accents_and_punctuation():
    assert name_key("Jimmy Butler III") == name_key("Jimmy Butler") == "jimmy butler"
    assert name_key("Nikola Jokić") == "nikola jokic"
    assert name_key("De'Aaron Fox") == "de aaron fox"


def test_first_season_moves_to_first_season_played_inside_window():
    from_year = pd.Series({1: 2018, 2: 2018, 3: 2010})
    shots = pd.Series([2019, 2020, 2018, 2019, 2018], index=[1, 1, 2, 2, 3])
    out = first_season_played(from_year, shots)
    assert out.to_dict() == {1: 2019,   # listed 2018, no shots that season -> 2019
                             2: 2018,   # played in his listed season -> unchanged
                             3: 2010}   # before the window: cannot be checked, unchanged


def test_experience_groups_leave_seasons_2_to_9_out():
    g = experience_group(pd.Series([1, 2, 9, 10, 15]), veteran_from=10)
    assert g.tolist() == ["rookie", pd.NA, pd.NA, "veteran", "veteran"]


def test_usage_tiers_thirds_and_minimum():
    t = pd.DataFrame({"FGA": [50, 100, 200, 300, 400, 500, 600],
                      "GP": [10, 10, 10, 10, 10, 10, 10]})
    tiers = usage_tiers(t, min_fga=100, n_tiers=3)
    assert pd.isna(tiers.iloc[0])           # below 100 FGA: no tier
    assert tiers.iloc[1:].tolist() == ["low", "low", "mid", "mid", "high", "high"]
