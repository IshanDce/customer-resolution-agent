# AeroResolve AI — Customer-Facing Resolution Agent (Airline Disruption)

An autonomous, empathetic, and policy-grounded AI resolution agent built strictly to the specifications of **Assignment 3: Customer-Facing Resolution Agent (Airline Disruption)**.

Operational Date Anchor: **Wednesday, 23 September 2026**.

---

## ⚡ Quick Start (One-Command Local Run)

### Prerequisites
- Python 3.10+ (FastAPI, Uvicorn, and Pydantic)

### 1-Command Run
```bash
python main.py
```
Open your browser to:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📋 Assignment 3 Scenario Coverage

| Scenario | Passenger | Loyalty Tier | Disruption | Customer Demands | Agent Resolution & Guardrail Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario 1** | **Priya Nair** (`SK4821X`) | **Gold** | `SK-204` (DEL → GOI) **Cancelled** (Operational reasons). *Return SK4821X on 25 Sep unaffected.* | Partway, she is "furious" and wants a **full cash refund** PLUS a **free upgrade to business class** on her return flight. | • Empathetically acknowledges disruption.<br>• Initiates full refund to original payment method (7 business days).<br>• Strictly **declines free business class upgrade** (prohibited compensation beyond policy).<br>• Clarifies Gold tier gives priority rebooking, not complimentary upgrades. |
| **Scenario 2** | **Arvind Kulkarni** (`TR1190B`) | **Silver** | `SK-118` (BOM → BLR) **Delayed 4h** (07:10 → 11:10). | Frustrated about missing a connecting meeting; asks for **hotel accommodation**. | • Empathetically validates missed meeting.<br>• Issues **₹750 meal voucher** and **executive lounge access** (with quiet workstations & Wi-Fi).<br>• Transparently clarifies that hotel accommodation requires a **>5h delay** (declines hotel politely). |
| **Scenario 3** | **Meher Kaur** (`WL7742`) | **Platinum** | `SK-305` (DEL → HYD) **Delayed 6h** (14:00 → 20:00). | 1. Asks for a **full night hotel stay** rather than coverage for delayed hours.<br>2. Asks to move onto a higher-fare flight (**fare difference: ₹2,000**). | • Arranges **day-use transit hotel room** covering delayed hours only (declines full night stay).<br>• Issues **₹1,000 meal voucher**.<br>• Explains voluntary rebooking rules: ₹2,000 exceeds agent waiver cap of ₹1,500.<br>• Escalates ticket to **Duty Supervisor** for Platinum waiver review. |

---

## 🛡️ Policy & Guardrail Enforcement

### Allowed Actions (Executed via Tool Engine)
1. **`priority_rebook_flight`**: Rebook passenger on next available flight within 24h at no charge for airline-caused disruptions.
2. **`issue_meal_voucher`**: Issue ₹500 (<3h), ₹750 (>3h), or ₹1,000 (>5h) meal vouchers.
3. **`issue_lounge_access`**: Grant executive airport lounge access passes for delays >3h.
4. **`arrange_day_hotel`**: Book transit hotel day-room strictly for delayed hours (>5h delay).
5. **`initiate_refund`**: Process full refund to original payment method within 7 business days.
6. **`get_booking_status`**: Provide flight and CRM travel history information.

### Prohibited Actions (Blocked & Escalated)
1. ❌ **Approving compensation beyond stated policy** (e.g. complimentary business class upgrades or unapproved cash).
2. ❌ **Waiving fare differences above ₹1,500** without supervisor approval.
3. ❌ **Making exceptions for non-airline-caused disruptions** (e.g. passenger missed flight).
4. ❌ **Handling threats of legal action or formal complaints** — immediately triggers `escalate_to_supervisor`.
5. ❌ **Processing refunds to a different payment method** than the original.

---

## 👥 Extensibility & Returning User Memory

- **CRM History**: Recognizes past flight counts and previous complaint resolutions (e.g., Priya's delayed baggage voucher or Meher's overbooking upgrade).
- **Custom Passenger / Data Builder**: Click the **"+ Custom Passenger / Data"** button in the top bar to add arbitrary passengers with custom flight numbers, delay hours, or cancellation reasons, demonstrating how the agent adapts to any customer dynamically!
- **Agent Brain HUD**: Real-time inspection panel showing detected sentiment, active policy rules, allowed vs prohibited checkmarks, and tool execution logs.
- **Supervisor Portal**: Live ticket review queue where supervisors can review escalated cases and approve/decline waivers.

---

## 🛠️ Admin Panel & Support Tickets

An **Admin Panel** treats every customer complaint as a support ticket. One ticket is auto-created per customer PNR as soon as that customer has any conversation history or an escalation, and the ticket thread is the PNR's full message history.

### How it works
1. **Admin Panel button** in the header opens the ticket management overlay.
2. The admin sees all customer tickets, selects one, reads the full thread (customer + AI agent messages), and writes a reply.
3. Submitting a reply appends it to that customer's conversation history, so it appears in the existing customer-facing chat feed.
4. Ticket status advances **`open` → `answered` → `resolved`** (a new customer message reopens an `answered` ticket back to `open`).
5. The **My Ticket** button opens a customer ticket thread view that reflects the linked API responses on refresh.

### Role-based access (simple role flag — no login)
| Role | Access |
| :--- | :--- |
| `admin` | List all tickets, fetch any ticket thread, respond to tickets. |
| `customer` | List and fetch only their own PNR's ticket thread. |

### Backend API summary
| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/tickets?role=admin` | List all support tickets. |
| `GET` | `/api/tickets?role=customer&pnr=SK4821X` | List a customer's own tickets. |
| `GET` | `/api/tickets/{ticket_id}?role=...&pnr=...` | Fetch one ticket with full thread + status history. |
| `POST` | `/api/tickets/{ticket_id}/respond` | Admin-only response (`{ "reply": "...", "resolve": false, "role": "admin" }`). |

Mount the router in the existing FastAPI server:
```python
from backend.ticket_routes import ticket_router
app.include_router(ticket_router)
```

---

## 🧪 Automated Testing

Run the automated test suite verifying all assignment rules and threshold checks:
```bash
python backend/test_scenarios.py
```
Output:
```text
======================================================================
STARTING TEST SUITE: AIRLINE DISRUPTION RESOLUTION AGENT
======================================================================
[PASS] Test 1: Policy Engine Unit Thresholds passed.
[PASS] Test 2: Scenario 1 (Priya Nair - Refund granted, Business upgrade prohibited) passed.
[PASS] Test 3: Scenario 2 (Arvind Kulkarni - Hotel declined for 4h, Lounge & Voucher granted) passed.
[PASS] Test 4: Scenario 3 (Meher Kaur - Day hotel granted, INR 2000 waiver escalated to supervisor) passed.
[PASS] Test 5: Legal threat triggers immediate escalation passed.
[PASS] Test 6: Support ticket auto-creation per PNR passed.
[PASS] Test 7: Admin response updates thread and ticket status passed.
[PASS] Test 8: Role-based ticket access and admin response passed.
======================================================================
ALL TESTS PASSED: 8/8 (100% Coverage of Assignment Rules)
======================================================================
```
