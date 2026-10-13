"""RBI/2019-20/67 — failed transactions: reversal TAT and ₹100/day compensation."""
from __future__ import annotations

from datetime import timedelta

from ..models import Channel, Confidence, Finding, Kind, Label, Question, Transaction
from ..twin import TwinContext
from .base import RuleEvaluator, dmy, inr

CHANNEL_RULE = {
    Channel.ATM: "RBI-TAT-2019-ATM",
    Channel.UPI: "RBI-TAT-2019-UPI",
    Channel.IMPS: "RBI-TAT-2019-UPI",
    Channel.CARD: "RBI-TAT-2019-UPI",
    Channel.POS: "RBI-TAT-2019-POS",
    Channel.ECOM: "RBI-TAT-2019-POS",
}

FAILED_Q = Question(
    id="txn_failed",
    text_en="Did this payment fail — money left your account but the shop/person/ATM did not get it?",
    text_ta="இந்த payment fail ஆச்சா — உங்க account-ல இருந்து பணம் போச்சு, ஆனா கடை/ஆள்/ATM-க்கு வரலயா?",
    options=["yes", "no", "not_sure"],
)


class FailedTransactionTAT(RuleEvaluator):
    """One evaluator covers all three TAT rules; the rule id is chosen per channel."""

    rule_id = "RBI-TAT-2019-ATM"  # default; overridden per finding

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        comp_credits = [t for t in ctx.txns if t.kind == Kind.COMPENSATION]

        # (a) failed debits that WERE reversed — was the reversal late?
        for pair in ctx.pairing.pairs:
            d = pair.debit
            rid = CHANNEL_RULE.get(d.channel)
            if not rid:
                continue
            self.rule_id = rid
            rule = self.rule(ctx)
            if not rule.in_force(d.date):
                continue
            tat = int(rule.parameters["tat_days"])
            per_day = float(rule.parameters["compensation_per_day"])
            due = d.date + timedelta(days=tat)
            rev = pair.reversal_date
            days_late = (rev - due).days
            if days_late <= 0:
                continue
            owed = days_late * per_day
            paid = sum(c.credit for c in comp_credits if d.date <= c.date <= rev + timedelta(days=45))
            net = owed - paid
            if net <= 0:
                continue
            calc = (f"Debited {dmy(d.date)} · reversal due by {dmy(due)} (T+{tat}) · reversed {dmy(rev)} "
                    f"({'partial credits: ' + ', '.join(inr(c.credit) for c in pair.credits) + ' · ' if len(pair.credits) > 1 else ''}"
                    f"{days_late} days late) · {days_late} × {inr(per_day)} = {inr(owed)}"
                    + (f" · compensation already credited {inr(paid)} → {inr(net)}" if paid else ""))
            out.append(self.finding(
                ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=net,
                evidence=[d.id] + [c.id for c in pair.credits],
                calculation=calc,
                expected=f"Reversal by {dmy(due)} and, for every day after that, {inr(per_day)} credited automatically.",
                actual=f"Reversed on {dmy(rev)}, {days_late} days late. Compensation credited: {inr(paid)}.",
                summary_en=f"Your {inr(d.debit)} {d.channel.value} transaction failed and came back {days_late} days late. RBI says the bank owes you {inr(net)} for the delay.",
                summary_ta=f"உங்க {inr(d.debit)} {d.channel.value} transaction fail ஆயி {days_late} நாள் late-ஆ திரும்பி வந்துச்சு. RBI படி bank உங்களுக்கு {inr(net)} தரணும்.",
                group_key="TAT", occurred_on=d.date,
                twin={"kind": "tat", "channel": d.channel.value, "debit_date": d.date.isoformat(), "amount": d.debit, "narration": d.narration,
                      "tat_days": tat, "deadline": due.isoformat(), "reversal_date": rev.isoformat(), "per_day": per_day,
                      "days_late": days_late, "expected_compensation": owed, "actual_compensation": paid, "delta": net,
                      "as_of": ctx.as_of.isoformat(), "rule_id": rid, "reversed": True},
            ))

        # (b) debits that say FAILED but were never reversed — principal + compensation
        for d in ctx.pairing.unreversed_failed:
            out.append(self._unreversed(ctx, d, Confidence.CONFIRMED))

        # (c) ordinary debits the customer has marked as failed (question answered "yes")
        for d in ctx.txns:
            if not d.is_debit or d.channel not in CHANNEL_RULE or d.failed_hint:
                continue
            if ctx.pairing.pair_for(d.id):
                continue
            ans = ctx.answer("txn_failed", d.id)
            if ans == "yes":
                out.append(self._unreversed(ctx, d, Confidence.CONFIRMED, user_confirmed=True))
        return out

    def _unreversed(self, ctx: TwinContext, d: Transaction, conf: Confidence, user_confirmed: bool = False) -> Finding:
        self.rule_id = CHANNEL_RULE[d.channel]
        rule = self.rule(ctx)
        tat = int(rule.parameters["tat_days"])
        per_day = float(rule.parameters["compensation_per_day"])
        due = d.date + timedelta(days=tat)
        days_late = max(0, (ctx.as_of - due).days)
        comp = days_late * per_day
        total = d.debit + comp
        calc = (f"Debited {dmy(d.date)} · narration says failed · no reversal found in the statement · reversal due {dmy(due)} · "
                f"as of {dmy(ctx.as_of)}: {days_late} × {inr(per_day)} = {inr(comp)} · plus the {inr(d.debit)} itself = {inr(total)}")
        return self.finding(
            ctx, label=Label.RECOVERABLE, confidence=conf, amount=total, evidence=[d.id], calculation=calc,
            expected=f"{inr(d.debit)} reversed by {dmy(due)}, then {inr(per_day)} per day.",
            actual=f"No reversal in the statement as of {dmy(ctx.as_of)}." + (" You confirmed the payment failed." if user_confirmed else ""),
            summary_en=f"{inr(d.debit)} left your account on {dmy(d.date)} in a failed {d.channel.value} transaction and has not come back. The bank owes the {inr(d.debit)} plus {inr(comp)} compensation.",
            summary_ta=f"{dmy(d.date)} அன்று fail ஆன {d.channel.value} transaction-ல {inr(d.debit)} போச்சு, இன்னும் திரும்பி வரல. Bank {inr(d.debit)}-ம் {inr(comp)} compensation-ம் தரணும்.",
            group_key="TAT", occurred_on=d.date,
            twin={"kind": "tat", "channel": d.channel.value, "debit_date": d.date.isoformat(), "amount": d.debit, "narration": d.narration,
                  "tat_days": tat, "deadline": due.isoformat(), "reversal_date": None, "per_day": per_day,
                  "days_late": days_late, "expected_compensation": comp, "actual_compensation": 0.0, "delta": total,
                  "as_of": ctx.as_of.isoformat(), "rule_id": self.rule_id, "reversed": False, "principal_outstanding": d.debit},
        )


def failed_candidates_needing_confirmation(ctx: TwinContext) -> list[Transaction]:
    """Debits with no reversal and no failed hint — we never claim these; we may ASK about
    the ones that look suspicious (an exact same-amount retry within 2 days)."""
    out = []
    debits = [t for t in ctx.txns if t.is_debit and t.channel in CHANNEL_RULE and t.kind in {Kind.DEBIT, Kind.ATM_WITHDRAWAL}]
    for i, d in enumerate(debits):
        if ctx.pairing.pair_for(d.id) or d.failed_hint:
            continue
        for e in debits[i + 1:]:
            if (e.date - d.date).days > 2:
                break
            if abs(e.debit - d.debit) < 0.01 and e.channel == d.channel and (e.merchant == d.merchant or d.channel == Channel.ATM):
                out.append(d)
                break
    return out
