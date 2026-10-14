"""Read raw files for one season and season type. Never writes to data/raw/."""

import pandas as pd

from hothand.acquire import SEASON_TYPE_CODE, season_start_year
from hothand.config import RAW

SHOT_KEY = ["GAME_ID", "GAME_EVENT_ID", "PLAYER_ID"]


def _bulk_name(prefix: str, season: str, season_type: str) -> str:
    po = "po_" if season_type == "Playoffs" else ""
    return f"{prefix}_{po}{season_start_year(season)}.csv"


def load_shots(season: str, season_type: str) -> pd.DataFrame:
    return pd.read_csv(RAW / "bulk" / _bulk_name("shotdetail", season, season_type))


def load_pbp(season: str, season_type: str) -> pd.DataFrame:
    return pd.read_csv(RAW / "bulk" / _bulk_name("nbastatsv3", season, season_type))


def load_player_index() -> pd.DataFrame:
    """All PlayerIndex season files stacked; one row per player per season file."""
    files = sorted((RAW / "nba_api" / "players").glob("playerindex_*.csv"))
    return pd.concat([pd.read_csv(f).assign(index_season=f.stem.split("_")[1]) for f in files],
                     ignore_index=True)


def load_player_totals(season: str, season_type: str) -> pd.DataFrame:
    code = SEASON_TYPE_CODE[season_type]
    return pd.read_csv(RAW / "nba_api" / "totals" / f"playertotals_{code}_{season}.csv")


def parse_iso_clock(clock: pd.Series) -> pd.Series:
    """'PT11M43.50S' -> 703.5 seconds remaining in the period."""
    parts = clock.str.extract(r"PT(\d+)M([\d.]+)S")
    return parts[0].astype(float) * 60 + parts[1].astype(float)


def period_length(period: pd.Series) -> pd.Series:
    """Regulation quarters are 12 minutes, overtimes 5."""
    return period.le(4).map({True: 720.0, False: 300.0})


def game_seconds_elapsed(period: pd.Series, seconds_remaining: pd.Series) -> pd.Series:
    """Seconds of game clock elapsed since tip-off, continuous across periods and overtimes."""
    before = ((period - 1) * 720).where(period <= 4, 4 * 720 + (period - 5) * 300)
    return before + period_length(period) - seconds_remaining
