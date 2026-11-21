"""Open-Meteo helpers (free, no API key)."""
import os
from datetime import date

import requests

LAT = float(os.getenv("THERMO_LAT", "38.595"))   # Ballwin, MO
LON = float(os.getenv("THERMO_LON", "-90.546"))
TZ = os.getenv("THERMO_TZ", "America/Chicago")
URL = "https://api.open-meteo.com/v1/forecast"


def get_weather():
    """Current conditions plus today's high/low and a short hourly outlook."""
    r = requests.get(
        URL,
        params={
            "latitude": LAT,
            "longitude": LON,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "hourly": "apparent_temperature",
            "temperature_unit": "fahrenheit",
            "timezone": TZ,
            "forecast_days": 2,
        },
        timeout=10,
    )
    r.raise_for_status()
    d = r.json()
    return {
        "now_f": d["current"]["temperature_2m"],
        "feels_like_f": d["current"]["apparent_temperature"],
        "humidity_pct": d["current"]["relative_humidity_2m"],
        "today_high_f": d["daily"]["temperature_2m_max"][0],
        "today_low_f": d["daily"]["temperature_2m_min"][0],
        "tomorrow_high_f": d["daily"]["temperature_2m_max"][1],
        "tomorrow_low_f": d["daily"]["temperature_2m_min"][1],
        "next_12h_feels_like_f": d["hourly"]["apparent_temperature"][:12],
    }


def daily_means(start_date: str):
    """Map of 'YYYY-MM-DD' -> mean outdoor temp (F), from start_date to today (max ~92 days back)."""
    days_back = (date.today() - date.fromisoformat(start_date)).days
    past = max(1, min(days_back + 1, 92))
    r = requests.get(
        URL,
        params={
            "latitude": LAT,
            "longitude": LON,
            "daily": "temperature_2m_mean",
            "temperature_unit": "fahrenheit",
            "timezone": TZ,
            "past_days": past,
            "forecast_days": 1,
        },
        timeout=10,
    )
    r.raise_for_status()
    d = r.json()["daily"]
    return dict(zip(d["time"], d["temperature_2m_mean"]))
