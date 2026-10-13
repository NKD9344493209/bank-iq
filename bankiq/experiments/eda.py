"""EDA on the transaction dataset -> results/eda.json + fig1..fig4."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.generator import CATEGORIES, load
from ..features import customer_profile, month_panel
from .common import C, SERIES, bar_with_labels, plt, save_fig, save_json

PRETTY = {c: c.replace("_", " ").title().replace("Upi", "UPI").replace("Atm", "ATM").replace("Pos", "POS").replace("Emi", "EMI") for c in CATEGORIES}


def run():
    tx, cu = load()
    tx["amount"] = tx["debit"] + tx["credit"]
    tx["ym"] = pd.to_datetime(tx["date"]).dt.to_period("M").astype(str)
    dup = int(tx.duplicated(subset=["customer_id", "date", "narration", "debit", "credit"]).sum())
    out = {"rows": int(len(tx)), "customers": int(cu["customer_id"].nunique()), "months": int(tx["ym"].nunique()), "banks": cu["bank"].value_counts().to_dict(),
           "archetypes": cu["archetype"].value_counts().to_dict(), "missing": tx.isna().sum().to_dict(), "duplicates": dup,
           "category_counts": tx["category"].value_counts().to_dict(), "category_share": tx["category"].value_counts(normalize=True).round(4).to_dict(),
           "debit_share": float((tx["debit"] > 0).mean()), "total_debit": float(tx["debit"].sum()), "total_credit": float(tx["credit"].sum()),
           "amount_by_category": tx.groupby("category")["amount"].agg(["median", "mean", "max"]).round(1).to_dict("index"),
           "narration_len": {"mean": float(tx["narration"].str.len().mean()), "min": int(tx["narration"].str.len().min()), "max": int(tx["narration"].str.len().max())},
           "monthly_spend_total": tx.groupby("ym")["debit"].sum().round(0).to_dict()}
    panel = month_panel(tx)
    prof = customer_profile(tx)
    out["panel_rows"] = int(len(panel)); out["panel_corr_next_spend"] = panel.drop(columns=["customer_id", "ym"]).corr(numeric_only=True)["next_spend"].drop("next_spend").round(3).sort_values(ascending=False).head(10).to_dict()
    out["profile_describe"] = prof.drop(columns=["customer_id"]).describe().round(2).to_dict()
    print(f"[eda] rows={len(tx):,} customers={len(cu)} categories={len(CATEGORIES)} rule-baseline later")

    # Fig 1: category distribution + debit/credit + amount by category
    cats = tx["category"].value_counts()
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6))
    bar_with_labels(axes[0], [PRETTY[c] for c in cats.index][::-1], cats.values.tolist()[::-1], fmt="{:,.0f}", horizontal=True)
    axes[0].set_title("Transactions by category", loc="left", fontweight="bold"); axes[0].tick_params(axis="y", labelsize=8)
    dc = pd.Series({"Debit": int((tx["debit"] > 0).sum()), "Credit": int((tx["credit"] > 0).sum())})
    bar_with_labels(axes[1], dc.index.tolist(), dc.values.tolist(), color=[C["orange"], C["blue"]], fmt="{:,.0f}")
    axes[1].set_title("Debit vs credit lines", loc="left", fontweight="bold")
    order = tx.groupby("category")["amount"].median().sort_values().index
    axes[2].boxplot([np.log10(tx.loc[tx["category"] == c, "amount"].clip(lower=1)) for c in order], vert=False, showfliers=False, medianprops={"color": C["orange"]}, boxprops={"color": C["blue"]}, whiskerprops={"color": C["grey"]}, capprops={"color": C["grey"]})
    axes[2].set_yticks(range(1, len(order) + 1), [PRETTY[c] for c in order], fontsize=8); axes[2].set_xlabel("log10 amount (INR)")
    axes[2].set_title("Amount by category", loc="left", fontweight="bold")
    fig.suptitle(f"Fig. 1  Transaction dataset: {len(tx):,} lines · {len(cu)} customers · {tx['ym'].nunique()} months", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig1_dataset")

    # Fig 2: monthly spend & income trend, archetype mix
    ms = tx.groupby("ym").agg(spend=("debit", "sum"), credit=("credit", "sum"))
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    axes[0].plot(ms.index, ms["spend"] / 1e6, marker="o", color=C["orange"], linewidth=2, label="debits")
    axes[0].plot(ms.index, ms["credit"] / 1e6, marker="o", color=C["blue"], linewidth=2, label="credits")
    axes[0].tick_params(axis="x", labelsize=7, rotation=45); axes[0].set_ylabel("INR millions"); axes[0].legend(fontsize=8)
    axes[0].set_title("Monthly totals across all customers", loc="left", fontweight="bold")
    ar = cu["archetype"].value_counts()
    bar_with_labels(axes[1], ar.index.tolist(), ar.values.tolist(), fmt="{:d}")
    axes[1].set_title("Customer archetypes (hidden from the models)", loc="left", fontweight="bold")
    fig.suptitle("Fig. 2  Time structure and customer mix", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig2_trends")

    # Fig 3: customer profile distributions
    fig, axes = plt.subplots(1, 4, figsize=(13, 3))
    for ax, col, title in zip(axes, ["monthly_spend", "txn_per_month", "upi_share", "charges_per_month"], ["Monthly spend (INR)", "Transactions / month", "UPI share of spend", "Bank charges / month"]):
        ax.hist(prof[col], bins=30, color=C["blue"], edgecolor="#fcfcfb"); ax.set_title(title, loc="left", fontweight="bold", fontsize=10)
    fig.suptitle("Fig. 3  Customer-level behaviour (500 customers)", x=0.01, ha="left", fontsize=12)
    save_fig(fig, "fig3_customer_profiles")

    # Fig 4: correlation of month features with next-month spend
    corr = panel.drop(columns=["customer_id", "ym"]).corr(numeric_only=True)["next_spend"].drop("next_spend").sort_values()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    vals = corr.values; cols = [C["blue"] if v >= 0 else C["orange"] for v in vals]
    ax.barh([c.replace("_", " ") for c in corr.index], vals, color=cols, height=0.6)
    ax.axvline(0, color=C["ink2"], linewidth=0.8); ax.tick_params(axis="y", labelsize=7); ax.set_xlabel("Pearson r with next-month spend")
    ax.set_title("Fig. 4  Which month-t features predict month t+1 spend?", loc="left", fontweight="bold")
    save_fig(fig, "fig4_panel_correlation")
    save_json(out, "eda")
    return out


if __name__ == "__main__":
    run()
