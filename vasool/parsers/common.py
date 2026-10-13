from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

BANK_PATTERNS = [
    ("SBI", r"\b(SBI|STATE BANK OF INDIA|SBIN)\b"),
    ("HDFC", r"\bHDFC\b"),
    ("ICICI", r"\bICICI\b"),
    ("AXIS", r"\bAXIS\b"),
    ("CANARA", r"\bCANARA\b"),
    ("PNB", r"\b(PNB|PUNJAB NATIONAL)\b"),
    ("BOB", r"\b(BANK OF BARODA|BOB)\b"),
    ("UNION", r"\bUNION BANK\b"),
    ("KOTAK", r"\bKOTAK\b"),
    ("INDIAN BANK", r"\bINDIAN BANK\b|\bIDIB0|INDOASIS"),
    ("IOB", r"\b(IOB|INDIAN OVERSEAS)\b"),
    ("BOI", r"\bBANK OF INDIA\b"),
    ("TMB", r"\b(TMB|TAMILNAD MERCANTILE)\b"),
    ("CUB", r"\b(CUB|CITY UNION)\b"),
    ("KVB", r"\b(KVB|KARUR VYSYA)\b"),
    ("FEDERAL", r"\bFEDERAL BANK\b"),
    ("IDBI", r"\bIDBI\b"),
    ("YES", r"\bYES BANK\b"),
    ("INDUSIND", r"\bINDUSIND\b"),
]


def detect_bank(text: str) -> str:
    up = text.upper()
    counts = []
    for name, pat in BANK_PATTERNS:
        n = len(re.findall(pat, up))
        if n:
            counts.append((n, name))
    if not counts:
        return ""
    counts.sort(reverse=True)
    return counts[0][1]


@dataclass
class ParseResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    bank: str = ""              # bank used for the scan (user's choice wins over detection)
    detected_bank: str = ""     # what the file itself says
    account_last4: str = ""
    holder_name: str = ""
    period_from: Optional[date] = None
    period_to: Optional[date] = None
    source_kind: str = ""       # csv / pdf / image
    raw_text: str = ""
    warnings: list[str] = field(default_factory=list)

    def finalize(self) -> "ParseResult":
        self.rows = [r for r in self.rows if r.get("date")]
        self.rows.sort(key=lambda r: r["date"])
        if self.rows:
            self.period_from = self.rows[0]["date"]
            self.period_to = self.rows[-1]["date"]
        return self


DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y", "%d %B %Y",
    "%d-%b-%y", "%d %b %y", "%d.%m.%Y", "%d.%m.%y", "%m/%d/%Y", "%b %d, %Y",
]


def parse_date(s: str) -> Optional[date]:
    s = (s or "").strip().strip(",")
    if not s:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # last resort: dateutil
    try:
        from dateutil import parser as dp
        return dp.parse(s, dayfirst=True).date()
    except Exception:
        return None


_AMT = re.compile(r"^[\s₹Rs\.INR]*(-?)\(?\s*([\d,]+(?:\.\d{1,2})?)\s*\)?\s*(Cr|Dr|CR|DR)?\s*$")


def parse_amount(s: Any) -> float:
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if not s or s in {"-", "—", "–", "NA", "nil"}:
        return 0.0
    m = _AMT.match(s)
    if not m:
        digits = re.sub(r"[^\d.]", "", s)
        return float(digits) if digits else 0.0
    neg, num, _ = m.groups()
    val = float(num.replace(",", ""))
    return -val if neg else val


REF_RE = re.compile(r"\b(\d{12})\b|\bUTR[:\s]*([A-Z0-9]{10,22})\b|\bRRN[:\s]*(\d{12})\b|\bREF[:\s]*([A-Z0-9]{8,22})\b", re.I)


def extract_ref(narration: str) -> str:
    m = REF_RE.search(narration or "")
    if not m:
        return ""
    return next(g for g in m.groups() if g) or ""
