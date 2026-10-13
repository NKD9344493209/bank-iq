"""Concept 2 – Transaction category classification: Logistic Regression, Naive Bayes, Decision Tree, kNN
(+ the existing rule-based classifier as the baseline).  Stratified 5-fold CV + held-out test.

Feature sets
  sparse : TF-IDF word(1-2) + char(3-5) n-grams on the cleaned narration + 9 scaled numeric features
  svd    : TruncatedSVD(200) of the sparse matrix (dense) – used for kNN and the boosted trees
"""
from __future__ import annotations

import time

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier

from ..data.generator import CATEGORIES, load
from ..features import NUMERIC_COLS, TransactionFeaturizer
from ..rulemap import rule_categories, rule_category
from .common import C, ROOT, SERIES, bar_with_labels, plt, save_fig, save_json
from .eda import PRETTY

MODEL_DIR = ROOT / "models"


def prepare(n_rows: int = 40_000, seed: int = 42):
    tx, _ = load()
    s = tx.sample(n=min(n_rows, len(tx)), random_state=seed).reset_index(drop=True)
    tr, te = train_test_split(s, test_size=0.2, random_state=seed, stratify=s["category"])
    fz = TransactionFeaturizer().fit(tr)
    Xtr, Xte = fz.transform(tr), fz.transform(te)
    svd = TruncatedSVD(n_components=200, random_state=seed).fit(Xtr)
    return tr, te, fz, Xtr, Xte, svd, svd.transform(Xtr), svd.transform(Xte)


def sample_statements() -> pd.DataFrame:
    """The app's sample statements (real bank formats, written for the regex engine) as a tiny out-of-distribution check.
    The rule category is treated as the reference label here because the samples were authored for those rules."""
    from vasool.parsers import parse_file
    frames = []
    for f in sorted((ROOT / "data" / "samples").glob("*.*")):
        if f.suffix.lower() not in (".csv", ".tsv"):
            continue
        parsed = parse_file(f)
        d = pd.DataFrame([{"date": r["date"], "narration": r["narration"], "debit": r.get("debit", 0) or 0.0, "credit": r.get("credit", 0) or 0.0, "balance": r.get("balance"), "customer_id": f.stem} for r in parsed.rows])
        d["rule"] = [rule_category(n, a, b) for n, a, b in zip(d["narration"], d["debit"], d["credit"])]
        frames.append(d)
    S = pd.concat(frames, ignore_index=True); S["date"] = pd.to_datetime(S["date"])
    return S


def sample_statement_check(tr: pd.DataFrame, fitted: dict, seed: int = 42) -> dict:
    """Agreement with the rule engine on the sample statements for every fitted model, plus a sweep of the numeric-block
    weight for logistic regression (the hyper-parameter this check was used to choose)."""
    S = sample_statements()
    ytr = np.asarray(tr["category"].astype(str).tolist())
    out = {"n_lines": int(len(S)), "statements": sorted(S["customer_id"].unique().tolist()), "agreement": {}, "num_weight_sweep_logreg": {}}
    for name, (fz, m) in fitted.items():
        out["agreement"][name] = float((m.predict(fz.transform(S)) == S["rule"].values).mean())
    for w in (1.0, 0.3, 0.1, 0.0):
        fz = TransactionFeaturizer(num_weight=w).fit(tr)
        m = LogisticRegression(max_iter=3000, C=5.0, class_weight="balanced").fit(fz.transform(tr), ytr)
        out["num_weight_sweep_logreg"][str(w)] = float((m.predict(fz.transform(S)) == S["rule"].values).mean())
        print(f"  [samples] num_weight={w}: logistic agreement with rules on {len(S)} real-format lines = {out['num_weight_sweep_logreg'][str(w)]:.2f}")
    return out


def evaluate(model, Xtr, ytr, Xte, yte, cv, name):
    t0 = time.time()
    cvr = cross_validate(model, Xtr, ytr, cv=cv, scoring=["accuracy", "f1_macro"], n_jobs=1)
    model.fit(Xtr, ytr)
    yp = model.predict(Xte)
    r = {"cv_accuracy": float(cvr["test_accuracy"].mean()), "cv_accuracy_std": float(cvr["test_accuracy"].std()), "cv_f1_macro": float(cvr["test_f1_macro"].mean()),
         "accuracy": float(accuracy_score(yte, yp)), "f1_macro": float(f1_score(yte, yp, average="macro")), "f1_weighted": float(f1_score(yte, yp, average="weighted")),
         "per_class_f1": {k: float(v["f1-score"]) for k, v in classification_report(yte, yp, output_dict=True, zero_division=0).items() if k in CATEGORIES},
         "confusion": confusion_matrix(yte, yp, labels=CATEGORIES).tolist(), "fit_seconds": round(time.time() - t0, 1)}
    print(f"  {name:28s} CV acc={r['cv_accuracy']:.3f}±{r['cv_accuracy_std']:.3f} test acc={r['accuracy']:.3f} macro-F1={r['f1_macro']:.3f} ({r['fit_seconds']}s)")
    return r, yp


