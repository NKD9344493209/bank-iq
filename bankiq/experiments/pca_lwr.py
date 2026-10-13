"""Concept 4 – PCA on customer profiles (+ SVD dimensionality sweep on the text features)
Concept 6 – Locally weighted regression of monthly spend on monthly income (from scratch)."""
from __future__ import annotations

import numpy as np
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import f1_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from ..data.generator import load
from ..features import CLUSTER_FEATURES, PROFILE_FEATURES, customer_profile, month_panel
from ..models_lwr import LocallyWeightedRegression, rmse
from .classification import prepare
from .common import C, SERIES, plt, save_fig, save_json


def run_pca(seed: int = 42):
    tx, cu = load()
    prof = customer_profile(tx).merge(cu[["customer_id", "archetype"]], on="customer_id")
    Xs = StandardScaler().fit_transform(prof[CLUSTER_FEATURES])
    pca = PCA(random_state=seed).fit(Xs); evr = pca.explained_variance_ratio_; cum = np.cumsum(evr); n95 = int(np.searchsorted(cum, 0.95) + 1)
    y = np.asarray(prof["archetype"].astype(str).tolist())
    from sklearn.model_selection import StratifiedKFold, cross_validate
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    comps = [2, 3, 5, 8, len(CLUSTER_FEATURES)]
    perf = {}
    for n in comps:
        P = pca.transform(Xs)[:, :n]
        perf[str(n)] = {"RF archetype F1": float(cross_validate(RandomForestClassifier(200, random_state=seed), P, y, cv=cv, scoring="f1_macro")["test_score"].mean()),
                        "kNN archetype F1": float(cross_validate(KNeighborsClassifier(7), P, y, cv=cv, scoring="f1_macro")["test_score"].mean())}
    loadings = {f"PC{i + 1}": dict(zip(CLUSTER_FEATURES, np.round(pca.components_[i], 3))) for i in range(3)}
    print(f"[pca] profile features={len(CLUSTER_FEATURES)} components for 95%={n95}")
    # text SVD sweep (dimensionality reduction on the TF-IDF matrix)
    tr, te, fz, Xtr, Xte, svd, Ztr, Zte = prepare(20_000, seed)
    ytr, yte = np.asarray(tr["category"].astype(str).tolist()), np.asarray(te["category"].astype(str).tolist())
    dims = [10, 25, 50, 100, 200]
    svd_perf = {}
    for d in dims:
        s = TruncatedSVD(n_components=d, random_state=seed).fit(Xtr)
        lr = LogisticRegression(max_iter=2000, C=5.0).fit(s.transform(Xtr), ytr)
        svd_perf[str(d)] = {"logreg_f1": float(f1_score(yte, lr.predict(s.transform(Xte)), average="macro")), "explained": float(s.explained_variance_ratio_.sum())}
        print(f"  SVD {d:3d} dims: logreg macro-F1={svd_perf[str(d)]['logreg_f1']:.3f} explained={svd_perf[str(d)]['explained']:.2f}")
    full_f1 = float(f1_score(yte, LogisticRegression(max_iter=2000, C=5.0).fit(Xtr, ytr).predict(Xte), average="macro"))

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.4))
    x = np.arange(1, len(evr) + 1)
    axes[0].bar(x, evr, color=C["blue"], width=0.6, label="individual"); axes[0].plot(x, cum, marker="o", color=C["orange"], linewidth=2, markersize=4, label="cumulative"); axes[0].axhline(0.95, color=C["grey"], linestyle="--")
    axes[0].set_xlabel("principal component"); axes[0].set_ylabel("explained variance"); axes[0].legend(fontsize=8); axes[0].grid(axis="x", visible=False); axes[0].set_title(f"Customer profile PCA ({n95} PCs for 95%)", loc="left", fontweight="bold")
    for (m, col) in zip(["RF archetype F1", "kNN archetype F1"], SERIES):
        axes[1].plot([str(c) for c in comps], [perf[str(c)][m] for c in comps], marker="o", linewidth=2, color=col, label=m)
    axes[1].set_xlabel("principal components kept"); axes[1].set_ylabel("CV macro-F1 (archetype)"); axes[1].legend(fontsize=8); axes[1].set_title("Recovering the hidden customer type", loc="left", fontweight="bold")
    axes[2].plot(dims, [svd_perf[str(d)]["logreg_f1"] for d in dims], marker="o", color=C["blue"], linewidth=2, label="SVD + logistic")
    axes[2].axhline(full_f1, color=C["orange"], linestyle="--", label=f"all {fz.n_features:,} features")
    axes[2].set_xscale("log"); axes[2].set_xlabel("SVD components (text)"); axes[2].set_ylabel("test macro-F1"); axes[2].legend(fontsize=8); axes[2].set_title("Text TF-IDF → Truncated SVD", loc="left", fontweight="bold")
    fig.suptitle("Fig. 14  Dimensionality reduction: PCA on profiles, SVD on narrations", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig14_pca")
    out = {"n_features": len(CLUSTER_FEATURES), "explained_variance_ratio": evr.round(4).tolist(), "cumulative": cum.round(4).tolist(), "n_components_95": n95, "loadings_pc1_3": loadings,
           "components_tested": comps, "performance": perf, "text_svd_sweep": svd_perf, "text_full_features_f1": full_f1, "text_n_features": int(fz.n_features)}
    save_json(out, "pca")
    return out


def run_lwr(seed: int = 42):
    tx, cu = load()
    panel = month_panel(tx)
    p = panel[(panel["income"] > 0) & (panel["spend"] > 0)].copy()
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(p)); tr_i, te_i = idx[: min(3000, len(p) // 2)], idx[min(3000, len(p) // 2): min(6000, len(p))]
    x_tr, y_tr = p["income"].values[tr_i] / 1e3, p["spend"].values[tr_i] / 1e3
    x_te, y_te = p["income"].values[te_i] / 1e3, p["spend"].values[te_i] / 1e3
    grid = np.linspace(np.percentile(x_tr, 1), np.percentile(x_tr, 99), 80)
    bins = np.linspace(grid[0], grid[-1], 25); mid = (bins[:-1] + bins[1:]) / 2
    med = np.array([np.median(y_tr[(x_tr >= bins[i]) & (x_tr < bins[i + 1])]) if ((x_tr >= bins[i]) & (x_tr < bins[i + 1])).any() else np.nan for i in range(len(bins) - 1)])
    print(f"[lwr] train={len(x_tr)} test={len(x_te)} (customer-months, income>0)")
    results, curves = {}, {}
    lin = LinearRegression().fit(x_tr.reshape(-1, 1), y_tr); results["Linear"] = {"test_rmse_k": rmse(y_te, lin.predict(x_te.reshape(-1, 1)))}; curves["Linear"] = lin.predict(grid.reshape(-1, 1))
    pf = PolynomialFeatures(3); poly = LinearRegression().fit(pf.fit_transform(x_tr.reshape(-1, 1)), y_tr)
    results["Polynomial deg-3"] = {"test_rmse_k": rmse(y_te, poly.predict(pf.transform(x_te.reshape(-1, 1))))}; curves["Polynomial deg-3"] = poly.predict(pf.transform(grid.reshape(-1, 1)))
    for tau in (2.0, 5.0, 10.0, 25.0, 60.0):
        m = LocallyWeightedRegression(tau=tau).fit(x_tr, y_tr)
        results[f"LWR τ={tau}"] = {"test_rmse_k": rmse(y_te, m.predict(x_te)), "tau": tau}; curves[f"LWR τ={tau}"] = m.predict(grid)
        print(f"  tau={tau:5.1f} test RMSE=₹{1000 * results[f'LWR τ={tau}']['test_rmse_k']:,.0f}")
    best = min((k for k in results if k.startswith("LWR")), key=lambda k: results[k]["test_rmse_k"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    axes[0].scatter(x_tr, y_tr, s=5, alpha=0.2, color=C["grey"], linewidths=0, label="customer-months")
    axes[0].plot(mid, med, linestyle=":", color=C["ink2"], linewidth=1.5, label="median per income bin")
    axes[0].plot(grid, curves["Linear"], color=C["orange"], linewidth=2, label="linear"); axes[0].plot(grid, curves[best], color=C["blue"], linewidth=2.5, label=best)
    axes[0].set_xlabel("monthly income (₹ thousand)"); axes[0].set_ylabel("monthly spend (₹ thousand)"); axes[0].set_ylim(0, np.percentile(y_tr, 99)); axes[0].legend(fontsize=8)
    axes[0].set_title("Spend vs income: LWR against a global line", loc="left", fontweight="bold")
    for (n, c), col in zip([(k, v) for k, v in curves.items() if k.startswith("LWR")], SERIES):
        axes[1].plot(grid, c, linewidth=1.8, color=col, label=n)
    axes[1].plot(mid, med, linestyle=":", color=C["ink2"], linewidth=1.5, label="median per bin"); axes[1].set_ylim(0, np.nanmax(med) * 1.4)
    axes[1].set_xlabel("monthly income (₹ thousand)"); axes[1].legend(fontsize=7, ncol=2); axes[1].set_title("Bandwidth τ: small = wiggly, large → linear", loc="left", fontweight="bold")
    fig.suptitle("Fig. 15  Locally weighted regression (Gaussian kernel, from scratch)", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig15_lwr")
    out = {"n_train": int(len(x_tr)), "n_test": int(len(x_te)), "models": results, "best_lwr": best}
    save_json(out, "lwr")
    return out


def run(seed: int = 42):
    run_pca(seed); run_lwr(seed)


if __name__ == "__main__":
    run()
