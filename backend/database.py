"""
Database layer: In-memory store with session persistence, customer lookup,
supervisor ticket queue, and customer support-ticket store.
Pre-populated with Data Pack Assignment 3 customers and extensible for custom cases.
"""
import copy
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.data_pack import INITIAL_CUSTOMERS, SERVICE_POLICIES

class Database:
    def __init__(self):
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.conversation_histories: Dict[str, List[Dict[str, Any]]] = {}
        self.escalations: List[Dict[str, Any]] = []
        self.tickets: Dict[str, Dict[str, Any]] = {}
        self.reset_to_default()

    def reset_to_default(self):
        """Restore pristine initial state from assignment data pack."""
        self.customers = copy.deepcopy(INITIAL_CUSTOMERS)
        self.conversation_histories = {pnr: [] for pnr in self.customers.keys()}
        self.escalations = []
        self.tickets = {}

    def get_customer(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Look up by PNR, email, or partial name."""
        identifier_clean = identifier.strip().upper()
        if identifier_clean in self.customers:
            return self.customers[identifier_clean]
        
        # Search by email or name
        for pnr, cust in self.customers.items():
            if cust.get("email", "").lower() == identifier.lower():
                return cust
            if identifier.lower() in cust.get("name", "").lower():
                return cust
        return None

    def list_customers(self) -> List[Dict[str, Any]]:
        return list(self.customers.values())

    def save_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        pnr = customer_data["pnr"].strip().upper()
        self.customers[pnr] = customer_data
        if pnr not in self.conversation_histories:
            self.conversation_histories[pnr] = []
        return customer_data

    def get_history(self, pnr: str) -> List[Dict[str, Any]]:
        return self.conversation_histories.get(pnr.upper(), [])

    def append_message(self, pnr: str, role: str, content: str, action_cards: List[Dict[str, Any]] = None):
        pnr_upper = pnr.upper()
        if pnr_upper not in self.conversation_histories:
            self.conversation_histories[pnr_upper] = []
        self.conversation_histories[pnr_upper].append({
            "role": role,
            "content": content,
            "action_cards": action_cards or []
        })

        # Keep the per-PNR support ticket in sync with the conversation.
        ticket = self.ensure_ticket(pnr_upper)
        if ticket:
            ticket["updated_at"] = self._now()
            # A new customer message reopens a ticket that an admin already answered.
            if role == "user" and ticket.get("status") == "answered":
                self._set_ticket_status(ticket, "open", "customer")

    def add_escalation(self, ticket: Dict[str, Any]):
        self.escalations.append(ticket)
        pnr = ticket.get("data", {}).get("pnr")
        if pnr:
            t = self.ensure_ticket(pnr)
            if t:
                esc_id = ticket.get("data", {}).get("ticket_id")
                if esc_id and esc_id not in t.get("escalation_ids", []):
                    t["escalation_ids"].append(esc_id)
                t["updated_at"] = self._now()

    def get_escalations(self) -> List[Dict[str, Any]]:
        return self.escalations

    def resolve_escalation(self, ticket_id: str, status: str, notes: str) -> Optional[Dict[str, Any]]:
        for ticket in self.escalations:
            if ticket.get("data", {}).get("ticket_id") == ticket_id or ticket.get("ticket_id") == ticket_id:
                ticket["status"] = status
                ticket["supervisor_notes"] = notes
                return ticket
        return None

    # ── Support Tickets ─────────────────────────────────────────────────────

    def _now(self) -> str:
        """ISO-8601 UTC timestamp for ticket audit fields."""
        return datetime.now(timezone.utc).isoformat()

    def _derive_ticket_subject(self, customer: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
        """Use the latest customer message, else the booking disruption summary."""
        for message in reversed(history):
            if message.get("role") == "user":
                content = (message.get("content") or "").strip()
                if content:
                    return content[:90] + ("..." if len(content) > 90 else "")

        booking = customer["bookings"][0] if customer.get("bookings") else {}
        disruption = booking.get("disruption_type", "none")
        flight = booking.get("flight_number", "SK-Flight")
        if disruption == "cancellation":
            return f"Flight {flight} cancelled"
        if disruption == "delay":
            return f"Flight {flight} delayed {booking.get('delay_duration_hours', '?')}h"
        return f"Support inquiry for {customer.get('name', 'passenger')}"

    def _build_ticket(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        pnr = customer["pnr"]
        history = self.get_history(pnr)
        booking = customer["bookings"][0] if customer.get("bookings") else {}
        now = self._now()
        return {
            "ticket_id": f"TKT-{uuid.uuid4().hex[:6].upper()}",
            "pnr": pnr,
            "customer_name": customer.get("name", "Unknown"),
            "loyalty_tier": customer.get("loyalty_tier", "Member"),
            "email": customer.get("email", ""),
            "flight_number": booking.get("flight_number", ""),
            "route": booking.get("route", ""),
            "disruption_type": booking.get("disruption_type", "none"),
            "subject": self._derive_ticket_subject(customer, history),
            "status": "open",
            "created_at": now,
            "updated_at": now,
            "escalation_ids": [],
            "status_history": [{"status": "open", "at": now, "by": "system"}],
        }

    def _set_ticket_status(self, ticket: Dict[str, Any], status: str, by: str) -> None:
        ticket["status"] = status
        ticket["status_history"].append({"status": status, "at": self._now(), "by": by})

    def _sync_ticket_escalations(self, ticket: Dict[str, Any], pnr: str) -> None:
        ticket["escalation_ids"] = [
            esc.get("data", {}).get("ticket_id")
            for esc in self.escalations
            if esc.get("data", {}).get("pnr", "").upper() == pnr.upper()
            and esc.get("data", {}).get("ticket_id")
        ]

    def ensure_ticket(self, pnr: str) -> Optional[Dict[str, Any]]:
        """Create or refresh the single support ticket associated with a PNR."""
        customer = self.get_customer(pnr)
        if not customer:
            return None

        pnr_upper = customer["pnr"].upper()
        if pnr_upper not in self.tickets:
            self.tickets[pnr_upper] = self._build_ticket(customer)

        ticket = self.tickets[pnr_upper]
        booking = customer["bookings"][0] if customer.get("bookings") else {}
        ticket["customer_name"] = customer.get("name", ticket.get("customer_name"))
        ticket["loyalty_tier"] = customer.get("loyalty_tier", ticket.get("loyalty_tier"))
        ticket["email"] = customer.get("email", ticket.get("email"))
        ticket["flight_number"] = booking.get("flight_number", ticket.get("flight_number"))
        ticket["route"] = booking.get("route", ticket.get("route"))
        ticket["disruption_type"] = booking.get("disruption_type", ticket.get("disruption_type"))
        self._sync_ticket_escalations(ticket, pnr_upper)
        return ticket

    def list_tickets(self) -> List[Dict[str, Any]]:
        """Return all tickets for customers with conversation history or an escalation."""
        active_pnrs = set()
        for pnr, history in self.conversation_histories.items():
            if history:
                active_pnrs.add(pnr.upper())

        for escalation in self.escalations:
            pnr = escalation.get("data", {}).get("pnr")
            if pnr:
                active_pnrs.add(pnr.upper())

        for pnr in active_pnrs:
            self.ensure_ticket(pnr)

        return [self.tickets[pnr] for pnr in sorted(self.tickets.keys())]

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Look up a ticket by its ticket_id or by PNR."""
        identifier = (ticket_id or "").strip().upper()
        if not identifier:
            return None
        for ticket in self.tickets.values():
            if ticket.get("ticket_id", "").upper() == identifier:
                return ticket
        return self.tickets.get(identifier)

    def get_ticket_thread(self, ticket_id: str) -> Optional[List[Dict[str, Any]]]:
        """Full conversation thread (customer, assistant, and admin messages) for a ticket."""
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None
        return self.get_history(ticket["pnr"])

    def respond_to_ticket(
        self,
        ticket_id: str,
        reply: str,
        resolve: bool = False,
        responder: str = "admin",
    ) -> Optional[Dict[str, Any]]:
        """Append an admin reply to the customer thread and advance ticket status."""
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None

        pnr = ticket["pnr"]
        if pnr not in self.conversation_histories:
            self.conversation_histories[pnr] = []
        self.conversation_histories[pnr].append({
            "role": "admin",
            "content": reply,
            "action_cards": [],
        })

        new_status = "resolved" if resolve else "answered"
        self._set_ticket_status(ticket, new_status, responder)
        ticket["updated_at"] = self._now()
        return ticket

db = Database()