def run(n_rows: int = 40_000, seed: int = 42):
    tr, te, fz, Xtr, Xte, svd, Ztr, Zte = prepare(n_rows, seed)
    ytr, yte = np.asarray(tr["category"].astype(str).tolist()), np.asarray(te["category"].astype(str).tolist())
    print(f"[classification] train={len(tr):,} test={len(te):,} features={fz.n_features:,} (+SVD-200)")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    results, preds = {}, {}
    # rule-based baseline (no training)
    rb = rule_categories(te).values
    results["Rule-based (regex)"] = {"accuracy": float(accuracy_score(yte, rb)), "f1_macro": float(f1_score(yte, rb, average="macro")), "f1_weighted": float(f1_score(yte, rb, average="weighted")),
                                    "per_class_f1": {k: float(v["f1-score"]) for k, v in classification_report(yte, rb, output_dict=True, zero_division=0).items() if k in CATEGORIES},
                                    "confusion": confusion_matrix(yte, rb, labels=CATEGORIES).tolist(), "cv_accuracy": None, "cv_accuracy_std": None, "cv_f1_macro": None, "fit_seconds": 0}
    print(f"  {'Rule-based (regex)':28s} test acc={results['Rule-based (regex)']['accuracy']:.3f} macro-F1={results['Rule-based (regex)']['f1_macro']:.3f}")
    # text-only slice for Naive Bayes (needs non-negative features)
    n_text = fz.n_features - len(NUMERIC_COLS)
    models = [
        ("Logistic Regression", LogisticRegression(max_iter=3000, C=5.0, class_weight="balanced"), Xtr, Xte),
        ("Naive Bayes (Complement)", ComplementNB(alpha=0.1), Xtr[:, :n_text], Xte[:, :n_text]),
        ("Decision Tree", DecisionTreeClassifier(max_depth=30, min_samples_leaf=3, class_weight="balanced", random_state=seed), Xtr, Xte),
        ("kNN (k=7, SVD-200)", KNeighborsClassifier(n_neighbors=7, weights="distance", metric="cosine", n_jobs=-1), Ztr, Zte),
    ]
    fitted = {}
    for name, m, A, B in models:
        results[name], preds[name] = evaluate(m, A, ytr, B, yte, cv, name)
        if name in ("Logistic Regression", "Decision Tree"):
            fitted[name] = (fz, m)
        if name == "Logistic Regression":
            MODEL_DIR.mkdir(exist_ok=True)
            joblib.dump({"featurizer": fz, "model": m, "labels": CATEGORIES, "name": name}, MODEL_DIR / "txn_classifier_logreg.joblib")
    best = max((k for k in results if k != "Rule-based (regex)"), key=lambda k: results[k]["f1_macro"])
    # sweeps: kNN k, tree depth
    ks = [1, 3, 7, 15, 31]
    k_sweep = {k: float(cross_validate(KNeighborsClassifier(n_neighbors=k, weights="distance", metric="cosine", n_jobs=-1), Ztr, ytr, cv=cv, scoring="f1_macro")["test_score"].mean()) for k in ks}
    depths = [5, 10, 20, 30, 50, None]
    d_sweep = {}
    for d in depths:
        m = DecisionTreeClassifier(max_depth=d, min_samples_leaf=3, class_weight="balanced", random_state=seed)
        cvs = cross_validate(m, Xtr, ytr, cv=cv, scoring="f1_macro", return_train_score=True)
        d_sweep[str(d)] = {"cv_f1": float(cvs["test_score"].mean()), "train_f1": float(cvs["train_score"].mean())}
    # where ML beats rules: per-class comparison
    gain = {c: results[best]["per_class_f1"][c] - results["Rule-based (regex)"]["per_class_f1"][c] for c in CATEGORIES}
    # out-of-distribution sanity check on the app's real-format sample statements
    samples = sample_statement_check(tr, fitted, seed)

    # Fig 5: model comparison + per-class F1 (rules vs best ML)
    names = list(results)
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    w, x = 0.38, np.arange(len(names))
    for i, (metric, col) in enumerate(zip(["accuracy", "f1_macro"], SERIES)):
        vals = [results[n][metric] for n in names]
        bars = axes[0].bar(x + (i - 0.5) * w, vals, width=w - 0.03, color=col, label="Accuracy" if metric == "accuracy" else "Macro-F1")
        for b, v in zip(bars, vals):
            axes[0].text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}", ha="center", fontsize=7, color=C["ink2"])
    axes[0].set_xticks(x, [n.replace(" (", "\n(") for n in names], fontsize=7.5); axes[0].set_ylim(0, 1.15); axes[0].grid(axis="x", visible=False); axes[0].legend(fontsize=8, ncol=2, loc="upper center")
    axes[0].set_title("Rule baseline vs ML classifiers (test split)", loc="left", fontweight="bold")
    w2, x2 = 0.38, np.arange(len(CATEGORIES))
    axes[1].bar(x2 - w2 / 2, [results["Rule-based (regex)"]["per_class_f1"][c] for c in CATEGORIES], width=w2 - 0.03, color=C["grey"], label="Rule-based")
    axes[1].bar(x2 + w2 / 2, [results[best]["per_class_f1"][c] for c in CATEGORIES], width=w2 - 0.03, color=C["blue"], label=best)
    axes[1].set_xticks(x2, [PRETTY[c] for c in CATEGORIES], fontsize=6.5, rotation=35, ha="right"); axes[1].set_ylim(0, 1.3); axes[1].set_ylabel("F1"); axes[1].grid(axis="x", visible=False); axes[1].legend(fontsize=8, ncol=2, loc="upper center")
    axes[1].set_title("Per-class F1: where ML learns what the rules miss", loc="left", fontweight="bold")
    fig.suptitle("Fig. 5  Transaction classification", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig5_classification")

    # Fig 6: confusion matrices (rules vs best)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, name in zip(axes, ["Rule-based (regex)", best]):
        cm = np.array(results[name]["confusion"]); cmn = cm / cm.sum(axis=1, keepdims=True)
        ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1); ax.grid(False)
        short = [PRETTY[c][:10] for c in CATEGORIES]
        ax.set_xticks(range(len(CATEGORIES)), short, fontsize=6.5, rotation=45, ha="right"); ax.set_yticks(range(len(CATEGORIES)), short, fontsize=6.5)
        for i in range(len(CATEGORIES)):
            for j in range(len(CATEGORIES)):
                if cm[i, j]:
                    ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center", fontsize=6, color="white" if cmn[i, j] > 0.6 else C["ink"])
        ax.set_title(name, loc="left", fontweight="bold", fontsize=10); ax.set_xlabel("predicted"); ax.set_ylabel("true")
    fig.suptitle("Fig. 6  Row-normalised confusion matrices", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig6_confusion")

    # Fig 7: sweeps
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
    axes[0].plot(ks, [k_sweep[k] for k in ks], marker="o", color=C["blue"], linewidth=2); axes[0].set_xlabel("k"); axes[0].set_ylabel("CV macro-F1"); axes[0].set_title("kNN: effect of k", loc="left", fontweight="bold")
    dl = [str(d) for d in depths]
    axes[1].plot(dl, [d_sweep[d]["cv_f1"] for d in dl], marker="o", color=C["blue"], linewidth=2, label="CV F1"); axes[1].plot(dl, [d_sweep[d]["train_f1"] for d in dl], marker="o", color=C["orange"], linewidth=2, label="train F1")
    axes[1].set_xlabel("max_depth"); axes[1].legend(fontsize=8); axes[1].set_title("Decision tree: depth vs over-fitting", loc="left", fontweight="bold")
    fig.suptitle("Fig. 7  Hyperparameter sweeps", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig7_sweeps")

    out = {"n_train": int(len(tr)), "n_test": int(len(te)), "n_features": int(fz.n_features), "svd_components": 200, "models": results, "best": best,
           "knn_k_sweep_f1": k_sweep, "tree_depth_sweep": d_sweep, "ml_gain_over_rules_per_class": gain, "class_order": CATEGORIES, "sample_statement_check": samples,
           "train_class_counts": pd.Series(ytr).value_counts().to_dict()}
    save_json(out, "classification")
    joblib.dump({"svd": svd}, MODEL_DIR / "txn_svd.joblib")
    return out


if __name__ == "__main__":
    run()
