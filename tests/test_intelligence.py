"""Bank IQ ML layer: data generator, features, rule mapping, service and the /api/ml endpoints.
Model-dependent tests are skipped when models/*.joblib have not been trained yet."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from bankiq import service
from bankiq.data.generator import CATEGORIES, generate
from bankiq.features import PANEL_FEATURES, PROFILE_FEATURES, TransactionFeaturizer, clean_narration, customer_profile, month_panel
from bankiq.models_lwr import LocallyWeightedRegression
from bankiq.rulemap import rule_category

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)
needs_models = pytest.mark.skipif(not service.models_available(), reason="run `python -m bankiq.experiments.run_all` first")


@pytest.fixture(scope="module")
def small():
    tx, cu = generate(n_customers=12, months=4, seed=7)
    return tx, cu


# ---------------------------------------------------------------- data + features
def test_generator_shape_and_labels(small):
    tx, cu = small
    assert set(tx["category"]).issubset(CATEGORIES)
    assert {"customer_id", "date", "narration", "debit", "credit", "balance", "bank", "category"} <= set(tx.columns)
    assert len(cu) == 12 and (tx.groupby("customer_id").size() > 0).all()
    assert ((tx["debit"] > 0) ^ (tx["credit"] > 0)).all()          # exactly one side per line


def test_generator_is_deterministic():
    a, _ = generate(n_customers=3, months=2, seed=1); b, _ = generate(n_customers=3, months=2, seed=1)
    pd.testing.assert_frame_equal(a, b)


def test_clean_narration_masks_long_numbers():
    s = clean_narration("UPI/DR/512345678901/ZOMATO/ICIC/ref-99")
    assert "512345678901" not in s and "NUM" in s and "ZOMATO" in s


def test_featurizer_roundtrip(small):
    tx, _ = small
    fz = TransactionFeaturizer().fit(tx)
    X = fz.transform(tx.head(50))
    assert X.shape == (50, fz.n_features) and fz.n_features > 100


def test_month_panel_and_profile(small):
    tx, cu = small
    p = month_panel(tx)
    assert set(PANEL_FEATURES) <= set(p.columns)
    assert p.groupby("customer_id")["next_spend"].apply(lambda s: s.isna().sum()).eq(1).all()   # last month has no target
    assert p["next_month"].between(1, 12).all()
    prof = customer_profile(tx)
    assert len(prof) == len(cu) and set(PROFILE_FEATURES) <= set(prof.columns)
    assert prof["upi_share"].between(0, 1).all()


def test_rule_category_maps_vasool_kinds():
    assert rule_category("ATM WDL 1234 SBI MAIN BRANCH", 2000, 0) == "ATM_WITHDRAWAL"
    assert rule_category("SMS ALERT CHARGES JAN", 17.7, 0) == "BANK_CHARGE"
    assert rule_category("SALARY CREDIT ACME TECH", 0, 62000) == "INCOME_CREDIT"
    assert rule_category("UPI/DR/123/ZOMATO", 250, 0) == "UPI_PAYMENT"


def test_lwr_fits_a_line_exactly():
    x = np.linspace(0, 10, 50); y = 3 * x + 2
    m = LocallyWeightedRegression(tau=2.0).fit(x, y)
    assert np.allclose(m.predict(np.array([2.5, 7.5])), [9.5, 24.5], atol=1e-3)


# ---------------------------------------------------------------- service + api
@needs_models
def test_service_analyze_end_to_end(small):
    tx, _ = small
    one = tx[tx["customer_id"] == tx["customer_id"].iloc[0]]
    rows = one[["date", "narration", "debit", "credit", "balance"]].to_dict("records")
    out = service.analyze(rows, "C1")
    assert out["n_transactions"] == len(one)
    assert set(c["category"] for c in out["categories"]) <= set(CATEGORIES)
    assert out["segment"]["name"] and out["forecast"]["next_month_spend"] is not None
    assert out["insights"] and all("text" in i for i in out["insights"])
    acc = np.mean([t["category"] == c for t, c in zip(out["transactions"], one["category"])])
    assert acc > 0.9                                                 # ML categories agree with ground truth


def test_ml_status_is_public():
    r = TestClient(app).get("/api/ml/status")                       # fresh client: no session cookie
    assert r.status_code == 200 and "available" in r.json()


def test_ml_results_lists_experiments():
    r = client.get("/api/ml/results")
    assert r.status_code == 200 and "experiments" in r.json()


@needs_models
def test_ml_analyze_sample_csv():
    p = ROOT / "data" / "samples" / "hdfc_priya_salary_2026.csv"
    r = client.post("/api/ml/analyze", files={"file": (p.name, p.read_bytes(), "text/csv")})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["n_transactions"] > 5 and d["source"]["filename"] == p.name
    assert any(c["category"] == "INCOME_CREDIT" for c in d["credit_categories"])
    assert d["totals"]["charges"] >= 0


@needs_models
def test_ml_analyze_rejects_bad_upload():
    r = client.post("/api/ml/analyze", files={"file": ("x.exe", b"nope", "application/octet-stream")})
    assert r.status_code == 415


@needs_models
def test_account_intelligence_requires_login_and_works():
    p = ROOT / "data" / "samples" / "hdfc_priya_salary_2026.csv"
    anon = TestClient(app)
    s = client.post("/api/scan", files={"file": (p.name, p.read_bytes(), "text/csv")}, data={"profile": "{}"})
    assert s.status_code == 200, s.text
    acct = s.json()["account_id"]
    r = client.get(f"/api/accounts/{acct}/intelligence")
    assert r.status_code == 200 and r.json()["n_transactions"] > 5
    r2 = anon.get(f"/api/accounts/{acct}/intelligence")
    assert r2.status_code in (401, 404)
