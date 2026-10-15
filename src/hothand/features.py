"""Stage 4 entry point: build the feature table every hypothesis test reads.

  shots -> flags (D-018, D-024, D-026) -> game split (D-010, D-025) -> xFG fitted on the
  calibration half (D-032) -> leave-one-out baseline (D-027) -> clusters fitted on the calibration
  half (D-033 to D-035) -> pairs and streak states (D-006, D-029) -> segment labels (D-008, D-009,
  D-030, D-031) -> data/processed/features.parquet

Nothing here looks at an outcome of a hypothesis test.
"""

import pandas as pd

from hothand import clusters, segments, xfg
from hothand.config import PROCESSED, load_config
from hothand.pairs import (
    GAME_SPLIT,
    ZONE_NAMES,
    assign_game_split,
    build_pairs,
    flag_shots,
    load_cleaned,
    load_game_split,
    player_baselines,
)

FEATURES = PROCESSED / "features.parquet"
SHOTS = PROCESSED / "shots_features.parquet"  # shot-level table, used by the permutation test
CLUSTERS = PROCESSED / "player_clusters.csv"


def game_split(shots: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """The saved split, checked against a fresh draw; written on the first run."""
    fresh = assign_game_split(shots, cfg)
    if GAME_SPLIT.exists():
        saved = load_game_split()
        if not saved.equals(fresh):
            raise RuntimeError("saved game split differs from the seeded draw; investigate first")
        return saved
    fresh.to_csv(GAME_SPLIT, index=False)
    return fresh


def fit_clusters(shots: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    seg = cfg["segments"]
    cal = shots[(shots.half == "calibration") & shots.in_analysis_population
                & (shots.season_type == "Regular Season")]
    shares = clusters.zone_shares(cal, seg["cluster_min_fga_season"])
    model = clusters.fit(shares[ZONE_NAMES].to_numpy(), seg["cluster_k"], cfg["random_seed"])
    centroids = pd.DataFrame(model.cluster_centers_, columns=ZONE_NAMES)
    names = clusters.name_clusters(centroids)
    out = shares.reset_index()
    out["cluster"] = pd.Series(model.labels_).map(names).to_numpy()
    return out


def pairs_table(shots: pd.DataFrame, cfg: dict, ps: pd.DataFrame, cl: pd.DataFrame) -> pd.DataFrame:
    """Pairs with outcomes and segment labels, from the shot table (with xFG, baseline and half).
    Stage 7 calls this with modified pair rules."""
    pairs = build_pairs(shots, cfg)
    dist = cfg["features"]["distance_column"]
    pairs["distance_vs_baseline_ft"] = pairs[dist] - pairs.baseline_distance_ft
    pairs["prev_surprise"] = pairs.prev_made - pairs.prev_xfg
    for z in ZONE_NAMES:
        pairs[f"next_is_{z}"] = (pairs.zone == z).astype("int8")
    pairs["next_is_three"] = (pairs.shot_value == 3).astype("int8")
    pairs = pairs.merge(ps[["player_id", "season", "season_type", "season_no", "experience_group",
                            "usage_tier", "all_star"]],
                        on=["player_id", "season", "season_type"], how="left", validate="many_to_one")
    return pairs.merge(cl[["player_id", "season", "cluster"]], on=["player_id", "season"],
                       how="left", validate="many_to_one")  # D-035: playoffs use the RS cluster


def build() -> pd.DataFrame:
    cfg = load_config()
    shots = flag_shots(load_cleaned(cfg), cfg)
    shots = shots.merge(game_split(shots, cfg), on="game_id", how="left", validate="many_to_one")

    pop = shots.in_analysis_population
    predict = xfg.fit_final(shots[pop & (shots.half == "calibration")], cfg)
    shots.loc[pop, "xfg"] = predict(shots[pop])
    shots = shots.join(player_baselines(shots, cfg))

    cl = fit_clusters(shots, cfg)
    cl.to_csv(CLUSTERS, index=False)

    shots["distance_vs_baseline_ft"] = (shots[cfg["features"]["distance_column"]]
                                        - shots.baseline_distance_ft)
    shots.to_parquet(SHOTS, index=False)

    ps = segments.build(shots, cfg)
    ps.to_csv(segments.PLAYER_SEASONS, index=False)
    pairs = pairs_table(shots, cfg, ps, cl)
    pairs.to_parquet(FEATURES, index=False)
    return pairs


if __name__ == "__main__":
    f = build()
    print(f"{len(f):,} pairs, {f.shape[1]} columns -> {FEATURES}")
