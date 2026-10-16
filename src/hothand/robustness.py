"""Stage 7: try to break the headline (playbook 7.1-7.6).

Every variation changes one thing and re-runs Model 3 (D-048). The survival rule (D-045) and the
counting rules (D-046) were committed before anything here ran.
"""

import copy

import numpy as np
import pandas as pd
import pyfixest as pf

from hothand import core, segtests
from hothand.features import pairs_table
from hothand.rawio import load_pbp

OUTCOME = "distance_vs_baseline_ft"
POSSESSION_ENDS_FOR_OPPONENT = {"Made Shot", "Missed Shot", "Rebound"}
POSSESSION_ENDS_FOR_OWN = {"Turnover", "Made Shot"}


# ---------- estimators ----------

def model3(d: pd.DataFrame, treatment: str = "prev_made", extra: str = "",
           vcov: dict | None = None, replace_prev_controls: str | None = None) -> dict:
    """Model 3 (D-036, D-037) with optional extra terms, a different treatment or vcov."""
    rhs = core.formulas(OUTCOME, treatment)["Model 3"].split("~", 1)[1]
    if replace_prev_controls:
        covs, fe = rhs.split("|")
        rhs = f"{covs} + {replace_prev_controls} | {fe}"
    if extra:
        covs, fe = rhs.split("|")
        rhs = f"{covs} + {extra} | {fe}"
    m = pf.feols(f"{OUTCOME} ~ {rhs}", data=d, vcov=vcov or {"CRV1": "player_id"})
    t = m.tidy().loc[treatment]
    return {"estimate": t["Estimate"], "ci_low": t["2.5%"], "ci_high": t["97.5%"],
            "p_value": t["Pr(>|t|)"], "n_pairs": m._N, "n_players": d.player_id.nunique()}


def segment_gaps(d: pd.DataFrame) -> dict:
    """H2 (low minus high usage) and the H3 rim-bigs gap, reported without a verdict (D-046)."""
    h2 = segtests.interaction_test(d, d.usage_tier.map({"low": 1, "high": 0}), "H2")
    keep = d.cluster.isin(["rim_bigs", "three_point_shooters"])
    h3 = segtests.interaction_test(d[keep], d.loc[keep, "cluster"].eq("rim_bigs").astype(float),
                                   "H3 rim bigs minus three-point shooters")
    return {"h2_low_minus_high": h2["estimate"], "h2_ci_low": h2["ci_low"],
            "h2_ci_high": h2["ci_high"], "h3_rimbigs_minus_3pt": h3["estimate"],
            "h3_ci_low": h3["ci_low"], "h3_ci_high": h3["ci_high"]}


def player_bootstrap(d: pd.DataFrame, draws: int, seed: int) -> tuple[float, float]:
    """95% percentile interval for the Model 3 coefficient, resampling players with replacement."""
    rng = np.random.default_rng(seed)
    players = d.player_id.unique()
    by_player = {p: g for p, g in d.groupby("player_id")}
    est = []
    for _ in range(draws):
        pick = rng.choice(players, len(players), replace=True)
        parts = []
        for i, p in enumerate(pick):
            g = by_player[p].copy()
            g["player_season"] = g.player_season + f"_{i}"
            g["player_id"] = i
            parts.append(g)
        est.append(model3(pd.concat(parts, ignore_index=True))["estimate"])
    return float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


# ---------- second-chance flag (D-047) ----------

def _event_team(p: pd.DataFrame) -> pd.Series:
    """Team of each play-by-play event; team rebounds carry the team in personId."""
    return p.teamId.where(p.teamId != 0, p.personId)


