"""Fills the database with FAKE usage data so you can try the energy coach.
Run once:  python seed_demo.py     (delete thermo.db afterwards to start with your real data)
"""
import random
from datetime import date, timedelta

import db

db.init()
random.seed(1)
for i in range(30, 0, -1):
    d = date.today() - timedelta(days=i)
    setpoint = random.choice([68, 69, 70, 71, 72])
    cost = round(2.5 + (setpoint - 68) * 0.35 + random.uniform(-0.4, 0.8), 2)
    db.add_usage(d.isoformat(), cost, None, setpoint)
print("Seeded 30 days of demo data.")
