"""Stage 8: pre-aggregated tables the dashboard reads (playbook 8.2: the app never reads raw data
and never computes a result itself). Analysis half only. Output: data/processed/dashboard/*.csv

  explorer.csv  Model 3 shift (after make minus after miss) per group and outcome, with the
                after-make and after-miss means vs the player's baseline (display, D-041 design)
  shotmap.csv   share of next shots per court bin after a make minus after a miss, per group (D-051)
  players.csv   player-seasons with 100+ pairs after a make and 100+ after a miss (D-050)
  player_zones.csv  zone shares after a make and after a miss for those player-seasons (D-055)
"""

import numpy as np
import pandas as pd
import pyfixest as pf
from scipy import stats

from hothand import core, segtests
from hothand.config import PROCESSED, load_config
from hothand.features import FEATURES
from hothand.robustness import short_names

OUT = PROCESSED / "dashboard"
OUTCOMES = {
    "distance_vs_baseline_ft": "Distance vs own baseline (ft)",
    "rel_restricted_area": "Rim attempts (share, pp)",
    "rel_paint": "Paint attempts (share, pp)",
    "rel_mid_range": "Mid-range attempts (share, pp)",
    "rel_corner_three": "Corner threes (share, pp)",
    "rel_above_break_three": "Above-the-break threes (share, pp)",
    "rel_three": "All threes (share, pp)",
}
BIN_FT = 2.0
COURT_X = (-25.0, 25.0)
COURT_Y = (-5.0, 35.0)
MIN_BIN_SHOTS = 50
PLAYER_MIN_EACH_SIDE = 100


