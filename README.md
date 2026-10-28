# Wind Forecast Decision Support (GB day-ahead)

Web app for a UK utility's day-ahead desk: shows the **wind forecast that was actually available at the decision gate**
and **quantifies how wrong such forecasts have been**, for purchase decisions in **January 2026**.
Data: Elexon BMRS only — `FUELHH` (actuals, `fuelType=WIND`) and `WINDFOR` (forecasts).

> **AI disclosure:** this project was built with AI assistance (Claude by Anthropic) for code generation and scaffolding. Design decisions and logic should be reviewed by the author.

**Live app:** https://full-stack-swe-challenge-submission.vercel.app

## Key design decision
For delivery day D the buyer decides at gate G (default 09:00 UK on D-1, configurable in the UI). For every half-hour of D we take the
**latest WINDFOR run with `publishTime <= G`** — never later runs (no look-ahead). Accuracy is computed on exactly those forecasts vs FUELHH actuals,
so it measures what the desk really faced, not an idealised short-horizon forecast.
Error = forecast − actual (positive = over-forecast → utility short → must buy more). The decision view's P10–P90 band and "shortfall buffer"
use only error history from days *before* the selected day.

## Structure
```
backend/analysis.py     pure logic: forecast selection at gate, metrics (MAE, RMSE, bias, MAPE, quantiles), buffer
backend/elexon.py       Elexon API client (chunked, cached on disk)
backend/main.py         FastAPI: /api/days, /api/decision, /api/accuracy, /api/health
backend/tests/          unit tests (gate/no-look-ahead, error sign, buffer)
frontend/src/App.jsx    React (Vite + Recharts): Decision view, Accuracy view
docker-compose.yml      backend + nginx-served frontend
api/index.py, vercel.json   Vercel deployment (static frontend + FastAPI function)
```

## Run
```
docker compose up --build        # http://localhost:3000   (first request downloads Elexon data, ~1 min)
```
Without Docker: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload` and `cd frontend && npm i && npm run dev`.
Tests: `cd backend && pytest`.

## Assumptions / limitations
- Gate time default 09:00 UK is an assumption (GB day-ahead auctions close roughly mid-morning); change it in the UI.
- Elexon query parameters were written from the API docs; verify against live responses on first run.
- Forecast rows with horizon > 60h are dropped (irrelevant to day-ahead). Metrics are national-level, wind only.
- Vercel serverless has a time limit; first cold load may be slow. If it times out, pre-bake the cached JSON into the repo.
