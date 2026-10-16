"""Stage 4: shot-difficulty model (xFG), the expected make probability of a shot from its location
and type only.

Rules (playbook 4.6, docs/ownership.md rule 5):
  - fitted on calibration-half games only; the analysis half is never used for fitting or tuning
  - features come from config.yaml (`xfg.features`); the previous shot's result is never a feature
  - a logistic regression and a gradient-boosted model are compared on calibration games held out
    from fitting; the author picks the model
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer

FORBIDDEN = {"shot_made", "prev_made", "prev_shot_made", "prev_make_run", "prev2_made",
             "last_two", "three_plus_makes"}
NUMERIC = ["shot_distance", "shot_angle"]


def design(shots: pd.DataFrame, distance_col: str) -> pd.DataFrame:
    """Model inputs: distance, angle from the basket (0 = straight on, 90 = baseline), zone,
    shot type and action type."""
    return pd.DataFrame({
        "shot_distance": shots[distance_col].to_numpy(),
        "shot_angle": np.degrees(np.arctan2(shots.loc_x.abs(), shots.loc_y.clip(lower=0))).to_numpy(),
        "shot_zone_basic": shots.shot_zone_basic.to_numpy(),
        "shot_type": shots.shot_type.to_numpy(),
        "action_type": shots.action_type.to_numpy(),
    }, index=shots.index)


def check_features(cfg: dict) -> list[str]:
    feats = cfg["xfg"]["features"]
    bad = FORBIDDEN.intersection(feats)
    if bad:
        raise ValueError(f"xFG features must not include shot results: {sorted(bad)}")
    return feats


def pool_rare_actions(X: pd.DataFrame, keep: set[str]) -> pd.DataFrame:
    X = X.copy()
    X["action_type"] = X.action_type.where(X.action_type.isin(keep), "Other")
    return X


def logistic_model(seed: int):
    pre = ColumnTransformer([
        ("dist", SplineTransformer(n_knots=8, degree=3), ["shot_distance"]),
        ("angle", SplineTransformer(n_knots=5, degree=3), ["shot_angle"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=1),
         ["shot_zone_basic", "shot_type", "action_type"]),
    ])
    return make_pipeline(pre, LogisticRegression(max_iter=2000, C=1.0, random_state=seed))


def boosted_model(seed: int):
    pre = ColumnTransformer([
        ("num", "passthrough", NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
         ["shot_zone_basic", "shot_type", "action_type"]),
    ])
    return make_pipeline(pre, HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31, early_stopping=True,
        validation_fraction=0.1, random_state=seed))


def evaluate(y: np.ndarray, p: np.ndarray) -> dict:
    return {"log_loss": log_loss(y, p), "brier": brier_score_loss(y, p), "auc": roc_auc_score(y, p),
            "mean_pred": float(p.mean()), "mean_obs": float(y.mean())}


def calibration_table(y: np.ndarray, p: np.ndarray, bins: int = 20) -> pd.DataFrame:
    q = pd.qcut(p, bins, labels=False, duplicates="drop")
    return (pd.DataFrame({"bin": q, "pred": p, "obs": y}).groupby("bin")
            .agg(pred=("pred", "mean"), obs=("obs", "mean"), n=("obs", "size")).reset_index())


def fit_final(cal_shots: pd.DataFrame, cfg: dict):
    """Fit the chosen model (D-032) on all calibration-half analysis-population shots.

    Returns a function that predicts xFG for any shots.
    """
    check_features(cfg)
    dist = cfg["features"]["distance_column"]
    counts = cal_shots.action_type.value_counts()
    keep = set(counts[counts >= cfg["xfg"]["min_action_count"]].index)
    make = {"logistic": logistic_model, "boosted": boosted_model}[cfg["xfg"]["model"]]
    model = make(cfg["random_seed"]).fit(pool_rare_actions(design(cal_shots, dist), keep),
                                         cal_shots.shot_made)

    def predict(shots: pd.DataFrame) -> pd.Series:
        X = pool_rare_actions(design(shots, dist), keep)
        return pd.Series(model.predict_proba(X)[:, 1], index=shots.index, name="xfg")

    return predict
