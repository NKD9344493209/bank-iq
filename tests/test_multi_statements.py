"""Multiple statements per account, history, and the printable complaint."""
from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("VASOOL_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402
from vasool import merge, scan  # noqa: E402
from vasool.models import AccountProfile  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"
MAIN, PREV = SAMPLES / "canara_amma_pension_2026.csv", SAMPLES / "canara_amma_pension_2026_mar_may.csv"
PROFILE = '{"bank":"CANARA","min_balance_required":500,"holder_name":"Selvi R","account_type":"PENSION","language":"en"}'
client = TestClient(app)


def _post(path, files, data=None):
    return client.post(path, files=[("files", (p.name, open(p, "rb"), "text/csv")) for p in files], data=data or {})


# ----- engine-level merge --------------------------------------------------- #
def test_merge_drops_overlap_and_keeps_existing_ids():
    prof = AccountProfile(bank="CANARA", min_balance_required=500)
    a = scan.scan_file(str(MAIN), prof, as_of=date(2026, 9, 13))
    b = scan.scan_file(str(PREV), prof, as_of=date(2026, 9, 13))
    ids_before = {t.id for t in a.transactions}
    m = merge.merge_transactions(a.transactions, b.transactions)
    assert m.duplicates == 2 and len(m.added) == 18 and len(m.transactions) == 41
    assert ids_before <= {t.id for t in m.transactions}
    assert [t.seq for t in m.transactions] == list(range(41))
    assert not m.warnings   # balances chain exactly


def test_merge_is_idempotent():
    prof = AccountProfile(bank="CANARA")
    a = scan.scan_file(str(MAIN), prof)
    m = merge.merge_transactions(a.transactions, scan.scan_file(str(MAIN), prof).transactions)
    assert m.duplicates == len(a.transactions) and not m.added


def test_coverage_finds_gaps():
    cov = merge.coverage([(date(2026, 1, 1), date(2026, 3, 31)), (date(2026, 6, 1), date(2026, 8, 31)), (date(2026, 4, 2), date(2026, 4, 30))])
    assert cov.to_dict()["gaps"] == [["2026-05-01", "2026-05-31"]]
    assert cov.to_dict()["from"] == "2026-01-01" and cov.to_dict()["to"] == "2026-08-31"


# ----- API ------------------------------------------------------------------ #
@pytest.fixture(scope="module")
def account():
    r = _post("/api/scan", [MAIN], {"profile": PROFILE, "as_of": "2026-09-13"})
    assert r.status_code == 200, r.text
    return r.json()


def test_second_statement_changes_the_verdict(account):
    """One statement: June min-balance penalty needs a question. With May's balances on file: CONFIRMED."""
    aid = account["account_id"]
    before = next(f for f in account["findings"] if f["rule_id"] == "RBI-MINBAL-2014-NOTICE")
    assert before["label"] == "UNCLEAR"
    r = _post(f"/api/accounts/{aid}/statements", [PREV])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["upload"][0]["new"] == 18 and d["upload"][0]["duplicates"] == 2
    after = next(f for f in d["findings"] if f["rule_id"] == "RBI-MINBAL-2014-NOTICE")
    assert after["label"] == "RECOVERABLE" and after["confidence"] == "CONFIRMED"
    assert d["summary"]["total_recoverable"] > account["summary"]["total_recoverable"]
    assert d["coverage"]["from"] == "2026-03-02" and d["coverage"]["to"] == "2026-08-31" and not d["coverage"]["gaps"]
    assert len(d["statements"]) == 2


def test_same_file_twice_adds_nothing(account):
    aid = account["account_id"]
    d = _post(f"/api/accounts/{aid}/statements", [PREV]).json()
    assert d["upload"][0]["new"] == 0 and d["upload"][0]["duplicates"] == 20
    assert d["summary"]["transactions"] == 41


def test_other_banks_statement_is_refused(account):
    aid = account["account_id"]
    r = _post(f"/api/accounts/{aid}/statements", [SAMPLES / "hdfc_priya_salary_2026.csv"])
    assert r.status_code == 409 and r.json()["detail"]["code"] in ("bank_mismatch", "account_mismatch")


def test_two_files_in_one_scan_equals_merge():
    r = _post("/api/scan", [PREV, MAIN], {"profile": PROFILE, "as_of": "2026-09-13"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["summary"]["transactions"] == 41 and [u["created"] for u in d["upload"]] == [True, False]
    client.delete(f"/api/accounts/{d['account_id']}")


def test_history_lists_accounts_with_totals(account):
    rows = client.get("/api/accounts").json()
    me = next(a for a in rows if a["id"] == account["account_id"])
    assert me["statements"] == 3 and me["transactions"] == 41 and me["total_recoverable"] > 5000
    assert me["period"] == {"from": "2026-03-02", "to": "2026-08-31"} and me["profile"]["bank"] == "CANARA"


def test_printable_complaint(account):
    aid = account["account_id"]
    client.post(f"/api/accounts/{aid}/guardian", json={"name": "Kumar", "relation": "son", "phone": "+919876543210"})
    c = client.post(f"/api/accounts/{aid}/cases", json={}).json()
    h = client.get(f"/api/cases/{c['id']}/complaint.html?lang=ta").text
    assert "<title>Complaint" in h and "Annexure A" in h and "RBI/2019-20/67" in h and "Selvi R" in h
    assert "Accompanied by: Kumar" in h and "window.print()" in h and "@media print" in h
    assert "CHRG MIN BAL NON MAINT MAY26" in h            # evidence line printed verbatim
    assert "PSG COLLEGE FEES" not in h                    # ordinary spending never leaves the app
    assert "setTimeout(()=>window.print()" in client.get(f"/api/cases/{c['id']}/complaint.html?print=1").text
    o = client.get(f"/api/cases/{c['id']}/ombudsman.html").text
    assert "cms.rbi.org.in" in o and "Relief sought" in o
    audit = client.get(f"/api/accounts/{aid}/audit").json()
    assert any(a["action"] == "case.print" for a in audit)


def test_remove_statement_rescans(account):
    aid = account["account_id"]
    sts = client.get(f"/api/accounts/{aid}/statements").json()["statements"]
    prev = next(s for s in sts if s["filename"] == PREV.name and s["new_count"] == 18)
    d = client.delete(f"/api/accounts/{aid}/statements/{prev['id']}").json()
    assert d["summary"]["transactions"] == 23
    again = next(f for f in d["findings"] if f["rule_id"] == "RBI-MINBAL-2014-NOTICE")
    assert again["label"] == "UNCLEAR"   # May's balances are gone → back to the question
