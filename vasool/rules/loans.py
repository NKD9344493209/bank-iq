"""Loan-side rules. These need a document (the Key Fact Statement) the statement
cannot supply, so they raise 'needs checking' findings with document help."""
from __future__ import annotations

from ..models import Confidence, Finding, Kind, Label
from ..twin import TwinContext
from .base import RuleEvaluator, dmy, inr


class KfsCharges(RuleEvaluator):
    rule_id = "RBI-KFS-2024-NOEXTRA"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        rule = self.rule(ctx)
        kfs_charges = ctx.answers.get("kfs_charge_schedule")  # list of {name, amount} if the user uploaded a KFS
        for t in ctx.txns:
            if t.kind != Kind.LOAN_CHARGE or not rule.in_force(t.date):
                continue
            if kfs_charges:
                matched = any(abs(float(c.get("amount", -1)) - t.debit) < 1.0 for c in kfs_charges)
                if matched:
                    continue
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=t.debit, evidence=[t.id],
                    calculation=f"Loan charge {inr(t.debit)} on {dmy(t.date)} · not present in the Key Fact Statement schedule ({len(kfs_charges)} items)",
                    expected="Only charges listed in the Key Fact Statement may be levied.",
                    actual=f"{inr(t.debit)} charged; not in KFS.",
                    summary_en=f"A loan charge of {inr(t.debit)} on {dmy(t.date)} does not appear in your Key Fact Statement. RBI says it cannot be levied without your consent. Recoverable.",
                    summary_ta=f"{dmy(t.date)} loan charge {inr(t.debit)} உங்க Key Fact Statement-ல இல்ல. RBI படி இதை போடக்கூடாது. திரும்ப வாங்கலாம்.",
                    group_key="LOAN", occurred_on=t.date,
                ))
            else:
                out.append(self.finding(
                    ctx, label=Label.UNCLEAR, confidence=Confidence.NEEDS_CHECKING, amount=t.debit, evidence=[t.id],
                    calculation=f"Loan charge {inr(t.debit)} on {dmy(t.date)} · needs your Key Fact Statement to check",
                    expected="Every loan charge listed in the KFS you were given.",
                    actual=f"{inr(t.debit)} charged; KFS not yet provided.",
                    summary_en=f"A loan charge of {inr(t.debit)} on {dmy(t.date)}. To check it we need one document: your loan's Key Fact Statement. We'll show you where to find it.",
                    summary_ta=f"{dmy(t.date)} loan charge {inr(t.debit)}. Check பண்ண உங்க loan-ஓட Key Fact Statement வேணும். எங்க இருக்கும்-னு காட்றோம்.",
                    group_key="LOAN", occurred_on=t.date,
                ))
        return out


class PenalCharges(RuleEvaluator):
    rule_id = "RBI-PENAL-2023-NOCAP"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        rule = self.rule(ctx)
        for t in ctx.txns:
            if t.kind != Kind.LOAN_PENAL or not rule.in_force(t.date):
                continue
            is_interest = "INT" in t.narration.upper()
            out.append(self.finding(
                ctx, label=Label.UNCLEAR, confidence=Confidence.NEEDS_CHECKING, amount=t.debit, evidence=[t.id],
                calculation=f"Penal {'interest' if is_interest else 'charge'} {inr(t.debit)} on {dmy(t.date)}" + (" · 'penal interest' is not permitted after 1 Apr 2024; only a disclosed flat penal charge" if is_interest else " · must match the amount disclosed in the KFS"),
                expected="A disclosed, flat penal charge — never penal interest added to the loan.",
                actual=f"{inr(t.debit)} charged as {'penal interest' if is_interest else 'a penal charge'}.",
                summary_en=f"A {inr(t.debit)} {'penal interest' if is_interest else 'penal charge'} on {dmy(t.date)}. " + ("RBI banned 'penal interest' from April 2024 — this deserves checking against your loan documents." if is_interest else "It must match what your Key Fact Statement discloses."),
                summary_ta=f"{dmy(t.date)} அன்று {inr(t.debit)} penal {'interest' if is_interest else 'charge'}. " + ("2024 April-ல இருந்து penal interest கூடாது — loan documents-ஓட check பண்ணணும்." if is_interest else "KFS-ல சொன்ன தொகையா இருக்கணும்."),
                group_key="LOAN", occurred_on=t.date,
            ))
        return out