def groups(d: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
    """(group family, group label, mask) for every group the dashboard offers."""
    both = segtests.both_contexts(d)
    g = [("All players", "All players", pd.Series(True, index=d.index)),
         ("Experience", "Rookies", d.experience_group.eq("rookie")),
         ("Experience", "Veterans (10th season+)", d.experience_group.eq("veteran")),
         ("Usage", "Low usage", d.usage_tier.eq("low")),
         ("Usage", "Mid usage", d.usage_tier.eq("mid")),
         ("Usage", "High usage", d.usage_tier.eq("high")),
         ("Usage", "All-Stars (labelled subset)", d.all_star.astype(bool))]
    for c, label in [("rim_bigs", "Rim bigs"), ("rim_and_corner", "Rim and corner"),
                     ("mid_range_scorers", "Mid-range scorers"),
                     ("three_point_shooters", "Three-point shooters")]:
        g.append(("Playstyle", label, d.cluster.eq(c)))
    g += [("Season type", "Regular season", d.season_type.eq("Regular Season")),
          ("Season type", "Playoffs", d.season_type.eq("Playoffs")),
          ("Season type", "Regular season, players in both contexts",
           both & d.season_type.eq("Regular Season")),
          ("Season type", "Playoffs, players in both contexts",
           both & d.season_type.eq("Playoffs"))]
    return g


def explorer(d: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rows = []
    inf = cfg["inference"]
    for family, label, mask in groups(d):
        g = d[mask]
        n_pairs, n_players = len(g), g.player_id.nunique()
        enough = n_pairs >= inf["min_pairs_per_cell"] and n_players >= inf["min_players_per_cell"]
        for outcome, title in OUTCOMES.items():
            row = {"family": family, "group": label, "outcome": outcome, "outcome_label": title,
                   "n_pairs": n_pairs, "n_players": n_players}
            if not enough:
                rows.append({**row, "status": "too few shots to estimate"})
                continue
            m = pf.feols(f"{outcome} ~ {segtests._rhs()}",
                         data=g, vcov={"CRV1": "player_id"})
            t = m.tidy().loc["prev_made"]
            means = g.groupby("prev_made")[outcome].mean()
            scale = 1 if outcome == "distance_vs_baseline_ft" else 100
            rows.append({**row, "status": "estimated", "estimate": t["Estimate"] * scale,
                         "ci_low": t["2.5%"] * scale, "ci_high": t["97.5%"] * scale,
                         "after_miss_vs_baseline": means.get(0) * scale,
                         "after_make_vs_baseline": means.get(1) * scale})
    return pd.DataFrame(rows)


def shotmap(d: pd.DataFrame) -> pd.DataFrame:
    """Share of next shots per 2x2 ft bin after a make minus after a miss, per group (D-051).
    Bins with fewer than MIN_BIN_SHOTS shots in either condition are left out."""
    xe = np.arange(COURT_X[0], COURT_X[1] + BIN_FT, BIN_FT)
    ye = np.arange(COURT_Y[0], COURT_Y[1] + BIN_FT, BIN_FT)
    x, y = d.loc_x / 10, d.loc_y / 10
    rows = []
    for family, label, mask in groups(d):
        parts = {}
        for made in (0, 1):
            sel = mask & (d.prev_made == made)
            h, _, _ = np.histogram2d(x[sel], y[sel], bins=[xe, ye])
            parts[made] = h
        n0, n1 = parts[0].sum(), parts[1].sum()
        for i in range(len(xe) - 1):
            for j in range(len(ye) - 1):
                c0, c1 = parts[0][i, j], parts[1][i, j]
                if min(c0, c1) < MIN_BIN_SHOTS:
                    continue
                rows.append({"family": family, "group": label, "x_ft": xe[i] + BIN_FT / 2,
                             "y_ft": ye[j] + BIN_FT / 2, "shots_after_miss": int(c0),
                             "shots_after_make": int(c1),
                             "share_after_miss_pct": 100 * c0 / n0,
                             "share_after_make_pct": 100 * c1 / n1,
                             "diff_pp": 100 * (c1 / n1 - c0 / n0)})
    return pd.DataFrame(rows)


def players(d: pd.DataFrame) -> pd.DataFrame:
    """Player-seasons with 100+ pairs on each side: simple difference of mean distance vs baseline
    after a make minus after a miss, with a Welch 95% interval (D-050). Not Model 3: no controls."""
    names = short_names(d.drop_duplicates("player_id").set_index("player_id").player_name)
    rows = []
    for (pid, season), g in d.groupby(["player_id", "season"]):
        a, b = g.loc[g.prev_made == 1, "distance_vs_baseline_ft"], g.loc[g.prev_made == 0,
                                                                          "distance_vs_baseline_ft"]
        if len(a) < PLAYER_MIN_EACH_SIDE or len(b) < PLAYER_MIN_EACH_SIDE:
            continue
        va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
        se = np.sqrt(va + vb)
        df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
        q = stats.t.ppf(0.975, df)
        diff = a.mean() - b.mean()
        rows.append({"player_id": pid, "player": names[pid], "season": season,
                     "pairs_after_make": len(a), "pairs_after_miss": len(b),
                     "shift_ft": diff, "ci_low": diff - q * se, "ci_high": diff + q * se,
                     "experience_group": g.experience_group.iloc[0],
                     "usage_tier": g.usage_tier.iloc[0], "cluster": g.cluster.iloc[0]})
    return pd.DataFrame(rows).sort_values(["player", "season"]).reset_index(drop=True)


def player_zones(d: pd.DataFrame, eligible: pd.DataFrame) -> pd.DataFrame:
    """Per eligible player-season (D-050) and zone: share of next shots after a make and after a
    miss, and the difference in percentage points (D-055)."""
    from hothand.pairs import ZONE_NAMES

    keep = d.merge(eligible[["player_id", "season"]], on=["player_id", "season"])
    counts = (keep.groupby(["player_id", "season", "prev_made"]).zone.value_counts()
              .unstack(fill_value=0).reindex(columns=ZONE_NAMES, fill_value=0))
    rows = []
    for (pid, season), g in counts.groupby(level=[0, 1]):
        miss, make = g.xs(0, level=2).iloc[0], g.xs(1, level=2).iloc[0]
        for z in ZONE_NAMES:
            rows.append({"player_id": pid, "season": season, "zone": z,
                         "shots_after_miss": int(miss[z]), "shots_after_make": int(make[z]),
                         "share_after_miss_pct": 100 * miss[z] / miss.sum(),
                         "share_after_make_pct": 100 * make[z] / make.sum(),
                         "diff_pp": 100 * (make[z] / make.sum() - miss[z] / miss.sum())})
    return pd.DataFrame(rows)


def run() -> None:
    cfg = load_config()
    d = core.prepare(pd.read_parquet(FEATURES), cfg, "analysis")
    OUT.mkdir(parents=True, exist_ok=True)
    explorer(d, cfg).to_csv(OUT / "explorer.csv", index=False)
    shotmap(d).to_csv(OUT / "shotmap.csv", index=False)
    pl = players(d)
    pl.to_csv(OUT / "players.csv", index=False)
    player_zones(d, pl).to_csv(OUT / "player_zones.csv", index=False)


if __name__ == "__main__":
    run()
    for f in sorted(OUT.glob("*.csv")):
        print(f.name, len(pd.read_csv(f)), "rows,", f.stat().st_size // 1024, "KB")
