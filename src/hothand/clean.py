"""Stage 3 structural cleaning: raw shot files -> one cleaned table per season and season type.

Only structural fixes happen here (duplicates, types, names, clock parsing, labels, joins).
No shot is excluded for looking unusual; analytical exclusions belong to Stage 4.
Every rule records rows before and after, per season, in the attrition table.
"""

import numpy as np
import pandas as pd

from hothand.acquire import SEASON_TYPE_CODE
from hothand.config import INTERIM, ROOT, load_config
from hothand.rawio import SHOT_KEY, game_seconds_elapsed, load_pbp, load_shots, parse_iso_clock

ATTRITION = ROOT / "reports" / "stage3_attrition.csv"

RENAME = {
    "GAME_EVENT_ID": "game_event_id", "PLAYER_ID": "player_id", "PLAYER_NAME": "player_name",
    "TEAM_ID": "team_id", "TEAM_NAME": "team_name", "PERIOD": "period",
    "ACTION_TYPE": "action_type", "SHOT_TYPE": "shot_type", "SHOT_ZONE_BASIC": "shot_zone_basic",
    "SHOT_ZONE_AREA": "shot_zone_area", "SHOT_ZONE_RANGE": "shot_zone_range",
    "SHOT_DISTANCE": "shot_distance_ft", "LOC_X": "loc_x", "LOC_Y": "loc_y",
    "SHOT_MADE_FLAG": "shot_made", "HTM": "home_team", "VTM": "away_team",
}


def pbp_context(pbp: pd.DataFrame) -> pd.DataFrame:
    """Per play-by-play event: chronological position, precise clock and the score before it.

    The file's row order is chronological (the clock never runs backwards in it), while event
    numbers are sometimes assigned late, so position in the file is the ordering tiebreaker.
    """
    p = pbp.copy()
    p["pbp_row"] = p.groupby("gameId").cumcount()
    for side in ["Home", "Away"]:
        filled = p.groupby("gameId")[f"score{side}"].ffill().fillna(0)
        p[f"score_{side.lower()}_before"] = (
            filled.groupby(p.gameId).shift(1).fillna(0).astype(int))
    p["clock_remaining_s"] = parse_iso_clock(p.clock)
    return p[p.isFieldGoal == 1][["gameId", "actionNumber", "personId", "pbp_row", "location",
                                  "clock_remaining_s", "score_home_before", "score_away_before"]]


def clean_one(season: str, season_type: str, flags: dict) -> tuple[pd.DataFrame, list[dict]]:
    shots = load_shots(season, season_type)
    steps = [("raw", len(shots))]

    shots = shots.drop_duplicates()
    steps.append(("drop exact duplicate rows", len(shots)))
    shots = shots.drop_duplicates(SHOT_KEY)
    steps.append(("drop duplicate game/event/player keys", len(shots)))

    ctx = pbp_context(load_pbp(season, season_type))
    df = shots.merge(ctx, left_on=["GAME_ID", "GAME_EVENT_ID"],
                     right_on=["gameId", "actionNumber"], how="left")
    df = df[df.personId == df.PLAYER_ID]  # unmatched rows have NaN personId and drop here too
    steps.append(("drop shots with no play-by-play event for the same player", len(df)))

    out = df.rename(columns=RENAME)
    out.insert(0, "game_id", df.GAME_ID.astype(str).str.zfill(10))
    out["season"] = season
    out["season_type"] = season_type
    out["season_flag"] = flags.get(season, "")
    out["game_date"] = pd.to_datetime(df.GAME_DATE.astype(str), format="%Y%m%d")
    out["is_home"] = df.location.eq("h")
    out["shot_value"] = np.where(df.SHOT_TYPE.str.startswith("3"), 3, 2)
    out["game_elapsed_s"] = game_seconds_elapsed(out.period, out.clock_remaining_s)
    out["coord_distance_ft"] = (np.hypot(df.LOC_X, df.LOC_Y) / 10).round(2)
    own = np.where(out.is_home, out.score_home_before, out.score_away_before)
    opp = np.where(out.is_home, out.score_away_before, out.score_home_before)
    out["score_margin_before"] = own - opp  # from the shooter's team's point of view

    cols = ["game_id", "game_date", "season", "season_type", "season_flag", "home_team",
            "away_team", "game_event_id", "pbp_row", "period", "clock_remaining_s",
            "game_elapsed_s", "player_id", "player_name", "team_id", "team_name", "is_home",
            "score_home_before", "score_away_before", "score_margin_before", "action_type",
            "shot_type", "shot_value", "shot_zone_basic", "shot_zone_area", "shot_zone_range",
            "shot_distance_ft", "coord_distance_ft", "loc_x", "loc_y", "shot_made"]
    out = out[cols].sort_values(["game_id", "pbp_row"]).reset_index(drop=True)
    out["shot_made"] = out.shot_made.astype("int8")

    attrition = [{"season": season, "season_type": season_type, "step": i, "rule": rule,
                  "rows_after": n, "rows_removed": steps[i - 1][1] - n if i else 0}
                 for i, (rule, n) in enumerate(steps)]
    return out, attrition


def interim_path(season: str, season_type: str):
    return INTERIM / f"shots_{SEASON_TYPE_CODE[season_type]}_{season}.parquet"


def content_hash(df: pd.DataFrame) -> str:
    """Hash of the table's values, independent of parquet file metadata."""
    return format(int(pd.util.hash_pandas_object(df, index=False).sum()) % 2**64, "016x")


def run() -> pd.DataFrame:
    cfg = load_config()
    INTERIM.mkdir(parents=True, exist_ok=True)
    rows = []
    for season in cfg["data"]["seasons"]:
        for season_type in cfg["data"]["season_types"]:
            df, attrition = clean_one(season, season_type, cfg["data"]["flagged_seasons"])
            df.to_parquet(interim_path(season, season_type), index=False)
            attrition[-1]["content_hash"] = content_hash(df)
            rows.extend(attrition)
    table = pd.DataFrame(rows)
    table.to_csv(ATTRITION, index=False)
    return table


if __name__ == "__main__":
    t = run()
    final = t.groupby(["season", "season_type"], sort=False).last()
    print(final[["rows_after", "content_hash"]].to_string())
    print("removed by rule:", t.groupby("rule", sort=False).rows_removed.sum().to_dict())
