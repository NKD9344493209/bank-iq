"""Recovery Priority — should this bother a human at all?

score = amount × confidence × effort × legal strength (+ deadline urgency)

  RECOVER_NOW   strong, worth acting on alone
  COMBINE       real but small; bundle with others of the same group into one complaint
  NOT_WORTH_IT  we keep watching; never ask the user to act on this alone
  PREVENT       nothing to recover; we tell you how to stop the next one
"""
from __future__ import annotations

import math
import os
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from .models import Confidence, Finding, Label, Priority
from .rulebook import Rulebook

LEGAL_STRENGTH = {"statutory": 1.0, "refund": 0.75, "prevent": 0.0, "process": 0.0}
CONF_W = {Confidence.CONFIRMED: 1.0, Confidence.NEEDS_CHECKING: 0.6, Confidence.INFO: 0.0}

RECOVER_NOW_MIN = 500.0       # rupees, single finding
COMBINE_MIN_GROUP = 300.0     # rupees, group total
ASK_MIN = 100.0              # rupees: below this we do not even ask the question
OLD_CASE_DAYS = 300           # bank complaint should go before Ombudsman limitation bites

# The clock. RBI Integrated Ombudsman Scheme 2021, cl. 10(2): a complaint reaches the Ombudsman within one year
# of the bank's reply (or one year + 30 days if the bank never replies). So the bank complaint itself must be
# raised well inside a year of the event. We call that the act-by date, and turn red ALERT_DAYS before it.
LIMITATION_DAYS = int(os.getenv("VASOOL_LIMITATION_DAYS", "365"))
ALERT_DAYS = int(os.getenv("VASOOL_ALERT_DAYS", "60"))


def deadline(f: Finding, as_of: date) -> tuple[Optional[date], Optional[int], bool, str]:
    """→ (act_by, days_left, alert, reason). Unreversed failures are always urgent: every day adds ₹100
    but the principal is still gone, and the trail gets colder."""
    if f.twin.get("kind") == "tat" and f.twin.get("reversed") is False:
        by = date.fromisoformat(f.twin["debit_date"]) + timedelta(days=LIMITATION_DAYS)
        return by, (by - as_of).days, True, f"open failure — ₹{f.twin.get('per_day', 100):.0f}/day accruing; raise it now, don't wait to bundle"
    if not f.occurred_on:
        return None, None, False, ""
    by = f.occurred_on + timedelta(days=LIMITATION_DAYS)
    left = (by - as_of).days
    if f.label in (Label.RECOVERABLE, Label.UNCLEAR) and left <= ALERT_DAYS:
        return by, left, True, (f"{left} days to the limitation clock — raise it now, whatever the amount" if left >= 0 else "limitation clock has passed — raise it immediately; the Ombudsman may still admit it")
    return by, left, False, ""


def _amount_factor(a: float) -> float:
    if a <= 0:
        return 0.0
    return min(1.0, math.log10(a + 1) / 4.0)   # ₹100→0.50 · ₹1,000→0.75 · ₹10,000→1.0


def _effort_factor(f: Finding, rb: Rulebook) -> float:
    rule = rb.get(f.rule_id)
    if "document" in rule.evaluable_from and f.confidence != Confidence.CONFIRMED:
        return 0.5
    if f.questions:
        return 0.8
    return 1.0


def score_findings(findings: list[Finding], rb: Rulebook, as_of: date) -> list[Finding]:
    group_totals: dict[str, float] = defaultdict(float)
    for f in findings:
        if f.label in (Label.RECOVERABLE, Label.UNCLEAR):
            group_totals[f.group_key] += f.amount

    for f in findings:
        rule = rb.get(f.rule_id)
        legal = LEGAL_STRENGTH.get(rule.compensation_type, 0.5)
        conf = CONF_W[f.confidence]
        effort = _effort_factor(f, rb)
        amt = _amount_factor(f.amount)
        urgency = 0.0
        if f.occurred_on and (as_of - f.occurred_on).days > OLD_CASE_DAYS and f.label == Label.RECOVERABLE:
            urgency = 0.1
        score = 0.40 * amt + 0.25 * conf + 0.20 * legal + 0.15 * effort + urgency
        f.priority_score = round(min(score, 1.0), 3)
        reasons = [f"amount factor {amt:.2f}", f"confidence {conf:.2f}", f"legal strength {legal:.2f}", f"effort {effort:.2f}"]
        if urgency:
            reasons.append("older than 10 months — act before limitation")

        f.act_by, f.days_left, f.alert, f.alert_reason = deadline(f, as_of)
        if f.label == Label.AVOIDABLE:
            f.priority = Priority.PREVENT
        elif f.label in (Label.RECOVERABLE, Label.UNCLEAR):
            if f.alert:
                f.priority = Priority.RECOVER_NOW
                reasons.append("⏰ " + f.alert_reason)
            elif f.amount >= RECOVER_NOW_MIN or (f.priority_score >= 0.75 and f.amount >= 100):
                f.priority = Priority.RECOVER_NOW
            elif group_totals[f.group_key] >= COMBINE_MIN_GROUP:
                f.priority = Priority.COMBINE
                reasons.append(f"group '{f.group_key}' totals ₹{group_totals[f.group_key]:,.0f}")
            elif f.label == Label.UNCLEAR and f.amount >= ASK_MIN:
                f.priority = Priority.COMBINE
                reasons.append("one answer from you settles this")
            else:
                f.priority = Priority.NOT_WORTH_IT
                reasons.append("small on its own — we keep watching; it joins a bundle if more appear")
        else:
            f.priority = Priority.COMBINE
        f.priority_reasons = reasons
    return findings
