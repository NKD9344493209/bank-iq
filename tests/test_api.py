"""API tests: the whole human loop through HTTP, on a throwaway database."""
from __future__ import annotations

import os
from datetime import date
import tempfile
from pathlib import Path

import pytest

os.environ["VASOOL_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
client = TestClient(app)


@pytest.fixture(scope="module")
def account():
    with open(SAMPLES / "canara_amma_pension_2026.csv", "rb") as fh:
        r = client.post("/api/scan", files={"file": ("canara.csv", fh, "text/csv")},
                        data={"profile": '{"bank":"CANARA","min_balance_required":500,"holder_name":"Selvi R","language":"ta"}', "as_of": "2026-09-13"})
    assert r.status_code == 200, r.text
    return r.json()


def test_health():
    j = client.get("/api/health").json()
    assert j["ok"] and j["rules"] >= 20


def test_scan_returns_findings_and_summary(account):
    assert account["summary"]["total_recoverable"] > 0
    assert any(f["label"] == "RECOVERABLE" for f in account["findings"])
    assert account["profile"]["bank"] == "CANARA"


def test_answer_changes_label(account):
    aid = account["account_id"]
    f = next(f for f in account["findings"] if f["rule_id"] == "RBI-MINBAL-2014-NOTICE")
    r = client.post(f"/api/accounts/{aid}/answers", json={"answers": {f"notice_received:{f['evidence'][0]}": "no"}})
    assert r.status_code == 200
    g = next(x for x in r.json()["findings"] if x["rule_id"] == "RBI-MINBAL-2014-NOTICE")
    assert g["label"] == "RECOVERABLE"


def test_full_human_loop(account):
    aid = account["account_id"]
    # guardian with consent
    r = client.post(f"/api/accounts/{aid}/guardian", json={"name": "Kumar", "relation": "son", "phone": "+919876543210", "consent_transcript": "Amma's consent"})
    assert r.json()["consent_recorded_at"]
    # create case → prepared
    c = client.post(f"/api/accounts/{aid}/cases", json={}).json()
    assert c["state"] == "PREPARED" and c["amount"] > 0 and "RBI/2019-20/67" in client.get(f"/api/cases/{c['id']}/complaint.txt").text
    # approval request → holder called first, guardian messaged, nothing sent yet
    j = client.post(f"/api/cases/{c['id']}/request-approval").json()
    assert j["case"]["state"] == "AWAITING_APPROVAL"
    assert "Kumar" in j["holder_call"]["text"]
    assert "Balance" in j["guardian_message"] or "balance" in j["guardian_message"].lower()  # minimum-info note present
    notes = client.get(f"/api/accounts/{aid}/notifications").json()
    kinds = [n["kind"] for n in notes]
    assert kinds.index("guardian_message") < kinds.index("voice_call")  # newest first → call happened first
    # approve → sent, clock started
    s = client.post(f"/api/approvals/{j['approve_token']}?approver=Kumar").json()
    assert s["state"] == "SENT_TO_BANK" and s["bank_reply_due"] == "2026-10-13" and s["days_left"] == (date(2026, 10, 13) - date.today()).days
    # token is single-use
    assert client.post(f"/api/approvals/{j['approve_token']}").status_code == 404
    # illegal transition is refused
    assert client.post(f"/api/cases/{c['id']}/event", json={"state": "FOUND"}).status_code == 409
    # recovery marked
    s = client.post(f"/api/cases/{c['id']}/event", json={"state": "RECOVERED", "note": "credit seen"}).json()
    assert s["state"] == "RECOVERED"


def test_assistant_is_grounded(account):
    aid = account["account_id"]
    a = client.post(f"/api/accounts/{aid}/ask", json={"question": "why did the bank charge me 295?", "lang": "en"}).json()
    assert "RBI-MINBAL-2014-NOTICE" in a["grounded_on"]
    b = client.post(f"/api/accounts/{aid}/ask", json={"question": "why was 50000 taken?", "lang": "en"}).json()
    assert "ordinary payment" in b["text"] and not b["grounded_on"]


def test_user_claim_endpoints():
    r = client.post("/api/claims/card-closure", json={"request_date": "2026-08-03", "as_of": "2026-09-13"}).json()
    assert r["label"] == "RECOVERABLE" and r["amount"] > 0


def test_delete_is_total(account):
    aid = account["account_id"]
    assert client.delete(f"/api/accounts/{aid}").status_code == 200
    assert client.get(f"/api/accounts/{aid}").status_code == 404
    assert client.get(f"/api/accounts/{aid}/notifications").status_code == 404
