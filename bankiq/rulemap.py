"""Bridge between the existing rule-based classifier (vasool.classify) and the ML categories.

Used (a) as the *baseline* in the classification experiment — how well do the hand-written
regex rules do on the labelled data? — and (b) by the service to show both verdicts side by side.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from vasool.classify import CREDIT_HINTS, classify
from vasool.models import Channel, Kind, Transaction

CHARGE = {Kind.CHARGE_ATM, Kind.CHARGE_MIN_BAL, Kind.CHARGE_SMS, Kind.CHARGE_CARD_AMC, Kind.CHARGE_CHEQUE, Kind.CHARGE_REACTIVATION, Kind.CHARGE_OTHER, Kind.GST_ON_CHARGE, Kind.LOAN_PENAL, Kind.LOAN_CHARGE}


def rule_category(narration: str, debit: float, credit: float, d: date | None = None) -> str:
    t = classify(Transaction(date=d or date.today(), narration=str(narration), debit=float(debit or 0), credit=float(credit or 0)))
    n = str(narration).upper()
    if t.kind in CHARGE:
        return "BANK_CHARGE"
    if t.kind == Kind.LOAN_EMI:
        return "LOAN_EMI"
    if t.kind in (Kind.ATM_WITHDRAWAL, Kind.ATM_ENQUIRY):
        return "ATM_WITHDRAWAL"
    if t.kind in (Kind.REVERSAL, Kind.COMPENSATION):
        return "REFUND_REVERSAL"
    if t.kind == Kind.INTEREST_CREDIT:
        return "INTEREST_CREDIT"
    if t.kind == Kind.DEBIT:
        if t.channel == Channel.UPI:
            return "UPI_PAYMENT"
        if t.channel in (Channel.POS, Channel.ECOM, Channel.CARD):
            return "CARD_POS"
        return "TRANSFER_OUT"
    # credits
    if "SALARY" in n or "PENSION" in n or " SAL " in f" {n} " or n.startswith("SAL"):
        return "INCOME_CREDIT"
    return "TRANSFER_IN"


def rule_categories(df: pd.DataFrame) -> pd.Series:
    return pd.Series([rule_category(n, d, c) for n, d, c in zip(df["narration"], df["debit"], df["credit"])], index=df.index)
