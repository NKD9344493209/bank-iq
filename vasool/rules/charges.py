"""Charge rules: minimum balance, ATM, SMS, inoperative accounts, Basic account rights."""
from __future__ import annotations

from datetime import date, timedelta

from ..models import AccountType, CityTier, Confidence, Finding, Kind, Label, Question, Transaction
from ..twin import TwinContext, month_key
from .base import RuleEvaluator, dmy, inr, questions_of


# --------------------------------------------------------------------------- #
class MinBalanceNotice(RuleEvaluator):
    rule_id = "RBI-MINBAL-2014-NOTICE"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        rule = self.rule(ctx)
        penalties = [t for t in ctx.txns if t.kind == Kind.CHARGE_MIN_BAL and rule.in_force(t.date)]
        if ctx.profile.account_type == AccountType.BSBDA:
            return out  # handled by the BSBDA rule: no penalty is ever allowed
        for t in penalties:
            ans = ctx.answer("notice_received", t.id)
            lowest_prev = ctx.lowest_balance_in_prior_month(t.date)
            req = ctx.profile.min_balance_required
            above_min_all_month = lowest_prev is not None and req is not None and lowest_prev >= req
            gst = _gst_after(ctx, t)
            amount = t.debit + gst
            prev_key = ctx.prior_month_key(t.date)
            path = [[x.date.isoformat(), x.balance] for x in ctx.transactions_in_month(prev_key) if x.balance is not None]
            twin = {"kind": "minbal", "charge_date": t.date.isoformat(), "penalty": t.debit, "gst": gst, "required": req,
                    "month": prev_key, "lowest": lowest_prev, "path": path, "notice_answer": ans,
                    "month_visible": bool(path), "as_of": ctx.as_of.isoformat()}
            if above_min_all_month:
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=amount, evidence=[t.id] + ([gst_id(ctx, t)] if gst else []),
                    calculation=f"Penalty {inr(t.debit)} on {dmy(t.date)}" + (f" + GST {inr(gst)}" if gst else "") + f" · lowest balance in {prev_key}: {inr(lowest_prev)} · required: {inr(req)} → balance never fell below the minimum",
                    expected="No penalty when the balance stayed at or above the required minimum.",
                    actual=f"Penalty of {inr(t.debit)} charged.",
                    summary_en=f"You were charged {inr(amount)} as a minimum-balance penalty on {dmy(t.date)}, but your balance never went below {inr(req)} the month before. This is recoverable.",
                    summary_ta=f"{dmy(t.date)} அன்று {inr(amount)} minimum-balance penalty போட்டாங்க, ஆனா முந்தைய மாசம் உங்க balance {inr(req)}-க்கு கீழ போகவே இல்ல. இது திரும்ப வாங்கலாம்.",
                    group_key="MINBAL", occurred_on=t.date, twin=twin,
                ))
                continue
            if ans == "no":
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=amount, evidence=[t.id] + ([gst_id(ctx, t)] if gst else []),
                    calculation=f"Penalty {inr(t.debit)} on {dmy(t.date)}" + (f" + GST {inr(gst)}" if gst else "") + " · you confirmed no low-balance notice was received in the prior 30 days",
                    expected="A warning (SMS/email/letter) and one month to restore the balance before any penalty.",
                    actual=f"Penalty of {inr(t.debit)} charged; no warning received.",
                    summary_en=f"A {inr(amount)} minimum-balance penalty on {dmy(t.date)} with no prior warning. RBI requires a notice and one month to top up first. Recoverable — the bank must produce the notice or refund.",
                    summary_ta=f"{dmy(t.date)} அன்று எச்சரிக்கை இல்லாம {inr(amount)} minimum-balance penalty. RBI படி முன்னாடி SMS/email அனுப்பி ஒரு மாசம் time தரணும். திரும்ப வாங்கலாம்.",
                    prevention_en="Ask for a free conversion to a Basic Savings account (no minimum balance) — the bank must do it within 7 days.",
                    prevention_ta="Basic Savings account-ஆ மாத்த சொல்லுங்க (minimum balance இல்ல) — 7 நாளுக்குள்ள bank பண்ணணும்.",
                    group_key="MINBAL", occurred_on=t.date, twin=twin,
                ))
            elif ans == "yes":
                out.append(self.finding(
                    ctx, label=Label.AVOIDABLE, confidence=Confidence.INFO, amount=0, evidence=[t.id],
                    calculation=f"Penalty {inr(t.debit)} on {dmy(t.date)} · notice was received → charge is allowed",
                    expected="Notice + one month to restore.", actual="Notice received; penalty followed.",
                    summary_en=f"The {inr(amount)} penalty on {dmy(t.date)} followed a warning, so it is allowed. You can stop the next one.",
                    summary_ta=f"{dmy(t.date)} penalty-க்கு முன்னாடி எச்சரிக்கை வந்ததால அது சரி. அடுத்ததை தடுக்கலாம்.",
                    prevention_en="Convert to a Basic Savings account (no minimum balance, free) or set a low-balance alert one month ahead in Bank IQ.",
                    prevention_ta="Basic Savings account-ஆ மாத்துங்க அல்லது Bank IQ-ல ஒரு மாசம் முன்னாடி alert வைங்க.",
                    group_key="MINBAL", occurred_on=t.date, twin=twin,
                ))
            else:
                out.append(self.finding(
                    ctx, label=Label.UNCLEAR, confidence=Confidence.NEEDS_CHECKING, amount=amount, evidence=[t.id],
                    calculation=f"Penalty {inr(t.debit)} on {dmy(t.date)}" + (f" + GST {inr(gst)}" if gst else "") + " · the statement cannot show whether a warning was sent",
                    expected="A warning and one month to restore before any penalty.",
                    actual=f"Penalty of {inr(t.debit)} charged. Warning: unknown.",
                    summary_en=f"A {inr(amount)} minimum-balance penalty on {dmy(t.date)}. Whether it is recoverable depends on one thing the statement can't show: did the bank warn you first?",
                    summary_ta=f"{dmy(t.date)} அன்று {inr(amount)} minimum-balance penalty. Bank முன்னாடி எச்சரிச்சுதா-ங்கறது தான் கேள்வி.",
                    questions=questions_of(rule), group_key="MINBAL", occurred_on=t.date, twin=twin,
                ))
        return out


