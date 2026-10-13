"""Concept 5 – Ensembles for transaction classification: Bagging, Random Forest, AdaBoost, Gradient Boosting vs one tree.
Tree ensembles use the sparse TF-IDF matrix; HistGradientBoosting and AdaBoost use the dense SVD-200 features."""
from __future__ import annotations

import joblib
import numpy as np
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.tree import DecisionTreeClassifier

from ..data.generator import CATEGORIES
from .classification import MODEL_DIR, evaluate, prepare
from .common import C, SERIES, bar_with_labels, plt, save_fig, save_json
from .eda import PRETTY


def run(n_rows: int = 20_000, seed: int = 42):
    tr, te, fz, Xtr, Xte, svd, Ztr, Zte = prepare(n_rows, seed)
    ytr, yte = np.asarray(tr["category"].astype(str).tolist()), np.asarray(te["category"].astype(str).tolist())
    print(f"[ensembles] train={len(tr):,} test={len(te):,}")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    models = [
        ("Decision Tree (single)", DecisionTreeClassifier(max_depth=30, min_samples_leaf=3, class_weight="balanced", random_state=seed), Xtr, Xte),
        ("Bagging (50 trees)", BaggingClassifier(DecisionTreeClassifier(max_depth=30, min_samples_leaf=3, class_weight="balanced", random_state=seed), n_estimators=50, max_samples=0.8, max_features=0.5, n_jobs=-1, random_state=seed), Xtr, Xte),
        ("Random Forest (200)", RandomForestClassifier(n_estimators=200, min_samples_leaf=2, class_weight="balanced_subsample", n_jobs=-1, random_state=seed), Xtr, Xte),
        ("AdaBoost (30, SVD-200)", AdaBoostClassifier(DecisionTreeClassifier(max_depth=2), n_estimators=30, learning_rate=0.5, random_state=seed), Ztr, Zte),
        ("Gradient Boosting (SVD-200)", HistGradientBoostingClassifier(max_iter=100, learning_rate=0.1, max_depth=6, random_state=seed), Ztr, Zte),
    ]
    results, fitted = {}, {}
    for name, m, A, B in models:
        results[name], _ = evaluate(m, A, ytr, B, yte, cv, name)
        fitted[name] = m
    best = max(results, key=lambda k: results[k]["f1_macro"])
    rf = fitted["Random Forest (200)"]
    # top features of the random forest (word / char n-grams)
    names = list(fz.word.get_feature_names_out()) + ["char:" + c for c in fz.char.get_feature_names_out()] + list(fz.scaler.feature_names_in_)
    imp = sorted(zip(names, rf.feature_importances_), key=lambda x: -x[1])[:15]
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump({"featurizer": fz, "model": rf, "labels": CATEGORIES, "name": "Random Forest (200)"}, MODEL_DIR / "txn_classifier_rf.joblib")
    joblib.dump({"featurizer": fz, "svd": svd, "model": fitted["Gradient Boosting (SVD-200)"], "labels": CATEGORIES, "name": "Gradient Boosting (SVD-200)"}, MODEL_DIR / "txn_classifier_gb.joblib")

    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    nm = list(results); w, x = 0.38, np.arange(len(nm))
    for i, (metric, col) in enumerate(zip(["accuracy", "f1_macro"], SERIES)):
        vals = [results[n][metric] for n in nm]
        bars = axes[0].bar(x + (i - 0.5) * w, vals, width=w - 0.03, color=col, label="Accuracy" if metric == "accuracy" else "Macro-F1")
        for b, v in zip(bars, vals):
            axes[0].text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=7, color=C["ink2"])
    axes[0].set_xticks(x, [n.replace(" (", "\n(") for n in nm], fontsize=7.5); axes[0].set_ylim(0.8, 1.05); axes[0].grid(axis="x", visible=False); axes[0].legend(fontsize=8, ncol=2, loc="upper left")
    axes[0].set_title("Single tree vs ensembles (test split)", loc="left", fontweight="bold")
    bar_with_labels(axes[1], [n[:22] for n, _ in imp][::-1], [v for _, v in imp][::-1], horizontal=True, fmt="{:.3f}")
    axes[1].tick_params(axis="y", labelsize=7); axes[1].set_title("Random Forest – most important n-grams / features", loc="left", fontweight="bold")
    fig.suptitle("Fig. 8  Ensemble learning for transaction classification", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig8_ensembles")
    out = {"n_train": int(len(tr)), "n_test": int(len(te)), "models": results, "best": best, "rf_top_features": [{"feature": n, "importance": float(v)} for n, v in imp]}
    save_json(out, "ensembles")
    return out


if __name__ == "__main__":
    run()
