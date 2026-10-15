"""Stage 5: the core test (H0). After a make or a miss, does the next shot's distance, zone or
difficulty-adjusted make probability shift relative to the player's own baseline?

Three methods, all on one half of the games (`half`):
  1. Models 0-3 (playbook 5.3): regressions that add controls step by step, standard errors
     clustered by player. Outcomes are measured against the player's own leave-one-out baseline.
  2. Permutation test (playbook 5.4): the finite-sequence-bias-safe test. Shot order is shuffled
     within each player-game; the bias-corrected effect is observed minus mean shuffled.
  3. Mixed-effects model (playbook 5.5): random intercept per player, compared with Model 3.
Develop on the calibration half; the final run on the analysis half happens once (playbook 5.7).
"""

import warnings

import numpy as np
import pandas as pd
import pyfixest as pf

from hothand.pairs import ZONE_NAMES

warnings.filterwarnings("ignore", module="pyfixest")

ZONE_OUTCOMES = [f"rel_{z}" for z in ZONE_NAMES] + ["rel_three"]


def prepare(f: pd.DataFrame, cfg: dict, half: str) -> pd.DataFrame:
    """Pairs of one half with outcomes relative to the baseline and the model covariates."""
    d = f[f.half == half].copy()
    for z in ZONE_NAMES:
        d[f"rel_{z}"] = d[f"next_is_{z}"] - d[f"baseline_{z}"]
    d["rel_three"] = d.next_is_three - (d.baseline_corner_three + d.baseline_above_break_three)
    d["next_surprise"] = d.shot_made - d.xfg
    c = cfg["core"]
    d["period_cat"] = np.where(d.period <= 4, d.period.astype(str), "OT")
    d["margin_bin"] = pd.cut(d.score_margin_before, c["margin_bins"]).astype(str)
    d["shot_number_c"] = d.shot_number.clip(upper=c["shot_number_cap"])
    d["player_season"] = d.player_id.astype(str) + "_" + d.season + "_" + d.season_type
    return d


def formulas(outcome: str, treatment: str = "prev_made") -> dict[str, str]:
    """Models 0-3 (playbook 5.3); each adds one block of controls."""
    m1 = f"{treatment} + prev_coord_distance_ft + C(prev_zone) + prev_xfg"
    ctx = ("C(period_cat) + clock_remaining_s + C(margin_bin) + is_home + gap_s + shot_number_c")
    return {
        "Model 0": f"{outcome} ~ {treatment}",
        "Model 1": f"{outcome} ~ {m1}",
        "Model 2": f"{outcome} ~ {m1} + {ctx} + C(season) + C(season_type)",
        "Model 3": f"{outcome} ~ {m1} + {ctx} | player_season",  # FE absorb season and type
    }


def fit_models(d: pd.DataFrame, outcome: str, treatment: str = "prev_made") -> pd.DataFrame:
    rows = []
    for name, fml in formulas(outcome, treatment).items():
        m = pf.feols(fml, data=d, vcov={"CRV1": "player_id"})
        t = m.tidy().loc[treatment]
        rows.append({"outcome": outcome, "treatment": treatment, "model": name,
                     "estimate": t["Estimate"], "se": t["Std. Error"], "ci_low": t["2.5%"],
                     "ci_high": t["97.5%"], "p_value": t["Pr(>|t|)"], "n_pairs": m._N,
                     "n_players": d.player_id.nunique()})
    return pd.DataFrame(rows)


# ---------- permutation test ----------