class MinBalanceProportion(RuleEvaluator):
    rule_id = "RBI-MINBAL-2014-PROPORTION"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        rule = self.rule(ctx)
        req = ctx.profile.min_balance_required
        if not req or ctx.profile.account_type == AccountType.BSBDA:
            return out
        for t in ctx.txns:
            if t.kind != Kind.CHARGE_MIN_BAL or not rule.in_force(t.date):
                continue
            lowest_prev = ctx.lowest_balance_in_prior_month(t.date)
            if lowest_prev is None or lowest_prev >= req:
                continue
            shortfall = req - lowest_prev
            if t.debit > shortfall + 0.01:
                excess = t.debit - shortfall
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=excess, evidence=[t.id],
                    calculation=f"Required {inr(req)} · lowest balance {inr(lowest_prev)} · shortfall {inr(shortfall)} · penalty {inr(t.debit)} > shortfall → excess {inr(excess)}",
                    expected="A penalty proportionate to the shortfall — never more than the shortfall itself.",
                    actual=f"Penalty {inr(t.debit)} for a shortfall of {inr(shortfall)}.",
                    summary_en=f"The bank charged {inr(t.debit)} for being {inr(shortfall)} short. RBI says the penalty must be proportionate; {inr(excess)} is excess.",
                    summary_ta=f"{inr(shortfall)} குறைவுக்கு {inr(t.debit)} penalty. RBI படி penalty குறைவுக்கு ஏத்ததா இருக்கணும்; {inr(excess)} அதிகம்.",
                    group_key="MINBAL", occurred_on=t.date,
                ))
        return out


class MinBalanceNegative(RuleEvaluator):
    rule_id = "RBI-MINBAL-2014-NEGATIVE"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        rule = self.rule(ctx)
        for t in ctx.txns:
            if t.kind != Kind.CHARGE_MIN_BAL or not rule.in_force(t.date) or t.balance is None:
                continue
            if t.balance < 0:
                amount = min(t.debit, -t.balance)
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=amount, evidence=[t.id],
                    calculation=f"Penalty {inr(t.debit)} on {dmy(t.date)} → balance after: {inr(t.balance)} (negative)",
                    expected="A minimum-balance charge may never take the account below zero.",
                    actual=f"Balance went to {inr(t.balance)}.",
                    summary_en=f"A minimum-balance penalty on {dmy(t.date)} pushed your account to {inr(t.balance)}. RBI forbids this; {inr(amount)} is recoverable.",
                    summary_ta=f"{dmy(t.date)} penalty உங்க account-ஐ {inr(t.balance)}-க்கு கொண்டு போச்சு. RBI இதை தடை பண்ணுது; {inr(amount)} திரும்ப வாங்கலாம்.",
                    group_key="MINBAL", occurred_on=t.date,
                ))
        return out


