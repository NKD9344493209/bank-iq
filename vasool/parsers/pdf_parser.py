"""PDF statement parser.

Strategy: try table extraction with pdfplumber (works for most bank PDFs
because they are generated, not scanned); fall back to line-based regex on the
page text; and if the PDF has no text layer at all, hand the pages to the OCR
parser used for passbook photos.
"""
from __future__ import annotations

import re
from pathlib import Path

from .common import ParseResult, parse_amount, parse_date, extract_ref
from .csv_parser import parse_rows

DATE_TOKEN = r"(\d{2}[/-]\d{2}[/-]\d{2,4}|\d{2}[ -][A-Za-z]{3}[ -]\d{2,4}|\d{4}-\d{2}-\d{2})"
AMT_TOKEN = r"(-?[\d,]+\.\d{2})"
# "date narration ... debit credit balance"   or   "date narration ... amount balance"
LINE_RE = re.compile(
    rf"^\s*{DATE_TOKEN}\s+(.*?)\s+{AMT_TOKEN}(?:\s+{AMT_TOKEN})?(?:\s+{AMT_TOKEN})?\s*(Cr|Dr|CR|DR)?\s*$"
)


def _rows_from_tables(pdf) -> list[list[str]]:
    rows: list[list[str]] = []
    for page in pdf.pages:
        for table in page.extract_tables() or []:
            for r in table:
                rows.append([("" if c is None else str(c)).replace("\n", " ").strip() for c in r])
    return rows


def _rows_from_text(text: str) -> ParseResult:
    res = ParseResult(source_kind="pdf-text", raw_text=text[:5000])
    prev_balance = None
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        d = parse_date(m.group(1))
        if not d:
            continue
        narration = m.group(2).strip()
        nums = [parse_amount(x) for x in (m.group(3), m.group(4), m.group(5)) if x]
        drcr = (m.group(6) or "").upper()
        debit = credit = 0.0
        balance = None
        if len(nums) == 3:
            debit, credit, balance = nums
        elif len(nums) == 2:
            amt, balance = nums
            if drcr.startswith("D") or (prev_balance is not None and balance < prev_balance):
                debit = abs(amt)
            else:
                credit = abs(amt)
        elif len(nums) == 1:
            amt = nums[0]
            if drcr.startswith("D"):
                debit = abs(amt)
            elif drcr.startswith("C"):
                credit = abs(amt)
            else:
                continue
        prev_balance = balance if balance is not None else prev_balance
        res.rows.append({"date": d, "narration": narration, "debit": debit, "credit": credit, "balance": balance, "ref": extract_ref(narration)})
    return res.finalize()


# Indian Bank / IndOASIS-style layout: "DD Mon YYYY  narration…  - | INR 111.00   INR 199.00 | -   INR 1,028.58"
# The narration wraps onto following lines that carry no date; those lines belong to the row above.
INR_AMT = r"(?:INR\s*([\d,]+\.\d{2})|-)"
INR_LINE_RE = re.compile(rf"^\s*{DATE_TOKEN}\s+(.*?)\s+{INR_AMT}\s+{INR_AMT}\s+INR\s*([\d,]+\.\d{{2}})\s*$")
STOP_RE = re.compile(r"^\s*(Page\s+\d+|ACCOUNT\s|Account\s|Date\s+Transaction|Opening Balance|Closing Balance|Ending Balance|Total\s|This is a|Statement|Last \d+ Transactions|Customer|Branch|IFSC|Generated|Disclaimer|\*)", re.I)


def _rows_from_text_inr(text: str) -> ParseResult:
    res = ParseResult(source_kind="pdf-text", raw_text=text[:5000])
    cur = None
    for line in text.splitlines():
        m = INR_LINE_RE.match(line)
        if m:
            d = parse_date(m.group(1))
            if not d:
                cur = None
                continue
            cur = {"date": d, "narration": m.group(2).strip(), "debit": parse_amount(m.group(3)) if m.group(3) else 0.0,
                   "credit": parse_amount(m.group(4)) if m.group(4) else 0.0, "balance": parse_amount(m.group(5)), "ref": ""}
            res.rows.append(cur)
        elif cur is not None and not STOP_RE.match(line) and not re.match(rf"^\s*{DATE_TOKEN}", line):
            cur["narration"] = (cur["narration"] + " " + line.strip()).strip()
        else:
            cur = None
    for r in res.rows:
        r["ref"] = extract_ref(r["narration"])
    return res.finalize()


def parse(path: Path) -> ParseResult:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        table_rows = _rows_from_tables(pdf)
    if table_rows:
        res = parse_rows(table_rows, "pdf-table")
        if res.rows:
            res.raw_text = text[:5000]
            return res
    if text.strip():
        res = _rows_from_text(text)
        if res.rows:
            return res
        res = _rows_from_text_inr(text)
        if res.rows:
            return res
        res.warnings.append("PDF has text but no recognisable transaction lines; try CSV export.")
        return res
    # scanned PDF → OCR each page
    from . import image_parser
    return image_parser.parse_pdf_pages(path)
