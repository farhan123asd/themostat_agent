# ThermoAssistant

Chat-based thermostat advisor + energy-savings coach for Ballwin, MO.
Weather comes from Open-Meteo (free, no key). The OpenAI key is only used for the chat and coach text.

## Run
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    export OPENAI_API_KEY="sk-..."          # Windows PowerShell: $env:OPENAI_API_KEY="sk-..."
    uvicorn main:app --reload
Open http://127.0.0.1:8000

Optional: `python seed_demo.py` adds 30 days of FAKE usage to try the coach (delete thermo.db afterwards).
Env overrides: OPENAI_MODEL, THERMO_LAT, THERMO_LON, THERMO_TZ, THERMO_DB.