# --------------------------------------------------------------------------- #
class AtmCharges(RuleEvaluator):
    """Covers RBI-ATM-2025-FREE, RBI-ATM-2025-CAP and the historical RBI-ATM-2021-CAP."""

    rule_id = "RBI-ATM-2025-FREE"

    def _cap_rule_for(self, ctx: TwinContext, d: date):
        for rid in ("RBI-ATM-2025-CAP", "RBI-ATM-2021-CAP"):
            r = ctx.rulebook.get(rid)
            if r.in_force(d):
                return r
        return None

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        free_rule = ctx.rulebook.get("RBI-ATM-2025-FREE")
        for t in ctx.txns:
            if t.kind != Kind.CHARGE_ATM:
                continue
            gst = _gst_after(ctx, t)
            # ---- cap check (rule chosen by date) ----------------------------- #
            cap_rule = self._cap_rule_for(ctx, t.date)
            if cap_rule:
                cap = float(cap_rule.parameters["cap"])
                gst_rate = float(cap_rule.parameters.get("gst_rate", 0.18))
                allowed = cap * (1 + gst_rate) if not gst else cap
                if t.debit > allowed + 0.5:
                    excess = t.debit - allowed
                    self.rule_id = cap_rule.id
                    out.append(self.finding(
                        ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=excess, evidence=[t.id],
                        calculation=f"ATM charge {inr(t.debit)} on {dmy(t.date)} · cap in force on that date {inr(cap)}" + ("" if gst else " + 18% GST") + f" = {inr(allowed)} → excess {inr(excess)}",
                        expected=f"At most {inr(cap)} per transaction (plus tax) beyond the free limit.",
                        actual=f"{inr(t.debit)} charged.",
                        summary_en=f"An ATM charge of {inr(t.debit)} on {dmy(t.date)} is above RBI's cap of {inr(cap)} for that date. {inr(excess)} is recoverable.",
                        summary_ta=f"{dmy(t.date)} ATM charge {inr(t.debit)}, RBI cap {inr(cap)}-ஐ விட அதிகம். {inr(excess)} திரும்ப வாங்கலாம்.",
                        group_key="ATM", occurred_on=t.date,
                    ))
            # ---- free-limit check ------------------------------------------ #
            if not free_rule.in_force(t.date):
                continue
            self.rule_id = free_rule.id
            mk = month_key(t.date)
            uses = [u for u in ctx.atm_uses.values() if month_key(u.txn.date) == mk and u.txn.date <= t.date]
            if not uses:
                # a charge with no ATM use we can see this month — cannot judge; skip quietly
                continue
            last = max(uses, key=lambda u: (u.txn.date, u.index_in_month))
            metro = ctx.profile.city_tier == CityTier.METRO or bool(last.txn.meta.get("metro"))
            limit = int(free_rule.parameters["free_own"]) if last.own else int(free_rule.parameters["free_other_metro" if metro else "free_other_nonmetro"])
            known = all(u.txn.own_bank_atm is not None for u in uses)
            amount = t.debit + gst
            if last.index_in_month <= limit:
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED if known else Confidence.NEEDS_CHECKING,
                    amount=amount, evidence=[t.id] + [u.txn.id for u in uses],
                    calculation=f"{mk}: {last.index_in_month} {'own-bank' if last.own else 'other-bank'} ATM transaction(s) so far · free limit {limit} · charge {inr(t.debit)}" + (f" + GST {inr(gst)}" if gst else "") + " levied inside the free allowance",
                    expected=f"No charge for the first {limit} {'own-bank' if last.own else 'other-bank'} ATM transactions in a month.",
                    actual=f"{inr(t.debit)} charged after transaction #{last.index_in_month}.",
                    summary_en=f"You were charged {inr(amount)} for ATM use in {mk} while still within your {limit} free transactions. Recoverable." + ("" if known else " (We could not tell own-bank from other-bank for every ATM — please confirm.)"),
                    summary_ta=f"{mk}-ல {limit} free ATM transactions-க்குள்ளயே {inr(amount)} charge போட்டாங்க. திரும்ப வாங்கலாம்.",
                    questions=[] if known else [Question("atm_own_bank", "Were all your ATM withdrawals this month at your own bank's ATMs?", "இந்த மாசம் எல்லா ATM withdrawal-ம் உங்க சொந்த bank ATM-லயா?", ["yes", "no", "not_sure"])],
                    group_key="ATM", occurred_on=t.date,
                ))
            else:
                left_next = limit
                out.append(self.finding(
                    ctx, label=Label.AVOIDABLE, confidence=Confidence.INFO, amount=0, evidence=[t.id],
                    calculation=f"{mk}: transaction #{last.index_in_month} exceeded the free limit of {limit} → charge allowed",
                    expected=f"{limit} free transactions; a charge after that is permitted.",
                    actual=f"{inr(t.debit)} charged for transaction #{last.index_in_month}.",
                    summary_en=f"The {inr(amount)} ATM charge on {dmy(t.date)} is allowed — it was your transaction #{last.index_in_month} against {limit} free. Next month you have {left_next} free again.",
                    summary_ta=f"{dmy(t.date)} ATM charge {inr(amount)} சரி — {limit} free-க்கு மேல #{last.index_in_month}-வது. அடுத்த மாசம் திரும்ப {left_next} free.",
                    prevention_en="Use your own bank's ATM (5 free) and withdraw larger amounts fewer times. Balance enquiries count too — use the app instead.",
                    prevention_ta="சொந்த bank ATM-ஐ பயன்படுத்துங்க (5 free); கம்மி முறை, அதிக தொகை எடுங்க. Balance check-கும் count ஆகும் — app-ல பாருங்க.",
                    group_key="ATM", occurred_on=t.date,
                ))
        return out


