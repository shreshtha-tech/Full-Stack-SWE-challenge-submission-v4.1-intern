"""Pure analysis logic (no I/O) so it is unit-testable.

Key idea: a day-ahead buyer deciding for delivery day D at gate time G
(D-1, `cutoff_hour` London time) may only use forecasts with publishTime <= G.
For each half-hour we therefore take the *latest* forecast published before G.
"""
import numpy as np
import pandas as pd

LONDON = "Europe/London"
MONTH = ("2026-01-01", "2026-01-31")


def latest_forecast_at_cutoff(fc: pd.DataFrame, cutoff_hour: float) -> pd.DataFrame:
    d = fc.copy()
    local = d["startTime"].dt.tz_convert(LONDON)
    d["date"] = local.dt.strftime("%Y-%m-%d")
    cutoff = (pd.to_datetime(local.dt.strftime("%Y-%m-%d")) - pd.Timedelta(days=1)
              + pd.Timedelta(hours=cutoff_hour)).dt.tz_localize(LONDON, ambiguous="NaT", nonexistent="NaT")
    d = d[d["publishTime"] <= cutoff.dt.tz_convert("UTC")]
    d = d.sort_values("publishTime").groupby("startTime", as_index=False).last()
    d["date"] = d["startTime"].dt.tz_convert(LONDON).dt.strftime("%Y-%m-%d")
    return d[(d["date"] >= MONTH[0]) & (d["date"] <= MONTH[1])]


def build(fc: pd.DataFrame, act: pd.DataFrame, cutoff_hour: float) -> pd.DataFrame:
    sel = latest_forecast_at_cutoff(fc, cutoff_hour)
    df = sel.merge(act, on="startTime", how="left")
    df["error"] = df["forecast"] - df["actual"]          # +ve = over-forecast (shortfall risk)
    df["abs_error"] = df["error"].abs()
    df["hour"] = df["startTime"].dt.tz_convert(LONDON).dt.hour
    return df.sort_values("startTime").reset_index(drop=True)


def metrics(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["actual"])
    if d.empty:
        return {}
    e, a = d["error"], d["actual"]
    nz = a > 0
    return {
        "n": int(len(d)),
        "mae": float(e.abs().mean()),
        "rmse": float(np.sqrt((e ** 2).mean())),
        "bias": float(e.mean()),
        "mape": float((e[nz].abs() / a[nz]).mean() * 100) if nz.any() else None,
        "nmae_pct": float(e.abs().mean() / a.mean() * 100) if a.mean() else None,
        "p10_error": float(e.quantile(0.10)),
        "p90_error": float(e.quantile(0.90)),
        "p95_abs_error": float(e.abs().quantile(0.95)),
    }


def daily(df: pd.DataFrame) -> list:
    return [{"date": k, **metrics(g)} for k, g in df.groupby("date") if metrics(g)]


def by_hour(df: pd.DataFrame) -> list:
    return [{"hour": int(k), "mae": float(g["abs_error"].mean()), "bias": float(g["error"].mean())}
            for k, g in df.dropna(subset=["actual"]).groupby("hour")]


def histogram(df: pd.DataFrame, bins: int = 20) -> list:
    e = df["error"].dropna()
    if e.empty:
        return []
    c, edges = np.histogram(e, bins=bins)
    return [{"from": float(edges[i]), "to": float(edges[i + 1]), "count": int(c[i])} for i in range(bins)]


def risk_buffer(df: pd.DataFrame, date: str) -> dict:
    """Error distribution from days strictly BEFORE `date` (no look-ahead)."""
    prior = df[df["date"] < date].dropna(subset=["actual"])
    if len(prior) < 48:
        return {"n_days": 0, "p10": None, "p90": None}
    return {"n_days": int(prior["date"].nunique()),
            "p10": float(prior["error"].quantile(0.10)),
            "p90": float(prior["error"].quantile(0.90))}
