"""Passbook photo / scanned page parser (OCR via Tesseract).

Passbooks are the input for the half of India that has no PDF. OCR is noisy,
so this parser is deliberately conservative: it only accepts lines where a
date and at least one amount are recognisable, and it reports a quality score
so the UI can ask for a retake instead of guessing.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from .common import ParseResult, parse_amount, parse_date, extract_ref

DATE_RE = r"(\d{2}[/.-]\d{2}[/.-]\d{2,4})"
AMT_RE = r"(\d{1,3}(?:,\d{2,3})*\.\d{2}|\d+\.\d{2})"


WINDOWS_TESSERACT = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
]


class OcrUnavailable(ValueError):
    """Raised when the OCR engine is missing — the API turns this into a friendly 422, not a 500."""


def _find_tesseract() -> None:
    """Point pytesseract at tesseract.exe on Windows without the user editing PATH."""
    import pytesseract
    env = os.getenv("VASOOL_TESSERACT")
    if env and Path(env).exists():
        pytesseract.pytesseract.tesseract_cmd = env
        return
    if shutil.which("tesseract"):
        return
    for cand in WINDOWS_TESSERACT:
        if cand and Path(cand).exists():
            pytesseract.pytesseract.tesseract_cmd = cand
            return
    raise OcrUnavailable(
        "Photo reading needs the Tesseract OCR engine, which is not installed on this computer. "
        "Windows: install it from https://github.com/UB-Mannheim/tesseract/wiki (default folder), then restart the server. "
        "Or upload the statement as PDF/CSV instead.")


def _ocr_image(img) -> str:
    import pytesseract
    from PIL import ImageOps

    _find_tesseract()
    try:
        img = ImageOps.exif_transpose(img)   # phone photos carry rotation in EXIF
    except Exception:
        pass
    g = ImageOps.grayscale(img)
    # upscale small photos; passbook print is tiny
    if g.width < 1600:
        ratio = 1600 / g.width
        g = g.resize((int(g.width * ratio), int(g.height * ratio)))
    g = ImageOps.autocontrast(g)
    try:
        return pytesseract.image_to_string(g, config="--psm 6")
    except pytesseract.TesseractNotFoundError as e:
        raise OcrUnavailable("Tesseract OCR engine not found. Install it from https://github.com/UB-Mannheim/tesseract/wiki and restart, or upload PDF/CSV.") from e


DEBIT_HINT = re.compile(r"(WDL|WITHDRAW|CHRG|CHG|CHARGE|/DR/|\bDR\b|DEBIT|FEE|PENAL|PMSBY|PMJJBY|APY|EMI|POS|ATM)", re.I)
CREDIT_HINT = re.compile(r"(/CR/|\bCR\b|CREDIT|DEPOSIT|INT\b|INTEREST|SALARY|PENSION|NEFT CR|IMPS CR|BY TRANSFER)", re.I)


def _direction(amt: float, balance, prev, narration: str) -> tuple[float, float]:
    """Decide debit/credit for a single amount: balance movement first, narration second."""
    if prev is not None and balance is not None:
        if abs(prev - amt - balance) < 0.011:
            return amt, 0.0
        if abs(prev + amt - balance) < 0.011:
            return 0.0, amt
        if balance < prev:
            return amt, 0.0
        if balance > prev:
            return 0.0, amt
    if CREDIT_HINT.search(narration) and not DEBIT_HINT.search(narration):
        return 0.0, amt
    return amt, 0.0


def _repair(line: str) -> str:
    """Undo the commonest OCR slips around amounts: '548 .00' → '548.00', '6,500 .00', '1,2O0.00' (O for 0), '17,70' → '17.70'."""
    line = re.sub(r"(\d)\s+\.(\d{2})\b", r"\1.\2", line)
    line = re.sub(r"(\d)\.\s+(\d{2})\b", r"\1.\2", line)
    line = re.sub(r"(?<=\d)[Oo](?=[\d.,])|(?<=[\d.,])[Oo](?=\d)", "0", line)
    line = re.sub(r"(?<=\d),(\d{2})\b(?!,)", r".\1", line) if not re.search(r"\d,\d{3}", line) else line
    return line


def _rows_from_ocr_text(text: str, res: ParseResult) -> ParseResult:
    total_lines = 0
    for raw in text.splitlines():
        line = _repair(raw.strip())
        if not line:
            continue
        total_lines += 1
        dm = re.search(DATE_RE, line)
        if not dm:
            # a line with no date and no amount is usually the tail of a long UPI narration
            # ("UPI/DR/6408.../RAJALAKSHN/" on one line, "KSH/CNRB/..." on the next): keep it with the previous row
            if res.rows and not re.search(AMT_RE, line) and len(line) > 3 and re.search(r"[A-Za-z]", line):
                res.rows[-1]["narration"] = (res.rows[-1]["narration"] + " " + line).strip()[:160]
                res.rows[-1]["ref"] = res.rows[-1]["ref"] or extract_ref(line)
            continue
        d = parse_date(dm.group(1))
        if not d:
            continue
        rest = line[dm.end():]
        # a second date (value date) right after the first is common — drop it
        rest = re.sub(r"^\s*[|:-]?\s*" + DATE_RE, "", rest)
        amts = re.findall(AMT_RE, rest)
        if not amts:
            continue
        narration = re.sub(AMT_RE, "", rest).strip(" |-:")
        nums = [parse_amount(a) for a in amts]
        prev = res.rows[-1]["balance"] if res.rows and res.rows[-1]["balance"] is not None else None
        debit = credit = 0.0
        balance = None
        if len(nums) >= 3:
            a, b, balance = nums[-3], nums[-2], nums[-1]
            # columns may be (debit, credit, balance) or (deposits, withdrawals, balance): let the balance decide
            if prev is not None and abs(prev - a - balance) < 0.011:
                debit = a
            elif prev is not None and abs(prev + a - balance) < 0.011:
                credit = a
            elif prev is not None and abs(prev - b - balance) < 0.011:
                debit = b
            elif prev is not None and abs(prev + b - balance) < 0.011:
                credit = b
            elif a and not b:
                debit, credit = _direction(a, balance, prev, narration)
            elif b and not a:
                debit, credit = _direction(b, balance, prev, narration)
            else:
                debit, credit = a, b
        elif len(nums) == 2:
            amt, balance = nums
            debit, credit = _direction(amt, balance, prev, narration)
        else:
            amt = nums[0]
            debit, credit = _direction(amt, None, None, narration)
        if not (debit or credit):
            continue
        res.rows.append({"date": d, "narration": narration, "debit": debit, "credit": credit, "balance": balance, "ref": extract_ref(narration)})
    accepted = len(res.rows)
    quality = accepted / max(total_lines, 1)
    # The real quality signal is the balance chain: if every row's balance equals the previous balance
    # plus credit minus debit, OCR read the numbers right — whatever the ratio of text lines says.
    chain = [r for r in res.rows if r["balance"] is not None]
    links = sum(1 for a, b in zip(chain, chain[1:]) if abs(a["balance"] + b["credit"] - b["debit"] - b["balance"]) < 0.011)
    chain_ok = len(chain) >= 2 and links == len(chain) - 1
    if chain_ok:
        res.warnings.append(f"OCR: {accepted} transactions read from {total_lines} text lines · balance chain verified ✓ ({links}/{links} steps reconcile).")
    else:
        res.warnings.append(f"OCR: {accepted} transactions read from {total_lines} text lines · balance chain {links}/{max(len(chain) - 1, 0)} steps reconcile.")
        if accepted < 5 or (len(chain) > 2 and links < (len(chain) - 1) * 0.7):
            res.warnings.append("Low OCR confidence — retake the photo (flat page, good light, no shadow) or upload the PDF/CSV statement.")
    return res.finalize()


def parse(path: Path) -> ParseResult:
    from PIL import Image

    res = ParseResult(source_kind="image")
    with Image.open(path) as img:
        text = _ocr_image(img)
    res.raw_text = text[:5000]
    return _rows_from_ocr_text(text, res)


def parse_pdf_pages(path: Path) -> ParseResult:
    import pdfplumber

    res = ParseResult(source_kind="pdf-ocr")
    chunks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pil = page.to_image(resolution=200).original
            chunks.append(_ocr_image(pil))
    text = "\n".join(chunks)
    res.raw_text = text[:5000]
    return _rows_from_ocr_text(text, res)
