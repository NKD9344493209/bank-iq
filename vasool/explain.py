"""Explainability — the digital twin as a picture, and "why wasn't this flagged?".

Everything here is *derived* from the twin the engine already built (`build_twin`) and from the
findings it already produced. Nothing is re-decided: this module reports what the engine saw.

  twin_summary(ctx, findings)   → the account state as counts, the balance path, the reversal pairs
  why_not_flagged(ctx, txn, findings) → the deterministic checklist for one transaction
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from .models import CHARGE_KINDS, Finding, Kind, Transaction
from .twin import TwinContext, month_key

# rule families → which kinds/channels they look at (used to say "these rules examined this line")
FAMILY_OF_KIND = {
    Kind.ATM_WITHDRAWAL: ["RBI-TAT-2019-ATM", "RBI-ATM-2025-FREE", "RBI-ATM-2025-FEECAP"],
    Kind.ATM_ENQUIRY: ["RBI-ATM-2025-FREE"],
    Kind.CHARGE_ATM: ["RBI-ATM-2025-FREE", "RBI-ATM-2025-FEECAP"],
    Kind.CHARGE_MIN_BAL: ["RBI-MINBAL-2014-NOTICE", "RBI-MINBAL-2014-PROPORTIONATE", "RBI-BSBDA-2019"],
    Kind.CHARGE_SMS: ["RBI-SMS-2015-USAGE"],
    Kind.CHARGE_REACTIVATION: ["RBI-INOP-2024-NOCHARGE"],
    Kind.CHARGE_CARD_AMC: ["RBI-CARD-2022-CLOSURE"],
    Kind.CHARGE_CHEQUE: ["RBI-CHEQUE-2018"],
}
TAT_DAYS = {"UPI": 1, "IMPS": 1, "ATM": 5, "CARD": 5, "POS": 5, "ECOM": 5}


def _d(t: Transaction) -> dict[str, Any]:
    return {"id": t.id, "date": t.date.isoformat(), "narration": t.narration, "debit": t.debit, "credit": t.credit,
            "balance": t.balance, "kind": t.kind.value, "channel": t.channel.value}


def twin_summary(ctx: TwinContext, findings: list[Finding]) -> dict[str, Any]:
    """The reconstructed account state, as the twin screen draws it. Every number is a count over real lines."""
    txns = ctx.txns
    charges = [t for t in txns if t.kind in CHARGE_KINDS]
    gst = [t for t in txns if t.kind == Kind.GST_ON_CHARGE]
    reversals = [t for t in txns if t.kind == Kind.REVERSAL]
    atm = [t for t in txns if t.kind == Kind.ATM_WITHDRAWAL]
    failed_hint = [t for t in txns if t.failed_hint]
    flagged_ids = {e for f in findings for e in f.evidence}
    pairs = []
    for p in ctx.pairing.pairs:
        rev = p.reversal_date
        pairs.append({"debit": _d(p.debit), "credits": [_d(c) for c in p.credits], "method": p.method,
                      "days": (rev - p.debit.date).days if rev else None, "reversed_amount": p.reversed_amount,
                      "tat_days": TAT_DAYS.get(p.debit.channel.value), "finding_ids": [f.id for f in findings if p.debit.id in f.evidence]})
    unreversed = [{"txn": _d(t), "tat_days": TAT_DAYS.get(t.channel.value), "days_open": (ctx.as_of - t.date).days,
                   "finding_ids": [f.id for f in findings if t.id in f.evidence]} for t in ctx.pairing.unreversed_failed]
    path = [[t.date.isoformat(), t.balance] for t in txns if t.balance is not None]
    months = sorted({month_key(t.date) for t in txns})
    atm_by_month = {}
    for t in atm:
        u = ctx.atm_uses.get(t.id)
        atm_by_month.setdefault(month_key(t.date), []).append({"id": t.id, "date": t.date.isoformat(), "own": u.own if u else None, "n": u.index_in_month if u else None})
    rules = [r for r in ctx.rulebook.all() if r.status == "active"]
    per_rule = {}
    for f in findings:
        per_rule[f.rule_id] = per_rule.get(f.rule_id, 0) + 1
    return {
        "as_of": ctx.as_of.isoformat(),
        "period": {"from": txns[0].date.isoformat() if txns else None, "to": txns[-1].date.isoformat() if txns else None},
        "counts": {
            "transactions": len(txns), "debits": sum(1 for t in txns if t.is_debit), "credits": sum(1 for t in txns if t.credit > 0),
            "charges": len(charges), "gst_lines": len(gst), "charges_total": round(sum(t.debit for t in charges), 2),
            "reversals": len(reversals), "pairs": len(pairs), "unreversed_failed": len(unreversed), "failed_hints": len(failed_hint),
            "atm_withdrawals": len(atm), "months": len(months), "rules_evaluated": len(rules), "findings": len(findings),
            "flagged_lines": len(flagged_ids), "unflagged_lines": len(txns) - len([t for t in txns if t.id in flagged_ids]),
        },
        "balance_path": path,
        "month_min_balance": ctx.month_min_balance,
        "min_balance_required": ctx.profile.min_balance_required,
        "months": months,
        "atm_by_month": atm_by_month,
        "pairs": pairs,
        "unreversed": unreversed,
        "charges": [_d(t) | {"finding_ids": [f.id for f in findings if t.id in f.evidence]} for t in charges],
        "findings_per_rule": per_rule,
        "rules_active": [r.id for r in rules],
    }


def why_not_flagged(ctx: TwinContext, txn: Transaction, findings: list[Finding]) -> dict[str, Any]:
    """The checklist the engine effectively ran on this one line. Deterministic; no model involved.

    Returns {"checks": [{"ok": bool, "text_en", "text_ta"}], "result_en", "result_ta", "flagged": bool, "finding_ids": [...]}.
    """
    checks: list[dict[str, Any]] = []
    hits = [f for f in findings if txn.id in f.evidence]

    def add(ok: bool, en: str, ta: str):
        checks.append({"ok": ok, "text_en": en, "text_ta": ta})

    k, ch = txn.kind, txn.channel
    add(True, f"Classified as {k.value.replace('_', ' ').lower()} via {ch.value}.", f"{ch.value} வழியா {k.value.replace('_', ' ').lower()}-னு வகைப்படுத்தினோம்.")

    if k in (Kind.CREDIT,):
        add(True, "Money came in — no rule applies to an ordinary credit.", "பணம் வந்திருக்கு — சாதாரண credit-க்கு rule எதுவும் இல்ல.")
    if k == Kind.REVERSAL:
        pr = next((p for p in ctx.pairing.pairs if any(c.id == txn.id for c in p.credits)), None)
        if pr:
            add(True, f"This credit reverses the {pr.debit.date.strftime('%d %b')} {pr.debit.channel.value} debit of ₹{pr.debit.debit:,.0f} (matched by {pr.method}).",
                f"இது {pr.debit.date.strftime('%d %b')} {pr.debit.channel.value} debit ₹{pr.debit.debit:,.0f}-ஐ reverse பண்ணுது ({pr.method} match).")
        else:
            add(True, "A reversal credit with no failed debit in this statement — nothing to claim on it.", "இந்த statement-ல அதுக்கான debit இல்லாத reversal — claim எதுவும் இல்ல.")

    if txn.is_debit and k in (Kind.DEBIT, Kind.ATM_WITHDRAWAL):
        pr = ctx.pairing.pair_for(txn.id)
        tat = TAT_DAYS.get(ch.value)
        if txn.failed_hint:
            add(True, "Narration says the transaction failed.", "Narration-ல fail-னு இருக்கு.")
        else:
            add(True, "Narration does not say failed / declined / timeout.", "Narration-ல fail / declined / timeout-னு எதுவும் இல்ல.")
        if pr:
            rev = pr.reversal_date
            days = (rev - txn.date).days if rev else None
            within = tat is not None and days is not None and days <= tat
            add(within, f"Reversed after {days} day(s) — {'within' if within else 'beyond'} the T+{tat} deadline (RBI/2019-20/67).",
                f"{days} நாள்-ல reverse ஆச்சு — T+{tat} deadline-க்கு {'உள்ள' if within else 'அப்புறம்'} (RBI/2019-20/67).")
        elif txn in ctx.pairing.unreversed_failed:
            add(False, "Marked failed and never reversed — this line IS a finding.", "Fail ஆயி reverse ஆகல — இது finding தான்.")
        else:
            add(True, "No reversal credit found, and nothing marks it as failed → treated as a successful payment.", "Reversal இல்ல, fail-னும் இல்ல → வெற்றிகரமான payment.")
            same = [o for o in ctx.txns if o.id != txn.id and o.is_debit and abs(o.debit - txn.debit) < 0.01 and abs((o.date - txn.date).days) <= 2 and o.channel == ch]
            if same:
                add(True, f"A same-amount retry exists within 2 days ({same[0].date.isoformat()}) — the engine asks you, it never assumes.",
                    f"2 நாளுக்குள்ள அதே தொகை retry இருக்கு ({same[0].date.isoformat()}) — engine கேக்கும், அனுமானிக்காது.")
        if k == Kind.ATM_WITHDRAWAL:
            u = ctx.atm_uses.get(txn.id)
            if u:
                add(True, f"ATM use #{u.index_in_month} this month at an {'own-bank' if u.own else 'other-bank'} ATM — counted toward the free limit.",
                    f"இந்த மாசம் {'own-bank' if u.own else 'other-bank'} ATM-ல #{u.index_in_month} use — free limit-ல கணக்கு.")
        if txn.debit >= 10000 and not txn.failed_hint and not pr:
            add(True, "Large amount, but size alone is never a reason to flag — there is no anomaly detection here, only rule checks.",
                "பெரிய தொகை, ஆனா தொகை மட்டும் flag பண்ண காரணம் இல்ல — anomaly detection இல்ல, rule check மட்டும்.")

    if k in CHARGE_KINDS or k == Kind.GST_ON_CHARGE:
        fam = FAMILY_OF_KIND.get(k, [])
        if k == Kind.GST_ON_CHARGE:
            add(True, "GST line — folded into the charge it follows; judged with that charge.", "GST line — முந்தைய charge-ஓட சேர்த்து பாக்கறோம்.")
        elif fam:
            add(True, f"Examined by {', '.join(fam)}.", f"{', '.join(fam)} rules பாத்தது.")
        if k == Kind.CHARGE_MIN_BAL:
            low = ctx.lowest_balance_in_prior_month(txn.date)
            req = ctx.profile.min_balance_required
            if low is None:
                add(True, "Previous month not in the uploaded statements — the notice question decides (or add that statement).", "முந்தைய மாசம் statement இல்ல — notice கேள்வி முடிவு பண்ணும் (அல்லது அந்த statement சேர்க்கவும்).")
            elif req is not None:
                add(low >= req, f"Lowest balance in the previous month ₹{low:,.0f} vs required ₹{req:,.0f}.", f"முந்தைய மாசம் lowest balance ₹{low:,.0f}, தேவை ₹{req:,.0f}.")

    if hits:
        add(False, f"Result: {len(hits)} finding(s) reference this line — {', '.join(f.rule_id for f in hits)}.", f"முடிவு: {len(hits)} finding இந்த line-ஐ குறிக்குது — {', '.join(f.rule_id for f in hits)}.")
    else:
        add(True, "Result: no rule condition was met. No finding generated.", "முடிவு: எந்த rule condition-ம் பொருந்தல. Finding இல்ல.")
    return {"txn": _d(txn), "checks": checks, "flagged": bool(hits), "finding_ids": [f.id for f in hits],
            "result_en": ("Flagged — see the finding(s)." if hits else "Not flagged — no regulatory condition applies to this line."),
            "result_ta": ("Flag ஆச்சு — finding பாருங்க." if hits else "Flag ஆகல — இந்த line-க்கு எந்த rule-ம் பொருந்தல.")}
