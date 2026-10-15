"""Stage 4: playstyle clusters (H3) from each player-season's shot-zone mix (playbook 4.8-4.9).

Fitted on calibration-half games only. Features are the five zone shares of a player-season's
analysis-population shots (no heaves, putbacks, tips or backcourt shots); shares are used as they
are (same units, they sum to 1), so standardising would overweight rare zones such as corner threes.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

from hothand.pairs import ZONE_NAMES


def zone_shares(shots: pd.DataFrame, min_fga: int) -> pd.DataFrame:
    """One row per player-season with at least `min_fga` shots: share of shots in each zone."""
    counts = pd.crosstab([shots.player_id, shots.season], shots.zone).reindex(
        columns=ZONE_NAMES, fill_value=0)
    n = counts.sum(axis=1)
    shares = counts.div(n, axis=0)
    shares["n_shots"] = n
    return shares[n >= min_fga]


def fit(X: np.ndarray, k: int, seed: int) -> KMeans:
    return KMeans(n_clusters=k, n_init=20, random_state=seed).fit(X)


def compare_k(X: np.ndarray, ks: list[int], seed: int, n_seeds: int, n_boot: int) -> pd.DataFrame:
    """Silhouette, seed stability and bootstrap stability (adjusted Rand index) for each k."""
    rng = np.random.default_rng(seed)
    rows = []
    for k in ks:
        ref = fit(X, k, seed)
        sil = silhouette_score(X, ref.labels_, sample_size=min(len(X), 5000), random_state=seed)
        seed_ari = [adjusted_rand_score(ref.labels_, fit(X, k, int(s)).labels_)
                    for s in rng.integers(0, 2**31, n_seeds)]
        boot_ari = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(X), len(X))
            m = KMeans(n_clusters=k, n_init=5, random_state=int(rng.integers(0, 2**31))).fit(X[idx])
            boot_ari.append(adjusted_rand_score(ref.labels_, m.predict(X)))
        sizes = np.bincount(ref.labels_)
        rows.append({"k": k, "silhouette": sil, "seed_ari_min": min(seed_ari),
                     "boot_ari_median": float(np.median(boot_ari)),
                     "boot_ari_p10": float(np.percentile(boot_ari, 10)),
                     "smallest_cluster": int(sizes.min()), "largest_cluster": int(sizes.max())})
    return pd.DataFrame(rows)


def profiles(shares: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """Average zone mix per cluster, in percent, with cluster sizes."""
    p = shares[ZONE_NAMES].groupby(labels).mean().mul(100).round(1)
    p["player_seasons"] = np.bincount(labels)
    return p


CLUSTER_NAMES = ["rim_bigs", "three_point_shooters", "mid_range_scorers", "rim_and_corner"]


def name_clusters(centroids: pd.DataFrame) -> dict[int, str]:
    """Name the k = 4 clusters from their average zone mix (D-033), independent of label order:
    most restricted-area shots -> rim bigs; most above-the-break threes -> three-point shooters;
    of the other two, more mid-range -> mid-range scorers, the other -> rim and corner."""
    if len(centroids) != 4:
        raise ValueError("cluster names are defined for k = 4 only")
    rim = centroids.restricted_area.idxmax()
    three = centroids.above_break_three.idxmax()
    rest = centroids.drop(index=[rim, three])
    mid = rest.mid_range.idxmax()
    other = rest.drop(index=mid).index[0]
    names = {rim: "rim_bigs", three: "three_point_shooters", mid: "mid_range_scorers",
             other: "rim_and_corner"}
    if len(set(names)) != 4:
        raise ValueError("cluster naming rule is ambiguous for these centroids")
    return names
