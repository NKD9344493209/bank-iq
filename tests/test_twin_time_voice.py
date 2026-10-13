"""v0.5.0 — Twin View payloads, the as-of time slider, and the real Tamil call (Twilio)."""
from __future__ import annotations

import io
import json
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

os.environ.setdefault("VASOOL_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402
from api import main as api_main  # noqa: E402
from vasool import voice  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
client = TestClient(api_main.app)
PROFILE = '{"bank":"CANARA","min_balance_required":500,"holder_name":"Selvi R","language":"ta","holder_phone":"+91 90000 00000"}'


def _scan(as_of="2026-09-13"):
    with open(SAMPLES / "canara_amma_pension_2026.csv", "rb") as fh:
        r = client.post("/api/scan", files={"file": ("c.csv", fh, "text/csv")}, data={"profile": PROFILE, "as_of": as_of})
    assert r.status_code == 200, r.text
    return r.json()


# ---- 1. Twin View: every ₹/day and min-balance finding carries the twin ------------------
def test_tat_findings_carry_twin_payload():
    d = _scan()
    tats = [f for f in d["findings"] if f["twin"].get("kind") == "tat"]
    assert len(tats) == 2
    upi = next(f for f in tats if f["rule_id"] == "RBI-TAT-2019-UPI")
    w = upi["twin"]
    assert w["reversed"] is False and w["deadline"] == "2026-08-11" and w["per_day"] == 100.0
    assert w["days_late"] == 33 and w["expected_compensation"] == 3300.0 and w["actual_compensation"] == 0.0
    assert w["delta"] == w["principal_outstanding"] + w["expected_compensation"] == upi["amount"] == 3800.0
    atm = next(f for f in tats if f["rule_id"] == "RBI-TAT-2019-ATM")
    assert atm["twin"]["reversed"] is True and atm["twin"]["reversal_date"] == "2026-08-20" and atm["twin"]["days_late"] == 12


def test_minbal_twin_is_blind_without_prior_month_then_sees_the_path():
    d = _scan()
    mb = next(f for f in d["findings"] if f["twin"].get("kind") == "minbal")
    w = mb["twin"]
    assert w["month"] == "2026-05" and w["month_visible"] is False and w["path"] == [] and w["lowest"] is None
    with open(SAMPLES / "canara_amma_pension_2026_mar_may.csv", "rb") as fh:
        d2 = client.post(f"/api/accounts/{d['account_id']}/statements", files={"file": ("m.csv", fh, "text/csv")}).json()
    mb2 = next(f for f in d2["findings"] if f["twin"].get("kind") == "minbal")
    w2 = mb2["twin"]
    assert w2["month_visible"] is True and w2["lowest"] >= 500 and len(w2["path"]) >= 3
    assert all(len(p) == 2 and p[0].startswith("2026-05") for p in w2["path"])
    assert mb2["label"] == "RECOVERABLE"


# ---- 2. Time slider: every day the bank waits, the number grows ------------------------------
def test_as_of_slider_recomputes_per_day_claims():
    d = _scan("2026-09-13")
    aid = d["account_id"]
    assert d["as_of"] == "2026-09-13"
    base = d["summary"]["total_recoverable"]
    later = client.post(f"/api/accounts/{aid}/as-of", json={"as_of": "2026-10-13"}).json()
    assert later["as_of"] == "2026-10-13"
    assert later["summary"]["total_recoverable"] == base + 30 * 100      # the unreversed UPI grows ₹100/day
    upi = next(f for f in later["findings"] if f["rule_id"] == "RBI-TAT-2019-UPI")
    assert upi["twin"]["days_late"] == 63 and upi["amount"] == 500 + 63 * 100
    atm = next(f for f in later["findings"] if f["rule_id"] == "RBI-TAT-2019-ATM")
    assert atm["amount"] == 1200.0                                         # already reversed: frozen
    # persisted: a reload of the account still reports the moved date
    assert client.get(f"/api/accounts/{aid}").json()["as_of"] == "2026-10-13"
    earlier = client.post(f"/api/accounts/{aid}/as-of", json={"as_of": "2026-08-12"}).json()
    upi2 = next(f for f in earlier["findings"] if f["rule_id"] == "RBI-TAT-2019-UPI")
    assert upi2["twin"]["days_late"] == 1 and upi2["amount"] == 600.0


# ---- 3. Real call: off = simulated, on = one HTTPS POST to Twilio, demo phone overrides -------
class FakeResp:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_voice_unconfigured_is_simulated_not_failed():
    r = voice.TwilioChannel(voice.VoiceConfig()).call("+919876543210", "வணக்கம்")
    assert r["placed"] is False and r["simulated"] is True and "not configured" in r["reason"]


def test_voice_demo_phone_overrides_and_posts_tamil_twiml(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["body"] = dict(x.split("=", 1) for x in req.data.decode().split("&"))
        return FakeResp({"sid": "CA123", "status": "queued"})

    monkeypatch.setattr(voice.urllib.request, "urlopen", fake_urlopen)
    ch = voice.TwilioChannel(voice.VoiceConfig(sid="ACxx", token="tok", sender="+15550001111", demo_phone="+919000000000"))
    r = ch.call("+911234567890", "வணக்கம் அம்மா", "ta")
    assert r["placed"] and r["call_sid"] == "CA123" and r["to"] == "+919000000000" and r["requested_to"] == "+911234567890"
    assert seen["url"].endswith("/Accounts/ACxx/Calls.json") and seen["auth"].startswith("Basic ")
    body = {k: urllib.request.unquote(v.replace("+", " ")) for k, v in seen["body"].items()}
    assert body["To"] == "+919000000000" and body["From"] == "+15550001111"
    assert 'language="ta-IN"' in body["Twiml"] and "வணக்கம் அம்மா" in body["Twiml"]


def test_voice_bad_number_and_twilio_error_never_crash(monkeypatch):
    ch = voice.TwilioChannel(voice.VoiceConfig(sid="ACxx", token="tok", sender="+15550001111"))
    r = ch.call("9876543210", "x")
    assert r["placed"] is False and "+91" in r["reason"]

    def boom(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b'{"message":"Authenticate"}'))

    monkeypatch.setattr(voice.urllib.request, "urlopen", boom)
    r = ch.call("+919876543210", "x")
    assert r["placed"] is False and r["simulated"] and "Twilio 401" in r["reason"]


def test_request_approval_places_the_holder_call_and_logs_it(monkeypatch):
    calls = []

    class Fake(voice.TwilioChannel):
        def call(self, to, text, lang="ta", kind="voice_real"):
            calls.append((to, text, lang, kind))
            return {"kind": kind, "requested_to": to, "to": to, "lang": lang, "text": text, "placed": True, "simulated": False, "call_sid": "CA9"}

    monkeypatch.setattr(api_main, "_voice", Fake(voice.VoiceConfig(sid="a", token="b", sender="+1")))
    d = _scan()
    aid = d["account_id"]
    c = client.post(f"/api/accounts/{aid}/cases", json={}).json()
    j = client.post(f"/api/cases/{c['id']}/request-approval").json()
    assert j["call"]["placed"] and j["call"]["call_sid"] == "CA9"
    assert calls and calls[0][0] == "+919000000000" and calls[0][2] == "ta" and "Bank IQ" in calls[0][1]
    notes = client.get(f"/api/accounts/{aid}/notifications").json()
    assert any(n["kind"] == "voice_real" and n.get("call_sid") == "CA9" and n["case_id"] == c["id"] for n in notes)


def test_test_call_endpoint_and_health_status(monkeypatch):
    j = client.get("/api/health").json()
    assert "voice" in j["notify"] and "demo_phone" in j["notify"]
    r = client.post("/api/notify/test-call", json={"to": "+919876543210", "lang": "ta"}).json()
    assert r["kind"] == "voice_test" and r["simulated"] is True


def test_trial_account_falls_back_to_hosted_twiml_url(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=None):
        body = {k: urllib.request.unquote(v.replace("+", " ")) for k, v in (x.split("=", 1) for x in req.data.decode().split("&"))}
        seen.append(body)
        if "Twiml" in body:
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {},
                                         io.BytesIO(b'{"message":"Invalid or disallowed parameters provided - trial accounts have limited parameter access"}'))
        return FakeResp({"sid": "CA77", "status": "queued"})

    monkeypatch.setattr(voice.urllib.request, "urlopen", fake_urlopen)
    ch = voice.TwilioChannel(voice.VoiceConfig(sid="ACxx", token="tok", sender="+15550001111"))
    r = ch.call("+919876543210", "வணக்கம்", "ta")
    assert r["placed"] and r["via"] == "url" and r["call_sid"] == "CA77"
    assert len(seen) == 2 and seen[1]["Url"].startswith(voice.ECHO + "?Twiml=")
    inner = urllib.parse.parse_qs(urllib.parse.urlparse(seen[1]["Url"]).query)["Twiml"][0]
    assert 'language="ta-IN"' in inner and "வணக்கம்" in inner


def test_custom_twiml_bin_is_used_directly(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=None):
        seen.append(dict(x.split("=", 1) for x in req.data.decode().split("&")))
        return FakeResp({"sid": "CA1", "status": "queued"})

    monkeypatch.setattr(voice.urllib.request, "urlopen", fake_urlopen)
    ch = voice.TwilioChannel(voice.VoiceConfig(sid="a", token="b", sender="+1", twiml_url="https://handler.twilio.com/twiml/EH9"))
    r = ch.call("+919876543210", "hello", "en")
    assert r["placed"] and len(seen) == 1 and "Twiml" not in seen[0]
    assert urllib.request.unquote(seen[0]["Url"]).startswith("https://handler.twilio.com/twiml/EH9?text=hello&voice=Google.en-IN")
