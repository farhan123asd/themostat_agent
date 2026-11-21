"""LLM layer: a tool-calling chat assistant and a one-shot energy coach (OpenAI Responses API)."""
import json
import os

from openai import OpenAI

import advisor
import analysis
import db
import weather

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_TOOL_ROUNDS = 5
SESSIONS: dict = {}  # session_id -> conversation items (in memory; resets on restart)


def _client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())


CHAT_SYSTEM = """You are ThermoAssistant, a friendly home-thermostat advisor for a user in Ballwin, Missouri.
- Always check the real weather with get_weather before recommending a temperature; never guess it.
- Call get_preferences to respect the user's comfort settings, and get_baseline_recommendation for a starting point,
  then adjust for what the user tells you (guests, being away, sleeping, etc.).
- When the user states a lasting preference ("I like it at 68 at night"), save it with save_preference.
- Use get_energy_analysis when they ask about bills, costs, or savings.
- Temperatures are in Fahrenheit. Be concise: at most 4 sentences unless asked for more.
- You advise only; you cannot change the thermostat yourself."""

COACH_SYSTEM = """You are an energy-savings coach. You get JSON statistics about a household's daily heating/cooling
costs. Write 3-5 short bullet points: what the numbers show, then specific, realistic actions. Quote the provided
numbers exactly; do not invent figures, and mention that savings estimates are rough rules of thumb."""

TOOLS = [
    {"type": "function", "name": "get_weather",
     "description": "Current conditions, today's high/low, tomorrow's high/low, and next 12h feels-like for Ballwin, MO.",
     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"type": "function", "name": "get_preferences",
     "description": "The user's saved comfort settings (F).",
     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"type": "function", "name": "get_baseline_recommendation",
     "description": "Rule-based thermostat suggestion from current weather and saved preferences.",
     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"type": "function", "name": "save_preference",
     "description": "Save a lasting comfort preference.",
     "parameters": {"type": "object",
                    "properties": {"key": {"type": "string", "enum": list(db.DEFAULT_PREFS)},
                                   "value": {"type": "number"}},
                    "required": ["key", "value"], "additionalProperties": False}},
    {"type": "function", "name": "get_energy_analysis",
     "description": "Stats on the user's logged energy costs, trends, and estimated savings.",
     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}},
]


def _stats_for_llm():
    s = analysis.get_stats()
    s.pop("daily", None)  # keep the prompt small
    return s


def run_tool(name, args):
    if name == "get_weather":
        return weather.get_weather()
    if name == "get_preferences":
        return db.get_prefs()
    if name == "get_baseline_recommendation":
        return advisor.baseline(weather.get_weather(), db.get_prefs())
    if name == "save_preference":
        db.set_pref(args["key"], args["value"])
        return {"saved": True, **args}
    if name == "get_energy_analysis":
        return _stats_for_llm()
    return {"error": f"unknown tool {name}"}


def chat(session_id: str, message: str) -> str:
    client = _client()
    history = SESSIONS.setdefault(session_id, [])
    history.append({"role": "user", "content": message})
    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.responses.create(model=MODEL, instructions=CHAT_SYSTEM, tools=TOOLS, input=history)
        history += resp.output
        calls = [i for i in resp.output if i.type == "function_call"]
        if not calls:
            return resp.output_text
        for c in calls:
            try:
                result = run_tool(c.name, json.loads(c.arguments or "{}"))
            except Exception as e:  # report tool failures to the model instead of crashing
                result = {"error": str(e)}
            history.append({"type": "function_call_output", "call_id": c.call_id, "output": json.dumps(result)})
    return "Sorry, I couldn't finish that. Please try rephrasing."


def reset(session_id: str):
    SESSIONS.pop(session_id, None)


def coach_advice() -> str:
    stats = _stats_for_llm()
    if not stats.get("enough_data"):
        return stats["message"]
    resp = _client().responses.create(
        model=MODEL, instructions=COACH_SYSTEM, input=json.dumps(stats)
    )
    return resp.output_text
