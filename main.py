"""
AeroResolve AI — FastAPI application entrypoint.

Serves the customer-facing web app, the existing resolution APIs consumed by
the frontend, and the Admin Panel support-ticket router.

Run:
    python main.py
Then open http://localhost:8000
"""

from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent import agent
from backend.config import GEMINI_MODEL_NAME
from backend.data_pack import (
    ALLOWED_ACTIONS,
    OPERATIONAL_DATE,
    PROHIBITED_ACTIONS,
    SERVICE_POLICIES,
)
from backend.database import db
from backend.ticket_routes import ticket_router

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="AeroResolve AI", version="1.0.0")
app.include_router(ticket_router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Request models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    pnr: str
    message: str
    api_provider: str = "gemini"
    api_key: Optional[str] = None


class CustomerCreateRequest(BaseModel):
    pnr: str
    name: str
    loyalty_tier: str = "Member"
    email: str = ""
    phone: str = ""
    flight_number: str = "SK-Flight"
    route: str = "Delhi → Mumbai"
    date: str = "Wed 23 Sep 2026"
    scheduled_departure: str = "12:00"
    disruption_status: str = "Cancelled (operational reasons)"
    delay_hours: float = 0
    airline_caused: bool = True
    flights_last_12m: int = 0
    prior_complaint_issue: Optional[str] = None


class EscalationResolveRequest(BaseModel):
    status: str
    notes: str = ""


# ── Page & info routes ──────────────────────────────────────────────────────

@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/info")
def get_info() -> Dict[str, Any]:
    return {
        "name": "AeroResolve AI",
        "assignment": "Assignment 3: Customer-Facing Resolution Agent (Airline Disruption)",
        "operational_date": OPERATIONAL_DATE,
        "model": GEMINI_MODEL_NAME,
        "status": "active",
    }


@app.get("/api/policies")
def get_policies() -> Dict[str, Any]:
    return {
        "service_policies": SERVICE_POLICIES,
        "allowed_actions": ALLOWED_ACTIONS,
        "prohibited_actions": PROHIBITED_ACTIONS,
    }


# ── Customer routes ─────────────────────────────────────────────────────────

@app.get("/api/customers")
def list_customers():
    return db.list_customers()


@app.get("/api/customers/{identifier}")
def get_customer(identifier: str):
    customer = db.get_customer(identifier)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.post("/api/customers")
def create_customer(request: CustomerCreateRequest):
    status = request.disruption_status or ""
    if status.lower().startswith("cancelled"):
        disruption_type = "cancellation"
    elif status.lower().startswith("delayed"):
        disruption_type = "delay"
    else:
        disruption_type = "none"

    prior_complaints = []
    if request.prior_complaint_issue:
        prior_complaints.append({
            "issue": request.prior_complaint_issue,
            "resolution": "resolved by support team",
            "date": "2026-09-01",
        })

    customer_data = {
        "pnr": request.pnr.strip().upper(),
        "name": request.name.strip(),
        "loyalty_tier": request.loyalty_tier,
        "email": request.email,
        "phone": request.phone,
        "travel_history": {
            "flights_last_12m": request.flights_last_12m,
            "prior_complaints": prior_complaints,
        },
        "bookings": [
            {
                "flight_number": request.flight_number,
                "route": request.route,
                "date": request.date,
                "scheduled_departure": request.scheduled_departure,
                "status": status,
                "disruption_type": disruption_type,
                "airline_caused": request.airline_caused,
                "is_return": False,
                "delay_duration_hours": request.delay_hours or 0,
                "fare_paid": 5000,
            }
        ],
        "scenario_description": f"Custom passenger {request.name} ({request.pnr.strip().upper()})",
    }

    return db.save_customer(customer_data)


# ── Conversation & resolution routes ────────────────────────────────────────

@app.get("/api/history/{pnr}")
def get_history(pnr: str):
    return db.get_history(pnr)


@app.post("/api/chat")
def chat(request: ChatRequest):
    return agent.process_message(
        pnr=request.pnr,
        user_message=request.message,
        api_provider=request.api_provider,
        api_key=request.api_key,
    )


# ── Supervisor escalation routes ────────────────────────────────────────────

@app.get("/api/escalations")
def get_escalations():
    return db.get_escalations()


@app.post("/api/escalations/{ticket_id}/resolve")
def resolve_escalation(ticket_id: str, request: EscalationResolveRequest):
    resolved = db.resolve_escalation(ticket_id, request.status, request.notes)
    if not resolved:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return resolved


# ── System reset ────────────────────────────────────────────────────────────

@app.post("/api/reset")
def reset_system():
    db.reset_to_default()
    return {"status": "reset", "customers": len(db.list_customers())}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
