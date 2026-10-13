"""Concept 3 – Customer segmentation from transaction behaviour: K-Means vs Agglomerative (Ward).
The generator's hidden archetype is used only to *evaluate* the clusters (ARI) – never as a feature."""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from ..data.generator import load
from ..features import CLUSTER_FEATURES, PROFILE_FEATURES, customer_profile
from .classification import MODEL_DIR
from .common import C, SERIES, plt, save_fig, save_json


def name_segments(prof: pd.DataFrame) -> dict:
    names = {}
    for i, r in prof.iterrows():
        if r["monthly_spend"] >= prof["monthly_spend"].max() * 0.7:
            names[i] = "High-value / business"
        elif r["txn_per_month"] <= prof["txn_per_month"].min() * 1.3 and r["monthly_spend"] <= prof["monthly_spend"].median() and r["txn_per_month"] < 6:
            names[i] = "Low-activity"
        elif r["upi_share"] >= prof["upi_share"].max() * 0.9:
            names[i] = "Digital-first (UPI heavy)"
        elif r["atm_share"] >= prof["atm_share"].max() * 0.85 or r["atm_share"] >= 0.3:
            names[i] = "Cash-reliant / low-activity" if r["txn_per_month"] < 7 else "Cash-reliant"
        else:
            names[i] = "Regular salaried"
    seen = {}
    for k, v in list(names.items()):
        seen[v] = seen.get(v, 0) + 1
        if seen[v] > 1:
            names[k] = f"{v} {seen[v]}"
    return names


