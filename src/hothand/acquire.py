"""Stage 2: download raw data and record where every file came from.

Nothing is cleaned here. Every file is written to data/raw/ as soon as it arrives and skipped on
re-runs, so an interrupted run resumes instead of restarting.

Routes (decision D-004):
  A. nba_api (NBA.com stats endpoints): player table and the cross-check season.
  B. shufinskiy/nba_data bulk files: shot details and play-by-play for every season.
"""

import csv
import hashlib
import io
import json
import logging
import tarfile
import time
import urllib.request
from datetime import date
from pathlib import Path

from hothand.config import RAW, load_config

BULK_INDEX_URL = "https://raw.githubusercontent.com/shufinskiy/nba_data/main/list_data.txt"
BULK_KINDS = {"shotdetail": "shots", "nbastatsv3": "pbp"}
SEASON_TYPE_CODE = {"Regular Season": "rs", "Playoffs": "po"}
MANIFEST = RAW / "manifest.csv"
MANIFEST_FIELDS = ["file", "kind", "season", "season_type", "route", "source",
                   "retrieved", "rows", "sha256"]

log = logging.getLogger("acquire")


# ---------- helpers ----------

def season_start_year(season: str) -> int:
    """'2024-25' -> 2024 (the bulk dataset labels a season by its start year)."""
    return int(season[:4])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_csv_rows(path: Path) -> int:
    """Count data rows (excluding header) in a CSV, respecting quoted newlines."""
    with open(path, newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def with_retries(fn, cfg: dict, what: str):
    """Call fn() with exponential backoff; log and re-raise after the last failure."""
    api = cfg["data"]["nba_api"]
    for attempt in range(1, api["max_retries"] + 1):
        try:
            return fn()
        except Exception as e:  # network errors come in many types
            wait = api["backoff_base_seconds"] * 2 ** (attempt - 1)
            log.warning("%s failed (attempt %d): %s; retrying in %ss", what, attempt, e, wait)
            if attempt == api["max_retries"]:
                log.error("%s gave up after %d attempts", what, attempt)
                raise
            time.sleep(wait)


def read_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    with open(MANIFEST, newline="") as f:
        return {row["file"]: row for row in csv.DictReader(f)}


def write_manifest(rows: dict[str, dict]) -> None:
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for key in sorted(rows):
            w.writerow(rows[key])


def record(manifest: dict, path: Path, **fields) -> None:
    """Add or refresh a manifest row for a file already on disk."""
    rel = str(path.relative_to(RAW))
    if rel in manifest and manifest[rel]["sha256"] == sha256(path):
        return  # unchanged, keep the original retrieval date
    rows = count_csv_rows(path) if path.suffix == ".csv" else fields.pop("rows", "")
    manifest[rel] = {"file": rel, "retrieved": date.today().isoformat(), "rows": rows,
                     "sha256": sha256(path), **fields}


# ---------- route B: bulk dataset ----------

def bulk_index() -> dict[str, str]:
    with urllib.request.urlopen(BULK_INDEX_URL, timeout=60) as r:
        text = r.read().decode()
    return dict(item.split("=", 1) for item in text.split() if "=" in item)


def fetch_bulk(cfg: dict, manifest: dict) -> None:
    out_dir = RAW / "bulk"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = None
    for season in cfg["data"]["seasons"]:
        for season_type in cfg["data"]["season_types"]:
            code = SEASON_TYPE_CODE[season_type]
            for prefix, kind in BULK_KINDS.items():
                name = f"{prefix}_{'po_' if code == 'po' else ''}{season_start_year(season)}"
                csv_path = out_dir / f"{name}.csv"
                if not csv_path.exists():
                    index = index or bulk_index()
                    if name not in index:
                        log.error("bulk file %s not listed; fill from nba_api", name)
                        continue
                    url = index[name]
                    log.info("downloading %s", url)
                    blob = with_retries(lambda: urllib.request.urlopen(url, timeout=300).read(),
                                        cfg, name)
                    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:xz") as tar:
                        member = tar.getmember(f"{name}.csv")
                        csv_path.write_bytes(tar.extractfile(member).read())
                record(manifest, csv_path, kind=kind, season=season, season_type=season_type,
                       route="B_bulk", source=f"shufinskiy/nba_data:{name}")


# ---------- route A: nba_api ----------

def _nba_api_json(endpoint_cls, cfg: dict, what: str, **params) -> dict:
    api = cfg["data"]["nba_api"]

    def call():
        ep = endpoint_cls(**params, timeout=api["timeout_seconds"])
        return ep.get_dict()

    result = with_retries(call, cfg, what)
    time.sleep(api["sleep_between_requests_seconds"])
    return result


def save_result_set(payload: dict, out: Path, result_name: str | None = None) -> None:
    """Write one result set of an nba_api response to CSV, and the full JSON alongside it."""
    out.with_suffix(".json").write_text(json.dumps(payload))
    sets = payload["resultSets"]
    rs = next(s for s in sets if result_name is None or s["name"] == result_name)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(rs["headers"])
        w.writerows(rs["rowSet"])


def fetch_players(cfg: dict, manifest: dict) -> None:
    """Player index per season: first season, draft year, position."""
    from nba_api.stats.endpoints import playerindex

    out_dir = RAW / "nba_api" / "players"
    out_dir.mkdir(parents=True, exist_ok=True)
    for season in cfg["data"]["seasons"]:
        out = out_dir / f"playerindex_{season}.csv"
        if not out.exists():
            payload = _nba_api_json(playerindex.PlayerIndex, cfg, f"playerindex {season}",
                                    season=season, historical_nullable="0")
            save_result_set(payload, out)
        record(manifest, out, kind="players", season=season, season_type="",
               route="A_nba_api", source="stats.nba.com/playerindex")


ROW_CAP = 102_400  # NBA.com silently truncates a shot-chart response at this many rows


def fetch_shots_nba_api(cfg: dict, manifest: dict, season: str, season_type: str) -> None:
    """All league field-goal attempts for one season and type (cross-check route).

    A league-wide request is truncated at ROW_CAP rows, so shots are pulled one team at a time
    (each part cached on disk) and concatenated.
    """
    from nba_api.stats.endpoints import shotchartdetail
    from nba_api.stats.static import teams

    code = SEASON_TYPE_CODE[season_type]
    out_dir = RAW / "nba_api" / "shots"
    parts_dir = out_dir / f"parts_{code}_{season}"
    parts_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"shotchart_{code}_{season}.csv"
    if not out.exists():
        parts = []
        for team in sorted(teams.get_teams(), key=lambda t: t["id"]):
            part = parts_dir / f"team_{team['id']}.csv"
            if not part.exists():
                payload = _nba_api_json(
                    shotchartdetail.ShotChartDetail, cfg,
                    f"shotchart {season} {season_type} {team['abbreviation']}",
                    team_id=team["id"], player_id=0, season_nullable=season,
                    season_type_all_star=season_type, context_measure_simple="FGA",
                )
                save_result_set(payload, part, "Shot_Chart_Detail")
            if count_csv_rows(part) >= ROW_CAP:
                raise RuntimeError(f"{part} hit the {ROW_CAP}-row cap; split it further")
            parts.append(part)
        header, body = None, []
        for part in parts:
            lines = part.read_text().splitlines(keepends=True)
            header = header or lines[0]
            body.extend(lines[1:])
        out.write_text(header + "".join(body))
    record(manifest, out, kind="shots", season=season, season_type=season_type,
           route="A_nba_api", source="stats.nba.com/shotchartdetail (per team)")


# ---------- entry point ----------

def run(cross_check_season: str = "2024-25") -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(RAW / "acquire.log")])
    cfg = load_config()
    manifest = read_manifest()
    try:
        fetch_bulk(cfg, manifest)
        fetch_players(cfg, manifest)
        for season_type in cfg["data"]["season_types"]:
            fetch_shots_nba_api(cfg, manifest, cross_check_season, season_type)
    finally:
        write_manifest(manifest)


if __name__ == "__main__":
    run()
