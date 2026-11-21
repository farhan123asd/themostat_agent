"""FastAPI app. Run: uvicorn main:app --reload"""
import os
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import agent
import analysis
import db
import weather

db.init()
app = FastAPI(title="ThermoAssistant")


def need_key():
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, "OPENAI_API_KEY is not set on the server.")


class ChatIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=2000)


class UsageIn(BaseModel):
    date: str
    cost: float = Field(ge=0, le=10000)
    kwh: Optional[float] = Field(default=None, ge=0, le=100000)
    setpoint: Optional[float] = Field(default=None, ge=40, le=100)


@app.get("/api/weather")
def api_weather():
    try:
        return weather.get_weather()
    except Exception as e:
        raise HTTPException(502, f"Weather lookup failed: {e}")


@app.post("/api/chat")
def api_chat(body: ChatIn):
    need_key()
    try:
        return {"reply": agent.chat(body.session_id, body.message)}
    except Exception as e:
        raise HTTPException(502, f"Assistant error: {e}")


@app.post("/api/chat/reset")
def api_reset(body: ChatIn):
    agent.reset(body.session_id)
    return {"ok": True}


@app.get("/api/usage")
def api_usage():
    return db.get_usage(90)


@app.post("/api/usage")
def api_add_usage(body: UsageIn):
    try:
        d = date.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(422, "date must be YYYY-MM-DD")
    if d > date.today():
        raise HTTPException(422, "date can't be in the future")
    db.add_usage(d.isoformat(), body.cost, body.kwh, body.setpoint)
    return {"ok": True}


@app.delete("/api/usage/{day}")
def api_delete_usage(day: str):
    db.delete_usage(day)
    return {"ok": True}


@app.get("/api/coach/stats")
def api_stats():
    return analysis.get_stats()


@app.get("/api/coach/advice")
def api_advice():
    need_key()
    try:
        return {"advice": agent.coach_advice()}
    except Exception as e:
        raise HTTPException(502, f"Coach error: {e}")


app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True))
