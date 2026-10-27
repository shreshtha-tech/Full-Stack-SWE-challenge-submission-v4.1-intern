import functools
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import analysis, elexon

app = FastAPI(title="Wind Forecast Decision Support")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])


@functools.lru_cache(maxsize=1)
def raw():
    return elexon.fetch_forecasts(), elexon.fetch_actuals()


@functools.lru_cache(maxsize=16)
def dataset(cutoff_hour: float):
    fc, act = raw()
    return analysis.build(fc, act, cutoff_hour)


def _nan(v):
    return None if v != v else v


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/accuracy")
def accuracy(cutoff_hour: float = Query(9, ge=0, le=23.5)):
    df = dataset(cutoff_hour)
    return {"cutoff_hour": cutoff_hour, "overall": analysis.metrics(df), "daily": analysis.daily(df),
            "by_hour": analysis.by_hour(df), "histogram": analysis.histogram(df)}


@app.get("/api/decision")
def decision(date: str, cutoff_hour: float = Query(9, ge=0, le=23.5)):
    df = dataset(cutoff_hour)
    d = df[df["date"] == date]
    if d.empty:
        raise HTTPException(404, "No data for that delivery day")
    buf = analysis.risk_buffer(df, date)
    series = [{"t": r.startTime.isoformat(), "forecast": r.forecast, "actual": _nan(r.actual),
               "publishTime": r.publishTime.isoformat()} for r in d.itertuples()]
    return {
        "date": date, "cutoff_hour": cutoff_hour, "series": series, "buffer": buf,
        "summary": {
            "avg_mw": float(d["forecast"].mean()), "peak_mw": float(d["forecast"].max()),
            "min_mw": float(d["forecast"].min()), "energy_mwh": float(d["forecast"].sum() / 2),
            "latest_publish": d["publishTime"].max().isoformat(),
            "earliest_publish": d["publishTime"].min().isoformat()},
        "realised": analysis.metrics(d),
    }


@app.get("/api/days")
def days(cutoff_hour: float = Query(9)):
    return sorted(dataset(cutoff_hour)["date"].unique().tolist())
