"""Thin client for the Elexon BMRS (Insights) API with on-disk caching."""
import json, os, hashlib
from datetime import datetime, timedelta, timezone
import httpx
import pandas as pd

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
CACHE_DIR = os.environ.get("CACHE_DIR", "/tmp/elexon_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# January 2026 delivery days -> forecasts published from 30 Dec 2025 onwards
START = datetime(2025, 12, 30, tzinfo=timezone.utc)
END = datetime(2026, 2, 1, tzinfo=timezone.utc)


def _get(path: str, params: dict) -> list:
    key = hashlib.md5((path + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    f = os.path.join(CACHE_DIR, key + ".json")
    if os.path.exists(f):
        return json.load(open(f))
    r = httpx.get(f"{BASE}/{path}", params={**params, "format": "json"}, timeout=120)
    r.raise_for_status()
    data = r.json()
    data = data["data"] if isinstance(data, dict) and "data" in data else data
    json.dump(data, open(f, "w"))
    return data


def fetch_actuals() -> pd.DataFrame:
    """FUELHH, WIND only. Returns startTime (UTC), actual (MW)."""
    rows, d = [], START
    while d < END:
        nxt = min(d + timedelta(days=7), END)
        rows += _get("FUELHH/stream", {
            "settlementDateFrom": d.date().isoformat(),
            "settlementDateTo": nxt.date().isoformat(),
            "fuelType": "WIND"})
        d = nxt
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return (df.rename(columns={"generation": "actual"})[["startTime", "actual"]]
              .drop_duplicates("startTime"))


def fetch_forecasts(max_horizon_h: int = 60) -> pd.DataFrame:
    """WINDFOR. Returns startTime, publishTime (UTC), forecast (MW).
    Rows with horizon > max_horizon_h are dropped (irrelevant to day-ahead)."""
    rows, d = [], START
    while d < END:
        nxt = min(d + timedelta(days=2), END)
        rows += _get("WINDFOR/stream", {
            "publishDateTimeFrom": d.strftime("%Y-%m-%dT%H:%MZ"),
            "publishDateTimeTo": nxt.strftime("%Y-%m-%dT%H:%MZ")})
        d = nxt
    df = pd.DataFrame(rows)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.rename(columns={"generation": "forecast"})[["startTime", "publishTime", "forecast"]]
    h = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    return df[(h >= 0) & (h <= max_horizon_h)].reset_index(drop=True)
