import time
import httpx

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"

def fetch_tmax(lat: float, lon: float, start_year: int, end_year: int):
    """Daily max temperature (°C) from Open-Meteo (ERA5 reanalysis). Retries on 429/5xx."""
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": f"{start_year}-01-01", "end_date": f"{end_year}-12-31",
        "daily": "temperature_2m_max", "temperature_unit": "celsius", "timezone": "auto",
    }
    last_err = None
    for attempt in range(3):
        try:
            r = httpx.get(ARCHIVE_URL, params=params, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt * 2)
                continue
            r.raise_for_status()
            d = r.json()["daily"]
            return d["time"], d["temperature_2m_max"]
        except httpx.HTTPError as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Open-Meteo unavailable: {last_err}")

def geocode(q: str):
    r = httpx.get(GEO_URL, params={"name": q, "count": 5, "language": "en", "format": "json"}, timeout=15)
    r.raise_for_status()
    return [
        {"name": x["name"], "admin1": x.get("admin1"), "country": x.get("country"),
         "lat": x["latitude"], "lon": x["longitude"]}
        for x in r.json().get("results", [])
    ]