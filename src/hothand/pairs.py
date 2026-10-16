"""Stage 4: shot pairs, streak states, the game split and the leave-one-out baseline.

Definitions are in docs/decisions.md; every threshold comes from config.yaml.
  D-006  a pair = same player, same game, no other attempt by that player in between,
         at most `max_gap_game_seconds` of game clock apart
  D-017  shot order = play-by-play file order (`pbp_row`)
  D-018  heaves (36+ ft, last 3 s of Q1-Q3) are never analysed
  D-024  a pair is left out when either shot is a putback or tip
  D-029  putbacks and tips still count in the streak state, made or missed
  D-010  games are randomly split into calibration and analysis halves
"""

import numpy as np
import pandas as pd

from hothand.clean import interim_path
from hothand.config import PROCESSED

ZONES = {  # five analysis zones (Primary 2), from the published shot_zone_basic
    "Restricted Area": "restricted_area",
    "In The Paint (Non-RA)": "paint",
    "Mid-Range": "mid_range",
    "Left Corner 3": "corner_three",
    "Right Corner 3": "corner_three",
    "Above the Break 3": "above_break_three",
}
ZONE_NAMES = ["restricted_area", "paint", "mid_range", "corner_three", "above_break_three"]
GAME_SPLIT = PROCESSED / "game_split.csv"


def load_cleaned(cfg: dict) -> pd.DataFrame:
    frames = [pd.read_parquet(interim_path(s, t))
              for s in cfg["data"]["seasons"] for t in cfg["data"]["season_types"]]
    return pd.concat(frames, ignore_index=True)


