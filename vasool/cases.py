"""Case state machine with the statutory clock and the closed loop.

FOUND → PREPARED → AWAITING_APPROVAL → SENT_TO_BANK → (BANK_REPLIED | DEADLINE_PASSED)
      → ESCALATED_OMBUDSMAN → RECOVERED | CLOSED_BANK_RIGHT | CLOSED_BY_USER

The user never sees this diagram. They see: "We're handling the next step."
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from .models import Case, CaseEvent, CaseState, Finding, Transaction
from .rulebook import Rulebook

ALLOWED = {
    CaseState.FOUND: {CaseState.PREPARED, CaseState.CLOSED_BY_USER},
    CaseState.PREPARED: {CaseState.AWAITING_APPROVAL, CaseState.SENT_TO_BANK, CaseState.CLOSED_BY_USER},
    CaseState.AWAITING_APPROVAL: {CaseState.SENT_TO_BANK, CaseState.CLOSED_BY_USER},
    CaseState.SENT_TO_BANK: {CaseState.BANK_REPLIED, CaseState.DEADLINE_PASSED, CaseState.RECOVERED, CaseState.CLOSED_BANK_RIGHT, CaseState.CLOSED_BY_USER},
    CaseState.BANK_REPLIED: {CaseState.RECOVERED, CaseState.CLOSED_BANK_RIGHT, CaseState.ESCALATED_OMBUDSMAN, CaseState.CLOSED_BY_USER},
    CaseState.DEADLINE_PASSED: {CaseState.ESCALATED_OMBUDSMAN, CaseState.RECOVERED, CaseState.CLOSED_BY_USER},
    CaseState.ESCALATED_OMBUDSMAN: {CaseState.RECOVERED, CaseState.CLOSED_BANK_RIGHT, CaseState.CLOSED_BY_USER},
    CaseState.RECOVERED: set(),
    CaseState.CLOSED_BANK_RIGHT: set(),
    CaseState.CLOSED_BY_USER: set(),
}

USER_STATUS = {
    CaseState.FOUND: ("We found this. Nothing sent yet.", "கண்டுபிடிச்சோம். இன்னும் எதுவும் அனுப்பல."),
    CaseState.PREPARED: ("Complaint prepared. Waiting for your OK.", "Complaint தயார். உங்க OK-க்கு காத்திருக்கோம்."),
    CaseState.AWAITING_APPROVAL: ("Waiting for your guardian to approve.", "உங்க காப்பாளர் OK சொல்ல காத்திருக்கோம்."),
    CaseState.SENT_TO_BANK: ("Approved — evidence pack ready to submit. Hand it to the branch or file it at cms.rbi.org.in; this app does not transmit it. We're watching the 30-day clock.", "OK ஆச்சு — evidence pack தயார். Branch-ல கொடுங்க அல்லது cms.rbi.org.in-ல file பண்ணுங்க; இந்த app அனுப்பாது. 30 நாள் clock-ஐ நாங்க பாத்துக்கறோம்."),
    CaseState.BANK_REPLIED: ("The bank replied. Checking it.", "Bank பதில் சொல்லிடுச்சு. Check பண்றோம்."),
    CaseState.DEADLINE_PASSED: ("Bank didn't reply in 30 days. We're preparing the next step.", "30 நாள்ல bank பதில் சொல்லல. அடுத்த step தயார் பண்றோம்."),
    CaseState.ESCALATED_OMBUDSMAN: ("Escalated to the RBI Ombudsman. Free, and we're tracking it.", "RBI Ombudsman-க்கு போயாச்சு. Free. நாங்க track பண்றோம்."),
    CaseState.RECOVERED: ("Money came back. Case closed.", "பணம் திரும்பி வந்துடுச்சு. Case முடிஞ்சது."),
    CaseState.CLOSED_BANK_RIGHT: ("The bank showed the charge was valid. We've updated our checks.", "Bank charge சரி-ன்னு காட்டிடுச்சு. எங்க check-ஐ update பண்ணிட்டோம்."),
    CaseState.CLOSED_BY_USER: ("Closed by you.", "நீங்க close பண்ணீங்க."),
}


def new_case(account_id: str, findings: list[Finding]) -> Case:
    rec = [f for f in findings if f.label.value == "RECOVERABLE"]
    c = Case(account_id=account_id, finding_ids=[f.id for f in rec], amount=sum(f.amount for f in rec), rule_ids=sorted({f.rule_id for f in rec}))
    c.events.append(CaseEvent(datetime.now(), CaseState.FOUND, f"{len(rec)} finding(s), {c.amount:.2f}"))
    return c


def transition(case: Case, to: CaseState, note: str = "", actor: str = "system", rb: Optional[Rulebook] = None, on: Optional[date] = None) -> Case:
    if to not in ALLOWED[case.state]:
        raise ValueError(f"Cannot go from {case.state.value} to {to.value}")
    case.state = to
    case.events.append(CaseEvent(datetime.now(), to, note, actor))
    if to == CaseState.SENT_TO_BANK:
        on = on or date.today()
        case.sent_on = on
        clock = (rb or _rb()).get("RBI-OMBUDSMAN-2026-CLOCK").parameters
        case.bank_reply_due = on + timedelta(days=int(clock["bank_reply_days"]))
        case.ombudsman_deadline = case.bank_reply_due + timedelta(days=int(clock["ombudsman_window_days"]))
    return case


def tick(case: Case, today: Optional[date] = None) -> Case:
    """Advance clock-driven states. Call daily (or on every load)."""
    today = today or date.today()
    if case.state == CaseState.SENT_TO_BANK and case.bank_reply_due and today > case.bank_reply_due:
        transition(case, CaseState.DEADLINE_PASSED, f"No reply by {case.bank_reply_due.isoformat()}")
    return case


def days_left(case: Case, today: Optional[date] = None) -> Optional[int]:
    today = today or date.today()
    if case.state == CaseState.SENT_TO_BANK and case.bank_reply_due:
        return (case.bank_reply_due - today).days
    if case.state in (CaseState.DEADLINE_PASSED, CaseState.BANK_REPLIED, CaseState.ESCALATED_OMBUDSMAN) and case.ombudsman_deadline:
        return (case.ombudsman_deadline - today).days
    return None


def detect_recovery(case: Case, new_txns: list[Transaction], since: Optional[date] = None) -> Optional[Transaction]:
    """Closed loop: a credit at/after sending, within ±2% of the claimed amount (or of any single
    finding amount), with a reversal/refund/compensation-looking narration."""
    since = since or case.sent_on or date.today() - timedelta(days=90)
    import re
    pat = re.compile(r"REV|REFUND|COMP|CREDIT ADJ|REVERS|GRIEV|COMPLAINT|SETTLE", re.I)
    targets = [case.amount]
    for t in new_txns:
        if t.credit <= 0 or t.date < since:
            continue
        if any(abs(t.credit - a) <= max(2.0, 0.02 * a) for a in targets) and (pat.search(t.narration) or t.kind.value in ("REVERSAL", "COMPENSATION")):
            return t
    return None


def user_status(case: Case, lang: str = "en") -> str:
    en, ta = USER_STATUS[case.state]
    return ta if lang == "ta" else en


def _rb() -> Rulebook:
    from . import rulebook
    return rulebook.load()
