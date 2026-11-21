"""Deterministic energy analysis. The LLM explains these numbers; it never computes them."""
from statistics import mean

import db
import weather

BASE_TEMP_F = 65.0
# Rough rule of thumb: ~1% of heating/cooling cost per degree F of setback held ~8 hrs/day.
PCT_PER_DEGREE = 0.01


def get_stats(days=60):
    rows = db.get_usage(days)
    if len(rows) < 5:
        return {
            "enough_data": False,
            "entries": len(rows),
            "message": "Log at least 5 days of cost (and thermostat setpoint if you can) to unlock the coach.",
        }

    try:
        temps = weather.daily_means(rows[0]["date"])
    except Exception:
        temps = {}

    enriched = []
    for r in rows:
        t = temps.get(r["date"])
        dd = abs(t - BASE_TEMP_F) if t is not None else None
        cpdd = r["cost"] / dd if dd and dd >= 3 else None  # skip mild days (no real load)
        enriched.append({**r, "outdoor_mean_f": t, "degree_days": dd, "cost_per_degree_day": cpdd})

    costs = [r["cost"] for r in enriched]
    avg_daily = mean(costs)
    cpdds = [r["cost_per_degree_day"] for r in enriched if r["cost_per_degree_day"]]
    setpoints = [r["setpoint"] for r in enriched if r["setpoint"] is not None]

    recent, prior = enriched[-7:], enriched[-14:-7]
    trend = None
    if len(prior) >= 3:
        trend = {
            "last_7_avg_daily_cost": round(mean(r["cost"] for r in recent), 2),
            "previous_7_avg_daily_cost": round(mean(r["cost"] for r in prior), 2),
        }
        rc = [r["cost_per_degree_day"] for r in recent if r["cost_per_degree_day"]]
        pc = [r["cost_per_degree_day"] for r in prior if r["cost_per_degree_day"]]
        if rc and pc:
            trend["last_7_cost_per_degree_day"] = round(mean(rc), 3)
            trend["previous_7_cost_per_degree_day"] = round(mean(pc), 3)

    worst = sorted((r for r in enriched if r["cost_per_degree_day"]),
                   key=lambda r: r["cost_per_degree_day"], reverse=True)[:3]

    return {
        "enough_data": True,
        "entries": len(enriched),
        "total_cost": round(sum(costs), 2),
        "avg_daily_cost": round(avg_daily, 2),
        "avg_setpoint_f": round(mean(setpoints), 1) if setpoints else None,
        "avg_cost_per_degree_day": round(mean(cpdds), 3) if cpdds else None,
        "trend": trend,
        "least_efficient_days": [
            {"date": r["date"], "cost": r["cost"], "setpoint": r["setpoint"],
             "outdoor_mean_f": round(r["outdoor_mean_f"], 1),
             "cost_per_degree_day": round(r["cost_per_degree_day"], 3)}
            for r in worst
        ],
        "est_monthly_savings_per_degree_setback": round(avg_daily * 30 * PCT_PER_DEGREE, 2),
        "assumptions": "Savings use a ~1%/degree-F rule of thumb (setback held ~8 hrs/day); real results vary. "
                       "Cost-per-degree-day = daily cost / |outdoor mean - 65F|, skipping mild days.",
        "daily": [
            {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()} for r in enriched
        ],
    }
