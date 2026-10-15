"""Stage 6: does the H0 shift differ between groups? (H1 to H4, playbook 6.1-6.8)

Every test reuses Model 3 from Stage 5 (D-036, D-037): distance vs the player's own baseline, the
previous shot's location and difficulty, game context, player-season fixed effects, standard errors
clustered by player. A group's difference in the shift is the coefficient on
"previous shot made x group" (D-041); the group's own level is absorbed by the fixed effects,
because every group here is constant within a player-season.
"""

import numpy as np
import pandas as pd
import pyfixest as pf
from statsmodels.stats.multitest import multipletests

from hothand.core import formulas

OUTCOME = "distance_vs_baseline_ft"


def _rhs(extra: str = "") -> str:
    """Model 3's right-hand side with optional extra terms before the fixed effects."""
    rhs = formulas(OUTCOME)["Model 3"].split("~", 1)[1]
    covariates, fe = rhs.split("|")
    return f"{covariates.strip()}{' + ' + extra if extra else ''} | {fe.strip()}"


def _coef(m, name: str) -> dict:
    t = m.tidy().loc[name]
    return {"estimate": t["Estimate"], "se": t["Std. Error"], "ci_low": t["2.5%"],
            "ci_high": t["97.5%"], "p_value": t["Pr(>|t|)"]}


def group_shift(d: pd.DataFrame, cfg: dict, label: str, mask: pd.Series) -> dict:
    """Model 3's make-minus-miss shift inside one group (for display), with the minimum-cell rule."""
    g = d[mask]
    inf = cfg["inference"]
    row = {"group": label, "n_pairs": len(g), "n_players": g.player_id.nunique()}
    if row["n_pairs"] < inf["min_pairs_per_cell"] or row["n_players"] < inf["min_players_per_cell"]:
        return {**row, "status": "too few shots to estimate"}
    m = pf.feols(f"{OUTCOME} ~ {_rhs()}", data=g, vcov={"CRV1": "player_id"})
    after = g.groupby("prev_made")[OUTCOME].mean()
    return {**row, "status": "estimated", **_coef(m, "prev_made"),
            "after_miss_vs_baseline_ft": after.get(0, np.nan),
            "after_make_vs_baseline_ft": after.get(1, np.nan)}


def interaction_test(d: pd.DataFrame, indicator: pd.Series, label: str) -> dict:
    """Difference in the shift between the indicator group (1) and the reference group (0), on
    the rows where the indicator is defined."""
    g = d[indicator.notna()].copy()
    g["grp"] = indicator[indicator.notna()].astype(int)
    g["made_x_grp"] = g.prev_made * g.grp
    m = pf.feols(f"{OUTCOME} ~ {_rhs('made_x_grp')}", data=g, vcov={"CRV1": "player_id"})
    return {"test": label, "n_pairs": len(g), "n_players": g.player_id.nunique(),
            **_coef(m, "made_x_grp")}


def joint_cluster_test(d: pd.DataFrame, clusters: list[str], reference: str) -> dict:
    """H3: one Wald test that the shift is equal in every cluster (playbook 6.2)."""
    g = d[d.cluster.notna()].copy()
    terms = []
    for c in clusters:
        if c == reference:
            continue
        g[f"made_x_{c}"] = g.prev_made * (g.cluster == c)
        terms.append(f"made_x_{c}")
    m = pf.feols(f"{OUTCOME} ~ {_rhs(' + '.join(terms))}", data=g, vcov={"CRV1": "player_id"})
    names = list(m.coef().index)
    R = np.zeros((len(terms), len(names)))
    for i, t in enumerate(terms):
        R[i, names.index(t)] = 1
    w = m.wald_test(R=R)
    pairwise = {t: _coef(m, t) for t in terms}
    return {"test": f"H3 joint: shift equal across clusters (reference {reference})",
            "n_pairs": len(g), "n_players": g.player_id.nunique(),
            "statistic": float(w["statistic"]), "p_value": float(w["pvalue"]),
            "pairwise_vs_reference": pairwise}


def both_contexts(d: pd.DataFrame) -> pd.Series:
    """Player-seasons with pairs in both the regular season and the playoffs (D-044)."""
    types = d.groupby(["player_id", "season"]).season_type.nunique()
    keep = types[types == 2].index
    return d.set_index(["player_id", "season"]).index.isin(keep)


def holm(pvalues: dict[str, float], alpha: float) -> pd.DataFrame:
    names = list(pvalues)
    reject, adj, _, _ = multipletests([pvalues[n] for n in names], alpha=alpha, method="holm")
    return pd.DataFrame({"hypothesis": names, "p_unadjusted": [pvalues[n] for n in names],
                         "p_holm": adj, "reject_at_alpha": reject})


def joint_secondary(d: pd.DataFrame) -> pd.DataFrame:
    """Rookie, usage and cluster interactions in one model (playbook 6.5, secondary)."""
    g = d.copy()
    terms = {"made_x_rookie": (g.experience_group == "rookie"),
             "made_x_veteran": (g.experience_group == "veteran"),
             "made_x_usage_low": (g.usage_tier == "low"),
             "made_x_usage_high": (g.usage_tier == "high")}
    for c in ["rim_bigs", "mid_range_scorers", "rim_and_corner"]:
        terms[f"made_x_{c}"] = g.cluster == c
    for t, mask in terms.items():
        g[t] = g.prev_made * mask.fillna(False).astype(int)
    m = pf.feols(f"{OUTCOME} ~ {_rhs(' + '.join(terms))}", data=g, vcov={"CRV1": "player_id"})
    return pd.DataFrame([{"term": t, **_coef(m, t)} for t in terms])


def zone_moves(d: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Mean change in each zone's share vs the player's baseline after a make and after a miss,
    per group (for the cluster heat map, playbook 6.8)."""
    cols = [c for c in d.columns if c.startswith("rel_") and c != "rel_three"]
    out = d.groupby([group_col, "prev_made"])[cols].mean().mul(100)
    out.index = out.index.set_levels(["after a miss", "after a make"], level=1)
    return out
