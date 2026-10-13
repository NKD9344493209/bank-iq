"""Render Amma's statement as a printed passbook page (PNG) to exercise the OCR path.
Synthetic, clearly labelled. Output: data/samples/passbook_amma_page.png"""
from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "samples" / "canara_amma_pension_2026.csv"
OUT = ROOT / "data" / "samples" / "passbook_amma_page.png"


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


rows = []
with open(SRC, encoding="utf-8") as fh:
    for r in csv.reader(fh):
        if len(r) == 8 and r[0][:2].isdigit():
            rows.append(r)

W, H = 1400, 120 + 34 * (len(rows) + 3)
img = Image.new("L", (W, H), 245)
d = ImageDraw.Draw(img)
f = font(22)
fs = font(18)
d.text((40, 20), "CANARA BANK   SB PENSION   A/C XXXXXXXX4417   SELVI R   (SYNTHETIC SAMPLE)", font=fs, fill=40)
y = 70
d.text((40, y), f"{'DATE':<12}{'PARTICULARS':<36}{'WITHDRAWAL':>12}{'DEPOSIT':>12}{'BALANCE':>14}", font=f, fill=20)
y += 34
d.line((40, y - 6, W - 40, y - 6), fill=120, width=1)
for r in rows:
    date, _, desc, ref, _, dr, cr, bal = r
    line = f"{date:<12}{desc[:34]:<36}{dr:>12}{cr:>12}{bal:>14}"
    d.text((40, y), line, font=f, fill=25)
    y += 34
# light print noise: faint horizontal guide lines like a real passbook
for gy in range(100, H, 34):
    d.line((40, gy + 26, W - 40, gy + 26), fill=225, width=1)
img.save(OUT)
print("wrote", OUT, img.size)
