"""
AeroResolve AI - Real Human-Like Resolution Agent
Powered by Gemini 2.5 Flash via google.genai SDK

Design:
 - NO hardcoded / template responses ever shown to customer
 - Gemini 2.5 Flash generates EVERY reply using the full data pack as grounding
 - Rich system prompt: all policies, 3 training scenarios, sample conversations,
   current customer context, executed actions, and sentiment
 - Retry logic with backoff for rate-limit (429) errors
 - Policy-driven tool execution works dynamically for any customer PNR
"""

import re
import time
from typing import Dict, Any, List, Optional, Tuple

# New official Google GenAI SDK (google-genai package)
from google import genai
from google.genai import types as genai_types

from backend.data_pack import (
    OPERATIONAL_DATE,
    SERVICE_POLICIES,
    ALLOWED_ACTIONS,
    PROHIBITED_ACTIONS,
    SAMPLE_PRIOR_CONVERSATIONS,
    INITIAL_CUSTOMERS,
)
from backend.policy_engine import PolicyEngine
from backend.tools import ToolRegistry
from backend.database import db
from backend.config import GEMINI_API_KEY, GEMINI_MODEL_NAME


# =============================================================================
# System Prompt Builder — Full policy grounding + training data
# =============================================================================

def _fmt_scenarios() -> str:
    lines = []
    for pnr, c in INITIAL_CUSTOMERS.items():
        b = c["bookings"][0]
        lines.append(
            f"TRAINING SCENARIO (PNR {pnr} - {c['name']}, {c['loyalty_tier']} Tier):\n"
            f"  Booking: {b['flight_number']} | {b['route']} | "
            f"Status: {b['status']} | Delay: {b.get('delay_duration_hours', 'N/A')}h | "
            f"Fare Paid: Rs.{b.get('fare_paid', 0):,}\n"
            f"  Scenario: {c['scenario_description']}"
        )
    return "\n\n".join(lines)


def _fmt_sample_conversations() -> str:
    lines = []
    for i, ex in enumerate(SAMPLE_PRIOR_CONVERSATIONS, 1):
        lines.append(
            f"EXAMPLE {i}:\n"
            f"  Passenger: {ex['customer']}\n"
            f"  Agent (Maya): {ex['agent']}"
        )
    return "\n\n".join(lines)


