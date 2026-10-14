import { Chart } from "react-chartjs-2";
import { Chart as ChartJS, registerables } from "chart.js";
ChartJS.register(...registerables);

export default function Charts({ data }) {
  const rows = data.yearly;
  const tr = data.trend;
  const labels = rows.map((r) => r.year);
  const v = (k) => rows.map((r) => (r.valid ? r[k] : null));
  const fit = tr.ok ? rows.map((r) => (r.valid ? +(tr.ols_intercept + tr.ols_slope * r.year).toFixed(2) : null)) : [];

  const daysData = {
    labels,
    datasets: [
      { type: "bar", label: "Heatwave days", data: v("heatwave_days"), backgroundColor: "rgba(239,68,68,.6)" },
      { type: "line", label: "5-yr rolling avg", data: data.rolling_5yr, borderColor: "#1d4ed8", pointRadius: 0, tension: 0.3 },
      ...(tr.ok ? [{ type: "line", label: "Linear trend", data: fit, borderColor: "#111", borderDash: [6, 4], pointRadius: 0 }] : []),
    ],
  };
  const evData = {
    labels,
    datasets: [
      { type: "bar", label: "Events", data: v("events"), backgroundColor: "rgba(245,158,11,.7)", yAxisID: "y" },
      { type: "line", label: "Longest event (days)", data: v("max_duration"), borderColor: "#7c3aed", yAxisID: "y1", spanGaps: true },
    ],
  };
  const base = { responsive: true, plugins: { legend: { position: "bottom" } } };

  return (
    <>
      <h3>Heatwave days per year</h3>
      <Chart type="bar" data={daysData} options={{ ...base, scales: { y: { beginAtZero: true, title: { display: true, text: "days" } } } }} />
      <h3>Frequency and duration</h3>
      <Chart type="bar" data={evData} options={{ ...base, scales: {
        y: { beginAtZero: true, title: { display: true, text: "events" } },
        y1: { beginAtZero: true, position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "days" } } } }} />
      <h3>Longest events</h3>
      <table>
        <thead><tr><th>Start</th><th>End</th><th>Days</th><th>Peak °C</th><th>Avg excess °C</th></tr></thead>
        <tbody>
          {data.top_events.map((e) => (
            <tr key={e.start}><td>{e.start}</td><td>{e.end}</td><td>{e.duration}</td><td>{e.peak_temp}</td><td>{e.mean_excess}</td></tr>
          ))}
        </tbody>
      </table>
    </>
  );
}