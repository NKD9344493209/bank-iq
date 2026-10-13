"""Merging several statements of the same account into one transaction history.

Why this exists
* Banks hand out statements in slices (quarter, month, "last 6 months"). The
  Digital Twin needs the *whole* path: a minimum-balance penalty charged on
  30 June is judged on May's balances, which live in the previous statement.
* Slices overlap (a statement "1 Mar – 4 Jun" and one "2 Jun – 31 Aug" share
  a few lines). Overlaps must be dropped, not double counted, or the ATM
  counters and charge totals go wrong.

Rules
* Identity of a line = (date, normalised narration, debit, credit, balance).
  Balance is part of the key when both sides have one — two identical ₹500
  UPI payments to the same shop on the same day are different lines *only*
  if the running balance differs.
* Existing transactions keep their ids. Finding ids and the user's answers
  hang off transaction ids, so a second upload must never re-key the first.
* New lines get fresh ids; the merged list is renumbered so `seq` keeps
  same-day order stable across files (existing lines first).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, Optional

from .models import Transaction

_WS = re.compile(r"\s+")


def line_key(t: Transaction, with_balance: bool = True) -> tuple:
    narr = _WS.sub(" ", (t.narration or "").strip().upper())
    key = (t.date.isoformat(), narr, round(float(t.debit or 0), 2), round(float(t.credit or 0), 2))
    if with_balance:
        key += (None if t.balance is None else round(float(t.balance), 2),)
    return key


@dataclass
class MergeResult:
    transactions: list[Transaction]
    added: list[Transaction] = field(default_factory=list)
    duplicates: int = 0
    warnings: list[str] = field(default_factory=list)


def merge_transactions(existing: list[Transaction], incoming: list[Transaction]) -> MergeResult:
    """Union of two statements; existing ids preserved; incoming duplicates dropped."""
    seen_full = {line_key(t, True) for t in existing}
    seen_nobal = {line_key(t, False) for t in existing}
    merged = list(existing)
    added: list[Transaction] = []
    dups = 0
    for t in incoming:
        k_full, k_nobal = line_key(t, True), line_key(t, False)
        # exact line already present → duplicate. If either side lacks a balance,
        # fall back to the balance-less key (passbook photo vs CSV of the same month).
        if k_full in seen_full or (t.balance is None or k_full[-1] is None) and k_nobal in seen_nobal:
            dups += 1
            continue
        seen_full.add(k_full)
        seen_nobal.add(k_nobal)
        merged.append(t)
        added.append(t)
    # stable order: date, then original file order (existing lines first)
    added_ids = {t.id for t in added}
    merged.sort(key=lambda t: (t.date, 1 if t.id in added_ids else 0, t.seq))
    for i, t in enumerate(merged):
        t.seq = i
    res = MergeResult(transactions=merged, added=added, duplicates=dups)
    res.warnings.extend(_balance_continuity_warnings(existing, added))
    return res


def _balance_continuity_warnings(existing: list[Transaction], added: list[Transaction]) -> list[str]:
    """If the new slice's first balance doesn't follow from the old slice's last balance,
    say so — it usually means a different account, or a missing slice in between."""
    if not existing or not added:
        return []
    old = [t for t in existing if t.balance is not None]
    new = [t for t in added if t.balance is not None]
    if not old or not new:
        return []
    old_last = max(old, key=lambda t: (t.date, t.seq))
    new_first = min(new, key=lambda t: (t.date, t.seq))
    if new_first.date <= old_last.date:
        return []   # overlapping or earlier slice — continuity is checked the other way round below
    expected = round(old_last.balance - new_first.debit + new_first.credit, 2)
    if abs(expected - new_first.balance) > 0.01:
        return [f"Balance jump between {old_last.date.isoformat()} ({expected:.2f} expected) and {new_first.date.isoformat()} ({new_first.balance:.2f}). "
                "Some transactions between the two statements may be missing — upload the statement for that period too."]
    return []


@dataclass
class Coverage:
    periods: list[tuple[date, date]]
    gaps: list[tuple[date, date]]

    def to_dict(self) -> dict:
        return {"periods": [[a.isoformat(), b.isoformat()] for a, b in self.periods],
                "gaps": [[a.isoformat(), b.isoformat()] for a, b in self.gaps],
                "from": self.periods[0][0].isoformat() if self.periods else None,
                "to": self.periods[-1][1].isoformat() if self.periods else None}


def coverage(periods: Iterable[tuple[Optional[date], Optional[date]]], tolerance_days: int = 7) -> Coverage:
    """Merge statement periods into covered ranges and list the gaps between them.
    A gap shorter than `tolerance_days` (statement issued on a Friday, next starts Monday) is ignored."""
    ps = sorted((a, b) for a, b in periods if a and b)
    merged: list[tuple[date, date]] = []
    for a, b in ps:
        if merged and a <= merged[-1][1] + timedelta(days=tolerance_days):
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    gaps = [(merged[i][1] + timedelta(days=1), merged[i + 1][0] - timedelta(days=1)) for i in range(len(merged) - 1)]
    return Coverage(periods=merged, gaps=gaps)
