"""Passbook photos: real-world layouts, OCR slips, and a missing OCR engine must never 500."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("VASOOL_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402
from vasool.parsers import image_parser, parse_file  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
client = TestClient(app)


def _render(lines: list[str], path: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (1400, 60 + 48 * len(lines)), "white")
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
    except Exception:
        f = ImageFont.load_default()
    y = 30
    for l in lines:
        d.text((30, y), l, fill="black", font=f)
        y += 48
    im.save(path)
    return path


CANARA_PASSBOOK = [
    "Date        Particulars                          Deposits   Withdrawals    Balance",
    "11-02-2026  JNS-PMSBY                                          20.00       709.00",
    "11-02-2026  UPI/DR/640821377048/RAJALAKSHN/                     1.00       708.00",
    "            KSH/CNRB/A58-1@OKSBI/UPI//AXIDE8A",
    "11-02-2026  UPI/CR/640855120011/RAJALAKSHN/      50.00                     758.00",
    "            KSH/CNRB/A58-1@OKSBI/UPI",
    "11-02-2026  APY CONTRI                                        210.00       548.00",
    "13-02-2026  UPI/CR/641233001/MRS DEEPTI/        100.00                     648.00",
    "            YBL/deepti@ybl/UPI",
    "13-02-2026  UPI/DR/641298877/MS KAVITHA/                       87.00       561.00",
    "28-02-2026  SMS ALERT CHRG                                     17.70       543.30",
    "01-03-2026  NEFT CR PENSION TN TREASURY        6500.00                    7043.30",
]


@pytest.mark.skipif(not (image_parser.shutil.which("tesseract")), reason="tesseract not installed")
def test_canara_passbook_layout(tmp_path):
    r = parse_file(_render(CANARA_PASSBOOK, tmp_path / "pb.png"))
    got = [(x["date"].isoformat(), x["debit"], x["credit"], x["balance"]) for x in r.rows]
    assert got == [
        ("2026-02-11", 20.0, 0.0, 709.0), ("2026-02-11", 1.0, 0.0, 708.0), ("2026-02-11", 0.0, 50.0, 758.0),
        ("2026-02-11", 210.0, 0.0, 548.0), ("2026-02-13", 0.0, 100.0, 648.0), ("2026-02-13", 87.0, 0.0, 561.0),
        ("2026-02-28", 17.7, 0.0, 543.3), ("2026-03-01", 0.0, 6500.0, 7043.3),
    ]
    assert "KSH/CNRB" in r.rows[1]["narration"]          # continuation line joined to its transaction
    assert r.rows[1]["ref"] == "640821377048"


def test_repair_ocr_amount_slips():
    assert image_parser._repair("APY CONTRI 210.00 548 .00") == "APY CONTRI 210.00 548.00"
    assert image_parser._repair("SMS ALERT CHRG 17,70 543.30") == "SMS ALERT CHRG 17.70 543.30"
    assert image_parser._repair("NEFT CR 6,500.00 7,O43.30") == "NEFT CR 6,500.00 7,043.30"


def test_missing_ocr_engine_is_a_friendly_422(monkeypatch):
    monkeypatch.setattr(image_parser.shutil, "which", lambda *_: None)
    monkeypatch.setattr(image_parser, "WINDOWS_TESSERACT", [])
    monkeypatch.delenv("VASOOL_TESSERACT", raising=False)
    with open(SAMPLES / "passbook_amma_page.png", "rb") as fh:
        r = client.post("/api/scan", files={"file": ("photo.png", fh, "image/png")}, data={"profile": "{}"})
    assert r.status_code == 422
    assert "Tesseract" in r.json()["detail"]["message"] and "PDF/CSV" in r.json()["detail"]["message"]


def test_parser_crash_is_a_friendly_422(monkeypatch):
    monkeypatch.setattr(image_parser, "_ocr_image", lambda img: (_ for _ in ()).throw(RuntimeError("boom")))
    with open(SAMPLES / "passbook_amma_page.png", "rb") as fh:
        r = client.post("/api/scan", files={"file": ("photo.png", fh, "image/png")}, data={"profile": "{}"})
    assert r.status_code == 422 and "couldn't read" in r.json()["detail"]["message"]