def same_possession(sub: pd.DataFrame, p: pd.DataFrame) -> pd.Series:
    """For pairs `sub` of one season file and its play-by-play `p`: True when the next shot comes in
    the same possession after the previous (missed) shot. The shooter's team must have an offensive
    rebound in between, and no possession-ending event may happen in between (opponent shot or
    rebound, own turnover, own made field goal, end of period). Free throws are ignored (a known
    approximation)."""
    p = p.copy()
    p["game_id"] = p.gameId.astype(str).str.zfill(10)
    p["row"] = p.groupby("gameId").cumcount()
    p["etype"] = p.actionType.str.strip()
    p["team"] = _event_team(p)
    teams = sub[["game_id", "team_id"]].drop_duplicates()
    ev = p[["game_id", "row", "etype", "team"]].merge(teams, on="game_id")
    own = ev.team == ev.team_id
    ends = (((~own) & ev.team.ne(0) & ev.etype.isin(POSSESSION_ENDS_FOR_OPPONENT))
            | (own & ev.etype.isin(POSSESSION_ENDS_FOR_OWN)) | ev.etype.eq("period"))
    ev["cum_end"] = ends.groupby([ev.game_id, ev.team_id]).cumsum()
    ev["cum_oreb"] = (own & ev.etype.eq("Rebound")).groupby([ev.game_id, ev.team_id]).cumsum()
    idx = ev.set_index(["game_id", "team_id", "row"])[["cum_end", "cum_oreb"]]
    at_prev = idx.reindex(pd.MultiIndex.from_arrays(
        [sub.game_id, sub.team_id, sub.prev_pbp_row.astype(int)])).to_numpy()
    before_next = idx.reindex(pd.MultiIndex.from_arrays(
        [sub.game_id, sub.team_id, sub.pbp_row - 1])).to_numpy()
    same = ((sub.prev_made.to_numpy() == 0)
            & (before_next[:, 0] == at_prev[:, 0])      # nothing ended the possession
            & (before_next[:, 1] > at_prev[:, 1]))      # an offensive rebound in between
    return pd.Series(same, index=sub.index)


def second_chance(pairs: pd.DataFrame, seasons: list[tuple[str, str]]) -> pd.Series:
    """same_possession() for every season file (D-047)."""
    flags = []
    for season, season_type in seasons:
        sub = pairs[(pairs.season == season) & (pairs.season_type == season_type)]
        if not sub.empty:
            flags.append(same_possession(sub, load_pbp(season, season_type)))
    return pd.concat(flags).reindex(pairs.index, fill_value=False)


# ---------- pair rebuilds ----------

def rebuild(shots: pd.DataFrame, cfg: dict, ps: pd.DataFrame, cl: pd.DataFrame, half: str,
            **pair_rules) -> pd.DataFrame:
    """Pairs of one half under modified pair rules (e.g. max_gap_game_seconds=60)."""
    c = copy.deepcopy(cfg)
    c["pairs"].update(pair_rules)
    if c["pairs"]["max_gap_game_seconds"] is None:
        c["pairs"]["max_gap_game_seconds"] = np.inf
    return core.prepare(pairs_table(shots[shots.half == half], c, ps, cl), cfg, half)


def with_prev_xfg(d: pd.DataFrame, shots: pd.DataFrame, predict) -> pd.DataFrame:
    """Replace prev_xfg using another difficulty model."""
    s = shots[shots.in_analysis_population]
    new = pd.Series(predict(s).to_numpy(), index=pd.MultiIndex.from_frame(
        s[["game_id", "player_id", "pbp_row"]]))
    d = d.copy()
    d["prev_xfg"] = new.reindex(pd.MultiIndex.from_arrays(
        [d.game_id, d.player_id, d.prev_pbp_row.astype(int)])).to_numpy()
    return d


def heave_or_garbage(d: pd.DataFrame, shots: pd.DataFrame, cfg: dict) -> pd.Series:
    """Pairs where either shot is in the last seconds of a period, or in garbage time (D-022)."""
    r = cfg["robustness"]
    s = shots.set_index(["game_id", "player_id", "pbp_row"])[
        ["period", "clock_remaining_s", "score_margin_before"]]
    prev = s.reindex(pd.MultiIndex.from_arrays(
        [d.game_id, d.player_id, d.prev_pbp_row.astype(int)]))

    def flag(period, clock, margin):
        last_seconds = clock <= r["heave_seconds_remaining"]
        garbage = ((period == 4) & (clock <= r["garbage_time_minutes_left"] * 60)
                   & (margin.abs() >= r["garbage_time_margin"]))
        return (last_seconds | garbage).to_numpy()

    return pd.Series(flag(d.period, d.clock_remaining_s, d.score_margin_before)
                     | flag(prev.period, prev.clock_remaining_s, prev.score_margin_before),
                     index=d.index)


