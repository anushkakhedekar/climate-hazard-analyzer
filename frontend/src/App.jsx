import { useState } from "react";
import MapPicker from "./MapPicker";
import Charts from "./Charts";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "";
const LAST_YEAR = new Date().getFullYear() - 1;
const wrapLng = (x) => ((((x + 180) % 360) + 360) % 360) - 180;

export default function App() {
  const [place, setPlace] = useState({ lat: 28.61, lon: 77.21, label: "New Delhi" });
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState([]);
  const [hazard, setHazard] = useState("heatwave");
  const [startYear, setStartYear] = useState(1990);
  const [endYear, setEndYear] = useState(LAST_YEAR);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search(e) {
    e.preventDefault();
    if (query.trim().length < 2) return;
    const r = await fetch(`${API}/api/geocode?q=${encodeURIComponent(query)}`);
    setMatches(r.ok ? await r.json() : []);
  }

  const qs = `lat=${place.lat}&lon=${place.lon}&start_year=${startYear}&end_year=${endYear}&hazard=${hazard}`;

  async function analyze() {
    setLoading(true); setError("");
    try {
      const r = await fetch(`${API}/api/analysis?${qs}`);
      const j = await r.json();
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "Invalid input");
      setData(j);
    } catch (e) { setError(e.message); setData(null); }
    finally { setLoading(false); }
  }

  return (
    <div className="wrap">
      <h1>Climate Hazard Trend Analyzer</h1>

      <section className="panel">
        <form onSubmit={search} className="row">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search city or state…" />
          <button>Search</button>
        </form>
        {matches.length > 0 && (
          <ul className="matches">
            {matches.map((m, i) => (
              <li key={i} onClick={() => { setPlace({ lat: m.lat, lon: m.lon, label: [m.name, m.admin1, m.country].filter(Boolean).join(", ") }); setMatches([]); }}>
                {[m.name, m.admin1, m.country].filter(Boolean).join(", ")}
              </li>
            ))}
          </ul>
        )}
        <MapPicker lat={place.lat} lon={place.lon}
          onPick={(la, lo) => setPlace({ lat: +la.toFixed(3), lon: +wrapLng(lo).toFixed(3), label: "Custom point" })} />
        <p className="muted">Selected: {place.label} ({place.lat}, {place.lon}). Click the map to change it.</p>

        <div className="row">
          <label>Hazard
            <select value={hazard} onChange={(e) => setHazard(e.target.value)}>
              <option value="heatwave">Heatwave</option>
              <option disabled>Drought (coming soon)</option>
              <option disabled>Heavy rainfall (coming soon)</option>
            </select>
          </label>
          <label>From <input type="number" min="1950" max={LAST_YEAR} value={startYear} onChange={(e) => setStartYear(+e.target.value)} /></label>
          <label>To <input type="number" min="1950" max={LAST_YEAR} value={endYear} onChange={(e) => setEndYear(+e.target.value)} /></label>
          <button onClick={analyze} disabled={loading}>{loading ? "Analyzing… (first run can take ~10s)" : "Analyze"}</button>
        </div>
      </section>

      {error && <p className="error">{error}</p>}

      {data && (
        <section className="panel">
          <h2>{data.insight.headline}</h2>
          <p>{data.insight.detail}</p>
          <p className="muted"><b>Definition:</b> {data.definition.rule}</p>
          <p className="muted">
            Data quality: {data.quality.missing_raw} missing days, {data.quality.out_of_range_removed} impossible values and{" "}
            {data.quality.spikes_removed} spikes removed, {data.quality.gaps_interpolated} short gaps filled. Served from cache: {data.cache}.
          </p>
          <Charts data={data} />
          <h3>Caveats</h3>
          <ul>{data.insight.caveats.map((c, i) => <li key={i}>{c}</li>)}</ul>
          <a href={`${API}/api/export.csv?${qs}`}>Download CSV</a>
          <p className="muted">{data.source}</p>
        </section>
      )}
    </div>
  );
}