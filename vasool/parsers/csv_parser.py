"""CSV / Excel statement parser with column auto-detection.

Handles the common Indian bank export shapes:
  * separate Debit / Withdrawal and Credit / Deposit columns
  * a single Amount column with a Dr/Cr column or a signed amount
  * header rows preceded by account metadata lines
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any

from .common import ParseResult, parse_amount, parse_date, extract_ref

HEADER_ALIASES = {
    "date": ["txn date", "transaction date", "value date", "date", "tran date", "posting date", "txn dt"],
    "narration": ["narration", "description", "particulars", "details", "transaction details", "remarks", "transaction remarks", "desc"],
    "debit": ["withdrawal amt", "withdrawal", "debit", "debit amount", "withdrawal amount", "withdrawals", "dr", "debit amt", "withdrawal (dr)"],
    "credit": ["deposit amt", "deposit", "credit", "credit amount", "deposit amount", "deposits", "cr", "credit amt", "deposit (cr)"],
    "balance": ["closing balance", "balance", "available balance", "running balance", "balance amt", "bal"],
    "amount": ["amount", "transaction amount", "amt"],
    "drcr": ["dr/cr", "cr/dr", "type", "dr cr", "transaction type", "txn type"],
    "ref": ["ref no", "chq/ref no", "cheque no", "ref no./cheque no.", "reference", "utr", "ref", "chq no", "cheque/ref no"],
}


def _norm(h: str) -> str:
    return re.sub(r"[^a-z/() ]", "", (h or "").strip().lower())


def _map_headers(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    normed = [_norm(h) for h in headers]
    for key, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            for i, h in enumerate(normed):
                if h == alias and key not in mapping and i not in mapping.values():
                    mapping[key] = i
                    break
            if key in mapping:
                break
        if key not in mapping:  # looser contains-match
            for alias in aliases:
                for i, h in enumerate(normed):
                    if alias in h and key not in mapping and i not in mapping.values():
                        mapping[key] = i
                        break
                if key in mapping:
                    break
    return mapping


def _find_header_row(rows: list[list[str]]) -> int:
    for idx, row in enumerate(rows[:40]):
        m = _map_headers(row)
        if "date" in m and ("narration" in m or "debit" in m or "amount" in m):
            return idx
    return -1


def parse_rows(rows: list[list[str]], source_kind: str = "csv") -> ParseResult:
    res = ParseResult(source_kind=source_kind)
    hidx = _find_header_row(rows)
    if hidx < 0:
        res.warnings.append("Could not find a header row with a Date column.")
        return res.finalize()
    meta_text = " ".join(" ".join(r) for r in rows[:hidx])
    res.raw_text = meta_text
    m = re.search(r"(?:A/?c|Account)\s*(?:No\.?|Number)?[:\s]*[X\*x]*(\d{4})\b", meta_text)
    if m:
        res.account_last4 = m.group(1)
    mapping = _map_headers(rows[hidx])
    for row in rows[hidx + 1:]:
        if not any(c.strip() for c in row):
            continue
        get = lambda k: row[mapping[k]] if k in mapping and mapping[k] < len(row) else ""
        d = parse_date(get("date"))
        if not d:
            continue
        narration = get("narration").strip()
        debit = credit = 0.0
        if "debit" in mapping or "credit" in mapping:
            debit = abs(parse_amount(get("debit")))
            credit = abs(parse_amount(get("credit")))
        elif "amount" in mapping:
            amt = parse_amount(get("amount"))
            drcr = get("drcr").strip().upper()
            if drcr.startswith("D") or amt < 0:
                debit = abs(amt)
            else:
                credit = abs(amt)
        bal_raw = get("balance")
        balance = parse_amount(bal_raw) if bal_raw.strip() else None
        ref = get("ref").strip() or extract_ref(narration)
        res.rows.append({"date": d, "narration": narration, "debit": debit, "credit": credit, "balance": balance, "ref": ref})
    return res.finalize()


def parse(path: Path) -> ParseResult:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    best: ParseResult | None = None
    for delim in ("\t", ",", ";", "|"):
        rows = [[c for c in r] for r in csv.reader(io.StringIO(text), delimiter=delim)]
        if _find_header_row(rows) < 0:
            continue
        res = parse_rows(rows, "csv")
        if best is None or len(res.rows) > len(best.rows):
            best = res
    if best is None:
        best = ParseResult(source_kind="csv")
        best.warnings.append("Could not find a header row with a Date column.")
    return best


def parse_excel(path: Path) -> ParseResult:
    try:
        import openpyxl  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("openpyxl is required for .xlsx statements") from e
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = [["" if v is None else str(v) for v in r] for r in ws.iter_rows(values_only=True)]
    return parse_rows(rows, "xlsx")
