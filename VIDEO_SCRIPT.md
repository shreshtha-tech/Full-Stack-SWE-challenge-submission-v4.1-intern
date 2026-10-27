# Video script (≤10 min)

## Part 1 – Client pitch (≤5 min)
1. (0:00) Problem: you buy day-ahead; wind is weather-driven; you must decide a day early on forecasts.
2. (0:30) Decision view, pick a January day: "this is the forecast you'd have had at 09:00 — newest run timestamp shown, later runs excluded."
3. (1:30) Show P10–P90 band and shortfall buffer: "history says actual wind falls this far short 1 time in 10 — plan thermal cover accordingly."
4. (2:30) Accuracy tab: MAE/RMSE/bias for the month, worst days, error by hour, distribution.
5. (3:45) Change decision gate to 07:00/11:00 – show how later gates change accuracy.
6. (4:30) Value summary + next steps (more months, regional data, price integration, alerts).

## Part 2 – Tech review (≤5 min)
1. Architecture: React → nginx → FastAPI → Elexon (disk cache). Docker compose; Vercel deploy.
2. Core logic in analysis.py: latest-forecast-before-gate, no look-ahead; error sign convention; buffer uses prior days only.
3. Walk tests; explain why logic is pure/I-O free.
4. Trade-offs: in-memory cache, drop horizon>60h, assumed 09:00 gate, no auth. Next: persistence (DB/parquet), CI, typed API schema.
5. AI usage disclosure and what was manually verified.
