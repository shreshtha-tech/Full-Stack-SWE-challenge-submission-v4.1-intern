import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
import analysis


def mk(rows):
    return pd.DataFrame(rows, columns=["startTime", "publishTime", "forecast"]).astype(
        {"startTime": "datetime64[ns, UTC]", "publishTime": "datetime64[ns, UTC]"})


def test_picks_latest_forecast_before_cutoff_only():
    t = pd.Timestamp("2026-01-10 12:00", tz="UTC")
    fc = mk([(t, pd.Timestamp("2026-01-08 12:00", tz="UTC"), 100),
             (t, pd.Timestamp("2026-01-09 08:00", tz="UTC"), 200),   # latest before 09:00
             (t, pd.Timestamp("2026-01-09 10:00", tz="UTC"), 999)])  # after gate -> must be ignored
    out = analysis.latest_forecast_at_cutoff(fc, 9)
    assert out["forecast"].tolist() == [200]


def test_error_sign_and_metrics():
    t = pd.Timestamp("2026-01-10 12:00", tz="UTC")
    fc = mk([(t, pd.Timestamp("2026-01-09 08:00", tz="UTC"), 150)])
    act = pd.DataFrame({"startTime": [t], "actual": [100.0]})
    df = analysis.build(fc, act, 9)
    assert df["error"].iloc[0] == 50           # over-forecast => positive
    m = analysis.metrics(df)
    assert m["mae"] == 50 and m["bias"] == 50 and m["mape"] == 50


def test_buffer_has_no_lookahead():
    rows, arows = [], []
    for day in range(1, 6):
        for h in range(24):
            t = pd.Timestamp(f"2026-01-{day:02d} {h:02d}:00", tz="UTC")
            rows.append((t, t - pd.Timedelta(hours=20 + 1), 100 + day))
            arows.append((t, 100.0))
    df = analysis.build(mk(rows), pd.DataFrame(arows, columns=["startTime", "actual"]), 9)
    assert analysis.risk_buffer(df, "2026-01-01")["n_days"] == 0
