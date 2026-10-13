"""Debit ↔ reversal pairing.

The hardest part of the failed-transaction rule is not the ₹100/day arithmetic,
it is deciding which credit reverses which debit. Pairing order:

  1. same reference number (UTR / RRN) on both lines
  2. same amount, same channel, credit within the window after the debit
  3. partial / batched reversals: up to three credits on the same channel
     within the window whose amounts sum to the debit

An ordinary UPI payment with no reversal is a successful payment, not a
claim. A debit only becomes a failed-transaction candidate if its narration
says so (FAILED / DECLINED / TIMEOUT), if a reversal exists (proving it
failed), or if the customer tells us it failed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from itertools import combinations
from typing import Optional

from .models import Channel, Kind, Transaction

PAIR_WINDOW_DAYS = 60
FAILED_CHANNELS = {Channel.ATM, Channel.UPI, Channel.IMPS, Channel.POS, Channel.ECOM, Channel.CARD}


@dataclass
class Pair:
    debit: Transaction
    credits: list[Transaction] = field(default_factory=list)
    method: str = ""              # ref / amount / partial

    @property
    def reversal_date(self):
        return max(c.date for c in self.credits) if self.credits else None

    @property
    def reversed_amount(self) -> float:
        return sum(c.credit for c in self.credits)


@dataclass
class PairingResult:
    pairs: list[Pair]
    unreversed_failed: list[Transaction]      # debit says failed, no reversal found
    used_credit_ids: set[str]

    def pair_for(self, debit_id: str) -> Optional[Pair]:
        return next((p for p in self.pairs if p.debit.id == debit_id), None)


def _candidate_debits(txns: list[Transaction]) -> list[Transaction]:
    return [t for t in txns if t.is_debit and t.channel in FAILED_CHANNELS and t.kind in {Kind.DEBIT, Kind.ATM_WITHDRAWAL}]


def _candidate_credits(txns: list[Transaction]) -> list[Transaction]:
    return [t for t in txns if t.credit > 0 and t.kind in {Kind.REVERSAL, Kind.CREDIT} and t.channel in FAILED_CHANNELS | {Channel.OTHER, Channel.BANK}]


def _same_channel(d: Transaction, c: Transaction) -> bool:
    if c.channel == d.channel:
        return True
    # reversals are often posted as generic bank credits
    return c.channel in {Channel.OTHER, Channel.BANK} and c.kind == Kind.REVERSAL


def pair_transactions(txns: list[Transaction], window_days: int = PAIR_WINDOW_DAYS) -> PairingResult:
    debits = _candidate_debits(txns)
    credits = _candidate_credits(txns)
    used: set[str] = set()
    pairs: list[Pair] = []

    def in_window(d: Transaction, c: Transaction) -> bool:
        return d.date <= c.date <= d.date + timedelta(days=window_days)

    # pass 1: reference match
    for d in debits:
        if not d.ref:
            continue
        for c in credits:
            if c.id in used or not in_window(d, c):
                continue
            if c.ref and c.ref == d.ref and abs(c.credit - d.debit) < 0.01:
                pairs.append(Pair(d, [c], "ref"))
                used.add(c.id)
                break

    paired_debits = {p.debit.id for p in pairs}

    # pass 2: exact amount, same channel, reversal-kind preferred
    for d in debits:
        if d.id in paired_debits:
            continue
        cands = [c for c in credits if c.id not in used and in_window(d, c) and abs(c.credit - d.debit) < 0.01 and _same_channel(d, c)]
        cands.sort(key=lambda c: (c.kind != Kind.REVERSAL, c.date))
        if cands and (cands[0].kind == Kind.REVERSAL or d.failed_hint):
            pairs.append(Pair(d, [cands[0]], "amount"))
            used.add(cands[0].id)
            paired_debits.add(d.id)

    # pass 3: partial / batched reversals (reversal-kind credits only)
    for d in debits:
        if d.id in paired_debits:
            continue
        cands = [c for c in credits if c.id not in used and in_window(d, c) and c.kind == Kind.REVERSAL and _same_channel(d, c) and c.credit < d.debit]
        found = None
        for k in (2, 3):
            for combo in combinations(cands, k):
                if abs(sum(c.credit for c in combo) - d.debit) < 0.01:
                    found = list(combo)
                    break
            if found:
                break
        if found:
            pairs.append(Pair(d, found, "partial"))
            used.update(c.id for c in found)
            paired_debits.add(d.id)

    unreversed_failed = [d for d in debits if d.id not in paired_debits and d.failed_hint]
    return PairingResult(pairs=pairs, unreversed_failed=unreversed_failed, used_credit_ids=used)
