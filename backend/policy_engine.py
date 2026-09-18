"""
Policy Engine: Strict enforcement of airline disruption service rules & guardrails.
Based strictly on Assignment 3 Data Pack (23 September 2026).
"""
import re
from typing import Dict, Any, List, Tuple
from backend.data_pack import SERVICE_POLICIES, ALLOWED_ACTIONS, PROHIBITED_ACTIONS

class PolicyEngine:
    @staticmethod
    def evaluate_cancellation_rebooking(booking: Dict[str, Any], rebook_within_24h: bool = True) -> Dict[str, Any]:
        """
        Rule: If a flight is cancelled by the airline, the customer is entitled to a free
        rebooking on the next available flight within 24 hours, or a full refund, customer's choice.
        """
        if booking.get("disruption_type") != "cancellation":
            return {"allowed": False, "reason": "Flight is not cancelled."}
        
        if not booking.get("airline_caused", True):
            return {
                "allowed": False, 
                "prohibited_action": "Making exceptions for non-airline-caused disruptions",
                "escalate": True,
                "reason": "Cancellation was not airline-caused. Exceptions require supervisor approval."
            }

        return {
            "allowed": True,
            "entitlements": [
                "Free rebooking on next available flight within 24 hours",
                "Full refund to original payment method (processed in 7 business days)"
            ],
            "cost": 0,
            "policy": "Cancellation Rebooking Rule"
        }

    @staticmethod
    def evaluate_delay_compensation(delay_hours: float) -> Dict[str, Any]:
        """
        Delay Compensation Rule:
        - Delay under 3 hours: ₹500 meal voucher
        - Delay more than 3 hours: meal voucher + lounge access
        - Delay more than 5 hours: meal voucher + hotel accommodation, covering only the delayed hours (not a full night's stay)
        """
        if delay_hours < 3.0:
            return {
                "tier": "under_3h",
                "meal_voucher": 500,
                "lounge_access": False,
                "hotel_eligible": False,
                "entitlements": ["₹500 meal voucher"],
                "policy": "Delay under 3 hours: ₹500 meal voucher"
            }
        elif 3.0 <= delay_hours <= 5.0:
            return {
                "tier": "3h_to_5h",
                "meal_voucher": 750,
                "lounge_access": True,
                "hotel_eligible": False,
                "entitlements": ["Meal voucher", "Lounge access pass"],
                "policy": "Delay more than 3 hours: meal voucher + lounge access"
            }
        else: # delay_hours > 5.0
            return {
                "tier": "more_than_5h",
                "meal_voucher": 1000,
                "lounge_access": True,
                "hotel_eligible": True,
                "hotel_scope": "delayed_hours_only",
                "entitlements": [
                    "Meal voucher", 
                    "Lounge access", 
                    "Day-use hotel accommodation covering only delayed hours (not a full night's stay)"
                ],
                "policy": "Delay more than 5 hours: meal voucher + hotel accommodation, covering only delayed hours (not a full night's stay)"
            }

    @staticmethod
    def evaluate_refund_request(booking: Dict[str, Any], requested_payment_method: str = "original") -> Dict[str, Any]:
        """
        Refund Processing Rule:
        Refunds for airline-caused cancellations are processed in full within 7 business days.
        Refunds are issued to the original payment method only.
        Prohibited: Processing refunds to a different payment method than the original.
        """
        if requested_payment_method != "original":
            return {
                "allowed": False,
                "prohibited_action": "Processing refunds to a different payment method than the original",
                "escalate": True,
                "reason": "Policy strictly prohibits processing refunds to an alternate payment method. Requires specialist escalation."
            }
        
        if booking.get("disruption_type") != "cancellation":
            return {
                "allowed": False,
                "reason": "Full refund under disruption policy applies to airline-caused cancellations."
            }

        return {
            "allowed": True,
            "refund_amount": booking.get("fare_paid", 5000),
            "timeline": "7 business days",
            "destination": "Original payment method",
            "policy": "Refund Processing Rule"
        }

    @staticmethod
    def evaluate_fare_difference_waiver(fare_difference: float) -> Dict[str, Any]:
        """
        Fare Difference Rule:
        If a customer voluntarily chooses to rebook on a higher-fare flight (not airline-caused),
        they must pay the fare difference. Agents cannot waive fare differences above ₹1,500 without supervisor approval.
        """
        if fare_difference <= 0:
            return {"allowed": True, "requires_waiver": False, "fare_difference": 0}
        
        if fare_difference <= 1500:
            return {
                "allowed": True,
                "requires_waiver": True,
                "can_agent_waive": True,
                "fare_difference": fare_difference,
                "policy": "Fare difference up to ₹1,500 can be waived with standard agent authority if justified."
            }
        else:
            return {
                "allowed": False,
                "requires_waiver": True,
                "can_agent_waive": False,
                "prohibited_action": "Waiving a fare difference above ₹1,500",
                "escalate": True,
                "fare_difference": fare_difference,
                "waiver_cap": 1500,
                "reason": f"Requested waiver of ₹{fare_difference:,.0f} exceeds the agent discretionary authority cap of ₹1,500. Supervisor approval required."
            }

    @staticmethod
    def evaluate_loyalty_benefits(tier: str, requested_benefit: str) -> Dict[str, Any]:
        """
        Loyalty Tier Rule:
        Gold and Platinum tier customers get priority rebooking (first access to next-available seats)
        but NO additional compensation beyond the standard policy.
        Prohibited: Approving any compensation beyond the stated policy amounts (e.g., complimentary upgrades).
        """
        tier_upper = tier.capitalize()
        is_priority = tier_upper in ["Gold", "Platinum"]
        
        # Check if customer requests seat upgrade or cash compensation beyond policy
        upgrade_keywords = ["upgrade", "business class", "first class", "free ticket", "extra compensation", "bonus"]
        is_upgrade_request = any(k in requested_benefit.lower() for k in upgrade_keywords)
        
        if is_upgrade_request:
            return {
                "allowed": False,
                "prohibited_action": "Approving any compensation beyond the stated policy amounts",
                "is_priority_rebooking_eligible": is_priority,
                "tier": tier,
                "reason": f"{tier_upper} tier entitles passenger to priority rebooking on available seats, but policy strictly prohibits complimentary seat class upgrades or extra compensation beyond standard rules."
            }

        return {
            "allowed": True,
            "tier": tier,
            "is_priority_rebooking_eligible": is_priority,
            "perks": ["Priority rebooking access (first access to next-available seats)"] if is_priority else []
        }

    @staticmethod
    def detect_legal_or_formal_threat(text: str) -> Tuple[bool, str]:
        """
        Prohibited Action: Handling threats of legal action or formal complaints — must be escalated immediately.
        """
        patterns = [
            (r"\b(legal action|lawyer|attorney|sue|court|lawsuit|consumer court)\b", "Threat of legal action detected"),
            (r"\b(formal complaint|official complaint|director general|aviation ministry|ombudsman|consumer forum)\b", "Formal regulatory/ombudsman complaint mentioned"),
            (r"\b(going to the media|press|social media storm|viral on twitter)\b", "Public media / PR escalation threat")
        ]
        
        for pattern, reason in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True, reason
        return False, ""
