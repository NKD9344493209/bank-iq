"""Login, per-user isolation, encryption at rest."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

os.environ.setdefault("VASOOL_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402
from api import main as api_main  # noqa: E402
from vasool import crypto  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
client = TestClient(api_main.app)
PROFILE = '{"bank":"CANARA","min_balance_required":500,"holder_name":"Selvi R","language":"en"}'


def _scan(c):
    with open(SAMPLES / "canara_amma_pension_2026.csv", "rb") as fh:
        r = c.post("/api/scan", files={"file": ("c.csv", fh, "text/csv")}, data={"profile": PROFILE, "as_of": "2026-09-13"})
    assert r.status_code == 200, r.text
    return r.json()


def test_login_required_for_account_apis_but_not_public_ones():
    anon = TestClient(api_main.app)
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/api/rules").status_code == 200
    assert anon.get("/api/accounts").status_code == 401
    with open(SAMPLES / "canara_amma_pension_2026.csv", "rb") as fh:
        assert anon.post("/api/scan", files={"file": ("c.csv", fh, "text/csv")}, data={"profile": PROFILE}).status_code == 401


def test_signup_login_logout_and_password_rules():
    c = TestClient(api_main.app)
    assert c.post("/api/auth/signup", json={"login": "+919000011111", "name": "Amma", "password": "short"}).status_code == 422
    r = c.post("/api/auth/signup", json={"login": "+919000011111", "name": "Amma", "password": "pension2026"})
    assert r.status_code == 200 and "vr_session" in r.cookies and r.json()["user"]["login"] == "+919000011111"
    assert c.post("/api/auth/signup", json={"login": "+919000011111", "name": "Again", "password": "pension2026"}).status_code == 409
    assert c.get("/api/auth/me").json()["user"]["name"] == "Amma"
    c.post("/api/auth/logout")
    assert c.get("/api/accounts").status_code == 401
    assert c.post("/api/auth/login", json={"login": "+919000011111", "password": "wrong"}).status_code == 401
    assert c.post("/api/auth/login", json={"login": "+919000011111", "password": "pension2026"}).status_code == 200
    assert c.get("/api/accounts").status_code == 200


def test_users_cannot_see_each_others_accounts():
    a = TestClient(api_main.app); a.post("/api/auth/signup", json={"login": "a@example.com", "name": "A", "password": "passwordA"})
    b = TestClient(api_main.app); b.post("/api/auth/signup", json={"login": "b@example.com", "name": "B", "password": "passwordB"})
    d = _scan(a)
    aid = d["account_id"]
    assert any(x["id"] == aid for x in a.get("/api/accounts").json())
    assert not any(x["id"] == aid for x in b.get("/api/accounts").json())
    assert b.get(f"/api/accounts/{aid}").status_code == 404          # not 403: existence is not confirmed
    assert b.get(f"/api/accounts/{aid}/twin").status_code == 404
    case = a.post(f"/api/accounts/{aid}/cases", json={}).json()
    assert b.get(f"/api/cases/{case['id']}").status_code == 404
    # the guardian's approval link still works without any login — the token is the credential
    j = a.post(f"/api/cases/{case['id']}/request-approval").json()
    anon = TestClient(api_main.app)
    assert anon.get(f"/api/approvals/{j['approve_token']}").status_code == 200


def test_everything_in_sqlite_is_ciphertext():
    c = TestClient(api_main.app); c.post("/api/auth/signup", json={"login": "enc@example.com", "name": "Enc Tester", "password": "encryptme"})
    d = _scan(c)
    aid = d["account_id"]
    c.post(f"/api/accounts/{aid}/guardian", json={"name": "Kumar", "relation": "son", "phone": "+919876543210"})
    db = sqlite3.connect(os.environ["VASOOL_DB"])
    row = db.execute("SELECT profile, transactions, answers FROM accounts WHERE id=?", (aid,)).fetchone()
    assert all(crypto.is_sealed(x) for x in row)
    assert "Selvi" not in row[0] and "PENSION" not in row[1] and "UPI" not in row[1]
    assert all(crypto.is_sealed(r[0]) for r in db.execute("SELECT doc FROM findings WHERE account_id=?", (aid,)))
    assert crypto.is_sealed(db.execute("SELECT doc FROM guardians WHERE account_id=?", (aid,)).fetchone()[0])
    u = db.execute("SELECT salt, pw_hash, name FROM users WHERE login='enc@example.com'").fetchone()
    assert "encryptme" not in (u[0] + u[1]) and crypto.is_sealed(u[2])
    # and the app still reads it back
    assert c.get(f"/api/accounts/{aid}").json()["profile"]["holder_name"] == "Selvi R"


def test_crypto_roundtrip_and_password_hash():
    s = crypto.seal({"a": 1, "ta": "வணக்கம்"})
    assert s.startswith("enc1:") and crypto.open_(s) == {"a": 1, "ta": "வணக்கம்"}
    assert crypto.open_('{"legacy": true}') == {"legacy": True}       # pre-encryption rows still load
    salt, h = crypto.hash_password("pension2026")
    assert crypto.verify_password("pension2026", salt, h) and not crypto.verify_password("pension2027", salt, h)
    salt2, h2 = crypto.hash_password("pension2026")
    assert h2 != h                                                     # fresh salt every time


def test_deadline_clock_promotes_small_claims_and_alerts_once(monkeypatch):
    from vasool import alerts
    sent = []
    monkeypatch.setattr(api_main, "_telegram", type("T", (), {"cfg": alerts.TelegramConfig(), "send": lambda self, text, kind="alert_telegram": sent.append(text) or {"kind": kind, "to": "x", "text": text, "sent": True, "simulated": False}})())
    c = TestClient(api_main.app); c.post("/api/auth/signup", json={"login": "clock@example.com", "name": "Clock", "password": "tick-tock"})
    d = _scan(c)
    aid = d["account_id"]
    small = next(f for f in d["findings"] if f["rule_id"] == "RBI-ATM-2025-FREE")
    assert small["priority"] == "NOT_WORTH_IT" and small["alert"] is False and small["act_by"] == "2027-07-09"
    upi = next(f for f in d["findings"] if f["rule_id"] == "RBI-TAT-2019-UPI")
    assert upi["alert"] is True and "open failure" in upi["alert_reason"]          # unreversed → always urgent
    assert len(d["alerts"]) == 1 and d["alerts"][0]["finding_id"] == upi["id"] and len(sent) == 1
    # move time to 20 days before the ₹27 limitation date → it turns red and is promoted, whatever the amount
    d2 = c.post(f"/api/accounts/{aid}/as-of", json={"as_of": "2027-06-19"}).json()
    small2 = next(f for f in d2["findings"] if f["rule_id"] == "RBI-ATM-2025-FREE")
    assert small2["alert"] is True and small2["priority"] == "RECOVER_NOW" and small2["days_left"] == 20
    assert any(a["finding_id"] == small2["id"] for a in d2["alerts"]) and "₹27.14" in "".join(sent)
    # a second recompute does not re-send the same alert
    d3 = c.post(f"/api/accounts/{aid}/as-of", json={"as_of": "2027-06-20"}).json()
    assert not any(a["finding_id"] == small2["id"] for a in d3["alerts"])
    # nothing sensitive in the message
    joined = "".join(sent)
    assert "50,000" not in joined and "PSG COLLEGE" not in joined and "16,255" not in joined   # no other lines, no balances


def test_telegram_unconfigured_is_simulated():
    from vasool import alerts
    r = alerts.TelegramChannel(alerts.TelegramConfig()).send("hi")
    assert r["sent"] is False and r["simulated"] and "not configured" in r["reason"]


def test_red_alert_message_is_actionable_and_minimal():
    """The Telegram text must let a customer act without the app: statement line, rule + circular,
    arithmetic, act-by date, the three steps — and never the balance."""
    from datetime import date
    from vasool import alerts, rulebook, scan
    from vasool.models import AccountProfile
    prof = AccountProfile(bank="CANARA", min_balance_required=500, holder_name="Selvi R", language="en")
    res = scan.scan_file(str(SAMPLES / "canara_amma_pension_2026.csv"), prof, as_of=date(2027, 6, 19))
    rb = rulebook.load()
    small = next(f for f in res.findings if f.alert and f.amount < 100)
    txt = alerts.alert_text("Selvi R", "CANARA", small, "en", txns=res.transactions, rule=rb.get(small.rule_id), last4="4417", as_of=res.as_of)
    assert "₹27.14" in txt and small.rule_id in txt and rb.get(small.rule_id).source["circular"] in txt
    assert "ATM CASH WDL CHRG" in txt and "09 Jul 2027" in txt and "20 days left" in txt
    assert "cms.rbi.org.in" in txt and "not guaranteed" in txt and "Nothing has been sent to any bank" in txt
    bal = {f"₹{t.balance:,.2f}" for t in res.transactions if t.balance}   # no running balance may leak into the message
    assert not any(b in txt for b in bal) and len(txt) <= alerts.TELEGRAM_MAX
    # the test button sends the same shape, from a real finding
    r = client.post("/api/notify/test-alert").json()
    assert r["kind"] == "alert_test" and "WHAT THE RBI RULE SAYS" in r["text"] and r["finding_id"] and r["source"]
