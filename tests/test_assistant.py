"""Ask Bank IQ: general banking questions, claim checks, account questions, honest fallback."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from vasool import rulebook, scan
from vasool.assistant import Assistant
from vasool.models import AccountProfile
from vasool import knowledge as kb

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


@pytest.fixture(scope="module")
def ctx():
    rb = rulebook.load()
    res = scan.scan_file(str(SAMPLES / "hdfc_priya_salary_2026.csv"), AccountProfile(bank="HDFC", min_balance_required=10000), as_of=date(2026, 4, 1))
    return Assistant(rb, "en"), res.findings


@pytest.mark.parametrize("q,entry", [
    ("how to download bank statements", "download-statement"),
    ("statement epdi download pannurathu", "download-statement"),
    ("what is kfs", "what-is-kfs"),
    ("my upi payment failed but money debited", "failed-upi"),
    ("how many free atm transactions", "atm-charges"),
    ("how to close credit card", "card-closure"),
    ("someone withdrew money without my permission", "unauthorised"),
    ("how to complain to rbi", "ombudsman"),
    ("gold loan rules", "gold-loan"),
    ("what can you do", "what-is-vasool"),
])
def test_knowledge_base_answers(ctx, q, entry):
    a, findings = ctx
    ans = a.answer(q, findings, [], "en")
    assert ans.kind == "knowledge" and ans.grounded_on[0] == entry, (q, ans.kind, ans.grounded_on)


@pytest.mark.parametrize("q,claim", [
    ("is it true that all ATM transactions are free?", "atm-unlimited-free"),
    ("I heard SMS charges are illegal now", "sms-illegal-now"),
    ("bank says I must complain to get reversal for failed upi", "failed-must-complain"),
    ("is the 100 rupees compensation capped at a maximum?", "compensation-capped"),
    ("do i need a lawyer for rbi ombudsman", "ombudsman-fee"),
    ("bank can charge minimum balance without notice right?", "minbal-no-notice"),
])
def test_wrong_statements_are_corrected(ctx, q, claim):
    a, findings = ctx
    ans = a.answer(q, findings, [], "en")
    assert ans.kind == "claim_check" and ans.grounded_on and kb.check_claim(q).id == claim
    assert ans.sources and ans.sources[0]["url"].startswith("http")


def test_account_question_uses_finding(ctx):
    a, findings = ctx
    ans = a.answer("why did the bank charge me 708?", findings, [], "en")
    assert ans.kind == "account" and "RBI-MINBAL-2014-NOTICE" in ans.grounded_on


def test_ordinary_payment_is_explained_not_flagged(ctx):
    a, findings = ctx
    ans = a.answer("why 15000 taken", findings, [], "en")
    assert ans.kind == "account" and "ordinary payment" in ans.text


def test_off_topic_gets_honest_fallback(ctx):
    a, findings = ctx
    ans = a.answer("what is the weather today", findings, [], "en")
    assert ans.kind == "fallback" and ans.suggestions


def test_tamil_question_answered_in_tamil(ctx):
    a, findings = ctx
    ans = a.answer("SMS-க்கு charge பண்ணலாமா?", findings, [], "en")
    assert ans.lang == "ta" and "2027" in ans.text


def test_works_without_any_statement():
    a = Assistant(rulebook.load(), "en")
    ans = a.answer("how do I complain to the rbi ombudsman", [], [], "en")
    assert ans.kind == "knowledge" and "cms.rbi.org.in" in ans.text
    ans2 = a.answer("what should I do?", [], [], "en")
    assert ans2.kind in ("fallback", "knowledge")


def test_greeting_and_thanks():
    a = Assistant(rulebook.load(), "en")
    assert a.answer("hello", [], [], "en").kind == "chat"
    assert a.answer("thanks", [], [], "en").kind == "chat"
