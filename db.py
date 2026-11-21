"""Tiny SQLite store for daily energy usage and user preferences."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

DB_PATH = os.getenv("THERMO_DB", os.path.join(os.path.dirname(__file__), "thermo.db"))

DEFAULT_PREFS = {
    "heat_home": 70,
    "heat_night": 66,
    "cool_home": 75,
    "cool_night": 73,
    "heat_below": 60,
    "cool_above": 75,
}


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS usage (
                 date TEXT PRIMARY KEY,
                 cost REAL NOT NULL,
                 kwh REAL,
                 setpoint REAL)"""
        )
        c.execute("CREATE TABLE IF NOT EXISTS prefs (key TEXT PRIMARY KEY, value REAL NOT NULL)")


def add_usage(day, cost, kwh=None, setpoint=None):
    with conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO usage (date, cost, kwh, setpoint) VALUES (?,?,?,?)",
            (day, cost, kwh, setpoint),
        )


def delete_usage(day):
    with conn() as c:
        c.execute("DELETE FROM usage WHERE date = ?", (day,))


def get_usage(days=60):
    since = (date.today() - timedelta(days=days)).isoformat()
    with conn() as c:
        rows = c.execute("SELECT * FROM usage WHERE date >= ? ORDER BY date", (since,)).fetchall()
    return [dict(r) for r in rows]


def get_prefs():
    prefs = dict(DEFAULT_PREFS)
    with conn() as c:
        for r in c.execute("SELECT key, value FROM prefs"):
            prefs[r["key"]] = r["value"]
    return prefs


def set_pref(key, value):
    if key not in DEFAULT_PREFS:
        raise ValueError(f"Unknown preference '{key}'. Valid: {', '.join(DEFAULT_PREFS)}")
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO prefs (key, value) VALUES (?,?)", (key, float(value)))
