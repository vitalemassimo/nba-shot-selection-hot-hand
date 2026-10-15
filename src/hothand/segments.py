"""Stage 4: segment labels per player-season (H1, H2 and the All-Star subset).

  D-008  rookie = first NBA season; veteran = 10th season or later; seasons 2-9 left out of H1
  D-030  first season = first season actually played (player table, corrected by the shot data)
  D-009  usage tier = thirds of FGA per game within each regular season, players with 100+ FGA
  D-031  a player's playoff tier is his regular-season tier of the same season
  D-016  All-Star selections from data/reference/allstars.csv, matched to player IDs by name
Output: data/processed/player_seasons.csv (one row per player, season and season type).
"""

import re
import unicodedata

import pandas as pd

from hothand.config import DATA, PROCESSED, load_config
from hothand.rawio import load_player_index, load_player_totals

PLAYER_SEASONS = PROCESSED / "player_seasons.csv"
WINDOW_START = 2018  # first season start year in the data window


def name_key(name: str) -> str:
    """Accent-, punctuation- and suffix-insensitive name key ('Jimmy Butler III' -> 'jimmy butler')."""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'\-]", " ", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    return " ".join(s.split())


def first_season_played(from_year: pd.Series, seasons_with_shots: pd.Series) -> pd.Series:
    """First NBA season (start year) actually played.

    `from_year` is the player table's first roster season; `seasons_with_shots` the start year of
    each season the player took a shot (both indexed by player). If the listed first season is in
    the window but the player took no shot in it, use his first season with a shot. Before the
    window the shot data cannot correct it, so the listed season is kept.
    """
    first_shot = seasons_with_shots.groupby(level=0).min()
    seen = seasons_with_shots.groupby(level=0).apply(set)
    played_listed = pd.Series({p: from_year[p] in seen.get(p, set()) for p in from_year.index})
    corrected = (from_year >= WINDOW_START) & ~played_listed & first_shot.reindex(from_year.index).notna()
    return from_year.where(~corrected, first_shot.reindex(from_year.index)).astype(int)


def experience_group(season_no: pd.Series, veteran_from: int) -> pd.Series:
    return pd.Series(pd.NA, index=season_no.index, dtype="object").mask(
        season_no == 1, "rookie").mask(season_no >= veteran_from, "veteran")


def usage_tiers(totals: pd.DataFrame, min_fga: int, n_tiers: int) -> pd.Series:
    """Tier (low/mid/high) by FGA per game within one regular season; NaN below the minimum."""
    eligible = totals[totals.FGA >= min_fga]
    fga_pg = eligible.FGA / eligible.GP
    labels = ["low", "mid", "high"] if n_tiers == 3 else [f"t{i + 1}" for i in range(n_tiers)]
    tiers = pd.qcut(fga_pg, n_tiers, labels=labels).astype("object")
    return tiers.reindex(totals.index)


def build(shots: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    seg = cfg["segments"]
    ps = shots[["player_id", "season", "season_type"]].drop_duplicates()
    ps["start"] = ps.season.str[:4].astype(int)

    idx = load_player_index().drop_duplicates("PERSON_ID").set_index("PERSON_ID")
    shot_seasons = ps.drop_duplicates(["player_id", "start"]).set_index("player_id").start
    first = first_season_played(idx.FROM_YEAR, shot_seasons).rename("first_season_played")
    ps = ps.merge(first, left_on="player_id", right_index=True, how="left")
    ps["listed_first_season"] = ps.player_id.map(idx.FROM_YEAR)
    ps["season_no"] = ps.start - ps.first_season_played + 1
    ps["experience_group"] = experience_group(ps.season_no, seg["veteran_min_season_number"])

    tiers = []
    for season in cfg["data"]["seasons"]:
        t = load_player_totals(season, "Regular Season").set_index("PLAYER_ID")
        tier = usage_tiers(t, seg["usage_min_fga_season"], seg["usage_tiers"])
        tiers.append(pd.DataFrame({"player_id": t.index, "season": season,
                                   "rs_fga": t.FGA.values, "rs_gp": t.GP.values,
                                   "usage_tier": tier.values}))
    ps = ps.merge(pd.concat(tiers), on=["player_id", "season"], how="left")  # D-031: playoffs too

    stars = pd.read_csv(DATA / "reference" / "allstars.csv")
    stars["k"] = stars.player_name.map(name_key)
    keys = ps[["player_id", "season"]].drop_duplicates()
    keys["k"] = keys.player_id.map((idx.PLAYER_FIRST_NAME + " " + idx.PLAYER_LAST_NAME)
                                   .map(name_key))
    matched = stars.merge(keys, on=["season", "k"], how="inner")
    if len(matched) != len(stars) or matched.duplicated(["season", "k"]).any():
        raise ValueError("All-Star names do not map one-to-one onto players with shots that season")
    ps["all_star"] = ps.set_index(["player_id", "season"]).index.isin(
        matched.set_index(["player_id", "season"]).index)
    return ps.drop(columns="start").sort_values(["season", "season_type", "player_id"])


def run() -> pd.DataFrame:
    from hothand.pairs import load_cleaned

    cfg = load_config()
    ps = build(load_cleaned(cfg), cfg)
    ps.to_csv(PLAYER_SEASONS, index=False)
    return ps


if __name__ == "__main__":
    out = run()
    rs = out[out.season_type == "Regular Season"]
    print(rs.experience_group.value_counts(dropna=False).to_string())
    print(rs.usage_tier.value_counts(dropna=False).to_string())
    print("All-Star player-seasons:", int(rs.all_star.sum()))
