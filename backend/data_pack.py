"""
Data Pack - Assignment 3: Customer-Facing Resolution Agent (Airline Disruption)
Operational Date: Wednesday, 23 September 2026.
"""

OPERATIONAL_DATE = "Wednesday, 23 September 2026"

INITIAL_CUSTOMERS = {
    "SK4821X": {
        "pnr": "SK4821X",
        "name": "Priya Nair",
        "loyalty_tier": "Gold",
        "email": "priya.nair@example.com",
        "phone": "+91-98xxxxxxx1",
        "travel_history": {
            "flights_last_12m": 6,
            "prior_complaints": [
                {
                    "issue": "delayed baggage",
                    "resolution": "resolved with voucher",
                    "date": "2026-04-10"
                }
            ]
        },
        "bookings": [
            {
                "flight_number": "SK-204",
                "route": "Delhi → Goa",
                "date": "Wed 23 Sep 2026",
                "scheduled_departure": "18:40",
                "status": "Cancelled (operational reasons)",
                "disruption_type": "cancellation",
                "airline_caused": True,
                "is_return": False,
                "fare_paid": 6500
            },
            {
                "flight_number": "SK-205",
                "route": "Goa → Delhi",
                "date": "Fri 25 Sep 2026",
                "scheduled_departure": "16:20",
                "status": "Unaffected",
                "disruption_type": "none",
                "airline_caused": False,
                "is_return": True,
                "fare_paid": 6800,
                "cabin_class": "Economy"
            }
        ],
        "scenario_description": "Scenario 1: Priya contacts about cancelled flight SK-204. Partway she is 'furious' and wants a full cash refund PLUS a free upgrade to business class on her return flight 'for the trouble'."
    },
    "TR1190B": {
        "pnr": "TR1190B",
        "name": "Arvind Kulkarni",
        "loyalty_tier": "Silver",
        "email": "arvind.kulkarni@example.com",
        "phone": "+91-98xxxxxxx2",
        "travel_history": {
            "flights_last_12m": 3,
            "prior_complaints": []
        },
        "bookings": [
            {
                "flight_number": "SK-118",
                "route": "Mumbai → Bengaluru",
                "date": "Wed 23 Sep 2026",
                "scheduled_departure": "07:10",
                "revised_departure": "11:10",
                "delay_duration_hours": 4.0,
                "status": "Delayed 4h (new departure 11:10)",
                "disruption_type": "delay",
                "airline_caused": True,
                "is_return": False,
                "fare_paid": 4200
            }
        ],
        "scenario_description": "Scenario 2: Arvind's flight SK-118 is delayed 4 hours. He is frustrated about missing a connecting meeting and asks for hotel accommodation 'since it's been such a long delay'."
    },
    "WL7742": {
        "pnr": "WL7742",
        "name": "Meher Kaur",
        "loyalty_tier": "Platinum",
        "email": "meher.kaur@example.com",
        "phone": "+91-98xxxxxxx3",
        "travel_history": {
            "flights_last_12m": 10,
            "prior_complaints": [
                {
                    "issue": "overbooking",
                    "resolution": "resolved with a tier-status upgrade",
                    "date": "2026-02-15"
                }
            ]
        },
        "bookings": [
            {
                "flight_number": "SK-305",
                "route": "Delhi → Hyderabad",
                "date": "Wed 23 Sep 2026",
                "scheduled_departure": "14:00",
                "revised_departure": "20:00",
                "delay_duration_hours": 6.0,
                "status": "Delayed 6h (new departure 20:00)",
                "disruption_type": "delay",
                "airline_caused": True,
                "is_return": False,
                "fare_paid": 5800
            }
        ],
        "scenario_description": "Scenario 3: Meher's flight SK-305 is delayed 6 hours. She asks for a full night's hotel stay rather than coverage for just delayed hours, and separately asks to move onto a higher-fare flight (fare diff: ₹2,000)."
    }
}

