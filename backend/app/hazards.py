import numpy as np
import pandas as pd

BASE_START, BASE_END = 1991, 2020   # WMO standard climate normal
PCTL = 95
WINDOW = 7          # ±7 days around each calendar day (15-day window)
MIN_RUN = 3         # 3+ consecutive days
MAX_MISSING_PCT = 10

def clean(s: pd.Series):
    """Handle noise: impossible values, spikes, short gaps. Returns (series, QC report)."""
    s = s.astype(float).copy()
    missing_raw = int(s.isna().sum())

    bad = (s < -90) | (s > 60)
    out_of_range = int(bad.sum())
    s[bad] = np.nan

    med = s.rolling(7, center=True, min_periods=3).median()
    spikes = (s - med).abs() > 20
    n_spikes = int(spikes.sum())
    s[spikes] = np.nan

    before = int(s.isna().sum())
    s = s.interpolate(limit=3, limit_area="inside")   # fill gaps of at most 3 days
    filled = before - int(s.isna().sum())

    return s, {
        "days_total": int(len(s)),
        "missing_raw": missing_raw,
        "out_of_range_removed": out_of_range,
        "spikes_removed": n_spikes,
        "gaps_interpolated": filled,
        "missing_after_cleaning": int(s.isna().sum()),
    }

def doy365(idx: pd.DatetimeIndex) -> np.ndarray:
    """Day-of-year on a 365-day calendar (Feb 29 merged into Feb 28)."""
    doy = idx.dayofyear.values.copy()
    leap = np.asarray(idx.is_leap_year)
    month = np.asarray(idx.month)
    day = np.asarray(idx.day)
    doy[leap & (month > 2)] -= 1
    doy[leap & (month == 2) & (day == 29)] = 59
    return doy

def daily_thresholds(s: pd.Series) -> np.ndarray:
    """95th percentile of Tmax for each calendar day, over 1991–2020, using a 15-day window."""
    base = s[(s.index.year >= BASE_START) & (s.index.year <= BASE_END)]
    doy = doy365(base.index)
    vals = base.values
    thr = np.full(366, np.nan)
    for d in range(1, 366):
        offs = ((np.arange(d - WINDOW, d + WINDOW + 1) - 1) % 365) + 1
        v = vals[np.isin(doy, offs)]
        v = v[~np.isnan(v)]
        if len(v) >= 100:
            thr[d] = np.percentile(v, PCTL)
    return thr

def detect_events(s: pd.Series, thr: np.ndarray):
    t = thr[doy365(s.index)]
    x = s.values
    exceed = (x > t) & ~np.isnan(x) & ~np.isnan(t)
    events, i, n = [], 0, len(s)
    while i < n:
        if exceed[i]:
            j = i
            while j + 1 < n and exceed[j + 1]:
                j += 1
            if j - i + 1 >= MIN_RUN:
                events.append({
                    "start": s.index[i].date().isoformat(),
                    "end": s.index[j].date().isoformat(),
                    "duration": j - i + 1,
                    "peak_temp": round(float(x[i:j + 1].max()), 1),
                    "mean_excess": round(float((x[i:j + 1] - t[i:j + 1]).mean()), 2),
                })
            i = j + 1
        else:
            i += 1
    return events

def yearly_stats(events, s_range: pd.Series, y0: int, y1: int):
    rows = []
    for y in range(y0, y1 + 1):
        ev = [e for e in events if int(e["start"][:4]) == y]
        sy = s_range[s_range.index.year == y]
        miss = float(sy.isna().mean() * 100) if len(sy) else 100.0
        rows.append({
            "year": y,
            "events": len(ev),
            "heatwave_days": sum(e["duration"] for e in ev),
            "max_duration": max([e["duration"] for e in ev], default=0),
            "mean_intensity": round(float(np.mean([e["mean_excess"] for e in ev])), 2) if ev else None,
            "missing_pct": round(miss, 1),
            "valid": miss <= MAX_MISSING_PCT,
        })
    return rows