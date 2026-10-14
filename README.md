# NBA Shot Selection and the Hot Hand

> Work in progress. The headline finding goes here once results are final.

**Question.** After a made or missed shot, how does an NBA player's next shot change in distance,
zone and difficulty compared with that same player's own baseline, and does that change differ by
experience, role, playstyle and season type?

Predictions were committed before any data was collected: see [docs/hypotheses.md](docs/hypotheses.md).
Every analytical choice is logged in [docs/decisions.md](docs/decisions.md).

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
