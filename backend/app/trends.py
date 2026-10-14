import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy import stats

def rolling_avg(rows, key="heatwave_days", w=5):
    s = pd.Series([r[key] if r["valid"] else np.nan for r in rows], dtype=float)
    r = s.rolling(w, center=True, min_periods=3).mean()
    return [None if pd.isna(v) else round(float(v), 2) for v in r]

def trend(years, values):
    if len(years) < 10:
        return {"ok": False, "reason": "Need at least 10 valid years for a trend."}
    x, y = np.array(years, float), np.array(values, float)
    lr = stats.linregress(x, y)
    m = mk.original_test(y)
    return {
        "ok": True,
        "ols_slope": float(lr.slope), "ols_intercept": float(lr.intercept),
        "ols_p": float(lr.pvalue), "r2": float(lr.rvalue ** 2),
        "mk_trend": str(m.trend), "mk_p": float(m.p), "sen_slope": float(m.slope),
        "significant": bool(m.p < 0.05),
    }

def build_insight(rows, tr, quality):
    valid = [r for r in rows if r["valid"]]
    caveats = [
        "Data is ERA5 reanalysis (modelled, ~25 km grid), not a weather-station record; local extremes may be smoothed.",
        "Heatwaves are defined relative to the 1991–2020 climate. Years before 1991 will naturally look cooler, and the baseline period itself averages ~5% hot days by construction.",
        "Results are for one grid cell, not an area average.",
    ]
    excluded = len(rows) - len(valid)
    if excluded:
        caveats.append(f"{excluded} year(s) excluded because more than 10% of days were missing.")
    if len(valid) < 10:
        return {"headline": "Not enough valid years to say anything reliable.", "detail": "", "caveats": caveats}

    k = max(3, min(10, len(valid) // 3))
    early, late = valid[:k], valid[-k:]
    a = float(np.mean([r["heatwave_days"] for r in early]))
    b = float(np.mean([r["heatwave_days"] for r in late]))
    span = f"{early[0]['year']}–{early[-1]['year']} vs {late[0]['year']}–{late[-1]['year']}"
    if a > 0:
        pct = (b - a) / a * 100
        change = f"{'increased' if pct >= 0 else 'decreased'} by {abs(pct):.0f}%"
    else:
        change = "changed"
    headline = f"Heatwave days {change} ({a:.1f} → {b:.1f} days/yr, {span})."

    if tr["ok"]:
        verdict = ("This trend is statistically significant (p < 0.05)." if tr["significant"]
                   else "This trend is NOT statistically significant, so treat it as inconclusive.")
        detail = (f"Mann-Kendall: {tr['mk_trend']} (p = {tr['mk_p']:.3f}). "
                  f"Sen's slope: {tr['sen_slope'] * 10:+.2f} heatwave days/yr per decade. {verdict}")
    else:
        detail = tr.get("reason", "")
    return {"headline": headline, "detail": detail, "caveats": caveats}