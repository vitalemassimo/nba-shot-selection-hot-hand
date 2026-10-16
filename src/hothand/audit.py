"""Stage 3 audit: find what is wrong with the raw data, per season and season type.

Reads data/raw/ only and never modifies it. Each check returns metrics plus a pass flag; failures
are not fixed here, they get a decision in docs/decisions.md.
"""

import numpy as np
import pandas as pd

from hothand.config import ROOT, load_config
from hothand.rawio import (
    SHOT_KEY,
    game_seconds_elapsed,
    load_pbp,
    load_player_index,
    load_player_totals,
    load_shots,
    parse_iso_clock,
)

# Real schedule lengths (regular season). 2019-20 was suspended (COVID) and finished with seeding
# games in the bubble; 2020-21 was a 72-game season.
RS_GAMES = {"2019-20": 1059, "2020-21": 1080}
RS_GAMES_DEFAULT = 1230
PLAYOFF_GAMES_RANGE = (60, 105)  # 15 series, 4-7 games each

COURT_X = (-250, 250)  # tenths of a foot from the basket, sideline to sideline
COURT_Y = (-52, 888)   # baseline (behind the rim) to the far baseline
CORNER_3_FT = 22.0
ARC_3_FT = 23.75
DIST_TOL_FT = 1.5      # allowed gap between stated distance and coordinate distance
THREE_TOL_FT = 0.5     # measurement noise allowed around the three-point line

NEEDED = ["GAME_ID", "GAME_EVENT_ID", "PLAYER_ID", "TEAM_ID", "PERIOD", "MINUTES_REMAINING",
          "SECONDS_REMAINING", "ACTION_TYPE", "SHOT_TYPE", "SHOT_ZONE_BASIC", "SHOT_DISTANCE",
          "LOC_X", "LOC_Y", "SHOT_MADE_FLAG", "GAME_DATE", "HTM", "VTM"]


def coord_distance_ft(shots: pd.DataFrame) -> pd.Series:
    return np.hypot(shots.LOC_X, shots.LOC_Y) / 10


def check_schema(frames: dict) -> pd.DataFrame:
    """Column names and dtypes per file, compared with the first file."""
    ref_key, ref = next(iter(frames.items()))
    ref_sig = list(zip(ref.columns, ref.dtypes.astype(str)))
    rows = []
    for key, df in frames.items():
        sig = list(zip(df.columns, df.dtypes.astype(str)))
        rows.append({"season": key[0], "season_type": key[1], "n_columns": len(sig),
                     "same_as_" + "_".join(ref_key): sig == ref_sig,
                     "differences": "; ".join(f"{a}->{b}" for a, b in
                                              set(sig).symmetric_difference(ref_sig))})
    return pd.DataFrame(rows)


