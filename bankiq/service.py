"""Bank IQ intelligence service – turns a list of parsed transactions into ML-backed insight.

    analyze(rows) -> dict
        rows: list of {date, narration, debit, credit, balance?}  (what the parsers / store give us)

    Pipeline
      1. ML category per transaction (logistic regression over TF-IDF n-grams + numeric features)
         + the rule-based category side by side, so the UI can show where the two disagree.
      2. Monthly panel  -> spend/income trend, category breakdown, month-on-month deltas.
      3. Customer profile -> K-Means segment.
      4. Next-month spend forecast (regression model) with a naive baseline for comparison.
      5. Unusual transactions: robust z-score of the amount within its category (|z| > 3) – an
         explainable anomaly flag that complements Bank IQ's rule findings.
      6. Plain-language business insights.
Models are loaded lazily from models/*.joblib (train them with `python -m bankiq.experiments.run_all`).
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .data.generator import CATEGORIES
from .experiments.eda import PRETTY
from .features import PANEL_FEATURES, PROFILE_FEATURES, customer_profile, month_panel
from .rulemap import rule_category

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "results"


class ModelsMissing(RuntimeError):
    pass


@lru_cache(maxsize=1)
def models() -> dict[str, Any]:
    need = {"clf": "txn_classifier_logreg.joblib", "reg": "spend_regressor.joblib", "seg": "segments_kmeans.joblib"}
    missing = [v for v in need.values() if not (MODEL_DIR / v).exists()]
    if missing:
        raise ModelsMissing(f"trained models missing: {missing}. Run `python -m bankiq.experiments.run_all` first.")
    return {k: joblib.load(MODEL_DIR / v) for k, v in need.items()}


def models_available() -> bool:
    try:
        models(); return True
    except ModelsMissing:
        return False


# ---------------------------------------------------------------------------- helpers
def _frame(rows: list[dict[str, Any]], customer_id: str = "upload") -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in ("debit", "credit", "balance"):
        df[c] = pd.to_numeric(df.get(c, 0.0), errors="coerce").fillna(0.0) if c != "balance" else pd.to_numeric(df.get(c), errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["narration"] = df["narration"].astype(str)
    if df["balance"].isna().all():                                 # reconstruct a running balance if the file has none
        df["balance"] = (df["credit"] - df["debit"]).cumsum()
    else:
        df["balance"] = df["balance"].ffill().bfill()
    df["customer_id"] = customer_id
    df["bank"] = str(rows[0].get("bank", "")) if rows else ""
    return df


CREDIT_CATS = {"INCOME_CREDIT", "TRANSFER_IN", "REFUND_REVERSAL", "INTEREST_CREDIT"}


def classify(df: pd.DataFrame) -> pd.DataFrame:
    m = models()["clf"]
    X = m["featurizer"].transform(df)
    proba = m["model"].predict_proba(X)
    labels = list(m["model"].classes_)
    # business constraint: a credit line can only be a credit category and vice versa
    mask = np.where((df["credit"].values > 0)[:, None], np.array([[l in CREDIT_CATS for l in labels]]), np.array([[l not in CREDIT_CATS for l in labels]]))
    proba = proba * mask; proba = proba / np.maximum(proba.sum(axis=1, keepdims=True), 1e-9)
    df = df.copy()
    df["category"] = [labels[i] for i in proba.argmax(axis=1)]
    df["confidence"] = proba.max(axis=1).round(3)
    df["rule_category"] = [rule_category(n, d, c) for n, d, c in zip(df["narration"], df["debit"], df["credit"])]
    return df


def _anomalies(df: pd.DataFrame, z_thresh: float = 3.0, max_items: int = 15) -> list[dict[str, Any]]:
    out = []
    deb = df[df["debit"] > 0]
    for cat, g in deb.groupby("category"):
        if len(g) < 5:
            continue
        x = np.log1p(g["debit"].values)
        med = np.median(x); mad = np.median(np.abs(x - med)) * 1.4826 or 1e-6
        z = (x - med) / mad
        for (i, r), zz in zip(g.iterrows(), z):
            if zz > z_thresh:
                typical = float(np.expm1(med))
                out.append({"date": r["date"].date().isoformat(), "narration": r["narration"][:80], "amount": float(r["debit"]), "category": cat,
                            "typical": round(typical, 2), "times_typical": round(float(r["debit"]) / max(typical, 1), 1), "z": round(float(zz), 2)})
    out.sort(key=lambda a: -a["z"])
    return out[:max_items]


def _fmt(v: float) -> str:
    return f"₹{v:,.0f}"


def _insights(panel: pd.DataFrame, cats: pd.DataFrame, segment: str, forecast: dict, anomalies: list, disagreements: int, n: int) -> list[dict[str, str]]:
    ins: list[dict[str, str]] = []
    last = panel.iloc[-1]
    if len(panel) >= 2:
        prev = panel.iloc[-2]
        delta = last["spend"] - prev["spend"]; pct = delta / max(prev["spend"], 1) * 100
        if prev["spend"] < 100:
            ins.append({"kind": "trend", "text": f"Spend in {last['month']} was {_fmt(last['spend'])} (almost nothing was spent in {prev['month']})."})
        else:
            ins.append({"kind": "trend", "text": f"Spend in {last['month']} was {_fmt(last['spend'])}, {abs(pct):.0f}% {'higher' if delta > 0 else 'lower'} than {prev['month']} ({_fmt(prev['spend'])})."})
        moves = []
        for c in CATEGORIES:
            a, b = float(last.get(f"amt_{c}", 0)), float(prev.get(f"amt_{c}", 0))
            if c in ("INCOME_CREDIT", "TRANSFER_IN", "REFUND_REVERSAL", "INTEREST_CREDIT") or max(a, b) < 500:
                continue
            moves.append((a - b, c, a, b))
        moves.sort(key=lambda m: -abs(m[0]))
        if moves and abs(moves[0][0]) > 0.1 * max(prev["spend"], 1):
            d, c, a, b = moves[0]
            ins.append({"kind": "category", "text": f"The biggest mover was {PRETTY[c]}: {_fmt(b)} → {_fmt(a)} ({'+' if d > 0 else '-'}{_fmt(abs(d))})."})
    top = cats.sort_values("amount", ascending=False)
    if len(top):
        t = top.iloc[0]
        ins.append({"kind": "mix", "text": f"{PRETTY[t['category']]} is the largest outflow at {_fmt(t['amount'])} ({t['share'] * 100:.0f}% of all debits over the period)."})
    charges = float(cats.loc[cats["category"] == "BANK_CHARGE", "amount"].sum()); n_ch = int(cats.loc[cats["category"] == "BANK_CHARGE", "count"].sum())
    if n_ch:
        ins.append({"kind": "charges", "text": f"{n_ch} bank charge{'s' if n_ch != 1 else ''} totalling {_fmt(charges)} were identified – open the Findings tab to see which are recoverable under the RBI / bank rules."})
    income = float(panel["income"].sum()); spend = float(panel["spend"].sum())
    if income > 0:
        rate = (income - spend) / income * 100
        ins.append({"kind": "savings", "text": f"Over {len(panel)} month{'s' if len(panel) != 1 else ''} the account {'saved' if rate >= 0 else 'overspent by'} {abs(rate):.0f}% of recognised income ({_fmt(income)} in, {_fmt(spend)} out)."})
    ins.append({"kind": "segment", "text": f"Behaviour matches the “{segment}” segment (K-Means on {len(PROFILE_FEATURES)} behavioural features)."})
    if forecast.get("next_month_spend") is not None:
        ins.append({"kind": "forecast", "text": f"Expected spend next month: about {_fmt(forecast['next_month_spend'])} ({forecast['model']}); the naive ‘same as last month’ guess would be {_fmt(forecast['naive'])}."})
    if anomalies:
        a = anomalies[0]
        ins.append({"kind": "anomaly", "text": f"{len(anomalies)} unusually large debit{'s' if len(anomalies) != 1 else ''} flagged – e.g. {_fmt(a['amount'])} on {a['date']} is {a['times_typical']}× the typical {PRETTY[a['category']]} amount."})
    if disagreements:
        ins.append({"kind": "model", "text": f"The ML classifier and the regex rules disagree on {disagreements} of {n} lines ({disagreements / n * 100:.0f}%) – mostly narrations the hand-written patterns do not cover."})
    return ins


# ---------------------------------------------------------------------------- main entry
def analyze(rows: list[dict[str, Any]], customer_id: str = "upload") -> dict[str, Any]:
    if not rows:
        raise ValueError("no transactions")
    M = models()
    df = classify(_frame(rows, customer_id))
    n = len(df)
    # category breakdown (debits + credits separately)
    deb = df[df["debit"] > 0].groupby("category")["debit"].agg(["sum", "size"]).reset_index()
    deb.columns = ["category", "amount", "count"]; deb["share"] = deb["amount"] / max(deb["amount"].sum(), 1)
    cred = df[df["credit"] > 0].groupby("category")["credit"].agg(["sum", "size"]).reset_index(); cred.columns = ["category", "amount", "count"]
    # monthly panel
    panel = month_panel(df)
    panel["month"] = panel["ym"].astype(str)
    # segment
    prof = customer_profile(df)
    seg = M["seg"]; Xp = seg["scaler"].transform(prof[seg["features"]])
    k = int(seg["kmeans"].predict(Xp)[0]); segment = seg["segment_names"].get(k, f"Segment {k}")
    dist = seg["kmeans"].transform(Xp)[0]
    # forecast from the latest complete-ish month
    reg = M["reg"]; last = panel.iloc[[-1]]
    forecast: dict[str, Any] = {"model": reg["name"], "naive": float(last["spend"].iloc[0]), "based_on_month": str(last["month"].iloc[0])}
    try:
        forecast["next_month_spend"] = float(round(max(0.0, reg["model"].predict(last[reg["features"]])[0]), -1))
    except Exception as e:  # pragma: no cover
        forecast["next_month_spend"] = None; forecast["error"] = str(e)
    anomalies = _anomalies(df)
    disagree = int((df["category"] != df["rule_category"]).sum())
    cats = [{"category": c, "label": PRETTY[c], "amount": float(r["amount"]), "count": int(r["count"]), "share": float(r["share"])} for c, r in deb.set_index("category").iterrows()]
    cats.sort(key=lambda c: -c["amount"])
    months = [{"month": r["month"], "spend": float(r["spend"]), "income": float(r["income"]), "credits": float(r["credits"]), "n_txn": int(r["n_txn"]),
               "end_balance": float(r["end_balance"]), **{f"amt_{c}": float(r[f"amt_{c}"]) for c in CATEGORIES}} for _, r in panel.iterrows()]
    txns = [{"date": r["date"].date().isoformat(), "narration": r["narration"], "debit": float(r["debit"]), "credit": float(r["credit"]), "category": r["category"], "label": PRETTY[r["category"]],
             "confidence": float(r["confidence"]), "rule_category": r["rule_category"], "agree": bool(r["category"] == r["rule_category"])} for _, r in df.iterrows()]
    profile = {k: float(prof[k].iloc[0]) for k in PROFILE_FEATURES}
    return {
        "n_transactions": n, "period": {"from": df["date"].min().date().isoformat(), "to": df["date"].max().date().isoformat(), "months": int(len(panel))},
        "totals": {"debits": float(df["debit"].sum()), "credits": float(df["credit"].sum()), "income": float(panel["income"].sum()),
                   "charges": float(deb.loc[deb["category"] == "BANK_CHARGE", "amount"].sum()), "refunds": float(cred.loc[cred["category"] == "REFUND_REVERSAL", "amount"].sum())},
        "categories": cats, "credit_categories": [{"category": c, "label": PRETTY[c], "amount": float(r["amount"]), "count": int(r["count"])} for c, r in cred.set_index("category").iterrows()],
        "months": months, "segment": {"id": k, "name": segment, "distance_to_centres": [round(float(d), 3) for d in dist]}, "profile": profile,
        "forecast": forecast, "anomalies": anomalies, "rule_disagreements": disagree,
        "insights": _insights(panel, deb, segment, forecast, anomalies, disagree, n), "transactions": txns,
        "models": {"classifier": M["clf"]["name"], "regressor": reg["name"], "segmenter": f"K-Means (k={seg['kmeans'].n_clusters})"},
    }


def results_summary() -> dict[str, Any]:
    """Headline numbers from results/*.json for the dashboard's 'model card'."""
    import json
    out: dict[str, Any] = {"available": models_available(), "experiments": {}}
    for name in ("eda", "classification", "ensembles", "regression", "clustering", "pca", "lwr"):
        p = RESULTS_DIR / f"{name}.json"
        if p.exists():
            out["experiments"][name] = json.loads(p.read_text())
    figs = sorted((RESULTS_DIR / "figures").glob("*.png")) if (RESULTS_DIR / "figures").exists() else []
    out["figures"] = [f.name for f in figs]
    return out