def future_placebo(d: pd.DataFrame) -> dict:
    """Replace "previous shot made" with "the shot after the next one was made", controlling for
    that later shot's distance, zone and xFG (D-048). The later shot is the next pair's next shot."""
    key = ["game_id", "player_id", "prev_pbp_row"]
    later = d[key + ["shot_made", "coord_distance_ft", "zone", "xfg"]].rename(columns={
        "prev_pbp_row": "pbp_row", "shot_made": "later_made",
        "coord_distance_ft": "later_distance", "zone": "later_zone", "xfg": "later_xfg"})
    later["pbp_row"] = later.pbp_row.astype(int)
    p = d.merge(later, on=["game_id", "player_id", "pbp_row"], how="inner")
    res = model3(p, treatment="later_made",
                 replace_prev_controls="later_distance + C(later_zone) + later_xfg + prev_made")
    return res


# ---------- the full loop ----------

def short_names(full: pd.Series) -> pd.Series:
    """First-name initial and last name ("L. Doncic"); the full name when two players would share
    the short form (e.g. twins with the same initial)."""
    first, _, last = full.str.partition(" ")[[0, 1, 2]].T.to_numpy()
    short = pd.Series([f"{f[0]}. {la}" if la else f for f, la in zip(first, last)], index=full.index)
    clash = short.duplicated(keep=False)
    return short.where(~clash, full)

def run_variations(f: pd.DataFrame, shots: pd.DataFrame, ps: pd.DataFrame, cl: pd.DataFrame,
                   cfg: dict, half: str, bootstrap_draws: int) -> pd.DataFrame:
    """Every Stage 7 variation for one half. `counted` follows D-046."""

    r = cfg["robustness"]
    other = "calibration" if half == "analysis" else "analysis"
    d = core.prepare(f, cfg, half)
    rows = []

    def add(family, variation, data, counted=True, **kw):
        res = model3(data, **kw)
        gaps = segment_gaps(data) if counted and family != "standard errors" else {}
        rows.append({"family": family, "variation": variation, "counted": counted, **res, **gaps})

    add("baseline", "Model 3, analysis rules", d, counted=False)
    for gap in r["pair_gap_variants_seconds"]:
        if gap == cfg["pairs"]["max_gap_game_seconds"]:
            continue
        add("pair gap", f"max gap {gap} s" if gap else "max gap: none",
            rebuild(shots, cfg, ps, cl, half, max_gap_game_seconds=gap))
    add("same period only", "pairs within one period",
        rebuild(shots, cfg, ps, cl, half, same_period_only=True))
    hg = heave_or_garbage(d, shots, cfg)
    add("heaves and garbage time", "drop last 3 s of any period and garbage time", d[~hg])
    for season in cfg["data"]["seasons"]:
        add("season by season", season, d[d.season == season])
    special = (d.season == "2020-21") | ((d.season == "2019-20") & (d.season_type == "Playoffs"))
    add("drop special seasons", "drop 2020-21 and the 2019-20 bubble playoffs", d[~special])
    n_shots = (shots[shots.in_analysis_population]
               .groupby(["player_id", "season", "season_type"]).size().rename("n_shots"))
    dn = d.join(n_shots, on=["player_id", "season", "season_type"])
    for n in r["min_fga_variants"]:
        add("minimum shots", f"player-seasons with {n}+ shots", dn[dn.n_shots >= n])
    cal_pop = shots[shots.in_analysis_population & (shots.half == "calibration")]
    boosted_cfg = copy.deepcopy(cfg)
    boosted_cfg["xfg"]["model"] = "boosted"
    add("difficulty model", "gradient-boosted xFG",
        with_prev_xfg(d, shots, xfg_fit(cal_pop, boosted_cfg)))
    swap_fit = xfg_fit(shots[shots.in_analysis_population & (shots.half == half)], cfg)
    d_other = core.prepare(f, cfg, other)
    add("swap halves", f"xFG fitted on the {half} half, tested on the {other} half",
        with_prev_xfg(d_other, shots, swap_fit))
    add("standard errors", "clustered by player and game", d,
        vcov={"CRV1": "player_id+game_id"})
    lo, hi = player_bootstrap(d, bootstrap_draws, cfg["random_seed"])
    base = model3(d)
    rows.append({"family": "standard errors", "variation": f"player bootstrap ({bootstrap_draws} draws)",
                 "counted": True, **base, "ci_low": lo, "ci_high": hi})
    top = d.player_id.value_counts().index[:10]
    names = short_names(d.drop_duplicates("player_id").set_index("player_id").player_name)
    infl = []
    for p in top:
        res = model3(d[d.player_id != p])
        infl.append({"family": "influence", "variation": f"drop {names[p]}", "counted": False, **res})
    worst = min(infl, key=lambda x: x["estimate"])
    rows.extend(infl)
    rows.append({**worst, "variation": f"worst case of the 10 drops ({worst['variation']})",
                 "counted": True})
    d["second_chance"] = second_chance(d, sorted(set(zip(d.season, d.season_type))))
    add("second chance", f"drop same-possession pairs after a miss ({int(d.second_chance.sum()):,})",
        d[~d.second_chance])

    # Not counted (D-046): a different quantity
    mm = d[d.last_two.isin(["made-made", "miss-miss"])].copy()
    mm["made_made"] = (mm.last_two == "made-made").astype(int)
    add("longer streaks (not counted)", "last two made vs last two missed", mm, counted=False,
        treatment="made_made")
    tp = d[d.three_plus_makes | (d.prev_made == 0)].copy()
    tp["three_plus"] = tp.three_plus_makes.astype(int)
    add("longer streaks (not counted)", "3+ makes in a row vs previous miss", tp, counted=False,
        treatment="three_plus")
    out = pd.DataFrame(rows)
    out.insert(0, "half", half)
    return out