# --------------------------------------------------------------------------- #
class SmsCharges(RuleEvaluator):
    rule_id = "RBI-SMS-2015-USAGE"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        ban = ctx.rulebook.get("RBI-SMS-2027-BAN")
        usage = ctx.rulebook.get("RBI-SMS-2015-USAGE")
        for t in ctx.txns:
            if t.kind != Kind.CHARGE_SMS:
                continue
            gst = _gst_after(ctx, t)
            amount = t.debit + gst
            if ban.in_force(t.date):
                self.rule_id = ban.id
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=amount, evidence=[t.id],
                    calculation=f"SMS charge {inr(t.debit)} on {dmy(t.date)} · charging for regulatory SMS alerts is barred from 1 Jan 2027",
                    expected="No charge for SMS alerts.", actual=f"{inr(t.debit)} charged.",
                    summary_en=f"An SMS alert charge of {inr(amount)} on {dmy(t.date)}. From 1 January 2027 banks may not charge for these. Recoverable.",
                    summary_ta=f"{dmy(t.date)} SMS charge {inr(amount)}. 2027 Jan 1-ல இருந்து இது கூடாது. திரும்ப வாங்கலாம்.",
                    group_key="SMS", occurred_on=t.date,
                ))
                continue
            if not usage.in_force(t.date):
                continue
            self.rule_id = usage.id
            if ctx.profile.account_type == AccountType.BSBDA:
                continue  # BSBDA rule handles it
            ans = ctx.answer("sms_disclosed", t.id)
            if ans == "no":
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=amount, evidence=[t.id],
                    calculation=f"SMS charge {inr(t.debit)} on {dmy(t.date)} · you confirmed it was never disclosed",
                    expected="SMS charges only on actual usage and only if disclosed upfront.",
                    actual=f"{inr(t.debit)} charged; not disclosed.",
                    summary_en=f"An SMS charge of {inr(amount)} on {dmy(t.date)} that was never disclosed to you. Recoverable — the bank must show the disclosure or refund.",
                    summary_ta=f"{dmy(t.date)} SMS charge {inr(amount)}, உங்களுக்கு சொல்லவே இல்ல. திரும்ப வாங்கலாம்.",
                    group_key="SMS", occurred_on=t.date,
                ))
            elif ans == "yes":
                out.append(self.finding(
                    ctx, label=Label.AVOIDABLE, confidence=Confidence.INFO, amount=0, evidence=[t.id],
                    calculation=f"SMS charge {inr(t.debit)} on {dmy(t.date)} · disclosed → allowed until 31 Dec 2026",
                    expected="Disclosed, usage-based SMS charge.", actual=f"{inr(t.debit)} charged.",
                    summary_en=f"The {inr(amount)} SMS charge on {dmy(t.date)} was disclosed, so it is allowed until 31 Dec 2026. From 1 Jan 2027 it must stop.",
                    summary_ta=f"{dmy(t.date)} SMS charge {inr(amount)} சொல்லப்பட்டது, அதனால 2026 Dec 31 வரை சரி. 2027 Jan 1-ல இருந்து நிக்கணும்.",
                    prevention_en="Switch to free email alerts, or a Basic Savings account where these charges don't apply.",
                    prevention_ta="Free email alert-க்கு மாறுங்க, அல்லது Basic Savings account.",
                    group_key="SMS", occurred_on=t.date,
                ))
            else:
                out.append(self.finding(
                    ctx, label=Label.UNCLEAR, confidence=Confidence.NEEDS_CHECKING, amount=amount, evidence=[t.id],
                    calculation=f"SMS charge {inr(t.debit)} on {dmy(t.date)} · recoverable only if never disclosed",
                    expected="Disclosed upfront, usage-based.", actual=f"{inr(t.debit)} charged; disclosure unknown.",
                    summary_en=f"An SMS alert charge of {inr(amount)} on {dmy(t.date)}. Recoverable if the bank never told you about it.",
                    summary_ta=f"{dmy(t.date)} SMS charge {inr(amount)}. Bank சொல்லாம போட்டிருந்தா திரும்ப வாங்கலாம்.",
                    questions=questions_of(usage), group_key="SMS", occurred_on=t.date,
                ))
        return out


