"""The Regulatory Twin.

A twin is the account's *rule-relevant state* rebuilt from the statement:
monthly ATM usage, the balance path, gaps between customer-initiated
transactions, the history of each charge kind, and the debit↔reversal pairs.
Rules read this state and compare what happened with what should have.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

from .models import AccountProfile, Kind, Transaction, CUSTOMER_INITIATED_KINDS, CHARGE_KINDS
from .pairing import PairingResult, pair_transactions
from .rulebook import Rulebook


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


@dataclass
class AtmUse:
    txn: Transaction
    own: bool
    index_in_month: int          # 1-based count of ATM txns of this class (own/other) so far this month


@dataclass
class TwinContext:
    txns: list[Transaction]
    profile: AccountProfile
    rulebook: Rulebook
    as_of: date
    answers: dict[str, Any] = field(default_factory=dict)   # question_id → answer (may be keyed "qid:txn_id")
    pairing: PairingResult = None  # type: ignore
    atm_uses: dict[str, AtmUse] = field(default_factory=dict)        # txn id → AtmUse
    month_min_balance: dict[str, float] = field(default_factory=dict)
    month_charge_history: dict[Kind, list[Transaction]] = field(default_factory=lambda: defaultdict(list))
    by_id: dict[str, Transaction] = field(default_factory=dict)

    def answer(self, qid: str, txn_id: str = "") -> Any:
        if txn_id and f"{qid}:{txn_id}" in self.answers:
            return self.answers[f"{qid}:{txn_id}"]
        return self.answers.get(qid)

    def last_customer_txn_before(self, d: date, exclude_id: str = "") -> Optional[Transaction]:
        last = None
        for t in self.txns:
            if t.date >= d:
                break
            if t.id != exclude_id and t.kind in CUSTOMER_INITIATED_KINDS:
                last = t
        return last

    def balance_before(self, txn: Transaction) -> Optional[float]:
        if txn.balance is None:
            return None
        return txn.balance + txn.debit - txn.credit

    def prior_month_key(self, d: date) -> str:
        return month_key(d.replace(day=1) - timedelta(days=1))

    def lowest_balance_in_prior_month(self, d: date) -> Optional[float]:
        return self.month_min_balance.get(self.prior_month_key(d))

    def transactions_in_month(self, key: str) -> list[Transaction]:
        return [t for t in self.txns if month_key(t.date) == key]


def build_twin(txns: list[Transaction], profile: AccountProfile, rulebook: Rulebook, as_of: Optional[date] = None, answers: Optional[dict[str, Any]] = None) -> TwinContext:
    txns = sorted(txns, key=lambda t: (t.date, t.seq))
    ctx = TwinContext(txns=txns, profile=profile, rulebook=rulebook, as_of=as_of or date.today(), answers=answers or {})
    ctx.by_id = {t.id: t for t in txns}
    ctx.pairing = pair_transactions(txns)

    # ATM usage per month, split own/other; unknown-bank ATMs are counted as OWN (conservative:
    # more free transactions → fewer claims → fewer false positives)
    counters: dict[tuple[str, bool], int] = defaultdict(int)
    for t in txns:
        if t.kind in {Kind.ATM_WITHDRAWAL, Kind.ATM_ENQUIRY}:
            own = True if t.own_bank_atm is None else t.own_bank_atm
            counters[(month_key(t.date), own)] += 1
            ctx.atm_uses[t.id] = AtmUse(t, own, counters[(month_key(t.date), own)])

    # balance path
    mins: dict[str, float] = {}
    for t in txns:
        if t.balance is None:
            continue
        k = month_key(t.date)
        mins[k] = min(mins.get(k, t.balance), t.balance)
    ctx.month_min_balance = mins

    # charge history
    for t in txns:
        if t.kind in CHARGE_KINDS:
            ctx.month_charge_history[t.kind].append(t)
    return ctx
