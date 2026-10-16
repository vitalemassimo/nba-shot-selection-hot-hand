# NBA Shot Selection and the Hot Hand

> Work in progress. The headline finding goes here once results are final.

**Question.** After a made or missed shot, how does an NBA player's next shot change in distance,
zone and difficulty compared with that same player's own baseline, and does that change differ by
experience, role, playstyle and season type?

Predictions were committed before any data was collected: see [docs/hypotheses.md](docs/hypotheses.md).
Every analytical choice is logged in [docs/decisions.md](docs/decisions.md).

## Robustness

Before the checks were run, the result was defined as robust if it stayed positive in every variation and stayed close to the original 1.50 ft size in at least 80% of them. By that rule it was met: the effect was positive in 24 of 24 variations and close to 1.50 ft in 20 of 24. It held when each season was analysed on its own, when special seasons, heaves and garbage time were removed, and when minimum-shot limits were applied. It also held with a different difficulty model, with the two halves of the data swapped, with alternative standard errors, with influential players dropped, and with second-chance possessions removed. The four variations that fell outside the range all changed how close in time two shots had to be to count as consecutive. The shift was larger when shots were close together (about 2.0 ft within 60 seconds) and smaller with no time limit (about 1.2 ft), but it was always positive. A placebo test, which should give zero, returned a small but nonzero +0.07 ft, so some leftover confounding cannot be ruled out and the size of the effect should be read with that limitation in mind. In short, the result is robust in direction, but its size depends on how consecutive shots are defined.

Full table: [data/processed/results_robustness.csv](data/processed/results_robustness.csv) ·
specification curve: [reports/figures/stage7_specification_curve.png](reports/figures/stage7_specification_curve.png)

## Reproduce it

Requires Python 3.10+ (developed on 3.13, macOS) and about 3 GB of disk. Run from your own computer:
NBA.com refuses many cloud IP addresses.

```bash
git clone https://github.com/vitalemassimo/nba-shot-selection-hot-hand.git
cd nba-shot-selection-hot-hand
make setup   # create .venv from the pinned lock file (~1 min)
make test    # 38 unit tests (~1 min)
make all     # download raw data, then run Stages 2-8 (~75 min on a laptop)
make dashboard-check   # every number the dashboard shows matches the results tables
make dashboard         # open the dashboard locally
```

`make all` regenerates every table in `data/processed/`, every figure in `reports/figures/` and the
executed notebooks. A cold clone on 2026-10-16 reproduced every results table byte for byte
(decision D-059). Re-downloads are checked against `data/raw/manifest.csv` (row counts and SHA-256
hashes); NBA.com's live endpoints can drift slightly over time.

## Repo structure

```
config.yaml        every tunable value (seasons, thresholds, seed)
data/raw/          downloaded files (not committed); manifest.csv is committed
data/interim/      cleaned shot tables (not committed)
data/processed/    results tables, game split, segment labels, dashboard tables (committed)
docs/              hypotheses (pre-registered), decisions log, data dictionary, ownership
notebooks/         02_audit, 03_features, 04_core_test, 05_segments, 06_robustness
src/hothand/       pipeline code (acquire, clean, pairs, xfg, clusters, core, segtests, robustness)
tests/             unit tests (pair and streak logic, permutation test, possession flag, ...)
dashboard/         Streamlit app, its wording (text.yaml) and the displayed-vs-CSV check
reports/figures/   charts used in the README and the dashboard
```

## Data

Shot data from NBA.com (via nba_api) and the shufinskiy/nba_data bulk dataset. Raw data is not
redistributed in this repository. Not affiliated with or endorsed by the NBA.

## References

- Gilovich, T., Vallone, R., and Tversky, A. (1985). The hot hand in basketball: On the misperception
  of random sequences. *Cognitive Psychology*, 17(3), 295-314.
- Miller, J. B., and Sanjurjo, A. (2018). Surprised by the hot hand fallacy? A truth in the law of
  small numbers. *Econometrica*, 86(6), 2019-2047.
- Bocskocsky, A., Ezekowitz, J., and Stein, C. (2014). The hot hand: A new approach to an old
  "fallacy". MIT Sloan Sports Analytics Conference.

## License

MIT
