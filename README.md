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

```bash
make setup   # create .venv from the pinned lock file
make test    # run the unit tests
make all     # run the pipeline
```

## Repo structure

```
config.yaml      every tunable value (seasons, thresholds, seed)
data/            raw/ and interim/ are not committed; processed/ holds small result tables
docs/            decisions log, data dictionary, pre-registered hypotheses
notebooks/       numbered, one question per notebook
src/hothand/     reusable functions
tests/           unit tests (streak logic, definitions)
dashboard/       interactive app (Stage 8)
reports/figures/ exported charts
```

## Data

Shot data from NBA.com (via nba_api) and the shufinskiy/nba_data bulk dataset. Raw data is not
redistributed in this repository. Not affiliated with or endorsed by the NBA.

## License

MIT
