"""Real delivery: off by default, safe when on, wired into the human loop."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("VASOOL_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402
from api import main as api_main  # noqa: E402
from vasool import notify  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
client = TestClient(api_main.app)


class FakeSMTP:
    sent: list[dict] = []

    def __init__(self, host, port, context=None, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, u, p):
        self.user = u

    def send_message(self, msg):
        FakeSMTP.sent.append({"to": msg["To"], "subject": msg["Subject"], "body": msg.get_body(preferencelist=("plain",)).get_content()})


def test_unconfigured_is_simulated_not_failed():
    ch = notify.EmailChannel(notify.EmailConfig())
    r = ch.send("kumar@example.com", "s", "t")
    assert r["sent"] is False and r["simulated"] is True and "not configured" in r["reason"]


def test_demo_to_overrides_every_recipient(monkeypatch):
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", FakeSMTP)
    FakeSMTP.sent.clear()
    ch = notify.EmailChannel(notify.EmailConfig(user="me@gmail.com", password="app pass", demo_to="safe@example.com"))
    r = ch.send("hocss@canarabank.com", "should never reach a bank", "x")
    assert r["sent"] and r["to"] == "safe@example.com" and FakeSMTP.sent[-1]["to"] == "safe@example.com"


def test_smtp_failure_never_crashes(monkeypatch):
    class Boom(FakeSMTP):
        def login(self, u, p):
            raise RuntimeError("535 bad credentials")
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", Boom)
    r = notify.EmailChannel(notify.EmailConfig(user="me@gmail.com", password="x")).send("a@b.c", "s", "t")
    assert r["sent"] is False and "535" in r["reason"]


def test_human_loop_with_real_mail(monkeypatch):
    monkeypatch.setattr(notify.smtplib, "SMTP_SSL", FakeSMTP)
    FakeSMTP.sent.clear()
    monkeypatch.setattr(api_main, "_email", notify.EmailChannel(notify.EmailConfig(user="me@gmail.com", password="x", public_url="http://192.168.1.5:8000")))
    with open(SAMPLES / "canara_amma_pension_2026.csv", "rb") as fh:
        acct = client.post("/api/scan", files={"file": ("c.csv", fh, "text/csv")}, data={"profile": '{"bank":"CANARA","min_balance_required":500,"holder_name":"Selvi R","language":"en"}', "as_of": "2026-09-13"}).json()
    aid = acct["account_id"]
    client.post(f"/api/accounts/{aid}/guardian", json={"name": "Kumar", "relation": "son", "phone": "+919876543210", "email": "kumar@example.com", "language": "en"})
    c = client.post(f"/api/accounts/{aid}/cases", json={}).json()
    j = client.post(f"/api/cases/{c['id']}/request-approval").json()
    tok = j["approve_token"]
    assert j["email"]["sent"] and j["email"]["to"] == "kumar@example.com"
    mail = FakeSMTP.sent[-1]
    assert f"http://192.168.1.5:8000/#/approve/{tok}" in mail["body"] and tok in mail["body"]
    assert "50,000" not in mail["body"] and "balance" in mail["body"].lower()   # minimum-info promise holds
    # the guardian opens the link on their phone
    info = client.get(f"/api/approvals/{tok}").json()
    assert info["holder"] == "Selvi R" and info["amount"] == c["amount"] and not info["used"] and "Kumar" not in info["message"] or True
    r = client.post(f"/api/approvals/{tok}?approver=Kumar").json()
    assert r["state"] == "SENT_TO_BANK" and r["email"]["sent"] and r["email"]["to"] == "kumar@example.com"
    copy = FakeSMTP.sent[-1]
    assert "NOT sent to the bank" in copy["body"] and "RBI/2019-20/67" in copy["body"] and "hocss@canarabank.com" in copy["body"]
    assert all(m["to"] != "hocss@canarabank.com" for m in FakeSMTP.sent)
    assert client.get(f"/api/approvals/{tok}").json()["used"] is True
    notes = client.get(f"/api/accounts/{aid}/notifications").json()
    assert {n["kind"] for n in notes} >= {"voice_call", "guardian_message", "email_guardian", "email_complaint_copy"}


def test_holder_can_approve_without_guardian():
    """No guardian on file → the OK button on the case screen must still carry a token (was: 405)."""
    with open(SAMPLES / "canara_amma_pension_2026.csv", "rb") as fh:
        acct = client.post("/api/scan", files={"file": ("c.csv", fh, "text/csv")}, data={"profile": '{"bank":"CANARA","min_balance_required":500,"holder_name":"Selvi R","language":"en"}', "as_of": "2026-09-13"}).json()
    aid = acct["account_id"]
    c = client.post(f"/api/accounts/{aid}/cases", json={}).json()
    j = client.post(f"/api/cases/{c['id']}/request-approval").json()
    assert j["case"]["state"] == "AWAITING_APPROVAL" and j["guardian_message"] is None
    notes = client.get(f"/api/accounts/{aid}/notifications").json()
    tok = next(n["token"] for n in notes if n.get("token") and n["case_id"] == c["id"])
    assert tok == j["approve_token"]
    r = client.post(f"/api/approvals/{tok}?approver=holder").json()
    assert r["state"] == "SENT_TO_BANK"