def audit_one(season: str, season_type: str, shots: pd.DataFrame, pbp: pd.DataFrame,
              players: pd.DataFrame, totals: pd.DataFrame) -> dict:
    r = {"season": season, "season_type": season_type, "rows": len(shots)}

    # Duplicates
    r["dup_exact_rows"] = int(shots.duplicated().sum())
    r["dup_key"] = int(shots.duplicated(SHOT_KEY).sum())

    # Missing values in fields the analysis needs
    nulls = shots[NEEDED].isna().sum()
    r["null_cells_needed"] = int(nulls.sum())
    r["null_columns"] = ", ".join(f"{c}={n}" for c, n in nulls[nulls > 0].items())

    # Made flag
    r["made_flag_values"] = ",".join(map(str, sorted(shots.SHOT_MADE_FLAG.unique())))
    r["made_vs_event_type_mismatch"] = int(
        ((shots.SHOT_MADE_FLAG == 1) != (shots.EVENT_TYPE == "Made Shot")).sum())
    r["attempted_flag_not_1"] = int((shots.SHOT_ATTEMPTED_FLAG != 1).sum())

    # Distance vs coordinates
    gap = shots.SHOT_DISTANCE - coord_distance_ft(shots)
    r["dist_gap_median_ft"] = round(float(gap.median()), 2)
    r["dist_gap_over_tol"] = int((gap.abs() > DIST_TOL_FT).sum())
    r["dist_gap_max_ft"] = round(float(gap.abs().max()), 1)

    # Three-point consistency (computed distance, so it is independent of SHOT_DISTANCE rounding)
    d = coord_distance_ft(shots)
    is3 = shots.SHOT_TYPE.str.startswith("3")
    r["three_inside_corner_line"] = int((is3 & (d < CORNER_3_FT - THREE_TOL_FT)).sum())
    r["two_beyond_arc"] = int((~is3 & (d > ARC_3_FT + THREE_TOL_FT)).sum())
    r["zone_type_mismatch"] = int((is3 != shots.SHOT_ZONE_BASIC.str.contains("3")).sum()
                                  - (shots.SHOT_ZONE_BASIC == "Backcourt").sum())

    # Value ranges
    r["loc_x_range"] = f"{shots.LOC_X.min()}..{shots.LOC_X.max()}"
    r["loc_y_range"] = f"{shots.LOC_Y.min()}..{shots.LOC_Y.max()}"
    r["out_of_court"] = int((~shots.LOC_X.between(*COURT_X) | ~shots.LOC_Y.between(*COURT_Y)).sum())
    r["period_range"] = f"{shots.PERIOD.min()}..{shots.PERIOD.max()}"
    period_s = np.where(shots.PERIOD <= 4, 720, 300)
    remaining = shots.MINUTES_REMAINING * 60 + shots.SECONDS_REMAINING
    r["bad_clock"] = int((~shots.SECONDS_REMAINING.between(0, 59) | (remaining > period_s)).sum())
    r["backcourt_shots"] = int((shots.SHOT_ZONE_BASIC == "Backcourt").sum())

    # Season type and season encoded in the game ID: 00 + type digit + 2-digit season + 5 digits
    gid = shots.GAME_ID.astype(str).str.zfill(10)
    want_type = "4" if season_type == "Playoffs" else "2"
    r["season_type_mismatch"] = int((gid.str[2] != want_type).sum())
    r["season_year_mismatch"] = int((gid.str[3:5] != season[2:4]).sum())

    # Game coverage
    r["games"] = shots.GAME_ID.nunique()
    r["games_not_two_teams"] = int((shots.groupby("GAME_ID").TEAM_ID.nunique() != 2).sum())
    if season_type == "Regular Season":
        r["games_expected"] = RS_GAMES.get(season, RS_GAMES_DEFAULT)
        r["games_ok"] = r["games"] == r["games_expected"]
    else:
        r["games_expected"] = "{}-{}".format(*PLAYOFF_GAMES_RANGE)
        r["games_ok"] = PLAYOFF_GAMES_RANGE[0] <= r["games"] <= PLAYOFF_GAMES_RANGE[1]

    # Join with play-by-play on game + event number
    fg = pbp[pbp.isFieldGoal == 1]
    m = shots.merge(fg, left_on=["GAME_ID", "GAME_EVENT_ID"], right_on=["gameId", "actionNumber"],
                    how="left", indicator=True)
    r["pbp_unmatched"] = int((m._merge == "left_only").sum())
    both = m[m._merge == "both"]
    r["pbp_player_mismatch"] = int((both.PLAYER_ID != both.personId).sum())
    r["pbp_made_mismatch"] = int(((both.SHOT_MADE_FLAG == 1) != (both.shotResult == "Made")).sum())
    r["pbp_fg_not_in_shots"] = len(fg) - len(both)

    # Ordering. Event numbers are sometimes assigned late, so sorting by them can send the clock
    # backwards (informational). The play-by-play file order is the ordering used for pairs and
    # must never send the clock backwards (pass rule).
    p = pbp.copy()
    p["elapsed"] = game_seconds_elapsed(p.period, parse_iso_clock(p.clock))
    r["clock_backwards_file_order"] = int((p.groupby("gameId").elapsed.diff() < 0).sum())
    s = both.sort_values(["GAME_ID", "PLAYER_ID", "GAME_EVENT_ID"]).copy()
    s["elapsed"] = game_seconds_elapsed(s.period, parse_iso_clock(s.clock))
    r["shots_out_of_order_by_event_id"] = int(
        (s.groupby(["GAME_ID", "PLAYER_ID"]).elapsed.diff() < 0).sum())

    # Team-level heave events (introduced in 2025-26: missed end-of-quarter heaves are no longer
    # credited to a player as a field-goal attempt)
    r["pbp_team_heave_events"] = int((pbp.actionType == "Heave").sum())

    # Player table join
    r["players_not_in_index"] = int((~shots.PLAYER_ID.isin(players.PERSON_ID)).sum())

    # Shot volume vs official box-score totals
    fga = shots.groupby("PLAYER_ID").size().rename("fga_shots")
    t = totals.set_index("PLAYER_ID").FGA.rename("fga_official")
    v = pd.concat([fga, t], axis=1).fillna(0)
    diff = (v.fga_shots - v.fga_official).abs()
    r["fga_shots_total"] = int(v.fga_shots.sum())
    r["fga_official_total"] = int(v.fga_official.sum())
    r["players_fga_exact"] = round(float((diff == 0).mean()), 4)
    r["players_fga_off_by_gt2"] = int((diff > 2).sum())
    return r


