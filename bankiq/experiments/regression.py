"""Concept 1 – Regression with cross-validation: predict next month's total spend of a customer from this month's behaviour.

Rows = customer-months (features of month t -> spend in month t+1).  GroupKFold by customer so that a
customer's months never appear in both train and validation folds (no leakage through customer identity).
Models: Linear, Ridge, Lasso, Polynomial-2 + Ridge, Decision Tree, Random Forest, Gradient Boosting.
Baselines: "same as this month" (naive) and the customer's running mean.
"""
from __future__ import annotations

import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from ..data.generator import load
from ..features import PANEL_FEATURES, month_panel
from .classification import MODEL_DIR
from .common import C, SERIES, bar_with_labels, plt, save_fig, save_json

MODELS = {
    "Linear Regression": make_pipeline(StandardScaler(), LinearRegression()),
    "Ridge (α=1)": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "Lasso (α=10)": make_pipeline(StandardScaler(), Lasso(alpha=10.0, max_iter=20000)),
    "Polynomial deg-2 + Ridge": make_pipeline(StandardScaler(), PolynomialFeatures(2, include_bias=False), Ridge(alpha=50.0)),
    "Decision Tree (depth 8)": DecisionTreeRegressor(max_depth=8, min_samples_leaf=20, random_state=42),
    "Random Forest (300)": RandomForestRegressor(n_estimators=300, max_depth=12, min_samples_leaf=5, n_jobs=-1, random_state=42),
    "Gradient Boosting (400)": GradientBoostingRegressor(n_estimators=400, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=42),
}


def metrics(y, yp):
    return {"rmse": float(np.sqrt(mean_squared_error(y, yp))), "mae": float(mean_absolute_error(y, yp)), "r2": float(r2_score(y, yp)),
            "mape": float(np.mean(np.abs(y - yp) / np.maximum(y, 500)))}


def run(seed: int = 42):
    tx, cu = load()
    panel = month_panel(tx).dropna(subset=["next_spend"]).reset_index(drop=True)
    X, y, groups = panel[PANEL_FEATURES], panel["next_spend"].values, panel["customer_id"].values
    tr_idx, te_idx = next(GroupShuffleSplit(test_size=0.2, random_state=seed).split(X, y, groups))
    Xtr, Xte, ytr, yte, gtr = X.iloc[tr_idx], X.iloc[te_idx], y[tr_idx], y[te_idx], groups[tr_idx]
    print(f"[regression] customer-months train={len(Xtr):,} test={len(Xte):,} features={len(PANEL_FEATURES)}")
    gkf = GroupKFold(n_splits=5)
    results, preds = {}, {}
    results["Naive (same as this month)"] = metrics(yte, Xte["spend"].values) | {"cv_r2": None, "cv_r2_std": None, "fit_seconds": 0}
    for name, m in MODELS.items():
        t0 = time.time()
        cv = cross_validate(m, Xtr, ytr, cv=gkf, groups=gtr, scoring="r2", n_jobs=1)
        m.fit(Xtr, ytr); yp = m.predict(Xte); preds[name] = yp
        results[name] = metrics(yte, yp) | {"cv_r2": float(cv["test_score"].mean()), "cv_r2_std": float(cv["test_score"].std()), "fit_seconds": round(time.time() - t0, 1)}
        print(f"  {name:28s} CV R²={results[name]['cv_r2']:.3f}±{results[name]['cv_r2_std']:.3f} test R²={results[name]['r2']:.3f} RMSE=₹{results[name]['rmse']:,.0f} MAE=₹{results[name]['mae']:,.0f}")
    best = max(MODELS, key=lambda k: results[k]["r2"])
    imp = dict(sorted(zip(PANEL_FEATURES, MODELS["Gradient Boosting (400)"].feature_importances_.round(4)), key=lambda x: -x[1]))
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": MODELS[best], "name": best, "features": PANEL_FEATURES}, MODEL_DIR / "spend_regressor.joblib")

    names = list(results)
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    r2 = [results[n]["r2"] for n in names]
    bars = axes[0].barh(names, r2, color=[C["grey"]] + [C["blue"]] * (len(names) - 1), height=0.6)
    for b, v in zip(bars, r2):
        axes[0].text(max(v, 0) + 0.01, b.get_y() + b.get_height() / 2, f"{v:.3f}", va="center", fontsize=8, color=C["ink2"])
    axes[0].invert_yaxis(); axes[0].grid(axis="y", visible=False); axes[0].set_xlabel("test R²"); axes[0].set_title("Next-month spend: model comparison", loc="left", fontweight="bold")
    yp = preds[best]; idx = np.random.default_rng(0).choice(len(yte), size=min(1500, len(yte)), replace=False)
    axes[1].scatter(yte[idx] / 1e3, yp[idx] / 1e3, s=7, alpha=0.4, color=C["blue"], linewidths=0)
    lim = np.percentile(yte, 99) / 1e3; axes[1].plot([0, lim], [0, lim], color=C["orange"], linewidth=1.5); axes[1].set_xlim(0, lim); axes[1].set_ylim(0, lim)
    axes[1].set_xlabel("actual next-month spend (₹ thousand)"); axes[1].set_ylabel("predicted"); axes[1].set_title(f"Predicted vs actual – {best}", loc="left", fontweight="bold")
    fig.suptitle("Fig. 9  Regression with GroupKFold cross-validation", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig9_regression")
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    k = list(imp)[:12]
    bar_with_labels(ax, [s.replace("_", " ") for s in k][::-1], [imp[s] for s in k][::-1], horizontal=True)
    ax.tick_params(axis="y", labelsize=8); ax.set_title("Fig. 10  Gradient Boosting feature importance (next-month spend)", loc="left", fontweight="bold")
    save_fig(fig, "fig10_regression_importance")
    out = {"n_train": int(len(Xtr)), "n_test": int(len(Xte)), "features": PANEL_FEATURES, "cv": "GroupKFold(5) by customer", "models": results, "best": best, "gb_importance": imp}
    save_json(out, "regression")
    return out


if __name__ == "__main__":
    run()