# --------------------------------------------------------------------------- #
class ChargeIncreaseNotice(RuleEvaluator):
    """'suggest' rule: same charge kind, amount went up — ask whether notice was given."""

    rule_id = "RBI-DISCLOSE-2015-NOTICE"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        rule = self.rule(ctx)
        for kind, lines in ctx.month_charge_history.items():
            if kind in {Kind.CHARGE_ATM, Kind.CHARGE_MIN_BAL}:   # these are governed by their own rules
                continue
            prev = None
            for t in lines:
                if prev and t.debit > prev.debit * 1.10 + 1 and rule.in_force(t.date):
                    out.append(self.finding(
                        ctx, label=Label.UNCLEAR, confidence=Confidence.NEEDS_CHECKING, amount=t.debit - prev.debit,
                        evidence=[prev.id, t.id],
                        calculation=f"{kind.value}: {inr(prev.debit)} on {dmy(prev.date)} → {inr(t.debit)} on {dmy(t.date)} (+{inr(t.debit - prev.debit)})",
                        expected="One month's advance notice before any charge is raised.",
                        actual=f"Charge rose from {inr(prev.debit)} to {inr(t.debit)}.",
                        summary_en=f"A recurring bank charge went up from {inr(prev.debit)} to {inr(t.debit)} on {dmy(t.date)}. Banks must give one month's notice first — did you get one?",
                        summary_ta=f"{dmy(t.date)} அன்று ஒரு charge {inr(prev.debit)}-ல இருந்து {inr(t.debit)}-ஆ ஏறிடுச்சு. ஒரு மாசம் முன்னாடி சொல்லணும் — சொன்னாங்களா?",
                        questions=questions_of(rule), group_key="INCREASE", occurred_on=t.date,
                    ))
                prev = t
        return out


# --------------------------------------------------------------------------- #
class InoperativeAccount(RuleEvaluator):
    rule_id = "RBI-INOP-2024-NOPENALTY"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        rule = self.rule(ctx)
        gap_days = int(rule.parameters["inoperative_after_days"])
        first_date = ctx.txns[0].date if ctx.txns else None
        for t in ctx.txns:
            if t.kind not in {Kind.CHARGE_MIN_BAL, Kind.CHARGE_REACTIVATION} or not rule.in_force(t.date):
                continue
            last = ctx.last_customer_txn_before(t.date, exclude_id=t.id)
            if last:
                gap = (t.date - last.date).days
            else:
                # no customer txn since the statement began; provable only if the statement itself spans the gap
                gap = (t.date - first_date).days if first_date else 0
            if gap >= gap_days:
                gst = _gst_after(ctx, t)
                out.append(self.finding(
                    ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=t.debit + gst, evidence=[t.id] + ([last.id] if last else []),
                    calculation=f"Last customer-initiated transaction {dmy(last.date) if last else 'none in statement'} · charge {dmy(t.date)} · gap {gap} days ≥ {gap_days} → account inoperative",
                    expected="No minimum-balance penalty or reactivation charge on an inoperative account.",
                    actual=f"{inr(t.debit)} charged.",
                    summary_en=f"Your account had no transactions of yours for {gap} days, which makes it 'inoperative' — and RBI forbids penalties or reactivation charges on such accounts. {inr(t.debit + gst)} recoverable.",
                    summary_ta=f"{gap} நாள் நீங்க எதுவும் பண்ணல, அதனால account inoperative. அதுல penalty போடக்கூடாது. {inr(t.debit + gst)} திரும்ப வாங்கலாம்.",
                    group_key="INOP", occurred_on=t.date,
                ))
        return out


