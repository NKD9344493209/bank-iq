"""Feature engineering for the three ML tasks.

Transaction level (classification):
    text   : cleaned narration -> TF-IDF (word 1-2 grams + char 3-5 grams), reference numbers masked
    numeric: amount, log amount, is_debit, round-amount flag, day of month, weekday, month-end flag,
             paise flag (charges/interest have paise), amount share of the customer's month

Customer-month level (regression): spend/count by category in month t -> next-month total spend.
Customer level (clustering / PCA / LWR): 12-month behavioural profile.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

from .data.generator import CATEGORIES

_NUM = re.compile(r"\d{2,}")
_SPACE = re.compile(r"\s+")
_LD = re.compile(r"(?<=[A-Z])(?=\d)|(?<=\d)(?=[A-Z])")


def clean_narration(s: str) -> str:
    s = str(s).upper()
    s = _LD.sub(" ", s)                   # JAN26 -> JAN 26, 4123XXXX7710 -> 4123 XXXX 7710
    s = _NUM.sub(" NUM ", s)              # reference numbers, years, months carry no meaning -> one token
    s = re.sub(r"[/\-_*@:.]+", " ", s)
    return _SPACE.sub(" ", s).strip()


NUMERIC_COLS = ["amount", "log_amount", "is_debit", "is_round", "day", "weekday", "month_end", "has_paise", "amt_share"]


def numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.DataFrame(index=df.index)
    amt = df["debit"].where(df["debit"] > 0, df["credit"]).astype(float)
    dt = pd.to_datetime(df["date"])
    d["amount"] = amt
    d["log_amount"] = np.log1p(amt)
    d["is_debit"] = (df["debit"] > 0).astype(int)
    d["is_round"] = ((amt % 100 == 0) & (amt > 0)).astype(int)
    d["day"] = dt.dt.day
    d["weekday"] = dt.dt.weekday
    d["month_end"] = (dt.dt.day >= 28).astype(int)
    d["has_paise"] = ((amt * 100).round() % 100 != 0).astype(int)
    if "customer_id" in df:
        key = df["customer_id"].astype(str) + dt.dt.to_period("M").astype(str)
        tot = amt.groupby(key).transform("sum")
        d["amt_share"] = (amt / tot.replace(0, np.nan)).fillna(0)
    else:
        d["amt_share"] = amt / max(float(amt.sum()), 1.0)
    return d


class TransactionFeaturizer:
    """TF-IDF (word + char) on cleaned narration + scaled numeric features -> sparse matrix.

    num_weight down-weights the nine standardised numeric columns: TF-IDF rows have unit norm (entries ~0.1-0.3) while a
    standardised column is ~N(0,1), so at weight 1 the amount features dominate a linear model and it learns the generator's
    amount habits (e.g. salaries never round) instead of the words. 0.1 was chosen by agreement with the rule engine on the
    app's real-format sample statements (see classification.json -> sample_statement_check)."""

    def __init__(self, max_word=20000, max_char=30000, num_weight: float = 0.1):
        self.word = TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=max_word, sublinear_tf=True, token_pattern=r"[A-Z0-9]+")
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=5, max_features=max_char, sublinear_tf=True)
        self.scaler = StandardScaler()
        self.num_weight = num_weight

    def fit(self, df: pd.DataFrame):
        txt = df["narration"].map(clean_narration)
        self.word.fit(txt); self.char.fit(txt); self.scaler.fit(numeric_features(df)[NUMERIC_COLS])
        return self

    def transform(self, df: pd.DataFrame):
        txt = df["narration"].map(clean_narration)
        num = sparse.csr_matrix(self.scaler.transform(numeric_features(df)[NUMERIC_COLS]) * self.num_weight)
        return sparse.hstack([self.word.transform(txt), self.char.transform(txt), num]).tocsr()

    def fit_transform(self, df):
        return self.fit(df).transform(df)

    @property
    def n_features(self):
        return len(self.word.vocabulary_) + len(self.char.vocabulary_) + len(NUMERIC_COLS)


