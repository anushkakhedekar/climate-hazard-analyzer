from datetime import datetime, timezone
import numpy as np
import pandas as pd
from pymongo import ReplaceOne
from .db import weather, results
from .openmeteo import fetch_tmax
from . import hazards, trends

def snap(x: float) -> float:
    return round(x * 4) / 4 + 0.0          # 0.25° grid; +0.0 avoids "-0.0"

def ensure_weather(loc_key, lat, lon, y0, y1):
    q = {"loc_key": loc_key, "year": {"$gte": y0, "$lte": y1}}
    have = {d["year"] for d in weather.find(q, {"year": 1})}
    missing = [y for y in range(y0, y1 + 1) if y not in have]
    if missing:
        times, vals = fetch_tmax(lat, lon, min(missing), max(missing))
        by = {}
        for t, v in zip(times, vals):
            d = by.setdefault(int(t[:4]), {"dates": [], "tmax": []})
            d["dates"].append(t)
            d["tmax"].append(v)
        now = datetime.now(timezone.utc)
        ops = [
            ReplaceOne({"loc_key": loc_key, "year": y},
                       {"loc_key": loc_key, "year": y, "lat": lat, "lon": lon, **d, "fetched_at": now},
                       upsert=True)
            for y, d in by.items() if y in missing
        ]
        if ops:
            weather.bulk_write(ops)
    return list(weather.find(q).sort("year", 1))

def to_series(docs):
    dates, vals = [], []
    for d in docs:
        dates += d["dates"]
        vals += d["tmax"]
    s = pd.Series([np.nan if v is None else v for v in vals], index=pd.to_datetime(dates), dtype=float)
    s = s[~s.index.duplicated()].sort_index()
    return s.reindex(pd.date_range(s.index[0], s.index[-1], freq="D"))   # make gaps explicit

def analyze(lat, lon, y0, y1):
    lat, lon = snap(lat), snap(lon)
    loc_key = f"{lat:.2f}_{lon:.2f}"
    key = f"{loc_key}|{y0}|{y1}|heatwave|v1"

    cached = results.find_one({"key": key}, {"_id": 0, "created_at": 0})
    if cached:
        cached["cache"] = "hit"
        return cached

    docs = ensure_weather(loc_key, lat, lon, min(y0, hazards.BASE_START), max(y1, hazards.BASE_END))
    s, qc = hazards.clean(to_series(docs))
    thr = hazards.daily_thresholds(s)
    s_rng = s[(s.index.year >= y0) & (s.index.year <= y1)]
    events = hazards.detect_events(s_rng, thr)
    rows = hazards.yearly_stats(events, s_rng, y0, y1)

    valid = [r for r in rows if r["valid"]]
    tr = trends.trend([r["year"] for r in valid], [r["heatwave_days"] for r in valid])

    out = {
        "key": key,
        "hazard": "heatwave",
        "location": {"lat": lat, "lon": lon, "grid_cell": "0.25°"},
        "range": {"start_year": y0, "end_year": y1},
        "definition": {
            "rule": f"≥{hazards.MIN_RUN} consecutive days with Tmax above the {hazards.PCTL}th percentile "
                    f"of that calendar day (±{hazards.WINDOW}-day window), baseline {hazards.BASE_START}–{hazards.BASE_END}",
        },
        "quality": qc,
        "yearly": rows,
        "rolling_5yr": trends.rolling_avg(rows),
        "trend": tr,
        "insight": trends.build_insight(rows, tr, qc),
        "top_events": sorted(events, key=lambda e: (-e["duration"], -e["peak_temp"]))[:10],
        "source": "Open-Meteo Historical Weather API (ERA5), CC BY 4.0",
        "cache": "miss",
    }
    results.replace_one({"key": key}, {**out, "created_at": datetime.now(timezone.utc)}, upsert=True)
    return out