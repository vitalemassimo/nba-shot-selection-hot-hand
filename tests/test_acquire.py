from hothand.acquire import season_start_year
from hothand.allstars import clean_name


def test_season_start_year():
    assert season_start_year("2024-25") == 2024


def test_clean_name_strips_markers():
    assert clean_name("Stephen CurryINJ2") == "Stephen Curry"
    assert clean_name("Joel EmbiidCOVID1") == "Joel Embiid"
    assert clean_name("Dallas MavericksNOTE1") == "Dallas Mavericks"
    assert clean_name("Jaren Jackson Jr.") == "Jaren Jackson Jr."
    assert clean_name("OG Anunoby") == "OG Anunoby"
    assert clean_name("Devin BookerREP1INJ3") == "Devin Booker"
    assert clean_name("Mike Conley REP3") == "Mike Conley"
    assert clean_name("Gary Payton II") == "Gary Payton II"
    assert clean_name("Jimmy Butler III") == "Jimmy Butler III"
