"""Rule-based baseline recommendation (the original thermostat_advisor logic).

The chat agent uses this as a starting point and adjusts it to the user's situation.
"""


def baseline(weather: dict, prefs: dict) -> dict:
    fl = weather["feels_like_f"]
    low = weather["today_low_f"]
    humidity = weather["humidity_pct"]

    if fl < prefs["heat_below"]:
        mode, now, night = "heat", prefs["heat_home"], prefs["heat_night"]
        if low <= 25:
            night += 1  # very cold night: don't let the house drop as far
    elif fl > prefs["cool_above"]:
        mode, now, night = "cool", prefs["cool_home"], prefs["cool_night"]
        if humidity >= 70:
            now -= 1
            night -= 1  # humid air feels warmer
    else:
        return {"mode": "off", "now_f": None, "overnight_f": None,
                "note": "Mild outside; system can likely stay off with windows open."}
    return {"mode": mode, "now_f": now, "overnight_f": night, "note": "Rule-based baseline."}