SERVICE_POLICIES = {
    "cancellation_rebooking": {
        "name": "Cancellation Rebooking Rule",
        "summary": "If a flight is cancelled by the airline, customer is entitled to free rebooking on next available flight within 24 hours, OR full refund, customer's choice.",
        "max_rebooking_window_hours": 24,
        "is_free": True
    },
    "delay_compensation": {
        "name": "Delay Compensation Rule",
        "tiers": [
            {
                "condition": "delay under 3 hours",
                "max_delay_hours": 3.0,
                "entitlements": ["₹500 meal voucher"],
                "voucher_amount": 500,
                "hotel_eligible": False,
                "lounge_eligible": False
            },
            {
                "condition": "delay more than 3 hours",
                "min_delay_hours": 3.0,
                "max_delay_hours": 5.0,
                "entitlements": ["Meal voucher", "Lounge access"],
                "voucher_amount": 750,
                "hotel_eligible": False,
                "lounge_eligible": True
            },
            {
                "condition": "delay more than 5 hours",
                "min_delay_hours": 5.0,
                "entitlements": ["Meal voucher", "Hotel accommodation (covering only delayed hours, not full night)"],
                "voucher_amount": 1000,
                "hotel_eligible": True,
                "hotel_coverage_type": "delayed_hours_only",
                "lounge_eligible": True
            }
        ]
    },
    "refund_processing": {
        "name": "Refund Processing Rule",
        "summary": "Refunds for airline-caused cancellations are processed in full within 7 business days. Issued to original payment method only.",
        "timeline_business_days": 7,
        "original_payment_method_strict": True
    },
    "fare_difference": {
        "name": "Fare Difference Rule",
        "summary": "If customer voluntarily rebooks on a higher-fare flight (not airline-caused), they must pay the fare difference. Agents cannot waive fare differences above ₹1,500 without supervisor approval.",
        "agent_waiver_cap": 1500
    },
    "loyalty_tier": {
        "name": "Loyalty Tier Rule",
        "summary": "Gold and Platinum customers get priority rebooking (first access to next-available seats) but no additional compensation beyond standard policy.",
        "priority_rebooking_tiers": ["Gold", "Platinum"],
        "extra_compensation_allowed": False
    }
}

ALLOWED_ACTIONS = [
    "Rebook the customer on the next available flight within 24 hours at no charge (airline-caused disruption)",
    "Issue meal vouchers and lounge access per the delay compensation rule",
    "Arrange hotel accommodation for the delayed-hours portion, where the delay qualifies (>5h)",
    "Initiate a refund request for airline-caused cancellations (7 business days, original payment method)",
    "Provide the customer's own booking and flight status information"
]

PROHIBITED_ACTIONS = [
    "Approving any compensation beyond the stated policy amounts (e.g., complimentary business class upgrade)",
    "Waiving a fare difference above ₹1,500 without supervisor approval",
    "Making exceptions for non-airline-caused disruptions (e.g., customer missed the flight)",
    "Handling threats of legal action or formal complaints — must be escalated immediately",
    "Processing refunds to a different payment method than the original"
]

SAMPLE_PRIOR_CONVERSATIONS = [
    {
        "id": "Sample A",
        "customer": "My flight got cancelled and no one told me anything!",
        "agent": "I completely understand the frustration — I can see flight SK-190 was cancelled due to operational reasons. I can rebook you on the next available flight at no extra cost, or process a full refund. Which would you prefer?"
    },
    {
        "id": "Sample B",
        "customer": "I want compensation, this delay ruined my whole day.",
        "agent": "I'm sorry for the disruption. Your flight was delayed 3 hours 40 minutes, which qualifies for a meal voucher and lounge access under our policy. I've applied both to your account now."
    },
    {
        "id": "Sample C",
        "customer": "This is unacceptable, I'm going to file a formal complaint and consider legal action over this.",
        "agent": "I hear you, and I'm sorry this has been such a frustrating experience. I want to make sure this gets the right attention — I'm escalating this to our specialist support team right now, and they'll reach out to you directly."
    }
]