def xfg_fit(fit_shots: pd.DataFrame, cfg: dict):
    from hothand import xfg as xfg_module
    return xfg_module.fit_final(fit_shots, cfg)


def cluster_variants(f: pd.DataFrame, shots: pd.DataFrame, cfg: dict, half: str) -> pd.DataFrame:
    """H3 joint test under other clusterings (not counted, D-046): k = 3 and 5, and k = 4 with
    other seeds. Clusters are refitted on the calibration half as in Stage 4."""
    from hothand import clusters as cl_module
    from hothand.pairs import ZONE_NAMES

    seg = cfg["segments"]
    cal = shots[(shots.half == "calibration") & shots.in_analysis_population
                & (shots.season_type == "Regular Season")]
    shares = cl_module.zone_shares(cal, seg["cluster_min_fga_season"])
    X = shares[ZONE_NAMES].to_numpy()
    d = core.prepare(f, cfg, half).drop(columns="cluster")
    rows = []
    for k, seed in [(3, cfg["random_seed"]), (5, cfg["random_seed"]),
                    (4, cfg["random_seed"] + 1), (4, cfg["random_seed"] + 2)]:
        lab = cl_module.fit(X, k, seed).labels_
        a = shares.reset_index()[["player_id", "season"]].assign(cluster=[f"c{x}" for x in lab])
        dk = d.merge(a, on=["player_id", "season"], how="left")
        names = sorted(dk.cluster.dropna().unique())
        res = segtests.joint_cluster_test(dk, names, names[-1])
        rows.append({"family": "cluster count (not counted)", "variation": f"k = {k}, seed {seed}",
                     "counted": False, "statistic": res["statistic"], "p_value": res["p_value"],
                     "n_pairs": res["n_pairs"], "n_players": res["n_players"]})
    return pd.DataFrame(rows)


def survival(table: pd.DataFrame, baseline: float, share: float) -> dict:
    """The automated check of D-045 on the counted rows (the verdict is the author's)."""
    c = table[table.counted]
    sign_ok = bool((c.estimate > 0).all())
    contains = (c.ci_low <= baseline) & (baseline <= c.ci_high)
    return {"counted_variations": len(c), "all_positive": sign_ok,
            "share_containing_baseline": float(contains.mean()),
            "required_share": share, "rule_met": sign_ok and contains.mean() >= share,
            "variations_not_containing": "; ".join(c.loc[~contains, "variation"])}
