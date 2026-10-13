"""v0.6.0 — explainability: the digital twin as data, "why wasn't this flagged?", scope honesty, upload hygiene."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("VASOOL_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402
from api import main as api_main  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
client = TestClient(api_main.app)
PROFILE = '{"bank":"CANARA","min_balance_required":500,"holder_name":"Selvi R","language":"en"}'


def _scan(name="canara_amma_pension_2026.csv", profile=PROFILE):
    with open(SAMPLES / name, "rb") as fh:
        r = client.post("/api/scan", files={"file": (name, fh, "text/csv")}, data={"profile": profile, "as_of": "2026-09-13"})
    assert r.status_code == 200, r.text
    return r.json()


def test_twin_summary_counts_are_derived_from_real_lines():
    d = _scan()
    tw = client.get(f"/api/accounts/{d['account_id']}/twin").json()
    c = tw["counts"]
    assert c["transactions"] == len(d["transactions"]) == 23
    assert c["debits"] + c["credits"] == c["transactions"]
    assert c["charges"] >= 3 and c["reversals"] >= 1 and c["pairs"] >= 1 and c["unreversed_failed"] == 1
    assert c["rules_evaluated"] == len(tw["rules_active"]) >= 19
    assert c["findings"] == len(d["findings"]) and c["flagged_lines"] + c["unflagged_lines"] == c["transactions"]
    assert len(tw["balance_path"]) == 23 and tw["period"] == {"from": "2026-06-02", "to": "2026-08-31"}
    atm_pair = next(p for p in tw["pairs"] if p["debit"]["channel"] == "ATM")
    assert atm_pair["days"] == 17 and atm_pair["tat_days"] == 5 and atm_pair["finding_ids"]
    assert tw["unreversed"][0]["txn"]["channel"] == "UPI" and tw["unreversed"][0]["finding_ids"]


def test_why_not_flagged_on_the_college_fee_and_on_a_flagged_line():
    d = _scan()
    aid = d["account_id"]
    big = max(d["transactions"], key=lambda t: t["debit"])
    assert big["debit"] >= 50000
    w = client.get(f"/api/accounts/{aid}/transactions/{big['id']}/why-not").json()
    assert w["flagged"] is False and w["finding_ids"] == []
    texts = " ".join(c["text_en"] for c in w["checks"])
    assert "successful payment" in texts and "no anomaly detection" in texts.lower()
    assert all(c["ok"] for c in w["checks"]) and w["result_en"].startswith("Not flagged")
    # a pension credit
    cr = next(t for t in d["transactions"] if t["credit"] > 0 and t["kind"] == "CREDIT")
    w2 = client.get(f"/api/accounts/{aid}/transactions/{cr['id']}/why-not").json()
    assert w2["flagged"] is False and any("no rule applies" in c["text_en"] for c in w2["checks"])
    # the failed UPI debit IS flagged and the checklist says so
    upi = next(f for f in d["findings"] if f["rule_id"] == "RBI-TAT-2019-UPI")
    w3 = client.get(f"/api/accounts/{aid}/transactions/{upi['evidence'][0]}/why-not").json()
    assert w3["flagged"] is True and upi["id"] in w3["finding_ids"] and any(not c["ok"] for c in w3["checks"])
    assert client.get(f"/api/accounts/{aid}/transactions/nope/why-not").status_code == 404


def test_why_not_explains_a_legitimate_retry_without_claiming_it():
    d = _scan("sbi_arun_student_2025.tsv", '{"bank":"SBI","min_balance_required":0,"holder_name":"Arun","language":"en"}')
    aid = d["account_id"]
    zom = [t for t in d["transactions"] if "ZOMATO" in t["narration"].upper() and t["debit"] > 0]
    assert len(zom) >= 2
    w = client.get(f"/api/accounts/{aid}/transactions/{zom[0]['id']}/why-not").json()
    assert any("retry" in c["text_en"] for c in w["checks"])
    assert not any(f["label"] == "RECOVERABLE" and zom[0]["id"] in f["evidence"] for f in d["findings"])


def test_scope_is_honest():
    s = client.get("/api/scope").json()
    assert s["implemented"] == 19 and s["listed"] == 22 and s["mapped"] == 40
    assert "not complete RBI coverage" in s["statement"]
    assert sum(s["categories"].values()) == s["implemented"]


def test_validation_endpoint_never_fabricates():
    v = client.get("/api/validation").json()
    if v["available"]:
        assert v["total"] == v["passed"] + v["failed"] + v["skipped"] and v["groups"] and v["ran_at"]
    else:
        assert "scripts/validate.py" in v["hint"]


def test_upload_hygiene_extension_and_headers():
    r = client.post("/api/scan", files={"file": ("evil.exe", b"MZ....", "application/octet-stream")}, data={"profile": PROFILE})
    assert r.status_code == 415
    h = client.get("/api/health")
    assert h.headers["x-content-type-options"] == "nosniff" and h.headers["x-frame-options"] == "DENY" and h.headers["cache-control"] == "no-store"


def test_indian_bank_inr_column_pdf_layout_and_sms_chgs():
    """Real Indian Bank (IndOASIS) PDF layout: 'INR' before every amount, '-' for an empty column,
    narrations wrapped onto dateless lines, page headers in between. Synthetic text, same shape."""
    from vasool.parsers import pdf_parser
    from vasool.classify import classify
    from vasool.models import Kind, Transaction
    from datetime import date
    text = """ACCOUNT ACTIVITY
Date Transaction Details Debits Credits Balance
10 Sep 2026 utib0000553/Google India - INR 111.00 INR 1,028.58
Digital Services
/XXXXX30724/gpayrefund-
online@axisbank
/UPI/XXXXXXXXXXXX/UPI
11 Sep 2026 YESB0MCHUPI/DONNE INR 199.00 - INR 829.58
BIRYANI HOUSE /XXXXX
Page 1 of 5
Date Transaction Details Debits Credits Balance
12 Sep 2026 IOBA0001845/D NAVEEN INR 700.00 - INR 129.58
KUMAR/XXXXX/UPI
23 Sep 2026 SMS_CHGS_JUNE- INR 10.80 - INR 0.78
26_QTR
Ending Balance INR 0.78 Total INR 7,563.80 INR 6,647.00
"""
    r = pdf_parser._rows_from_text_inr(text)
    assert len(r.rows) == 4
    assert r.rows[0]["credit"] == 111.0 and r.rows[0]["debit"] == 0 and r.rows[0]["balance"] == 1028.58
    assert "Digital Services" in r.rows[0]["narration"] and "Page 1" not in r.rows[1]["narration"] and "Date Transaction" not in r.rows[1]["narration"]
    assert r.rows[2]["debit"] == 700.0 and "KUMAR" in r.rows[2]["narration"]
    assert r.rows[3]["debit"] == 10.8 and "Ending Balance" not in r.rows[3]["narration"]
    t = classify(Transaction(date=date(2026, 9, 23), narration=r.rows[3]["narration"], debit=10.8, balance=0.78))
    assert t.kind == Kind.CHARGE_SMS
    from vasool.parsers.common import detect_bank
    assert detect_bank("IFSC IDIB000S107 Branch PEELAMEDU") == "INDIAN BANK"