def _slot_table(shots: pd.DataFrame, pairs: pd.DataFrame, within: list[str]) -> dict:
    """Arrays for fast shuffling: every analysis-population shot is a slot; a pair is a fixed pair
    of slots. Shuffling moves shot contents (result, xFG, distance, zone) between slots of the same
    player-game (or player-game-period); slot times, and so which slots form pairs, do not change,
    because putbacks, tips, heaves and backcourt shots never move."""
    key = ["game_id", "player_id", "pbp_row"]
    s = shots[shots.in_analysis_population].sort_values(key).reset_index(drop=True)
    s["slot"] = np.arange(len(s))
    slot_of = s.set_index(key).slot
    nxt = slot_of.reindex(pd.MultiIndex.from_frame(pairs[key])).to_numpy()
    prv = slot_of.reindex(pd.MultiIndex.from_arrays(
        [pairs.game_id, pairs.player_id, pairs.prev_pbp_row.astype(int)])).to_numpy()
    if np.isnan(nxt).any() or np.isnan(prv).any():
        raise ValueError("some pair shots are not analysis-population slots")
    group = s.groupby(within, sort=False).ngroup().to_numpy()
    return {"s": s, "next": nxt.astype(int), "prev": prv.astype(int), "group": group}


def _stats(made, content, nxt, prv) -> dict:
    """Effect after a make minus after a miss, for each outcome array in `content`."""
    pm = made[prv] == 1
    return {k: v[nxt][pm].mean() - v[nxt][~pm].mean() for k, v in content.items()}


def permutation_test(shots: pd.DataFrame, pairs: pd.DataFrame, n_perm: int, seed: int,
                     within: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Observed and shuffled 'after make minus after miss' differences for each outcome."""
    t = _slot_table(shots, pairs, within)
    s = t["s"]
    content = {"next_surprise": (s.shot_made - s.xfg).to_numpy(),
               "distance_vs_baseline_ft": s.distance_vs_baseline_ft.to_numpy(),
               "rel_three": (s.zone.isin(["corner_three", "above_break_three"]).astype(float)
                             - s.baseline_corner_three - s.baseline_above_break_three).to_numpy()}
    made = s.shot_made.to_numpy()
    observed = _stats(made, content, t["next"], t["prev"])

    rng = np.random.default_rng(seed)
    order_base = np.lexsort((np.arange(len(s)), t["group"]))
    draws = []
    for _ in range(n_perm):
        # a random permutation of slots within each group: sort by (group, random key)
        perm = np.lexsort((rng.random(len(s)), t["group"]))
        mapping = np.empty(len(s), dtype=int)
        mapping[order_base] = perm  # slot i now holds the shot that was in slot mapping[i]
        draws.append(_stats(made[mapping], {k: v[mapping] for k, v in content.items()},
                            t["next"], t["prev"]))
    null = pd.DataFrame(draws)
    rows = []
    for k, obs in observed.items():
        dist = null[k].to_numpy()
        rows.append({"outcome": k, "observed": obs, "null_mean": dist.mean(),
                     "bias_corrected": obs - dist.mean(), "null_sd": dist.std(ddof=1),
                     "p_two_sided": (np.sum(np.abs(dist - dist.mean()) >= abs(obs - dist.mean()))
                                     + 1) / (n_perm + 1),
                     "n_perm": n_perm, "within": "+".join(within)})
    return pd.DataFrame(rows), null


# ---------- mixed-effects second method ----------

def fit_mixed(d: pd.DataFrame, outcome: str) -> dict:
    """Random intercept per player with the Model 2 covariates (playbook 5.5)."""
    import statsmodels.formula.api as smf

    rhs = formulas(outcome)["Model 2"].split("~", 1)[1]
    m = smf.mixedlm(f"{outcome} ~ {rhs}", data=d, groups=d.player_id).fit(method="lbfgs")
    ci = m.conf_int().loc["prev_made"]
    return {"outcome": outcome, "model": "Mixed (random intercept per player)",
            "estimate": m.params["prev_made"], "se": m.bse["prev_made"], "ci_low": ci[0],
            "ci_high": ci[1], "p_value": m.pvalues["prev_made"], "n_pairs": int(m.nobs),
            "n_players": d.player_id.nunique(), "converged": bool(m.converged)}