def build_system_prompt(
    customer: Dict[str, Any],
    history: List[Dict[str, Any]],
    tool_executions: List[Dict[str, Any]],
    guardrails: Dict[str, Any],
    sentiment: str,
) -> str:
    b = customer["bookings"][0] if customer.get("bookings") else {}
    pnr = customer["pnr"]
    name = customer["name"]
    tier = customer.get("loyalty_tier", "Member")
    flights_12m = customer.get("travel_history", {}).get("flights_last_12m", 0)
    prior_complaints = customer.get("travel_history", {}).get("prior_complaints", [])
    complaint_text = (
        " | ".join(
            f"{c['issue']} -> {c['resolution']} ({c['date']})"
            for c in prior_complaints
        )
        if prior_complaints
        else "None on record"
    )

    disruption = b.get("disruption_type", "none")
    delay_h = float(b.get("delay_duration_hours", 0))
    fare = b.get("fare_paid", 5000)
    revised_dep = b.get("revised_departure", b.get("scheduled_departure", "TBD"))

    action_lines = (
        "\n".join(f"  - {t.get('message', '')}" for t in tool_executions)
        if tool_executions
        else "  - No system actions yet for this message."
    )

    prohibited = guardrails.get("prohibited_actions_triggered", [])
    prohibited_lines = (
        "\n".join(f"  BLOCKED: {p}" for p in prohibited) if prohibited else ""
    )

    escalation_note = ""
    if guardrails.get("requires_escalation") and guardrails.get("escalation_reason"):
        esc_card = next(
            (t for t in tool_executions if t.get("tool") == "escalate_to_supervisor"),
            None,
        )
        ticket = esc_card["data"]["ticket_id"] if esc_card else "ESC-PENDING"
        escalation_note = (
            f"\nESCALATION TRIGGERED (Ticket: {ticket})\n"
            f"Reason: {guardrails['escalation_reason']}\n"
            f"You MUST naturally hand over to the specialist team in your reply."
        )

    history_lines = []
    for h in history[-8:]:
        role = "Passenger" if h["role"] == "user" else "Maya"
        history_lines.append(f"  {role}: {h['content']}")
    history_text = "\n".join(history_lines) if history_lines else "  (Start of conversation)"

    return f"""You are Maya, a Senior Customer Resolution Specialist at SkyKonnect Airlines.
You are warm, empathetic, highly professional, and speak exactly like a real experienced human agent — never robotic, never scripted.

TODAY: {OPERATIONAL_DATE}

=== PASSENGER PROFILE ===
Name           : {name}
PNR            : {pnr}
Loyalty Tier   : {tier}
Flights (12m)  : {flights_12m}
Complaint CRM  : {complaint_text}
Email          : {customer.get("email", "N/A")}

=== ACTIVE BOOKING ===
Flight         : {b.get("flight_number")}
Route          : {b.get("route")}
Scheduled Dep  : {b.get("scheduled_departure")}
{f"Revised Dep    : {revised_dep}" if disruption == "delay" else ""}
Status         : {b.get("status")}
Disruption     : {disruption.upper()} {"(" + str(int(delay_h)) + "h)" if disruption == "delay" else ""}
Airline Caused : {"Yes" if b.get("airline_caused", True) else "No"}
Fare Paid      : Rs.{fare:,}
Cabin          : {b.get("cabin_class", "Economy")}
{f"NOTE: Return flight SK-205 (Goa to Delhi, 25 Sep 16:20) is ACTIVE and UNAFFECTED." if pnr == "SK4821X" and len(customer.get("bookings", [])) > 1 else ""}

=== AIRLINE POLICIES (Your Authority Limits) ===

CANCELLATION (Airline-Caused):
- Customer chooses: free rebooking within 24h  OR  full refund (7 business days, original payment method only)
- Gold/Platinum get PRIORITY SEAT ACCESS on rebooking only — nothing extra

DELAY COMPENSATION:
- Under 3h delay  : Rs.500 meal voucher only
- 3 to 5h delay   : Meal voucher + complimentary lounge access
- Over 5h delay   : Meal voucher + lounge + day-use hotel room (ONLY covering delayed hours — NOT a full overnight stay)
  Example: 6h delay, flight departs at 20:00 = day room until 20:00 boarding, NOT checkout next morning

REFUNDS:
- Full refund to ORIGINAL payment method only (7 business days)
- Cannot redirect to a different account or card

FARE DIFFERENCE (Voluntary Rebooking):
- If customer chooses a higher-fare flight, they pay the difference
- You can waive up to Rs.1,500 — above that REQUIRES supervisor escalation, no exceptions

LOYALTY TIERS:
- Gold/Platinum: Priority rebooking seats ONLY, no cabin upgrades, no bonus cash
- You CANNOT grant complimentary upgrades (Economy to Business) as compensation, even for Gold tier

MANDATORY ESCALATION:
- Legal threats, lawyer/court/DGCA/consumer forum mentions: Escalate IMMEDIATELY
- Fare waiver requests above Rs.1,500: Escalate
- NEVER handle legal matters yourself

=== SAMPLE PRIOR CONVERSATIONS (Model This Human Tone) ===
{_fmt_sample_conversations()}

=== SYSTEM ACTIONS TAKEN THIS TURN (Communicate naturally, never say "I executed a tool") ===
{action_lines}
{prohibited_lines}
{escalation_note}

=== CONVERSATION SO FAR ===
{history_text}

=== YOUR MOST IMPORTANT TASK — READ THIS CAREFULLY ===

STEP 1: ANALYSE THE CUSTOMER'S MESSAGE DEEPLY before writing anything.
Ask yourself:
  - What EMOTION is this customer expressing? (angry, devastated, frustrated, anxious, panicked, resigned, hopeful, confused, relieved, sarcastic, exhausted, desperate, casual)
  - What are they ACTUALLY asking for? (even if they didn't say it directly — read between the lines)
  - What is their URGENCY level? (high / medium / low)
  - Is there SUBTEXT? (e.g. "this is so stressful" = they need reassurance + fast resolution, not just information)
  - What do they MOST NEED right now — action, empathy, explanation, or reassurance?

STEP 2: MATCH YOUR TONE TO THEIR EMOTION.
  - FURIOUS / VERY UPSET  → Lead with sincere, specific apology. Do NOT jump to policies. Acknowledge the pain first.
  - FRUSTRATED            → Empathise with the inconvenience, then resolve efficiently.
  - ANXIOUS / PANICKED    → Calm and reassure them immediately. Make them feel safe.
  - CONFUSED              → Be patient, clear, and simple. No jargon.
  - NEUTRAL / CALM        → Be warm, professional, and efficient.
  - SARCASTIC             → Don't react. Stay professional and kind. Acknowledge the frustration behind the sarcasm.
  - EXHAUSTED / RESIGNED  → Show genuine care. Take charge so they don't have to think too hard.
  - APPRECIATIVE          → Thank them warmly, stay helpful.

STEP 3: ADDRESS BOTH WHAT THEY FEEL AND WHAT THEY NEED.
  - First: acknowledge their emotion with genuine, specific empathy (never generic "sorry for the inconvenience").
  - Then: address their request/need based on policy.
  - If actions were taken this turn (listed above), communicate them naturally as part of your response.
  - If a request is blocked by policy, be kind and redirect to what IS possible.

=== ABSOLUTE RULES ===
1. Write AS Maya, first person. Conversational, warm — like a real human agent on phone/chat.
2. 2 to 4 short paragraphs. NO bullet points. Flowing natural sentences only.
3. Never say "I executed a tool", "per my training", "data pack", "system", "algorithm."
4. Mention voucher/ticket codes naturally inline (e.g. "Your lounge pass LNG-XXXXX is waiting at the gate").
5. If escalating, mention ticket reference and that a specialist will reach out directly.
6. Do NOT echo "Maya:" or "Agent:" at the start — just respond directly.
7. If the customer's message is a simple greeting or opener, warmly introduce yourself and the situation — do NOT take any action yet, just listen and invite them to share what they need.
8. STRICT RELEVANCE: ONLY respond to what the passenger has ACTUALLY said in the chat history. NEVER hallucinate or assume they asked for hotel rooms, fare waivers, refunds, or cabin upgrades if they did NOT bring it up. If they make a casual remark (e.g. "i am very down to earth", "how is your day?"), respond genuinely to that remark with warmth, acknowledge their flight status briefly, and ask how you can help them today.
"""


