from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from ..models import Confidence, Finding, Label, Question
from ..rulebook import Rule
from ..twin import TwinContext


def inr(x: float) -> str:
    """Indian grouping: 1,23,456.00"""
    neg = x < 0
    x = abs(x)
    whole = int(round(x, 2))
    frac = round(x - whole, 2)
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    if frac:
        s += f".{int(round(frac * 100)):02d}"
    return ("-" if neg else "") + "₹" + s


def dmy(d: Optional[date]) -> str:
    return d.strftime("%d %b %Y") if d else "—"


def questions_of(rule: Rule) -> list[Question]:
    out = []
    for q in rule.questions:
        out.append(Question(id=q["id"], text_en=q.get("en", ""), text_ta=q.get("ta", ""), options=q.get("options", []), qtype=q.get("type", "choice")))
    return out


class RuleEvaluator(ABC):
    """One evaluator per rule id. Evaluators are pure: same twin → same findings."""

    rule_id: str = ""

    def rule(self, ctx: TwinContext) -> Rule:
        return ctx.rulebook.get(self.rule_id)

    def applies_on(self, ctx: TwinContext, d: date) -> bool:
        return self.rule(ctx).in_force(d)

    @abstractmethod
    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        ...

    # ----- helpers ---------------------------------------------------------- #
    def finding(self, ctx: TwinContext, *, label: Label, confidence: Confidence, amount: float,
                evidence: list[str], calculation: str, expected: str, actual: str,
                summary_en: str, summary_ta: str, questions: Optional[list[Question]] = None,
                prevention_en: str = "", prevention_ta: str = "", group_key: str = "",
                occurred_on: Optional[date] = None, twin: Optional[dict] = None) -> Finding:
        rule = self.rule(ctx)
        # A 'suggest' rule may never produce a RECOVERABLE claim on its own.
        if not rule.can_claim and label == Label.RECOVERABLE:
            label, confidence = Label.UNCLEAR, Confidence.NEEDS_CHECKING
        return Finding(
            rule_id=rule.id, label=label, confidence=confidence, amount=max(0.0, float(amount)),
            evidence=evidence, calculation=calculation, expected=expected, actual=actual,
            summary_en=summary_en, summary_ta=summary_ta, questions=questions or [],
            prevention_en=prevention_en, prevention_ta=prevention_ta,
            group_key=group_key or rule.id, occurred_on=occurred_on, twin=twin or {},
        )
