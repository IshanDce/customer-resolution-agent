"""
FastAPI route layer for the Admin Panel support-ticket feature.

Mount this router in the existing server entrypoint::

    from backend.ticket_routes import ticket_router
    app.include_router(ticket_router)

The endpoints use a simple ``role`` flag (query parameter or request body) for
role-based access. Only ``admin`` can respond to tickets; customers can only
view their own ticket threads.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.database import db
from backend.models import serialize_ticket, ticket_summary

ticket_router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class TicketRespondRequest(BaseModel):
    reply: str = Field(..., min_length=1, description="Admin response text")
    resolve: bool = Field(False, description="Set ticket status to resolved instead of answered")
    role: str = Field("customer", description="Role flag; must be 'admin' to respond")


def _guard_admin(role: Optional[str]) -> None:
    if not role or role.strip().lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin role required for this operation.")


@ticket_router.get("")
def list_tickets(
    role: str = Query("customer", description="Role flag: admin or customer"),
    pnr: Optional[str] = Query(None, description="Customer PNR (required when role=customer)"),
):
    role = role.strip().lower()
    tickets = db.list_tickets()

    if role == "admin":
        return [ticket_summary(ticket) for ticket in tickets]

    if not pnr:
        raise HTTPException(status_code=400, detail="Customer role requires a pnr query parameter.")

    own_tickets = [ticket for ticket in tickets if ticket["pnr"].upper() == pnr.upper()]
    return [ticket_summary(ticket) for ticket in own_tickets]


@ticket_router.get("/{ticket_id}")
def get_ticket(
    ticket_id: str,
    role: str = Query("customer", description="Role flag: admin or customer"),
    pnr: Optional[str] = Query(None, description="Customer PNR (required when role=customer)"),
):
    role = role.strip().lower()
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    if role != "admin":
        if not pnr or ticket["pnr"].upper() != pnr.upper():
            raise HTTPException(status_code=403, detail="Customer can only view their own ticket.")

    return serialize_ticket(
        ticket,
        include_thread=True,
        history=db.get_ticket_thread(ticket["ticket_id"]),
    )


@ticket_router.post("/{ticket_id}/respond")
def respond_to_ticket(ticket_id: str, request: TicketRespondRequest):
    _guard_admin(request.role)

    ticket = db.respond_to_ticket(
        ticket_id,
        reply=request.reply,
        resolve=request.resolve,
        responder="admin",
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    return serialize_ticket(
        ticket,
        include_thread=True,
        history=db.get_ticket_thread(ticket["ticket_id"]),
    )
