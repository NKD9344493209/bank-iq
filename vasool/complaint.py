"""Complaint pack generation.

Tone rules (deliberate): we never say the bank cheated. Every complaint asks
the bank to *produce* the notice / disclosure / reversal, states the RBI rule,
shows the arithmetic, and asks for the credit. That is exactly how the
Ombudsman frames it, and it survives the case where the bank turns out to be
right.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from .models import AccountProfile, Finding, Transaction
from .rulebook import Rulebook
from .rules.base import dmy, inr

BANK_GRIEVANCE_EMAIL = {
    "SBI": "customercare@sbi.co.in", "HDFC": "support@hdfcbank.com", "ICICI": "customer.care@icicibank.com",
    "AXIS": "customer.service@axisbank.com", "CANARA": "hocss@canarabank.com", "PNB": "care@pnb.co.in",
    "BOB": "cs.ho@bankofbaroda.com", "UNION": "customercare@unionbankofindia.bank", "KOTAK": "service.bank@kotak.com",
    "INDIAN BANK": "customercomplaints@indianbank.co.in", "IOB": "customercare@iobnet.co.in", "BOI": "boi.callcentre@bankofindia.co.in",
    "TMB": "customerservice@tmbank.in", "CUB": "customercare@cityunionbank.com", "KVB": "customersupport@kvbmail.com",
    "FEDERAL": "contact@federalbank.co.in", "IDBI": "customercare@idbi.co.in",
}


@dataclass
class ComplaintPack:
    subject: str
    bank_email_to: str
    bank_letter: str
    ombudsman_text: str
    evidence_table: str
    total: float
    reply_due: date
    ombudsman_window_ends: date


def _evidence_rows(findings: Iterable[Finding], txns_by_id: dict[str, Transaction]) -> tuple[str, list[Transaction]]:
    seen: dict[str, Transaction] = {}
    for f in findings:
        for tid in f.evidence:
            t = txns_by_id.get(tid)
            if t and tid not in seen:
                seen[tid] = t
    rows = sorted(seen.values(), key=lambda t: t.date)
    lines = ["| Date | Narration | Debit | Credit | Balance | Ref |", "|---|---|---|---|---|---|"]
    for t in rows:
        lines.append(f"| {t.date.isoformat()} | {t.narration} | {inr(t.debit) if t.debit else ''} | {inr(t.credit) if t.credit else ''} | {inr(t.balance) if t.balance is not None else ''} | {t.ref} |")
    return "\n".join(lines), rows


def build_pack(findings: list[Finding], txns_by_id: dict[str, Transaction], profile: AccountProfile, rb: Rulebook, sent_on: date | None = None, case_id: str = "") -> ComplaintPack:
    sent_on = sent_on or date.today()
    findings = [f for f in findings if f.label.value == "RECOVERABLE"]
    total = sum(f.amount for f in findings)
    bank = profile.bank or "the Bank"
    acct = f"account ending {profile.account_last4}" if profile.account_last4 else "my savings account"
    holder = profile.holder_name or "the account holder"
    clock = rb.get("RBI-OMBUDSMAN-2026-CLOCK").parameters
    reply_due = sent_on + timedelta(days=int(clock["bank_reply_days"]))
    omb_end = reply_due + timedelta(days=int(clock["ombudsman_window_days"]))

    items = []
    for i, f in enumerate(findings, 1):
        rule = rb.get(f.rule_id)
        items.append(
            f"{i}. {rule.title}\n"
            f"   RBI reference: {rule.source['circular']} ({rule.source['date']}), {rule.source['url']}\n"
            f"   What the rule requires: {f.expected}\n"
            f"   What the statement shows: {f.actual}\n"
            f"   Calculation: {f.calculation}\n"
            f"   Amount claimed: {inr(f.amount)}"
        )
    evidence_md, rows = _evidence_rows(findings, txns_by_id)

    subject = f"Grievance — {acct} — request for credit of {inr(total)} under RBI directions" + (f" [Ref {case_id}]" if case_id else "")

    bank_letter = f"""To: The Grievance Redressal Officer, {bank}
From: {holder}, {acct}
Date: {dmy(sent_on)}
Subject: {subject}

Dear Sir/Madam,

I am writing under your Board-approved grievance redressal policy and the Reserve Bank of India's customer-protection directions regarding the following entries in my account statement.

{chr(10).join(items)}

Total amount requested to be credited: {inr(total)}

I request that the Bank:
  (a) credit the above amount to my account, or
  (b) where the Bank believes a charge was correctly levied, provide me the specific evidence relied upon — the date and mode of the prior notice, the disclosure document, or the reversal reference — with the RBI provision that permits the charge.

Please treat this as a formal complaint and provide a written reply with a complaint reference number. Under the Reserve Bank – Integrated Ombudsman Scheme, 2026, if I do not receive a satisfactory reply within 30 days (by {dmy(reply_due)}), I intend to approach the RBI Ombudsman through cms.rbi.org.in.

The relevant statement entries are attached.

Yours faithfully,
{holder}
{acct}
"""

    ombudsman_text = f"""RBI COMPLAINT MANAGEMENT SYSTEM (cms.rbi.org.in) — DRAFT FOR SUBMISSION
(Submit only after {dmy(reply_due)} if the Bank has not replied, or earlier if the reply is unsatisfactory. Window closes {dmy(omb_end)}.)

Regulated Entity: {bank}
Account: {acct}
Nature of complaint: Deficiency in service — non-adherence to RBI directions on customer charges / failed-transaction compensation
Amount involved: {inr(total)}
Complaint first lodged with the Bank on: {dmy(sent_on)}    Bank reference: ________    Bank reply: ________

Facts:
{chr(10).join(items)}

Relief sought: Credit of {inr(total)} to my account together with any compensation the Ombudsman considers appropriate for the delay and deficiency in service.

Documents attached: account statement extract (below), copy of complaint to the Bank dated {dmy(sent_on)}, Bank's reply (if any).
"""
    return ComplaintPack(
        subject=subject, bank_email_to=BANK_GRIEVANCE_EMAIL.get(profile.bank.upper(), ""),
        bank_letter=bank_letter, ombudsman_text=ombudsman_text, evidence_table=evidence_md,
        total=total, reply_due=reply_due, ombudsman_window_ends=omb_end,
    )


def basic_account_request(profile: AccountProfile) -> str:
    bank = profile.bank or "the Bank"
    acct = f"account ending {profile.account_last4}" if profile.account_last4 else "my savings account"
    holder = profile.holder_name or "the account holder"
    return f"""To: The Branch Manager, {bank}
From: {holder}, {acct}
Date: {dmy(date.today())}
Subject: Request to convert {acct} to a Basic Savings Bank Deposit Account (BSBDA)

Dear Sir/Madam,

Under the Reserve Bank of India's directions on Basic Savings Bank Deposit Accounts (as amended with effect from 1 April 2026), every customer is entitled to convert an existing savings account into a BSBDA on request, and the bank is required to complete the conversion within 7 working days.

I request that {acct} be converted to a BSBDA. I understand a BSBDA carries no minimum-balance requirement and no charges for the basic services prescribed by RBI, and I do not hold any other BSBDA.

Kindly confirm the conversion in writing.

Yours faithfully,
{holder}
"""
