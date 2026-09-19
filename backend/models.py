"""
Data models and serialization helpers for the Admin Panel support-ticket feature.

These helpers are intentionally framework-agnostic so they can be reused by the
FastAPI route layer, the in-memory database, and the test suite without importing
a web framework.
"""

from typing import Any, Dict, List, Optional

# Ticket lifecycle: open -> answered -> resolved (customer reply can reopen to open).
TICKET_STATUSES = ("open", "answered", "resolved")


def serialize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single conversation message for the API/thread payload."""
    return {
        "role": message.get("role", "assistant"),
        "content": message.get("content", ""),
        "action_cards": message.get("action_cards", []),
    }


def serialize_ticket(
    ticket: Dict[str, Any],
    include_thread: bool = False,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build the API representation of a support ticket.

    When ``include_thread`` is true and ``history`` is provided, the full
    customer/assistant/admin conversation is attached as ``thread``.
    """
    payload: Dict[str, Any] = {
        "ticket_id": ticket.get("ticket_id"),
        "pnr": ticket.get("pnr"),
        "customer_name": ticket.get("customer_name"),
        "loyalty_tier": ticket.get("loyalty_tier"),
        "email": ticket.get("email"),
        "flight_number": ticket.get("flight_number"),
        "route": ticket.get("route"),
        "disruption_type": ticket.get("disruption_type"),
        "subject": ticket.get("subject"),
        "status": ticket.get("status", "open"),
        "created_at": ticket.get("created_at"),
        "updated_at": ticket.get("updated_at"),
        "escalation_ids": ticket.get("escalation_ids", []),
        "status_history": ticket.get("status_history", []),
    }

    if include_thread:
        payload["thread"] = [serialize_message(message) for message in (history or [])]

    return payload


def ticket_summary(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """Compact representation used by ticket-list endpoints."""
    return {
        "ticket_id": ticket.get("ticket_id"),
        "pnr": ticket.get("pnr"),
        "customer_name": ticket.get("customer_name"),
        "loyalty_tier": ticket.get("loyalty_tier"),
        "subject": ticket.get("subject"),
        "status": ticket.get("status", "open"),
        "created_at": ticket.get("created_at"),
        "updated_at": ticket.get("updated_at"),
        "escalation_ids": ticket.get("escalation_ids", []),
    }