# ---------------------------------------------------------------------------- customer-month panel
def month_panel(tx: pd.DataFrame) -> pd.DataFrame:
    t = tx.copy()
    t["ym"] = pd.to_datetime(t["date"]).dt.to_period("M")
    t["is_debit"] = (t["debit"] > 0).astype(int)
    t["amount"] = t["debit"] + t["credit"]
    t["income_amt"] = t["credit"].where(t["category"] == "INCOME_CREDIT", 0.0)
    key = ["customer_id", "ym"]
    g = t.groupby(key)
    p = g.agg(spend=("debit", "sum"), income=("income_amt", "sum"), credits=("credit", "sum"), n_txn=("debit", "size"), n_debit=("is_debit", "sum"),
              max_debit=("debit", "max"), end_balance=("balance", "last"), min_balance=("balance", "min"))
    p["avg_debit"] = (p["spend"] / p["n_debit"].replace(0, np.nan)).fillna(0)
    amt = t.pivot_table(index=key, columns="category", values="amount", aggfunc="sum", fill_value=0.0).reindex(columns=CATEGORIES, fill_value=0.0)
    cnt = t.pivot_table(index=key, columns="category", values="amount", aggfunc="size", fill_value=0).reindex(columns=CATEGORIES, fill_value=0)
    amt.columns = [f"amt_{c}" for c in CATEGORIES]; cnt.columns = [f"n_{c}" for c in CATEGORIES]
    p = p.join(amt).join(cnt).reset_index().sort_values(["customer_id", "ym"])
    p["month_idx"] = p.groupby("customer_id").cumcount()
    p["next_spend"] = p.groupby("customer_id")["spend"].shift(-1)
    p["prev_spend"] = p.groupby("customer_id")["spend"].shift(1).fillna(p["spend"])
    nm = (p["ym"].dt.month % 12) + 1          # calendar month of the month being predicted
    p["next_month"] = nm; p["next_month_sin"] = np.sin(2 * np.pi * nm / 12); p["next_month_cos"] = np.cos(2 * np.pi * nm / 12)
    return p


PANEL_FEATURES = ["spend", "prev_spend", "income", "credits", "n_txn", "n_debit", "avg_debit", "max_debit", "end_balance", "min_balance", "month_idx", "next_month", "next_month_sin", "next_month_cos"] + \
    [f"amt_{c}" for c in CATEGORIES] + [f"n_{c}" for c in CATEGORIES]


# ---------------------------------------------------------------------------- customer profile
def customer_profile(tx: pd.DataFrame) -> pd.DataFrame:
    t = tx.copy()
    t["ym"] = pd.to_datetime(t["date"]).dt.to_period("M")
    months = t.groupby("customer_id")["ym"].nunique().clip(lower=1)
    g = t.groupby("customer_id")
    debit_total = g["debit"].sum()
    def share(cat):
        return (t[t["category"] == cat].groupby("customer_id")["debit"].sum().reindex(debit_total.index).fillna(0) / debit_total.replace(0, np.nan)).fillna(0)
    # robust monthly statistics: the median month, not the mean, so one big-ticket month does not define the customer
    monthly = t.groupby(["customer_id", "ym"]).agg(spend=("debit", "sum"), n=("debit", "size")).reset_index()
    med_spend = monthly.groupby("customer_id")["spend"].median().reindex(debit_total.index).fillna(0)
    prof = pd.DataFrame({
        "monthly_spend": med_spend, "monthly_income": t[t["category"] == "INCOME_CREDIT"].groupby("customer_id")["credit"].sum().reindex(debit_total.index).fillna(0) / months,
        "txn_per_month": g.size() / months, "avg_txn": g["debit"].apply(lambda s: s[s > 0].median() if (s > 0).any() else 0.0),
        "upi_share": share("UPI_PAYMENT"), "card_share": share("CARD_POS"), "atm_share": share("ATM_WITHDRAWAL"), "transfer_share": share("TRANSFER_OUT"),
        "charges_per_month": t[t["category"] == "BANK_CHARGE"].groupby("customer_id").size().reindex(debit_total.index).fillna(0) / months,
        "refunds_per_month": t[t["category"] == "REFUND_REVERSAL"].groupby("customer_id").size().reindex(debit_total.index).fillna(0) / months,
        "has_emi": (t[t["category"] == "LOAN_EMI"].groupby("customer_id").size().reindex(debit_total.index).fillna(0) > 0).astype(int),
        "avg_balance": g["balance"].mean(), "min_balance": g["balance"].min(),
    })
    prof["spend_income_ratio"] = (prof["monthly_spend"] / prof["monthly_income"].replace(0, np.nan)).fillna(0).clip(upper=5)
    return prof.reset_index()


PROFILE_FEATURES = ["monthly_spend", "monthly_income", "txn_per_month", "avg_txn", "upi_share", "card_share", "atm_share", "transfer_share", "charges_per_month", "refunds_per_month", "has_emi", "avg_balance", "min_balance", "spend_income_ratio"]
# clustering / PCA use the continuous features only: a standardised binary (has_emi) dominates Euclidean distance and splits every segment in two
CLUSTER_FEATURES = [f for f in PROFILE_FEATURES if f != "has_emi"]
