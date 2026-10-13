"""Statement parsers: CSV (any bank), PDF text, passbook photo (OCR).

Each parser returns a list of raw rows {date, narration, debit, credit, balance, ref}.
Classification happens later in `vasool.classify`, so parsers stay dumb and
bank-agnostic. Bank detection is a hint used to decide own-bank vs other-bank
ATMs; it never changes the rules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import csv_parser, pdf_parser, image_parser
from .common import ParseResult, detect_bank


def parse_file(path: str | Path, bank_hint: str = "") -> ParseResult:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".csv", ".txt", ".tsv"}:
        res = csv_parser.parse(p)
    elif suffix == ".pdf":
        res = pdf_parser.parse(p)
    elif suffix in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
        res = image_parser.parse(p)
    elif suffix in {".xlsx", ".xls"}:
        res = csv_parser.parse_excel(p)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    res.detected_bank = res.bank or detect_bank(res.raw_text or " ".join(r["narration"] for r in res.rows))
    res.bank = bank_hint.upper() if bank_hint else res.detected_bank
    return res


def parse_bytes(data: bytes, filename: str, bank_hint: str = "") -> ParseResult:
    import tempfile
    suffix = Path(filename).suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
        fh.write(data)
        tmp = fh.name
    return parse_file(tmp, bank_hint)


__all__ = ["parse_file", "parse_bytes", "ParseResult"]
