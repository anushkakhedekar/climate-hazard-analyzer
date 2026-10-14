import csv, io
from datetime import date
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import ALLOWED_ORIGINS
from .db import init_indexes
from .openmeteo import geocode
from .service import analyze

LAST_YEAR = date.today().year - 1      # only complete years

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Climate Hazard Trend Analyzer")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_indexes()

def params(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start_year: int = Query(1990, ge=1950),
    end_year: int = Query(LAST_YEAR, ge=1950),
    hazard: Literal["heatwave"] = "heatwave",
):
    if end_year > LAST_YEAR:
        raise HTTPException(400, f"end_year cannot exceed {LAST_YEAR} (only complete years).")
    if end_year - start_year < 9:
        raise HTTPException(400, "Choose a range of at least 10 years for a meaningful trend.")
    return {"lat": lat, "lon": lon, "y0": start_year, "y1": end_year}

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/geocode")
@limiter.limit("60/minute")
def geocode_ep(request: Request, q: str = Query(..., min_length=2, max_length=80)):
    try:
        return geocode(q)
    except httpx.HTTPError:
        raise HTTPException(502, "Geocoding service unavailable.")

@app.get("/api/analysis")
@limiter.limit("30/minute")
def analysis(request: Request, p: dict = Depends(params)):
    try:
        return analyze(**p)
    except RuntimeError as e:
        raise HTTPException(502, str(e))

@app.get("/api/export.csv")
@limiter.limit("10/minute")
def export_csv(request: Request, p: dict = Depends(params)):
    try:
        data = analyze(**p)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    cols = ["year", "events", "heatwave_days", "max_duration", "mean_intensity", "missing_pct", "valid"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    w.writerows(data["yearly"])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=heatwave_trend.csv"})