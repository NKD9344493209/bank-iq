"""End-to-end: file → transactions → twin → findings → priorities → summary."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from . import rulebook as rb_mod
from .classify import classify_all
from .models import AccountProfile, Finding, Label, Transaction
from .parsers import parse_bytes, parse_file, ParseResult
from .priority import score_findings
from .rules import run_all
from .rules.failed_transactions import failed_candidates_needing_confirmation, FAILED_Q
from .twin import build_twin
import hashlib


def _stable_ids(findings: list[Finding]) -> list[Finding]:
    """Finding ids are a hash of (rule, evidence, label) so they survive rescans and re-answers."""
    seen: dict[str, int] = {}
    for f in findings:
        key = f.rule_id + "|" + ",".join(f.evidence) + "|" + f.label.value
        h = hashlib.sha1(key.encode()).hexdigest()[:8]
        n = seen.get(h, 0)
        seen[h] = n + 1
        f.id = "f_" + h + (f"_{n}" if n else "")
    return findings


@dataclass
class ScanResult:
    transactions: list[Transaction]
    findings: list[Finding]
    profile: AccountProfile
    parse: ParseResult
    as_of: date
    rulebook_version: str
    suspicious_debits: list[str] = field(default_factory=list)   # txn ids we may ask about

    @property
    def recoverable(self) -> list[Finding]:
        return [f for f in self.findings if f.label == Label.RECOVERABLE]

    @property
    def total_recoverable(self) -> float:
        return round(sum(f.amount for f in self.recoverable), 2)

    @property
    def total_unclear(self) -> float:
        return round(sum(f.amount for f in self.findings if f.label == Label.UNCLEAR), 2)

    def year_total_charges(self) -> float:
        from .models import CHARGE_KINDS
        return round(sum(t.debit for t in self.transactions if t.kind in CHARGE_KINDS), 2)

    def summary(self) -> dict[str, Any]:
        by_label = {l.value: 0 for l in Label}
        for f in self.findings:
            by_label[f.label.value] += 1
        return {
            "total_recoverable": self.total_recoverable,
            "total_unclear": self.total_unclear,
            "total_bank_charges_in_period": self.year_total_charges(),
            "counts": by_label,
            "transactions": len(self.transactions),
            "period": {"from": self.parse.period_from.isoformat() if self.parse.period_from else None,
                       "to": self.parse.period_to.isoformat() if self.parse.period_to else None},
            "bank": self.profile.bank,
            "rulebook_version": self.rulebook_version,
            "warnings": self.parse.warnings,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "profile": self.profile.to_dict(),
            "findings": [f.to_dict() for f in sorted(self.findings, key=lambda f: (-f.priority_score, -f.amount))],
            "transactions": [t.to_dict() for t in self.transactions],
            "suspicious_debits": self.suspicious_debits,
            "questions_for_suspicious": FAILED_Q.to_dict(),
        }


def _run(parse: ParseResult, profile: AccountProfile, as_of: Optional[date], answers: Optional[dict[str, Any]]) -> ScanResult:
    rb = rb_mod.load()
    if not profile.bank and parse.bank:
        profile.bank = parse.bank
    if not profile.account_last4 and parse.account_last4:
        profile.account_last4 = parse.account_last4
    txns = [Transaction(date=r["date"], narration=r["narration"], debit=r["debit"], credit=r["credit"], balance=r["balance"], ref=r.get("ref", ""), seq=i) for i, r in enumerate(parse.rows)]
    txns = classify_all(txns, own_bank=profile.bank)
    as_of = as_of or date.today()
    ctx = build_twin(txns, profile, rb, as_of=as_of, answers=answers)
    findings = _stable_ids(run_all(ctx))
    findings = score_findings(findings, rb, as_of)
    suspicious = [t.id for t in failed_candidates_needing_confirmation(ctx)]
    return ScanResult(transactions=ctx.txns, findings=findings, profile=profile, parse=parse, as_of=as_of, rulebook_version=rb.version, suspicious_debits=suspicious)


def scan_file(path: str, profile: Optional[AccountProfile] = None, as_of: Optional[date] = None, answers: Optional[dict[str, Any]] = None, bank_hint: str = "") -> ScanResult:
    profile = profile or AccountProfile()
    return _run(parse_file(path, bank_hint or profile.bank), profile, as_of, answers)


def scan_bytes(data: bytes, filename: str, profile: Optional[AccountProfile] = None, as_of: Optional[date] = None, answers: Optional[dict[str, Any]] = None) -> ScanResult:
    profile = profile or AccountProfile()
    return _run(parse_bytes(data, filename, profile.bank), profile, as_of, answers)


def rescan(transactions: list[Transaction], profile: AccountProfile, as_of: date, answers: dict[str, Any], parse: Optional[ParseResult] = None) -> ScanResult:
    """Re-run rules with new answers on already-parsed transactions."""
    rb = rb_mod.load()
    fresh = [Transaction(date=t.date, narration=t.narration, debit=t.debit, credit=t.credit, balance=t.balance, ref=t.ref, id=t.id, seq=t.seq) for t in transactions]
    fresh = classify_all(fresh, own_bank=profile.bank)
    ctx = build_twin(fresh, profile, rb, as_of=as_of, answers=answers)
    findings = score_findings(_stable_ids(run_all(ctx)), rb, as_of)
    parse = parse or ParseResult(rows=[], bank=profile.bank)
    if not parse.period_from and fresh:
        parse.period_from, parse.period_to = fresh[0].date, fresh[-1].date
    return ScanResult(transactions=ctx.txns, findings=findings, profile=profile, parse=parse, as_of=as_of, rulebook_version=rb.version, suspicious_debits=[t.id for t in failed_candidates_needing_confirmation(ctx)])