PASS_RULES = {
    "dup_key": lambda v: v == 0,
    "null_cells_needed": lambda v: v == 0,
    "made_flag_values": lambda v: v == "0,1",
    "made_vs_event_type_mismatch": lambda v: v == 0,
    "season_type_mismatch": lambda v: v == 0,
    "season_year_mismatch": lambda v: v == 0,
    "games_ok": bool,
    "games_not_two_teams": lambda v: v == 0,
    "out_of_court": lambda v: v == 0,
    "bad_clock": lambda v: v == 0,
    "pbp_unmatched": lambda v: v == 0,
    "pbp_player_mismatch": lambda v: v == 0,
    "pbp_made_mismatch": lambda v: v == 0,
    "clock_backwards_file_order": lambda v: v == 0,
    "players_not_in_index": lambda v: v == 0,
    "players_fga_off_by_gt2": lambda v: v == 0,
    "three_inside_corner_line": lambda v: v == 0,
    "two_beyond_arc": lambda v: v == 0,
    "dist_gap_over_tol": lambda v: v == 0,
}


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = load_config()
    players = load_player_index()
    frames, results = {}, []
    for season in cfg["data"]["seasons"]:
        for season_type in cfg["data"]["season_types"]:
            shots = load_shots(season, season_type)
            frames[(season, season_type)] = shots
            results.append(audit_one(season, season_type, shots, load_pbp(season, season_type),
                                     players, load_player_totals(season, season_type)))
    checks = pd.DataFrame(results)
    for col, rule in PASS_RULES.items():
        checks[f"pass_{col}"] = checks[col].map(rule)
    return checks, check_schema(frames)


# Checks allowed to fail because a dated decision in docs/decisions.md handles them.
DOCUMENTED = {
    "pbp_unmatched": "D-019",
    "pbp_player_mismatch": "D-019",
}
REPORT = ROOT / "reports" / "stage3_data_quality.md"
CHECKS_CSV = ROOT / "reports" / "stage3_checks.csv"


def summarize(checks: pd.DataFrame) -> pd.DataFrame:
    """One row per check: how many of the 16 files pass, and the decision for any failure."""
    rows = []
    for col in PASS_RULES:
        failed = checks.loc[~checks[f"pass_{col}"].astype(bool)]
        rows.append({
            "check": col,
            "files_passing": f"{len(checks) - len(failed)}/{len(checks)}",
            "failing_files": ", ".join(f"{r.season} {r.season_type}" for r in failed.itertuples()),
            "rows_affected": int(pd.to_numeric(failed[col], errors="coerce").fillna(0).sum()),
            "decision": DOCUMENTED.get(col, "") if len(failed) else "",
            "status": "pass" if failed.empty else ("documented" if col in DOCUMENTED else "FAIL"),
        })
    return pd.DataFrame(rows)


def write_report(checks: pd.DataFrame, schema: pd.DataFrame, attrition: pd.DataFrame) -> bool:
    summary = summarize(checks)
    ok = (summary.status != "FAIL").all() and bool(schema.iloc[:, 3].all())
    checks.to_csv(CHECKS_CSV, index=False)
    final = attrition.groupby(["season", "season_type"], sort=False).last().reset_index()
    info = checks[["season", "season_type", "rows", "games", "backcourt_shots",
                   "pbp_team_heave_events", "zone_type_mismatch", "shots_out_of_order_by_event_id",
                   "dist_gap_median_ft"]]
    lines = [
        "# Stage 3: data-quality report", "",
        ("Generated by `notebooks/01_audit.ipynb` (`hothand.audit` + `hothand.clean`). "
        "Do not edit by hand."), "",
        (f"**Automated checks: {'all pass or documented' if ok else 'FAILURES'}.** "
        "The stage gate is declared after the author's verification (docs/ownership.md)."), "",
        f"Schema identical across all {len(schema)} files: {bool(schema.iloc[:, 3].all())}.", "",
        "## Checks", "",
        summary.to_markdown(index=False), "",
        "## Informational measures (not pass/fail)", "",
        info.to_markdown(index=False), "",
        ("- `backcourt_shots` / `pbp_team_heave_events`: from 2025-26, missed end-of-quarter heaves "
        "are recorded as team events, not player attempts (D-018)."),
        ("- `zone_type_mismatch`: shots on the three-point line where the scorer's 2/3 ruling and "
        "the location zone disagree (D-020)."),
        ("- `shots_out_of_order_by_event_id`: event numbers assigned late; ordering uses the "
        "play-by-play file order instead (D-017)."),
        ("- `dist_gap_median_ft`: stated distance minus coordinate distance; about -0.5 ft because "
        "the stated distance is rounded down to whole feet."), "",
        "## Attrition (structural cleaning)", "",
        attrition.pivot_table(index=["season", "season_type"], columns="rule",
                              values="rows_after", sort=False).astype(int)
                 .reset_index().to_markdown(index=False), "",
        (f"Total rows removed: {int(attrition.rows_removed.sum())} of "
        f"{int(attrition[attrition.step == 0].rows_after.sum())}."), "",
        "## Cleaned files", "",
        final[["season", "season_type", "rows_after", "content_hash"]].to_markdown(index=False),
        "",
    ]
    REPORT.write_text("\n".join(lines))
    return ok


if __name__ == "__main__":
    checks, schema = run()
    pd.set_option("display.width", 250, "display.max_columns", 60)
    print(schema.to_string())
    print(checks.set_index(["season", "season_type"]).T.to_string())
