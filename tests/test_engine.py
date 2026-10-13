"""Golden tests: every sample statement, every trap, every rule boundary.

These are the tests that make the "just a rule engine" answer true: the engine
must be right on the cases that a naive statement scanner gets wrong.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from vasool import scan
from vasool.models import AccountProfile, AccountType, CityTier, Label, Priority, Confidence
from vasool.rules.user_claims import card_closure_claim, gold_release_claim, unauthorised_txn_claim
from vasool import rulebook as rb_mod

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def by_rule(res, rule_id):
    return [f for f in res.findings if f.rule_id == rule_id]


# --------------------------------------------------------------------------- #
# Amma — the demo statement
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def amma():
    return scan.scan_file(str(SAMPLES / "canara_amma_pension_2026.csv"), AccountProfile(bank="CANARA", min_balance_required=500, holder_name="Selvi R"), as_of=date(2026, 9, 13))


def test_amma_parses_all_lines(amma):
    assert len(amma.transactions) == 23
    assert amma.profile.account_last4 == "4417"


def test_amma_late_atm_reversal_is_exact(amma):
    f = by_rule(amma, "RBI-TAT-2019-ATM")
    assert len(f) == 1 and f[0].label == Label.RECOVERABLE and f[0].confidence == Confidence.CONFIRMED
    # debited 3 Aug, due 8 Aug (T+5), reversed 20 Aug → 12 days × ₹100
    assert f[0].amount == 1200.0
    assert "12 days late" in f[0].calculation


def test_amma_unreversed_failed_upi_claims_principal_plus_compensation(amma):
    f = by_rule(amma, "RBI-TAT-2019-UPI")
    assert len(f) == 1 and f[0].label == Label.RECOVERABLE
    # debited 10 Aug, due 11 Aug, as of 13 Sep → 33 days × 100 + 500 principal
    assert f[0].amount == 500 + 33 * 100


def test_amma_min_balance_asks_before_claiming(amma):
    f = by_rule(amma, "RBI-MINBAL-2014-NOTICE")
    assert len(f) == 1 and f[0].label == Label.UNCLEAR and f[0].questions
    assert f[0].amount == pytest.approx(295 + 53.10)   # GST line folded in


def test_amma_answer_no_notice_makes_it_recoverable(amma):
    tid = by_rule(amma, "RBI-MINBAL-2014-NOTICE")[0].evidence[0]
    res = scan.rescan(amma.transactions, amma.profile, amma.as_of, {f"notice_received:{tid}": "no"})
    f = by_rule(res, "RBI-MINBAL-2014-NOTICE")[0]
    assert f.label == Label.RECOVERABLE and f.confidence == Confidence.CONFIRMED


def test_amma_answer_yes_makes_it_avoidable_not_a_claim(amma):
    tid = by_rule(amma, "RBI-MINBAL-2014-NOTICE")[0].evidence[0]
    res = scan.rescan(amma.transactions, amma.profile, amma.as_of, {f"notice_received:{tid}": "yes"})
    f = by_rule(res, "RBI-MINBAL-2014-NOTICE")[0]
    assert f.label == Label.AVOIDABLE and f.amount == 0


def test_amma_atm_charge_inside_free_allowance(amma):
    f = by_rule(amma, "RBI-ATM-2025-FREE")
    assert len(f) == 1 and f[0].label == Label.RECOVERABLE
    assert f[0].amount == pytest.approx(23 + 4.14)


def test_amma_college_fee_is_never_flagged(amma):
    """The ₹50,000 college fee is a legitimate payment: no anomaly detection, no finding."""
    fee = next(t for t in amma.transactions if t.debit == 50000)
    assert all(fee.id not in f.evidence for f in amma.findings)


def test_amma_priority_ordering(amma):
    now = [f for f in amma.findings if f.priority == Priority.RECOVER_NOW]
    assert {f.rule_id for f in now} == {"RBI-TAT-2019-UPI", "RBI-TAT-2019-ATM"}
    small = [f for f in amma.findings if f.priority == Priority.NOT_WORTH_IT]
    assert any(f.rule_id == "RBI-ATM-2025-FREE" for f in small)


def test_finding_ids_are_stable_across_rescans(amma):
    res2 = scan.rescan(amma.transactions, amma.profile, amma.as_of, {})
    assert {f.id for f in amma.findings} == {f.id for f in res2.findings}


# --------------------------------------------------------------------------- #
# Arun — the trap statement
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def arun():
    return scan.scan_file(str(SAMPLES / "sbi_arun_student_2025.tsv"), AccountProfile(bank="SBI", min_balance_required=0), as_of=date(2025, 7, 1))


def test_arun_tsv_with_metadata_rows_parses(arun):
    assert len(arun.transactions) == 26


def test_arun_partial_reversal_within_tat_is_not_a_claim(arun):
    """₹2,000 failed ATM reversed as 2 × ₹1,000 on T+3 and T+4 → paired, no compensation."""
    assert by_rule(arun, "RBI-TAT-2019-ATM") == []


def test_arun_rule_versioning_by_effective_date(arun):
    """₹25 charge in April 2025 is over the ₹21 cap then; ₹23 in May 2025 is exactly the new cap."""
    old = by_rule(arun, "RBI-ATM-2021-CAP")
    assert len(old) == 1 and old[0].amount == pytest.approx(4.0) and old[0].occurred_on == date(2025, 4, 24)
    assert by_rule(arun, "RBI-ATM-2025-CAP") == []


def test_arun_sixth_withdrawal_charge_is_avoidable_not_recoverable(arun):
    f = [x for x in by_rule(arun, "RBI-ATM-2025-FREE") if x.occurred_on == date(2025, 5, 22)]
    assert len(f) == 1 and f[0].label == Label.AVOIDABLE and f[0].priority == Priority.PREVENT


def test_arun_same_amount_retry_is_asked_not_claimed(arun):
    ids = {t.id: t for t in arun.transactions}
    sus = [ids[i] for i in arun.suspicious_debits]
    assert any("ZOMATO" in t.narration for t in sus)
    assert by_rule(arun, "RBI-TAT-2019-UPI") == []


def test_arun_user_confirms_failure_then_claim_appears(arun):
    ids = {t.id: t for t in arun.transactions}
    zomato = [ids[i] for i in arun.suspicious_debits if "ZOMATO" in ids[i].narration][0]
    res = scan.rescan(arun.transactions, arun.profile, arun.as_of, {f"txn_failed:{zomato.id}": "yes"})
    f = by_rule(res, "RBI-TAT-2019-UPI")
    assert len(f) == 1 and f[0].amount == 349 + 15 * 100   # 15 Jun, due 16 Jun, as of 1 Jul = 15 days


# --------------------------------------------------------------------------- #
# Priya — HDFC salary, metro
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def priya():
    return scan.scan_file(str(SAMPLES / "hdfc_priya_salary_2026.csv"), AccountProfile(bank="HDFC", city_tier=CityTier.METRO, min_balance_required=10000), as_of=date(2026, 4, 1))


def test_priya_penalty_with_balance_always_above_minimum_is_confirmed(priya):
    f = by_rule(priya, "RBI-MINBAL-2014-NOTICE")
    assert len(f) == 1 and f[0].label == Label.RECOVERABLE and f[0].confidence == Confidence.CONFIRMED and f[0].amount == 708


def test_priya_imps_reversed_on_time_is_not_a_claim(priya):
    assert by_rule(priya, "RBI-TAT-2019-UPI") == []


def test_priya_subscription_price_creep_is_not_a_bank_charge(priya):
    netflix_ids = {t.id for t in priya.transactions if "NETFLIX" in t.narration}
    assert all(not (set(f.evidence) & netflix_ids) for f in priya.findings)


# --------------------------------------------------------------------------- #
# Murugan — inoperative account and BSBDA
# --------------------------------------------------------------------------- #
def test_inoperative_account_penalty_is_recoverable():
    res = scan.scan_file(str(SAMPLES / "indianbank_murugan_dormant_2026.csv"), AccountProfile(bank="INDIAN BANK", min_balance_required=500), as_of=date(2026, 9, 13))
    f = by_rule(res, "RBI-INOP-2024-NOPENALTY")
    assert {x.amount for x in f} == {236.0, 100.0}
    # the min-balance NOTICE question is suppressed because the same line is already recoverable
    assert by_rule(res, "RBI-MINBAL-2014-NOTICE") == []


def test_bsbda_account_every_charge_is_recoverable():
    res = scan.scan_file(str(SAMPLES / "indianbank_murugan_dormant_2026.csv"), AccountProfile(bank="INDIAN BANK", account_type=AccountType.BSBDA), as_of=date(2026, 9, 13))
    # every penalty line is recoverable under some rule and nothing is left as a question
    penalty_ids = {t.id for t in res.transactions if t.kind.value in ("CHARGE_MIN_BAL", "CHARGE_REACTIVATION")}
    covered = {f.evidence[0] for f in res.findings if f.label == Label.RECOVERABLE}
    assert penalty_ids <= covered
    assert all(f.label != Label.UNCLEAR for f in res.findings)


# --------------------------------------------------------------------------- #
# User-initiated claims
# --------------------------------------------------------------------------- #
def test_card_closure_penalty():
    rb = rb_mod.load()
    f = card_closure_claim(rb, date(2026, 8, 3), None, date(2026, 9, 13))   # Mon 3 Aug → 7 working days → Wed 12 Aug
    assert f.label == Label.RECOVERABLE and f.amount == (date(2026, 9, 13) - date(2026, 8, 12)).days * 500


def test_unauthorised_txn_zero_liability_no_shadow_credit():
    rb = rb_mod.load()
    f = unauthorised_txn_claim(rb, date(2026, 8, 3), 12000, date(2026, 8, 4), None, date(2026, 9, 13))
    assert f.label == Label.RECOVERABLE and f.amount == 12000


def test_unauthorised_txn_reported_late_is_not_automatic():
    rb = rb_mod.load()
    f = unauthorised_txn_claim(rb, date(2026, 8, 3), 12000, date(2026, 8, 20), None, date(2026, 9, 13))
    assert f.label == Label.UNCLEAR


def test_gold_release_before_rule_in_force_is_unclear():
    rb = rb_mod.load()
    f = gold_release_claim(rb, date(2025, 12, 1), None, date(2026, 1, 15))
    assert f.label == Label.UNCLEAR and f.amount == 0
    g = gold_release_claim(rb, date(2026, 6, 1), date(2026, 6, 30), date(2026, 9, 13))
    assert g.label == Label.RECOVERABLE and g.amount > 0


# --------------------------------------------------------------------------- #
# Rulebook integrity
# --------------------------------------------------------------------------- #
def test_rulebook_has_sources_and_dates():
    rb = rb_mod.load()
    for r in rb.all():
        assert r.source.get("url", "").startswith("http"), r.id
        assert r.effective_from
        if r.effective_to:
            assert r.effective_to > r.effective_from, r.id


def test_suggest_rules_never_claim():
    rb = rb_mod.load()
    assert any(r.status == "suggest" for r in rb.all())
    for r in rb.all():
        if r.status == "suggest":
            assert not r.can_claim


def test_atm_cap_rules_do_not_overlap():
    rb = rb_mod.load()
    old, new = rb.get("RBI-ATM-2021-CAP"), rb.get("RBI-ATM-2025-CAP")
    assert old.in_force(date(2025, 4, 30)) and not new.in_force(date(2025, 4, 30))
    assert new.in_force(date(2025, 5, 1)) and not old.in_force(date(2025, 5, 1))
