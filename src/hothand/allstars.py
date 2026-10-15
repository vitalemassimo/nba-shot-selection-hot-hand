"""Compile All-Star selections per season from Wikipedia's All-Star Game pages.

Source: the "Rosters" section of https://en.wikipedia.org/wiki/<YEAR>_NBA_All-Star_Game (CC BY-SA).
Every selected player counts, including injured selections and their replacements.
The All-Star game of season 2024-25 is played in 2025, so season "YYYY-YY" maps to page YYYY+1.
Output: data/reference/allstars.csv (small, committed, with the page revision id for provenance).
"""

import io
import json
import re
import time
import urllib.error
import urllib.request

import pandas as pd

from hothand.config import DATA, load_config

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "nba-shot-selection-hot-hand/0.1 (student research project)"}
OUT = DATA / "reference" / "allstars.csv"


def _get_json(params: str, retries: int = 5) -> dict:
    req = urllib.request.Request(f"{API}?{params}&format=json", headers=HEADERS)
    for attempt in range(retries):
        time.sleep(2 + 10 * attempt)  # be polite; back off harder after a 429
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == retries - 1:
                raise


def clean_name(name: str) -> str:
    """Strip footnote and injury markers, e.g. 'Stephen CurryINJ2' -> 'Stephen Curry'."""
    name = re.sub(r"\[.*?\]", "", str(name))
    # Footnote markers glued to the name (INJ1, REP1INJ3, COVID2) or after a space with a number
    # (" REP3"). A spaced marker needs a digit so suffixes like "II" or "III" survive.
    name = re.sub(r"(?:(?<=[a-zà-ÿ.'])(?:[A-Z]{2,}\d*)+|\s(?:[A-Z]{2,}\d+)+)$", "", name)
    return name.replace("*", "").replace("^", "").strip()


def season_rosters(season: str) -> pd.DataFrame:
    page = f"{int(season[:4]) + 1}_NBA_All-Star_Game"
    sections = _get_json(f"action=parse&page={page}&prop=sections")["parse"]["sections"]
    idx = next(s["index"] for s in sections if s["line"].startswith("Roster"))
    parsed = _get_json(f"action=parse&page={page}&prop=text|revid&section={idx}")["parse"]
    tables = pd.read_html(io.StringIO(parsed["text"]["*"]))
    rows = []
    for t in tables:
        if not isinstance(t.columns, pd.MultiIndex):
            continue  # the outer layout table
        t.columns = [c[0] for c in t.columns]
        for _, r in t.iterrows():
            player = clean_name(r["Player"])
            if not player or player in ("Starters", "Reserves") or player.startswith(
                    ("Starters", "Reserves", "Head coach")):
                continue
            rows.append({"season": season, "player_name": player, "team": clean_name(r["Team"]),
                         "source_page": page, "source_revid": parsed["revid"]})
    return pd.DataFrame(rows).drop_duplicates(["season", "player_name"])


def run() -> pd.DataFrame:
    seasons = load_config()["data"]["seasons"]
    df = pd.concat([season_rosters(s) for s in seasons], ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    return df


if __name__ == "__main__":
    out = run()
    print(out.groupby("season").size().to_string())