def run(seed: int = 42):
    tx, cu = load()
    prof = customer_profile(tx).merge(cu[["customer_id", "archetype"]], on="customer_id")
    scaler = StandardScaler().fit(prof[CLUSTER_FEATURES]); Xs = scaler.transform(prof[CLUSTER_FEATURES])
    truth = prof["archetype"].values
    print(f"[clustering] customers={len(prof)} features={len(CLUSTER_FEATURES)}")
    ks = list(range(2, 9)); inertia, sil, sil_h, ari_k, ari_h, agree_k = {}, {}, {}, {}, {}, {}
    for k in ks:
        km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(Xs); ag = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(Xs)
        inertia[k] = float(km.inertia_); sil[k] = float(silhouette_score(Xs, km.labels_)); sil_h[k] = float(silhouette_score(Xs, ag.labels_))
        ari_k[k] = float(adjusted_rand_score(truth, km.labels_)); ari_h[k] = float(adjusted_rand_score(truth, ag.labels_)); agree_k[k] = float(adjusted_rand_score(km.labels_, ag.labels_))
        print(f"  k={k} inertia={inertia[k]:,.0f} sil K-Means={sil[k]:.3f} Ward={sil_h[k]:.3f} K-Means~Ward ARI={agree_k[k]:.3f} | ARI vs archetype K-Means={ari_k[k]:.3f} Ward={ari_h[k]:.3f}")
    # k selection: K-Means silhouette; ks within 0.005 of the maximum are statistically indistinguishable (a plateau),
    # and among them the smallest k is kept (parsimony). The hidden archetype is NOT used here - only to report ARI afterwards.
    plateau = [k for k in ks if sil[k] >= max(sil.values()) - 0.005]
    best_k = min(plateau)
    print(f"  silhouette plateau k={plateau} -> best k={best_k} (smallest k on the plateau)")
    km = KMeans(n_clusters=best_k, n_init=10, random_state=seed).fit(Xs); ag = AgglomerativeClustering(n_clusters=best_k, linkage="ward").fit(Xs)
    prof["kmeans"] = km.labels_
    agree = float(adjusted_rand_score(km.labels_, ag.labels_))
    seg = prof.groupby("kmeans").agg(size=("customer_id", "size"), monthly_spend=("monthly_spend", "median"), monthly_income=("monthly_income", "median"), txn_per_month=("txn_per_month", "mean"),
                                     upi_share=("upi_share", "mean"), atm_share=("atm_share", "mean"), charges_per_month=("charges_per_month", "mean"), has_emi=("has_emi", "mean"), avg_balance=("avg_balance", "median")).round(3)
    seg["share"] = (seg["size"] / len(prof)).round(3)
    names = name_segments(seg); seg["segment"] = [names[i] for i in seg.index]
    seg["dominant_archetype"] = prof.groupby("kmeans")["archetype"].agg(lambda s: s.value_counts().index[0])
    joblib.dump({"kmeans": km, "scaler": scaler, "features": CLUSTER_FEATURES, "segment_names": names}, MODEL_DIR / "segments_kmeans.joblib")

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.3))
    axes[0].plot(ks, [inertia[k] for k in ks], marker="o", color=C["blue"], linewidth=2); axes[0].set_xlabel("k"); axes[0].set_ylabel("inertia"); axes[0].set_title("K-Means elbow", loc="left", fontweight="bold")
    axes[1].plot(ks, [sil[k] for k in ks], marker="o", color=C["blue"], linewidth=2, label="K-Means"); axes[1].plot(ks, [sil_h[k] for k in ks], marker="o", color=C["orange"], linewidth=2, label="Ward")
    ax2 = axes[1].twinx(); ax2.plot(ks, [agree_k[k] for k in ks], marker="s", color=C["aqua"], linewidth=1.5, linestyle="--", label="K-Means ~ Ward ARI (right)"); ax2.set_ylim(0.5, 1.05); ax2.grid(False); ax2.tick_params(labelsize=8)
    axes[1].axvline(best_k, color=C["grey"], linestyle="--"); axes[1].set_xlabel("k"); axes[1].set_ylabel("silhouette"); h1, l1 = axes[1].get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); axes[1].legend(h1 + h2, l1 + l2, fontsize=7, loc="lower left"); axes[1].set_title(f"Silhouette: plateau {plateau[0]}–{plateau[-1]} → k = {best_k}", loc="left", fontweight="bold")
    axes[2].plot(ks, [ari_k[k] for k in ks], marker="o", color=C["blue"], linewidth=2, label="K-Means"); axes[2].plot(ks, [ari_h[k] for k in ks], marker="o", color=C["orange"], linewidth=2, label="Ward")
    axes[2].set_xlabel("k"); axes[2].set_ylabel("ARI vs hidden archetype"); axes[2].legend(fontsize=8); axes[2].set_title("Agreement with the hidden customer type", loc="left", fontweight="bold")
    fig.suptitle("Fig. 11  Choosing the number of segments", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig11_cluster_selection")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.9))
    Z = linkage(Xs, method="ward"); dendrogram(Z, truncate_mode="lastp", p=30, ax=axes[0], color_threshold=0, above_threshold_color=C["blue"], no_labels=True)
    axes[0].set_title("Ward dendrogram (last 30 merges)", loc="left", fontweight="bold"); axes[0].grid(False); axes[0].set_ylabel("merge distance")
    P = PCA(n_components=2, random_state=seed).fit_transform(Xs)
    for c, col in zip(sorted(names), SERIES):
        m = km.labels_ == c; axes[1].scatter(P[m, 0], P[m, 1], s=14, alpha=0.7, color=col, linewidths=0, label=f"{c}: {names[c]}")
    axes[1].set_xlabel("PC1"); axes[1].set_ylabel("PC2"); axes[1].legend(fontsize=7, markerscale=2); axes[1].set_title("K-Means segments in PCA space", loc="left", fontweight="bold")
    fig.suptitle("Fig. 12  Hierarchical structure and segment map", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig12_dendrogram_segments")

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.2))
    labels = [f"{i}: " + names[i].replace(" / ", "/\n").replace(" (", "\n(") for i in seg.index]
    for ax, col, title, fmt in zip(axes, ["monthly_spend", "txn_per_month", "upi_share"], ["Median monthly spend (₹)", "Transactions / month", "UPI share of spend"], ["₹{:,.0f}", "{:.1f}", "{:.0%}"]):
        bars = ax.bar(labels, seg[col].values, color=SERIES[: len(seg)], width=0.6)
        for b, v in zip(bars, seg[col].values):
            ax.text(b.get_x() + b.get_width() / 2, v + seg[col].max() * 0.02, fmt.format(v), ha="center", fontsize=8, color=C["ink2"])
        ax.set_title(title, loc="left", fontweight="bold"); ax.grid(axis="x", visible=False); ax.tick_params(axis="x", labelsize=7); ax.set_ylim(0, seg[col].max() * 1.25)
    fig.suptitle("Fig. 13  Segment profiles", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig13_segment_profiles")
    out = {"customers": int(len(prof)), "features": CLUSTER_FEATURES, "k_range": ks, "kmeans_inertia": inertia, "kmeans_silhouette": sil, "ward_silhouette": sil_h,
           "ari_vs_archetype_kmeans": ari_k, "ari_vs_archetype_ward": ari_h, "kmeans_ward_agreement": agree_k, "silhouette_plateau": plateau, "best_k": int(best_k), "kmeans_vs_ward_ari": agree, "profiles": seg.reset_index().to_dict("records"), "segment_names": names}
    save_json(out, "clustering")
    return out


if __name__ == "__main__":
    run()
