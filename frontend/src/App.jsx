import { useEffect, useState } from "react";
import { ResponsiveContainer, ComposedChart, Line, Area, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

const API = import.meta.env.VITE_API_URL || "";
const get = (p) => fetch(API + p).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
const f0 = (v) => (v == null ? "–" : Math.round(v).toLocaleString());
const KPI = ({ l, v, u = "MW" }) => <div className="kpi"><span>{l}</span><b>{v}</b><span>{u}</span></div>;
const time = (iso) => new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" });
const stamp = (iso) => new Date(iso).toLocaleString("en-GB", { timeZone: "Europe/London", dateStyle: "medium", timeStyle: "short" });

function Decision({ cutoff, days }) {
  const [date, setDate] = useState(days[0]);
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { setD(null); get(`/api/decision?date=${date}&cutoff_hour=${cutoff}`).then(setD).catch((e) => setErr(String(e))); }, [date, cutoff]);
  if (err) return <div className="card">Error: {err}</div>;
  const b = d?.buffer;
  const series = d?.series.map((s) => ({
    ...s, time: time(s.t),
    band: b?.p90 != null ? [s.forecast - b.p90, s.forecast - b.p10] : null,
  }));
  return (<>
    <div className="card controls">
      <label>Delivery day <select value={date} onChange={(e) => setDate(e.target.value)}>{days.map((x) => <option key={x}>{x}</option>)}</select></label>
    </div>
    {!d ? <div className="card">Loading… (first load fetches Elexon data)</div> : (<>
      <div className="card">
        <div className="kpis">
          <KPI l="Avg forecast wind" v={f0(d.summary.avg_mw)} /><KPI l="Peak" v={f0(d.summary.peak_mw)} />
          <KPI l="Minimum" v={f0(d.summary.min_mw)} /><KPI l="Total energy" v={f0(d.summary.energy_mwh)} u="MWh" />
          {b?.p90 != null && <KPI l="Suggested shortfall buffer (P90)" v={f0(Math.max(b.p90, 0))} />}
        </div>
        <div className="note">Forecast used = latest WINDFOR run published before {String(cutoff).padStart(2, "0")}:00 UK on the day before delivery.
          Newest run used: <b>{stamp(d.summary.latest_publish)}</b>. Anything published later is excluded, as it would not be available when bidding.</div>
        {b?.p90 == null && <div className="note warn">Not enough prior-day history to estimate an error band for this day.</div>}
        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={series}><CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" interval={5} /><YAxis unit=" MW" width={80} /><Tooltip /><Legend />
            <Area dataKey="band" name={`Expected actual range (P10–P90, ${b?.n_days ?? 0} prior days)`} fill="#0b7bb5" stroke="none" fillOpacity={0.18} />
            <Line dataKey="forecast" name="Forecast at decision time" stroke="#0b7bb5" dot={false} strokeWidth={2} />
            <Line dataKey="actual" name="Actual (outturn)" stroke="#e05a00" dot={false} strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="card"><h3>How did this day turn out?</h3>
        <div className="kpis"><KPI l="MAE" v={f0(d.realised.mae)} /><KPI l="RMSE" v={f0(d.realised.rmse)} />
          <KPI l="Bias (fcst − actual)" v={f0(d.realised.bias)} /><KPI l="MAPE" v={d.realised.mape?.toFixed(1)} u="%" /></div></div>
    </>)}
  </>);
}

function Accuracy({ cutoff }) {
  const [a, setA] = useState(null);
  useEffect(() => { get(`/api/accuracy?cutoff_hour=${cutoff}`).then(setA); }, [cutoff]);
  if (!a) return <div className="card">Loading…</div>;
  const o = a.overall;
  return (<>
    <div className="card"><h3>January 2026 — day-ahead forecast accuracy</h3>
      <div className="kpis"><KPI l="MAE" v={f0(o.mae)} /><KPI l="RMSE" v={f0(o.rmse)} /><KPI l="Bias (+ = over-forecast)" v={f0(o.bias)} />
        <KPI l="MAPE" v={o.mape?.toFixed(1)} u="%" /><KPI l="MAE / mean actual" v={o.nmae_pct?.toFixed(1)} u="%" />
        <KPI l="P90 over-forecast" v={f0(o.p90_error)} /><KPI l="P95 |error|" v={f0(o.p95_abs_error)} /></div>
      <div className="note">Positive error = forecast above actual → the utility would be short and must buy the gap. P90 over-forecast is a practical buffer for procurement.</div></div>
    <div className="card"><h3>Daily MAE & bias</h3><ResponsiveContainer width="100%" height={260}>
      <BarChart data={a.daily}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" tickFormatter={(x) => x.slice(8)} /><YAxis width={70} /><Tooltip /><Legend />
        <Bar dataKey="mae" name="MAE (MW)" fill="#0b7bb5" /><Bar dataKey="bias" name="Bias (MW)" fill="#e05a00" /></BarChart></ResponsiveContainer></div>
    <div className="card"><h3>Error by hour of day</h3><ResponsiveContainer width="100%" height={240}>
      <BarChart data={a.by_hour}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="hour" /><YAxis width={70} /><Tooltip /><Legend />
        <Bar dataKey="mae" name="MAE (MW)" fill="#0b7bb5" /><Bar dataKey="bias" name="Bias (MW)" fill="#e05a00" /></BarChart></ResponsiveContainer></div>
    <div className="card"><h3>Error distribution (forecast − actual, MW)</h3><ResponsiveContainer width="100%" height={240}>
      <BarChart data={a.histogram.map((h) => ({ ...h, bin: Math.round((h.from + h.to) / 2) }))}><XAxis dataKey="bin" /><YAxis width={50} /><Tooltip />
        <Bar dataKey="count" name="Half-hours" fill="#0b7bb5" /></BarChart></ResponsiveContainer></div>
  </>);
}

export default function App() {
  const [tab, setTab] = useState("decision");
  const [cutoff, setCutoff] = useState(9);
  const [days, setDays] = useState(null);
  useEffect(() => { setDays(null); get(`/api/days?cutoff_hour=${cutoff}`).then(setDays).catch(() => setDays([])); }, [cutoff]);
  return (<>
    <header><h1>Wind Forecast Decision Support — GB Day-Ahead</h1></header>
    <main>
      <div className="card controls">
        <label>Decision gate (UK time, day before delivery){" "}
          <select value={cutoff} onChange={(e) => setCutoff(+e.target.value)}>
            {[7, 8, 9, 10, 11, 12].map((h) => <option key={h} value={h}>{String(h).padStart(2, "0")}:00</option>)}</select></label>
      </div>
      <div className="tabs"><button className={tab === "decision" ? "on" : ""} onClick={() => setTab("decision")}>Decision view</button>
        <button className={tab === "accuracy" ? "on" : ""} onClick={() => setTab("accuracy")}>Forecast accuracy</button></div>
      {!days ? <div className="card">Loading…</div> : days.length === 0 ? <div className="card">No data available.</div> :
        tab === "decision" ? <Decision key={cutoff} cutoff={cutoff} days={days} /> : <Accuracy cutoff={cutoff} />}
    </main></>);
}