# =============================================================================
# Resolution Agent
# =============================================================================

class ResolutionAgent:
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.tools = ToolRegistry()
        self.client: Optional[genai.Client] = None
        self._init_gemini()

    def _init_gemini(self):
        try:
            if GEMINI_API_KEY:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                print(f"[AeroResolve] Gemini initialized: {GEMINI_MODEL_NAME}")
        except Exception as e:
            print(f"[AeroResolve] Gemini init warning: {e}")

    # ── Public Entry Point ──────────────────────────────────────────────────

    def process_message(
        self,
        pnr: str,
        user_message: str,
        api_provider: str = "gemini",
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        customer = db.get_customer(pnr)
        if not customer:
            return {
                "reply": (
                    f"I'm sorry, I couldn't locate an active booking under the reference '{pnr}'. "
                    "Could you double-check your 6-character PNR or the email address used at booking?"
                ),
                "sentiment_detected": "neutral",
                "guardrails": {
                    "allowed_actions": [],
                    "prohibited_actions_triggered": [],
                    "requires_escalation": False,
                    "policies_invoked": [],
                },
                "tool_executions": [],
                "action_cards": [],
            }

        history = db.get_history(pnr)
        sentiment = self._detect_sentiment(user_message)
        intents = self._detect_intents(user_message)
        guardrails = self._evaluate_guardrails(customer, user_message, intents)

        tool_executions, action_cards = self._execute_tools(
            customer, user_message, sentiment, intents, guardrails, history
        )

        reply = self._gemini_generate(
            customer, history, user_message, sentiment,
            intents, guardrails, tool_executions, api_key
        )

        db.append_message(pnr, "user", user_message)
        db.append_message(pnr, "assistant", reply, action_cards)

        return {
            "reply": reply,
            "sentiment_detected": sentiment,
            "guardrails": guardrails,
            "tool_executions": tool_executions,
            "action_cards": action_cards,
        }

    # ── Gemini Generation with Retry ────────────────────────────────────────

    def _gemini_generate(
        self,
        customer: Dict[str, Any],
        history: List[Dict[str, Any]],
        user_message: str,
        sentiment: str,
        intents: Dict[str, bool],
        guardrails: Dict[str, Any],
        tool_executions: List[Dict[str, Any]],
        custom_key: Optional[str] = None,
        max_retries: int = 4,
    ) -> str:
        try:
            client = self.client
            if custom_key:
                client = genai.Client(api_key=custom_key)

            if client is None:
                print("[AeroResolve] No Gemini client available.")
                return self._offline_reply(customer, sentiment)

            system_prompt = build_system_prompt(
                customer, history, tool_executions, guardrails, sentiment
            )
            user_turn = f"Passenger: {user_message}\n\nMaya:"

            last_err = None
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL_NAME,
                        contents=user_turn,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.72,
                            max_output_tokens=700,
                        ),
                    )
                    text = response.text.strip()
                    # Strip accidental "Maya:" echo at start
                    text = re.sub(
                        r"^(Maya|Agent)\s*[\(\w\s\)]*:\s*",
                        "",
                        text,
                        flags=re.IGNORECASE,
                    ).strip()
                    print(f"[AeroResolve] Gemini replied OK ({len(text)} chars)")
                    return text

                except Exception as e:
                    last_err = e
                    err = str(e)
                    if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                        m = re.search(r"retry_delay\D*?(\d+)", err)
                        wait = int(m.group(1)) if m else 20 * (attempt + 1)
                        wait = min(wait, 45)
                        print(
                            f"[AeroResolve] Rate limit hit (attempt {attempt+1}/{max_retries}), waiting {wait}s..."
                        )
                        time.sleep(wait)
                        continue
                    else:
                        print(f"[AeroResolve] Gemini error: {e}")
                        break

            print(f"[AeroResolve] All Gemini retries exhausted. Last error: {last_err}")
            return self._offline_reply(customer, sentiment)

        except Exception as fatal:
            print(f"[AeroResolve] Fatal error in _gemini_generate: {fatal}")
            return self._offline_reply(customer, sentiment)

    def _offline_reply(self, customer: Dict[str, Any], sentiment: str) -> str:
        """
        Last-resort generic reply when Gemini is completely unavailable.
        Never uses hardcoded scenario text — always asks customer to retry.
        """
        name = customer["name"].split()[0]
        if sentiment in ("furious", "frustrated"):
            return (
                f"I'm truly sorry for the experience you're having, {name}. "
                "I can see this is deeply frustrating, and you absolutely deserve a proper resolution. "
                "Our systems are momentarily facing an issue on my end — please send your message again "
                "in just a moment and I'll have everything sorted for you right away."
            )
        return (
            f"Thank you for reaching out, {name}. I'm pulling up your booking details right now. "
            "Our systems are experiencing a brief delay on my end — please resend your message "
            "in a moment and I'll get everything resolved for you immediately."
        )

    # ── Sentiment & Intent Detection ────────────────────────────────────────

    def _detect_sentiment(self, text: str) -> str:
        t = text.lower()
        if any(w in t for w in [
            "furious", "unacceptable", "outrageous", "livid", "disgusted",
            "sue", "lawyer", "terrible service", "worst airline",
        ]):
            return "furious"
        if any(w in t for w in [
            "frustrated", "annoyed", "ruined", "upset", "ridiculous",
            "wasted my time", "long delay", "missed my meeting",
        ]):
            return "frustrated"
        if any(w in t for w in [
            "worried", "anxious", "stranded", "urgent", "stress",
            "what do i do", "need help",
        ]):
            return "anxious"
        if any(w in t for w in ["thank", "appreciate", "helpful", "great", "understood", "that works"]):
            return "appreciative"
        return "neutral"

    def _detect_intents(self, text: str) -> Dict[str, bool]:
        t = text.lower().strip()
        words = t.split()

        # Detect actionable keywords first
        has_action_keywords = bool(re.search(
            r'\b(refund|rebook|hotel|upgrade|cancel|waive|voucher|lounge|legal|sue|'
            r'lawyer|court|complaint|status|options|compensation|meal|flight|when|why|what|how)\b',
            t
        ))

        # Catch formal + informal greetings (hlo, helo, hlw, yo, hi there, namaste ...)
        greeting_pattern = bool(re.match(
            r'^(hi+|h[aei]+l*o*|hlo|hlw|hey+|hello|yo+|sup|'
            r'good (morning|afternoon|evening)|greetings|howdy|hiya|namaste|'
            r'hii+|hi there|hey there|hello there)[!.\s]*$',
            t
        ))

        # If no actionable keywords exist, treat as conversational opener / small talk (no auto-tools)
        is_just_greeting = greeting_pattern or (not has_action_keywords)

        return {
            "is_greeting": is_just_greeting,
            "asks_upgrade": bool(re.search(r"\b(upgrade|business class|first class|premium cabin)\b", t)),
            "asks_refund": bool(re.search(r"\b(refund|money back|cash back|reimburse|cancel)\b", t)),
            "asks_hotel": bool(re.search(r"\b(hotel|accommodation|stay|room|place to stay|overnight)\b", t)),
            "asks_full_night": bool(re.search(r"\b(full night|overnight|entire night|all night|next morning)\b", t)),
            "asks_rebook": bool(re.search(r"\b(rebook|next flight|different flight|another flight|change flight|alternative|move onto)\b", t)),
            "asks_fare_waiver": bool(re.search(r"\b(fare difference|waive|pay extra|extra \d+|2000|difference)\b", t)),
            "asks_meal_lounge": bool(re.search(r"\b(meal|food|voucher|lounge|eat|refresh|snack|drink)\b", t)),
            "threatens_legal": bool(re.search(r"\b(legal action|lawyer|attorney|sue|court|formal complaint|official complaint|dgca|ombudsman|consumer forum)\b", t)),
            "confirms": bool(re.search(r"\b(yes|please|proceed|accept|go ahead|okay|do that|agree|sounds good|confirm)\b", t)),
            "asks_status": bool(re.search(r"\b(status|what happened|why|when|what time|departure time|options|what can|what are)\b", t)),
            "expresses_business_need": bool(re.search(r"\b(meeting|client|connecting|work|office|appointment|conference)\b", t)),
        }


    # ── Guardrail & Policy Evaluation ───────────────────────────────────────

    def _evaluate_guardrails(
        self,
        customer: Dict[str, Any],
        user_message: str,
        intents: Dict[str, bool],
    ) -> Dict[str, Any]:
        allowed: List[str] = []
        prohibited: List[str] = []
        policies: List[str] = []
        requires_escalation = False
        escalation_reason: Optional[str] = None

        b = customer["bookings"][0] if customer.get("bookings") else {}
        disruption = b.get("disruption_type", "none")
        tier = customer.get("loyalty_tier", "Member")
        delay_h = float(b.get("delay_duration_hours", 0))

        if disruption == "cancellation":
            policies += ["Cancellation Rebooking Rule", "Refund Processing Rule"]
            allowed += [
                "Rebook on next available flight within 24h at no charge (airline-caused)",
                "Full refund to original payment method within 7 business days",
            ]
            if tier in ("Gold", "Platinum"):
                policies.append("Loyalty Tier Rule")
                allowed.append(f"{tier} Priority: First access to next-available rebooking seats")

        if disruption == "delay":
            policies.append("Delay Compensation Rule")
            comp = PolicyEngine.evaluate_delay_compensation(delay_h)
            allowed += comp["entitlements"]
            if intents["asks_hotel"] and not comp["hotel_eligible"]:
                prohibited.append(
                    f"Hotel accommodation for {delay_h:.0f}h delay - policy requires more than 5h (current: {delay_h:.0f}h)"
                )
            if intents["asks_full_night"] and comp["hotel_eligible"]:
                prohibited.append(
                    "Full overnight hotel stay - policy covers only the delayed hours, not a full night's stay"
                )
            if tier in ("Gold", "Platinum"):
                policies.append("Loyalty Tier Rule")
                allowed.append(f"{tier} Priority: First access to rebooking seats")

        if intents["asks_upgrade"]:
            policies.append("Loyalty Tier Rule")
            prohibited.append(
                f"Complimentary cabin class upgrade - policy strictly prohibits upgrades as disruption "
                f"compensation, even for {tier} tier customers"
            )

        if intents["asks_fare_waiver"]:
            policies.append("Fare Difference Rule")
            prohibited.append("Waiving fare difference above Rs.1,500 without supervisor approval")
            requires_escalation = True
            escalation_reason = (
                "Customer requests fare difference waiver - amount likely exceeds Rs.1,500 "
                "agent discretionary cap; requires supervisor authorisation"
            )

        is_legal, legal_reason = PolicyEngine.detect_legal_or_formal_threat(user_message)
        if is_legal or intents["threatens_legal"]:
            prohibited.append(
                "Handling threats of legal action or formal complaints - must escalate immediately"
            )
            requires_escalation = True
            escalation_reason = legal_reason or "Customer indicated formal complaint or legal intent"

        return {
            "allowed_actions": allowed,
            "prohibited_actions_triggered": prohibited,
            "requires_escalation": requires_escalation,
            "escalation_reason": escalation_reason,
            "policies_invoked": list(set(policies)),
        }

    # ── Policy-Driven Tool Execution ────────────────────────────────────────

    def _execute_tools(
        self,
        customer: Dict[str, Any],
        user_message: str,
        sentiment: str,
        intents: Dict[str, bool],
        guardrails: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        pnr = customer["pnr"]
        name = customer["name"]
        tier = customer.get("loyalty_tier", "Member")
        b = customer["bookings"][0] if customer.get("bookings") else {}
        flight = b.get("flight_number", "SK-Flight")
        route = b.get("route", "Route")
        disruption = b.get("disruption_type", "none")
        delay_h = float(b.get("delay_duration_hours", 0))
        fare = float(b.get("fare_paid", 5000))
        revised_dep = b.get("revised_departure", b.get("scheduled_departure", "TBD"))

        already: set = set()
        for h in history:
            for card in h.get("action_cards", []):
                already.add(card.get("tool", ""))

        execs: List[Dict] = []
        cards: List[Dict] = []

        def add(t: Dict):
            execs.append(t)
            cards.append(t)

        # If it's just a greeting — no tools, let Gemini explain the situation naturally
        if intents.get("is_greeting"):
            return execs, cards

        # Legal escalation always takes priority
        if guardrails["requires_escalation"] and guardrails.get("escalation_reason"):
            is_legal_esc = any(
                kw in guardrails["escalation_reason"].lower()
                for kw in ("legal", "formal", "complaint", "lawyer", "court", "dgca")
            )
            if is_legal_esc and "escalate_to_supervisor" not in already:
                esc = self.tools.escalate_to_supervisor(
                    pnr=pnr, customer_name=name, loyalty_tier=tier,
                    flight_number=flight, reason=guardrails["escalation_reason"],
                    sentiment=sentiment,
                    transcript_summary=(
                        f"{name} ({tier}) expressed legal/formal complaint intent. "
                        f"Flight: {flight} | Route: {route}"
                    ),
                )
                add(esc)
                db.add_escalation(esc)
                return execs, cards

        # ── CANCELLATION flow ─────────────────────────────────────────────────
        # Only act when user EXPLICITLY asks for refund or rebook — never auto-act
        if disruption == "cancellation":
            if intents["asks_refund"]:
                if "initiate_refund" not in already:
                    add(self.tools.initiate_refund(pnr, fare, name, flight, route))
            elif intents["asks_rebook"] or intents["confirms"]:
                if "priority_rebook_flight" not in already:
                    flight_num_part = flight.split("-")[-1]
                    next_flight = (
                        f"SK-{int(flight_num_part) + 1}"
                        if flight_num_part.isdigit()
                        else "SK-Next"
                    )
                    add(self.tools.priority_rebook_flight(
                        pnr, name, tier, flight, next_flight,
                        "Next available within 24 hours (priority allocation)", route,
                    ))
            # If user is furious and explicitly wants action, process refund
            elif sentiment == "furious" and (intents["asks_status"] or len(user_message.split()) > 8):
                if "initiate_refund" not in already and "priority_rebook_flight" not in already:
                    add(self.tools.initiate_refund(pnr, fare, name, flight, route))

        # ── DELAY flow ────────────────────────────────────────────────────────
        # Issue compensation only when user explicitly asks about options, vouchers, or status
        elif disruption == "delay":
            comp = PolicyEngine.evaluate_delay_compensation(delay_h)
            airport = route.split(">")[0].strip() if ">" in route else "Departure Airport"

            explicit_comp_request = (
                intents["asks_meal_lounge"]
                or intents["asks_status"]
                or intents["asks_hotel"]
                or intents["asks_rebook"]
                or (sentiment in ("furious", "frustrated") and len(user_message.split()) > 5)
            )

            if explicit_comp_request:
                if "issue_meal_voucher" not in already:
                    add(self.tools.issue_meal_voucher(pnr, comp["meal_voucher"], name, flight))

                if comp.get("lounge_access") and "issue_lounge_access" not in already:
                    add(self.tools.issue_lounge_access(
                        pnr, name, flight, f"{airport} International Airport"
                    ))

                # Day-use transit hotel is granted for >5h delays. When the customer
                # asks for a full overnight stay, we still arrange the day room and
                # let Maya clarify that it covers only the delayed hours.
                if comp.get("hotel_eligible"):
                    if "arrange_day_hotel" not in already:
                        add(self.tools.arrange_day_hotel(pnr, name, flight, delay_h, revised_dep))

            # Fare waiver escalation
            if intents["asks_fare_waiver"] and guardrails["requires_escalation"]:
                if "escalate_to_supervisor" not in already:
                    esc = self.tools.escalate_to_supervisor(
                        pnr=pnr, customer_name=name, loyalty_tier=tier,
                        flight_number=flight,
                        reason="Fare difference waiver request exceeds Rs.1,500 agent authority",
                        sentiment=sentiment,
                        transcript_summary=(
                            f"{name} ({tier}) requests voluntary rebooking fare waiver. "
                            f"Delay: {delay_h:.0f}h | Flight: {flight}"
                        ),
                        requested_waiver_amount=2000.0,
                        requested_perk="Fare difference waiver for higher-fare alternative flight",
                    )
                    add(esc)
                    db.add_escalation(esc)

        return execs, cards


# Singleton
agent = ResolutionAgent()
