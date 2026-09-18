"""
Tool Registry: Concrete resolution actions executing business changes and generating UI action cards.
"""
import uuid
from datetime import datetime
from typing import Dict, Any

class ToolRegistry:
    @staticmethod
    def issue_meal_voucher(pnr: str, amount: int, passenger_name: str, flight_number: str) -> Dict[str, Any]:
        voucher_code = f"MEAL-{uuid.uuid4().hex[:6].upper()}"
        return {
            "tool": "issue_meal_voucher",
            "status": "executed",
            "message": f"Issued ₹{amount} digital meal voucher for {passenger_name}",
            "card_type": "meal_voucher",
            "data": {
                "voucher_code": voucher_code,
                "amount": f"₹{amount}",
                "passenger_name": passenger_name,
                "flight_number": flight_number,
                "valid_at": "All Terminal Dining Outlets & Cafes",
                "expiry": "Valid for 24 hours from issuance",
                "issued_at": "23 Sep 2026, 11:20 IST"
            }
        }

    @staticmethod
    def issue_lounge_access(pnr: str, passenger_name: str, flight_number: str, airport: str) -> Dict[str, Any]:
        pass_id = f"LNG-{uuid.uuid4().hex[:6].upper()}"
        return {
            "tool": "issue_lounge_access",
            "status": "executed",
            "message": f"Granted complimentary Airport Lounge Access for {passenger_name}",
            "card_type": "lounge_pass",
            "data": {
                "pass_id": pass_id,
                "passenger_name": passenger_name,
                "flight_number": flight_number,
                "lounge_name": "Premium Executive Lounge (Terminal Departures)",
                "access_tier": "Complimentary Disruption Access",
                "amenities": ["High-Speed Wi-Fi", "Quiet Workstations", "Hot Buffet & Beverages", "Shower Facilities"],
                "airport": airport,
                "issued_at": "23 Sep 2026, 11:20 IST"
            }
        }

    @staticmethod
    def arrange_day_hotel(pnr: str, passenger_name: str, flight_number: str, delay_hours: float, departure_time: str) -> Dict[str, Any]:
        booking_ref = f"HTL-{uuid.uuid4().hex[:6].upper()}"
        return {
            "tool": "arrange_day_hotel",
            "status": "executed",
            "message": f"Arranged transit hotel day-room strictly covering delayed hours portion ({delay_hours:.0f}h) until {departure_time}",
            "card_type": "hotel_voucher",
            "data": {
                "booking_ref": booking_ref,
                "hotel_name": "Airport Transit Grand Hotel (Airside / Terminal Wing)",
                "passenger_name": passenger_name,
                "flight_number": flight_number,
                "coverage_type": f"Day-use transit room ({delay_hours:.0f} delay hours only)",
                "check_in": "Immediate access",
                "check_out": f"Prior to {departure_time} boarding",
                "note": "Per airline policy: Covers delayed hours only; overnight accommodation not applicable for scheduled daytime departure."
            }
        }

    @staticmethod
    def initiate_refund(pnr: str, amount: float, passenger_name: str, flight_number: str, route: str) -> Dict[str, Any]:
        refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
        return {
            "tool": "initiate_refund",
            "status": "executed",
            "message": f"Initiated full refund of ₹{amount:,.0f} to original payment method (7 business days)",
            "card_type": "refund_receipt",
            "data": {
                "refund_id": refund_id,
                "pnr": pnr,
                "passenger_name": passenger_name,
                "flight_number": flight_number,
                "route": route,
                "amount": f"₹{amount:,.0f}",
                "payment_destination": "Original Payment Method (Card ending in 4821)",
                "timeline": "Processed in full within 7 business days",
                "status": "Processing Initiated"
            }
        }

    @staticmethod
    def priority_rebook_flight(pnr: str, passenger_name: str, loyalty_tier: str, original_flight: str, new_flight: str, new_departure: str, route: str) -> Dict[str, Any]:
        eticket = f"ETK-{uuid.uuid4().hex[:8].upper()}"
        return {
            "tool": "priority_rebook_flight",
            "status": "executed",
            "message": f"Rebooked passenger on {new_flight} departing {new_departure} at no charge ({loyalty_tier} Priority)",
            "card_type": "rebooking_pass",
            "data": {
                "eticket": eticket,
                "pnr": pnr,
                "passenger_name": passenger_name,
                "loyalty_tier": loyalty_tier,
                "original_flight": original_flight,
                "confirmed_flight": new_flight,
                "route": route,
                "departure": new_departure,
                "seat_assignment": "12A (Priority Allocated)",
                "fare_difference_paid": "₹0.00 (Airline-Caused Disruption Waived)",
                "status": "Confirmed"
            }
        }

    @staticmethod
    def escalate_to_supervisor(pnr: str, customer_name: str, loyalty_tier: str, flight_number: str, reason: str, sentiment: str, transcript_summary: str, requested_waiver_amount: float = None, requested_perk: str = None) -> Dict[str, Any]:
        ticket_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
        return {
            "tool": "escalate_to_supervisor",
            "status": "escalated",
            "message": f"Escalated case {ticket_id} to Specialist Support & Supervisor Team",
            "card_type": "escalation_ticket",
            "data": {
                "ticket_id": ticket_id,
                "pnr": pnr,
                "customer_name": customer_name,
                "loyalty_tier": loyalty_tier,
                "flight_number": flight_number,
                "escalation_reason": reason,
                "customer_sentiment": sentiment,
                "requested_waiver_amount": f"₹{requested_waiver_amount:,.0f}" if requested_waiver_amount else None,
                "requested_perk": requested_perk,
                "status": "Urgent Human Handover (Priority Queue)",
                "transcript_summary": transcript_summary
            }
        }
