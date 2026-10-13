"""Rules that start from something the customer tells us, not from a statement line:
credit-card closure delay, unauthorised transaction, gold-loan collateral release.
Each is deterministic arithmetic on dates the user supplies."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from ..models import Confidence, Finding, Label
from ..rulebook import Rulebook
from .base import dmy, inr


def add_working_days(start: date, n: int) -> date:
    d = start
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:  # Mon–Fri; bank holidays are not modelled — say so in the complaint
            added += 1
    return d


def card_closure_claim(rb: Rulebook, request_date: date, closure_date: Optional[date], as_of: date, dues_cleared: bool = True) -> Finding:
    rule = rb.get("RBI-CARD-2022-CLOSURE")
    due = add_working_days(request_date, int(rule.parameters["working_days"]))
    end = closure_date or as_of
    days_late = max(0, (end - due).days)
    per_day = float(rule.parameters["penalty_per_day"])
    amount = days_late * per_day if dues_cleared else 0.0
    label = Label.RECOVERABLE if amount > 0 else Label.UNCLEAR
    return Finding(
        rule_id=rule.id, label=label if rule.in_force(request_date) else Label.UNCLEAR,
        confidence=Confidence.CONFIRMED if dues_cleared else Confidence.NEEDS_CHECKING, amount=amount, evidence=[],
        calculation=f"Closure requested {dmy(request_date)} · due within 7 working days → {dmy(due)} · {'closed ' + dmy(closure_date) if closure_date else 'still open as of ' + dmy(as_of)} · {days_late} days × {inr(per_day)} = {inr(amount)}",
        expected=f"Card closed by {dmy(due)}.", actual=("Closed " + dmy(closure_date)) if closure_date else "Not closed.",
        summary_en=f"You asked to close the card on {dmy(request_date)}. The bank had until {dmy(due)}. It is {days_late} days late — RBI's penalty is {inr(per_day)} a day: {inr(amount)}." + ("" if dues_cleared else " (Applies only if no dues were outstanding.)"),
        summary_ta=f"{dmy(request_date)} அன்று card close பண்ண சொன்னீங்க; {dmy(due)}-க்குள்ள பண்ணியிருக்கணும். {days_late} நாள் late — ஒரு நாளுக்கு {inr(per_day)}: {inr(amount)}.",
        group_key="CARD", occurred_on=request_date,
    )


def unauthorised_txn_claim(rb: Rulebook, txn_date: date, amount: float, reported_on: date, credited_on: Optional[date], as_of: date) -> Finding:
    rule = rb.get("RBI-LIAB-2017-ZERO")
    report_deadline = add_working_days(txn_date, int(rule.parameters["report_window_working_days"]))
    credit_due = add_working_days(reported_on, int(rule.parameters["shadow_credit_working_days"]))
    reported_in_time = reported_on <= report_deadline
    if not reported_in_time:
        return Finding(
            rule_id=rule.id, label=Label.UNCLEAR, confidence=Confidence.NEEDS_CHECKING, amount=amount, evidence=[],
            calculation=f"Transaction {dmy(txn_date)} · zero-liability window ended {dmy(report_deadline)} · reported {dmy(reported_on)} (late)",
            expected="Report within 3 working days for zero liability.", actual=f"Reported {dmy(reported_on)}.",
            summary_en=f"Reported {(reported_on - report_deadline).days} day(s) after the 3-working-day zero-liability window. Liability is then limited (₹5,000–₹25,000 depending on account type) — still worth a complaint, but not automatic.",
            summary_ta="3 working days window-க்கு அப்புறம் report பண்ணியிருக்கீங்க. Liability limited — complaint பண்ணலாம், ஆனா automatic இல்ல.",
            group_key="LIAB", occurred_on=txn_date,
        )
    if credited_on and credited_on <= credit_due:
        label, conf, amt, actual = Label.AVOIDABLE, Confidence.INFO, 0.0, f"Shadow credit on {dmy(credited_on)} — within time."
    elif credited_on:
        label, conf, amt, actual = Label.UNCLEAR, Confidence.NEEDS_CHECKING, 0.0, f"Shadow credit on {dmy(credited_on)}, {(credited_on - credit_due).days} days late (no per-day compensation is prescribed; deficiency of service)."
    else:
        label, conf, amt, actual = Label.RECOVERABLE, Confidence.CONFIRMED, amount, f"No credit as of {dmy(as_of)}; due by {dmy(credit_due)}."
    return Finding(
        rule_id=rule.id, label=label, confidence=conf, amount=amt, evidence=[],
        calculation=f"Transaction {dmy(txn_date)} · reported {dmy(reported_on)} (within 3 working days) · shadow credit due {dmy(credit_due)} · {actual}",
        expected=f"Zero liability; {inr(amount)} credited back by {dmy(credit_due)}.", actual=actual,
        summary_en=f"You reported the unauthorised {inr(amount)} within 3 working days, so your liability is zero. " + ("The bank should have credited it back by " + dmy(credit_due) + " and has not. Recoverable." if label == Label.RECOVERABLE else actual),
        summary_ta=f"3 working days-க்குள்ள report பண்ணதால உங்க பொறுப்பு zero. " + (dmy(credit_due) + "-க்குள்ள பணம் திரும்ப வந்திருக்கணும், வரல. திரும்ப வாங்கலாம்." if label == Label.RECOVERABLE else ""),
        group_key="LIAB", occurred_on=txn_date,
    )


def gold_release_claim(rb: Rulebook, repaid_on: date, released_on: Optional[date], as_of: date) -> Finding:
    rule = rb.get("RBI-GOLD-2025-RELEASE")
    due = add_working_days(repaid_on, int(rule.parameters["working_days"]))
    end = released_on or as_of
    days_late = max(0, (end - due).days)
    per_day = float(rule.parameters["compensation_per_day"])
    amount = days_late * per_day
    in_force = rule.in_force(repaid_on)
    return Finding(
        rule_id=rule.id, label=Label.RECOVERABLE if (amount > 0 and in_force) else Label.UNCLEAR,
        confidence=Confidence.CONFIRMED if in_force else Confidence.NEEDS_CHECKING, amount=amount if in_force else 0.0, evidence=[],
        calculation=f"Repaid {dmy(repaid_on)} · release due within 7 working days → {dmy(due)} · {'released ' + dmy(released_on) if released_on else 'not released as of ' + dmy(as_of)} · {days_late} × {inr(per_day)} = {inr(amount)}" + ("" if in_force else " · rule applies to repayments on/after 1 Apr 2026"),
        expected=f"Gold returned by {dmy(due)}.", actual=("Released " + dmy(released_on)) if released_on else "Not released.",
        summary_en=f"You repaid on {dmy(repaid_on)}; the lender had until {dmy(due)} to return your gold. {days_late} days late × {inr(per_day)} = {inr(amount)}." + ("" if in_force else " This rule applies to repayments from 1 April 2026."),
        summary_ta=f"{dmy(repaid_on)} அன்று அடைச்சீங்க; {dmy(due)}-க்குள்ள நகை திரும்ப தந்திருக்கணும். {days_late} நாள் late × {inr(per_day)} = {inr(amount)}.",
        group_key="GOLD", occurred_on=repaid_on,
    )
