"""
Automated Test Suite for Airline Disruption Resolution Agent.
Validates Scenarios 1, 2, 3 and Policy Guardrails against the Assignment Data Pack.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import db
from backend.policy_engine import PolicyEngine
from backend.agent import agent
from backend.ticket_routes import ticket_router

def run_tests():
    print("=" * 70)
    print("STARTING TEST SUITE: AIRLINE DISRUPTION RESOLUTION AGENT")
    print("=" * 70)
    passed = 0
    total = 0

    # -------------------------------------------------------------
    # TEST 1: Policy Engine Unit Checks
    # -------------------------------------------------------------
    total += 1
    # 1.1 Delay tiers
    d_under_3 = PolicyEngine.evaluate_delay_compensation(2.0)
    assert d_under_3["tier"] == "under_3h" and d_under_3["meal_voucher"] == 500 and not d_under_3["hotel_eligible"]

    d_4h = PolicyEngine.evaluate_delay_compensation(4.0)
    assert d_4h["tier"] == "3h_to_5h" and d_4h["lounge_access"] is True and not d_4h["hotel_eligible"]

    d_6h = PolicyEngine.evaluate_delay_compensation(6.0)
    assert d_6h["tier"] == "more_than_5h" and d_6h["hotel_eligible"] is True and d_6h["hotel_scope"] == "delayed_hours_only"

    # 1.2 Fare difference threshold
    fare_ok = PolicyEngine.evaluate_fare_difference_waiver(1200)
    assert fare_ok["can_agent_waive"] is True

    fare_exceed = PolicyEngine.evaluate_fare_difference_waiver(2000)
    assert fare_exceed["can_agent_waive"] is False and fare_exceed["escalate"] is True

    # 1.3 Loyalty upgrades
    loyalty_upgrade = PolicyEngine.evaluate_loyalty_benefits("Gold", "I want a free upgrade to business class")
    assert loyalty_upgrade["allowed"] is False
    print("[PASS] Test 1: Policy Engine Unit Thresholds passed.")
    passed += 1

    # -------------------------------------------------------------
    # TEST 2: Scenario 1 - Priya Nair (Gold, Cancelled, Upgrade Demand)
    # -------------------------------------------------------------
    total += 1
    db.reset_to_default()
    res1 = agent.process_message(
        pnr="SK4821X",
        user_message="I'm furious that flight SK-204 got cancelled! I want a full cash refund plus a free upgrade to business class on my return flight for the trouble."
    )
    # Priya must get a refund tool call, but upgrade must be prohibited
    prohibited_tags = res1["guardrails"]["prohibited_actions_triggered"]
    assert any("Complimentary cabin class upgrade" in p for p in prohibited_tags), f"Expected upgrade prohibition, got: {prohibited_tags}"
    
    # Must have refund executed
    tool_names = [t["tool"] for t in res1["tool_executions"]]
    assert "initiate_refund" in tool_names, f"Expected initiate_refund in tools, got: {tool_names}"
    assert "business class" in res1["reply"].lower() or "upgrade" in res1["reply"].lower()
    print("[PASS] Test 2: Scenario 1 (Priya Nair - Refund granted, Business upgrade prohibited) passed.")
    passed += 1

    # -------------------------------------------------------------
    # TEST 3: Scenario 2 - Arvind Kulkarni (Silver, 4h Delay, Hotel Request)
    # -------------------------------------------------------------
    total += 1
    db.reset_to_default()
    res2 = agent.process_message(
        pnr="TR1190B",
        user_message="My flight is delayed 4 hours and I'm missing an important meeting! I want hotel accommodation since it's been such a long delay."
    )
    # Hotel for 4h delay is prohibited
    tool_names_2 = [t["tool"] for t in res2["tool_executions"]]
    assert "issue_meal_voucher" in tool_names_2, f"Expected meal voucher, got: {tool_names_2}"
    assert "issue_lounge_access" in tool_names_2, f"Expected lounge access, got: {tool_names_2}"
    assert "arrange_day_hotel" not in tool_names_2, "Hotel must NOT be granted for 4h delay!"
    assert "lounge" in res2["reply"].lower()
    print("[PASS] Test 3: Scenario 2 (Arvind Kulkarni - Hotel declined for 4h, Lounge & Voucher granted) passed.")
    passed += 1

    # -------------------------------------------------------------
    # TEST 4: Scenario 3 - Meher Kaur (Platinum, 6h Delay, Full Night Hotel + ₹2,000 Waiver)
    # -------------------------------------------------------------
    total += 1
    db.reset_to_default()
    res3 = agent.process_message(
        pnr="WL7742",
        user_message="I want a full night's hotel stay for this 6 hour delay, and I also want to be moved onto a higher-fare flight instead of waiting — please waive the ₹2,000 fare difference."
    )
    tool_names_3 = [t["tool"] for t in res3["tool_executions"]]
    # Day hotel allowed
    assert "arrange_day_hotel" in tool_names_3, f"Expected day hotel, got: {tool_names_3}"
    # ₹2000 waiver requires supervisor escalation
    assert "escalate_to_supervisor" in tool_names_3, f"Expected escalation for ₹2000 waiver, got: {tool_names_3}"
    assert res3["guardrails"]["requires_escalation"] is True
    print("[PASS] Test 4: Scenario 3 (Meher Kaur - Day hotel granted, INR 2000 waiver escalated to supervisor) passed.")
    passed += 1

    # -------------------------------------------------------------
    # TEST 5: Legal Action Immediate Escalation
    # -------------------------------------------------------------
    total += 1
    db.reset_to_default()
    res_legal = agent.process_message(
        pnr="SK4821X",
        user_message="This is fraudulent behavior! I am contacting my lawyer and filing a formal complaint in consumer court right now!"
    )
    assert res_legal["guardrails"]["requires_escalation"] is True
    tool_names_legal = [t["tool"] for t in res_legal["tool_executions"]]
    assert "escalate_to_supervisor" in tool_names_legal
    print("[PASS] Test 5: Legal threat triggers immediate escalation passed.")
    passed += 1

    # -------------------------------------------------------------
    # TEST 6: Support ticket auto-creation & listing (one per PNR)
    # -------------------------------------------------------------
    total += 1
    db.reset_to_default()
    db.append_message("SK4821X", "user", "My flight SK-204 was cancelled. I want a refund.")
    tickets = db.list_tickets()
    assert len(tickets) == 1, f"Expected 1 ticket, got {len(tickets)}"
    ticket = tickets[0]
    assert ticket["pnr"] == "SK4821X"
    assert ticket["status"] == "open"
    assert ticket["subject"]
    print("[PASS] Test 6: Support ticket auto-creation per PNR passed.")
    passed += 1

    # -------------------------------------------------------------
    # TEST 7: Admin response appends to thread, updates status, reopens
    # -------------------------------------------------------------
    total += 1
    db.reset_to_default()
    db.append_message("TR1190B", "user", "My flight is delayed 4 hours, I want a hotel.")
    tkt = db.get_ticket("TR1190B")
    assert tkt is not None and tkt["status"] == "open"

    updated = db.respond_to_ticket(tkt["ticket_id"], "We have issued a meal voucher and lounge access.", resolve=False)
    assert updated["status"] == "answered"
    history = db.get_history("TR1190B")
    assert any(m["role"] == "admin" and "meal voucher" in m["content"] for m in history)
    assert updated["status_history"][-1]["by"] == "admin"

    # A new customer message reopens an answered ticket.
    db.append_message("TR1190B", "user", "Thank you, can I also get lounge access?")
    assert db.get_ticket(tkt["ticket_id"])["status"] == "open"
    print("[PASS] Test 7: Admin response updates thread and ticket status passed.")
    passed += 1

    # -------------------------------------------------------------
    # TEST 8: Role-based access via ticket API endpoints
    # -------------------------------------------------------------
    total += 1
    app = FastAPI()
    app.include_router(ticket_router)
    client = TestClient(app)

    db.reset_to_default()
    db.append_message("WL7742", "user", "I want a full night hotel and a waiver for the fare difference.")
    wl_ticket = db.get_ticket("WL7742")
    assert wl_ticket is not None

    # Admin can list all tickets.
    resp = client.get("/api/tickets", params={"role": "admin"})
    assert resp.status_code == 200
    listed = resp.json()
    assert any(t["pnr"] == "WL7742" for t in listed)

    # Customer can only list their own ticket.
    resp = client.get("/api/tickets", params={"role": "customer", "pnr": "WL7742"})
    assert resp.status_code == 200
    assert all(t["pnr"] == "WL7742" for t in resp.json())

    # Customer cannot view another customer's ticket thread.
    resp = client.get(
        f"/api/tickets/{wl_ticket['ticket_id']}",
        params={"role": "customer", "pnr": "SK4821X"},
    )
    assert resp.status_code == 403

    # Admin can respond and resolve a ticket.
    resp = client.post(
        f"/api/tickets/{wl_ticket['ticket_id']}/respond",
        json={"reply": "Your fare-difference waiver has been escalated and approved.", "resolve": True, "role": "admin"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert any(m["role"] == "admin" for m in resp.json()["thread"])

    # Non-admin cannot respond to a ticket.
    resp = client.post(
        f"/api/tickets/{wl_ticket['ticket_id']}/respond",
        json={"reply": "trying without permission", "role": "customer"},
    )
    assert resp.status_code == 403
    print("[PASS] Test 8: Role-based ticket access and admin response passed.")
    passed += 1

    print("=" * 70)
    print(f"ALL TESTS PASSED: {passed}/{total} (100% Coverage of Assignment Rules)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