# --------------------------------------------------------------------------- #
class BasicAccountRights(RuleEvaluator):
    rule_id = "RBI-BSBDA-2026-ZEROCHARGE"

    def evaluate(self, ctx: TwinContext) -> list[Finding]:
        out: list[Finding] = []
        rule = self.rule(ctx)
        charge_kinds = {Kind.CHARGE_MIN_BAL, Kind.CHARGE_SMS, Kind.CHARGE_CARD_AMC, Kind.CHARGE_ATM}
        if ctx.profile.account_type == AccountType.BSBDA:
            for t in ctx.txns:
                if t.kind in charge_kinds and rule.in_force(t.date):
                    gst = _gst_after(ctx, t)
                    out.append(self.finding(
                        ctx, label=Label.RECOVERABLE, confidence=Confidence.CONFIRMED, amount=t.debit + gst, evidence=[t.id],
                        calculation=f"Account type: Basic Savings · {t.kind.value} {inr(t.debit)} on {dmy(t.date)} → not permitted on a BSBDA",
                        expected="No minimum balance, free ATM/debit card, no charges for basic services.",
                        actual=f"{inr(t.debit)} charged.",
                        summary_en=f"Your account is a Basic Savings account, where a {t.kind.value.replace('CHARGE_', '').replace('_', ' ').lower()} charge is not allowed. {inr(t.debit + gst)} recoverable.",
                        summary_ta=f"உங்களுது Basic Savings account; இதுல இந்த charge கூடாது. {inr(t.debit + gst)} திரும்ப வாங்கலாம்.",
                        group_key="BSBDA", occurred_on=t.date,
                    ))
            return out
        # Not a BSBDA: if penalties recur, the strongest prevention is conversion
        penalties = [t for t in ctx.txns if t.kind == Kind.CHARGE_MIN_BAL]
        if len(penalties) >= 2 and rule.in_force(ctx.as_of):
            total = sum(t.debit for t in penalties)
            out.append(self.finding(
                ctx, label=Label.AVOIDABLE, confidence=Confidence.INFO, amount=0, evidence=[t.id for t in penalties],
                calculation=f"{len(penalties)} minimum-balance penalties totalling {inr(total)} in this statement",
                expected="A right to a zero-charge Basic Savings account, converted within 7 days of asking.",
                actual=f"{inr(total)} paid in penalties.",
                summary_en=f"You paid {inr(total)} in minimum-balance penalties in this period. You have the right to convert to a Basic Savings account with no minimum balance — the bank must do it within 7 days of your request.",
                summary_ta=f"இந்த காலத்துல {inr(total)} minimum-balance penalty கட்டியிருக்கீங்க. Basic Savings account-ஆ மாத்த உங்களுக்கு உரிமை இருக்கு — 7 நாளுக்குள்ள bank பண்ணணும்.",
                prevention_en="Tap 'Request Basic account' — we prepare the letter. No minimum balance, free card, free basic services.",
                prevention_ta="'Basic account கேளுங்க'-ஐ அழுத்துங்க — நாங்க letter தயார் பண்றோம்.",
                group_key="BSBDA", occurred_on=penalties[-1].date,
            ))
        return out


# --------------------------------------------------------------------------- #
def _gst_after(ctx: TwinContext, t: Transaction) -> float:
    """GST is often a separate line right after a charge (same date, ~18%)."""
    idx = ctx.txns.index(t)
    for nxt in ctx.txns[idx + 1: idx + 3]:
        if nxt.kind == Kind.GST_ON_CHARGE and nxt.date == t.date and abs(nxt.debit - round(t.debit * 0.18, 2)) < 1.0:
            return nxt.debit
    return 0.0


def gst_id(ctx: TwinContext, t: Transaction) -> str:
    idx = ctx.txns.index(t)
    for nxt in ctx.txns[idx + 1: idx + 3]:
        if nxt.kind == Kind.GST_ON_CHARGE and nxt.date == t.date:
            return nxt.id
    return ""
