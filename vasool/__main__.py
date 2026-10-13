"""Command line: python -m vasool scan <file> [--bank CANARA] [--min-balance 500] [--as-of 2026-09-13] [--json]"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import scan
from .models import AccountProfile, AccountType, CityTier
from .rules.base import inr


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vasool", description="Bank IQ — run the RBI rulebook on a bank statement.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan a statement (CSV/TSV/XLSX/PDF/image)")
    s.add_argument("file")
    s.add_argument("--bank", default="")
    s.add_argument("--account-type", default="SAVINGS", choices=[a.value for a in AccountType])
    s.add_argument("--city", default="NON_METRO", choices=[c.value for c in CityTier])
    s.add_argument("--min-balance", type=float, default=None)
    s.add_argument("--as-of", default=None)
    s.add_argument("--lang", default="en", choices=["en", "ta"])
    s.add_argument("--json", action="store_true")
    r = sub.add_parser("rules", help="list the rulebook")
    r.add_argument("--on", default=None, help="only rules in force on this date")
    a = ap.parse_args(argv)

    if a.cmd == "rules":
        from . import rulebook
        rb = rulebook.load()
        on = date.fromisoformat(a.on) if a.on else None
        for rule in rb.all():
            if on and not rule.in_force(on):
                continue
            print(f"{rule.id:28} {rule.status:8} {rule.effective_from} → {rule.effective_to or 'present'}  {rule.title}")
        return 0

    prof = AccountProfile(bank=a.bank.upper(), account_type=AccountType(a.account_type), city_tier=CityTier(a.city), min_balance_required=a.min_balance, language=a.lang)
    res = scan.scan_file(a.file, prof, as_of=date.fromisoformat(a.as_of) if a.as_of else None)
    if a.json:
        json.dump(res.to_dict(), sys.stdout, ensure_ascii=False, indent=2)
        return 0
    s = res.summary()
    print(f"\nBank IQ Scan · {s['bank'] or 'bank?'} · {s['period']['from']} → {s['period']['to']} · {s['transactions']} transactions · rulebook {s['rulebook_version']}")
    for w in s["warnings"]:
        print("  !", w)
    print(f"\n  {inr(s['total_recoverable'])} recoverable   ·   {inr(s['total_unclear'])} pending one answer   ·   bank charges in period {inr(s['total_bank_charges_in_period'])}\n")
    for f in sorted(res.findings, key=lambda f: (-f.priority_score, -f.amount)):
        tag = {"RECOVERABLE": "🔴", "AVOIDABLE": "🟡", "UNCLEAR": "⚪"}[f.label.value]
        print(f"  {tag} {inr(f.amount):>12}  {f.priority.value:12} {f.rule_id:26} {f.summary_ta if a.lang == 'ta' else f.summary_en}")
        print(f"       ↳ {f.calculation}")
        for q in f.questions:
            print(f"       ? {q.text_ta if a.lang == 'ta' else q.text_en}  [{' / '.join(q.options)}]")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