def flag_shots(shots: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Add the shot-level flags the pair rules need. Does not drop anything."""
    p = cfg["pairs"]
    out = shots.copy()
    out["is_putback_tip"] = out.action_type.isin(p["excluded_action_types"])
    out["is_heave"] = ((out.coord_distance_ft >= p["heave_min_distance_ft"])
                       & (out.clock_remaining_s <= p["heave_seconds_remaining"])
                       & (out.period <= p["heave_max_period"]))
    out["is_backcourt"] = out.shot_zone_basic.eq("Backcourt")  # left out of the analysis (D-026)
    out["zone"] = out.shot_zone_basic.map(ZONES)  # Backcourt has no analysis zone
    out["in_analysis_population"] = ~(out.is_putback_tip | out.is_heave | out.is_backcourt)
    return out


def build_pairs(shots: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """One row per next shot that has a valid previous shot, with the streak state of the past.

    Sequences are per player per game, in play-by-play order. If heaves do not break pairs, they
    are removed before sequencing; otherwise they stay in the sequence and any pair touching one
    is left out. Putbacks, tips (D-024) and backcourt shots (D-026) always stay in the sequence
    (D-006: they sit between the shots around them) and any pair touching one is left out.
    """
    p = cfg["pairs"]
    s = shots if p["heave_breaks_pair"] else shots[~shots.is_heave]
    s = s.sort_values(["game_id", "player_id", "pbp_row"]).reset_index(drop=True)
    g = s.groupby(["game_id", "player_id"], sort=False)

    prev = g[["pbp_row", "game_elapsed_s", "period", "shot_made", "coord_distance_ft",
              "shot_distance_ft", "zone", "shot_value", "is_putback_tip", "is_heave",
              "is_backcourt", "action_type"]].shift(1)
    s["shot_number"] = g.cumcount() + 1  # this player's attempt number in the game
    s["gap_s"] = s.game_elapsed_s - prev.game_elapsed_s
    s["same_period"] = s.period == prev.period

    # A link joins two consecutive shots for the streak state. Putbacks and tips count in the
    # streak, made or missed (D-029), so they do not break a link; heaves, backcourt shots and
    # the gap rule do.
    link = prev.pbp_row.notna() & (s.gap_s <= p["max_gap_game_seconds"])
    if p["same_period_only"]:
        link &= s.same_period
    link &= ~s.is_heave & ~prev.is_heave.astype(bool)
    link &= ~s.is_backcourt & ~prev.is_backcourt.astype(bool)
    # An analysed pair is a link where neither shot is a putback or tip (D-024).
    s["valid_pair"] = link & ~s.is_putback_tip & ~prev.is_putback_tip.astype(bool)

    # Streak state: consecutive makes ending at the previous shot, counted along an unbroken
    # chain of links (a broken link starts a new chain).
    chain = (~link).cumsum()  # also starts a new chain at each new player-game
    s["make_run_through_this"] = _run_length(s.shot_made, chain)
    s["prev_make_run"] = s.groupby(chain).make_run_through_this.shift(1)
    s["prev2_made"] = s.groupby(chain).shot_made.shift(2)

    for col in ["pbp_row", "shot_made", "coord_distance_ft", "shot_distance_ft", "zone",
                "shot_value", "action_type", "game_elapsed_s"]:
        s[f"prev_{col}"] = prev[col]
    if "xfg" in s:  # the previous shot's difficulty, when xFG has been attached
        s["prev_xfg"] = g.xfg.shift(1)
    pairs = s[s.valid_pair].copy()
    pairs["prev_made"] = pairs.prev_shot_made.astype("int8")
    pairs["last_two"] = np.where(
        pairs.prev2_made.isna(), "",
        pairs.prev2_made.map({1.0: "made", 0.0: "miss"}) + "-"
        + pairs.prev_made.map({1: "made", 0: "miss"}))
    pairs["three_plus_makes"] = pairs.prev_make_run >= 3
    return pairs.drop(columns=["valid_pair", "make_run_through_this"])


def _run_length(made: pd.Series, chain: pd.Series) -> pd.Series:
    """Length of the current run of makes, within each chain, at each shot (0 after a miss)."""
    block = (made != 1).groupby(chain).cumsum()
    return made.groupby([chain, block]).cumsum()


def assign_game_split(games: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Seeded random split of games (not shots) into calibration and analysis halves (D-010),
    drawn separately within each season and season type (D-025).

    `games` needs game_id, season and season_type; duplicates are ignored.
    """
    games = games[["game_id", "season", "season_type"]].drop_duplicates()
    rng = np.random.default_rng(cfg["random_seed"])
    parts = []
    for _, cell in games.sort_values(["season", "season_type", "game_id"]).groupby(
            ["season", "season_type"], sort=True):
        shuffled = rng.permutation(cell.game_id.to_numpy())
        n_cal = round(len(shuffled) * cfg["split"]["calibration_fraction"])
        parts.append(pd.DataFrame({"game_id": shuffled,
                                   "half": ["calibration"] * n_cal
                                   + ["analysis"] * (len(shuffled) - n_cal)}))
    return pd.concat(parts).sort_values("game_id").reset_index(drop=True)


def player_baselines(shots: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Leave-one-out baseline for every analysis-population shot, within the D-027 group
    (player, season, season type, half). Needs `half` and the flags from flag_shots."""
    pop = shots[shots.in_analysis_population]
    return loo_baseline(pop, cfg["features"]["baseline_group"])


def loo_baseline(shots: pd.DataFrame, group: list[str]) -> pd.DataFrame:
    """Leave-one-out baseline for every shot: the mean distance and zone shares of the same group's
    other shots, so a shot never contributes to its own baseline."""
    s = shots[group + ["coord_distance_ft"]].copy()
    for z in ZONE_NAMES:
        s[f"z_{z}"] = (shots.zone == z).astype(float)
    cols = ["coord_distance_ft"] + [f"z_{z}" for z in ZONE_NAMES]
    g = s.groupby(group)
    n = g.coord_distance_ft.transform("size")
    out = pd.DataFrame(index=shots.index)
    out["baseline_n"] = n - 1
    for c in cols:
        loo = (g[c].transform("sum") - s[c]) / (n - 1)
        name = "baseline_distance_ft" if c == "coord_distance_ft" else f"baseline_{c[2:]}"
        out[name] = loo.where(n > 1)
    return out


def load_game_split() -> pd.DataFrame:
    """The saved game split; game IDs are read as text so their leading zeros survive."""
    return pd.read_csv(GAME_SPLIT, dtype={"game_id": str})
