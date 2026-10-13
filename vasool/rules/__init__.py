"""Rule registry: every evaluator that runs on a twin."""
from __future__ import annotations

from ..models import Finding
from ..twin import TwinContext
from .base import RuleEvaluator
from .charges import (AtmCharges, BasicAccountRights, ChargeIncreaseNotice, InoperativeAccount,
                      MinBalanceNegative, MinBalanceNotice, MinBalanceProportion, SmsCharges)
from .failed_transactions import FailedTransactionTAT
from .loans import KfsCharges, PenalCharges

EVALUATORS: list[type[RuleEvaluator]] = [
    FailedTransactionTAT,
    MinBalanceNotice,
    MinBalanceProportion,
    MinBalanceNegative,
    AtmCharges,
    SmsCharges,
    ChargeIncreaseNotice,
    InoperativeAccount,
    BasicAccountRights,
    KfsCharges,
    PenalCharges,
]


def run_all(ctx: TwinContext) -> list[Finding]:
    findings: list[Finding] = []
    for cls in EVALUATORS:
        findings.extend(cls().evaluate(ctx))
    return _dedupe(findings)


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """If two rules flag the same penalty line as RECOVERABLE, keep the one with the larger
    amount (e.g. NOTICE says whole penalty, PROPORTION says only the excess)."""
    best: dict[str, Finding] = {}
    others: list[Finding] = []
    for f in findings:
        if f.label.value != "RECOVERABLE" or not f.evidence:
            others.append(f)
            continue
        key = f.evidence[0]
        cur = best.get(key)
        if cur is None or f.amount > cur.amount:
            best[key] = f
    covered = set(best.keys())
    # an UNCLEAR/AVOIDABLE finding on a line already recoverable under another rule is noise
    others = [f for f in others if not (f.evidence and f.evidence[0] in covered and f.label.value in ("UNCLEAR", "AVOIDABLE") and f.group_key != "BSBDA")]
    return list(best.values()) + others


__all__ = ["run_all", "EVALUATORS", "RuleEvaluator"]
