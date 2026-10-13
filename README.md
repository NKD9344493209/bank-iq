# Bank IQ — a Regulatory Digital Twin with a machine-learning intelligence layer

> **Rules decide. Models learn. Both are shown side by side.**

Give Bank IQ a bank statement (CSV / PDF / passbook photo). It rebuilds the account as a **digital twin**, runs a deterministic **RBI rule engine** over it to find money the bank owes you — and, new in this version, runs a **classical machine-learning intelligence layer** over the same transactions: every line is categorised by a trained classifier (not just regexes), the customer is placed in a behavioural **segment**, next month's spend is **forecast**, unusual debits are **flagged**, and the result is written up as plain-language **business insights** on an *Intelligence* dashboard.

Bank IQ is the machine-learning-laboratory (22MDC56) project of **Sandhru Duraisamy, Coimbatore Institute of Technology**. It is built on top of **Vasool Raja**, the HackVerse 2.0 hackathon project by team Mad Angles (Nandana R, Naveen Kumar D, Nethra Devi R, Sandhru Duraisamy); the rule engine, parsers, twin, guardian flow and the Tamil/English UI come from that work unchanged, and everything under `bankiq/` is new.

---

## 1. What is new: the intelligence layer

| Syllabus concept | Where it lives | What it does in the product |
|---|---|---|
| **Regression + cross-validation** | `bankiq/experiments/regression.py` | predicts a customer's **next-month spend** from this month's behaviour; Linear / Ridge / Lasso / polynomial / tree / forest / boosting; **GroupKFold by customer** so no customer leaks across folds |
| **Classification: Decision Tree, Naive Bayes, kNN** (+ Logistic Regression) | `experiments/classification.py` | categorises each statement line into 10 classes; **stratified 5-fold CV**; compared with the existing **regex rule classifier** as the baseline; checked on the app's real-format sample statements |
| **K-Means & hierarchical clustering** | `experiments/clustering.py` | **customer segmentation** on a 13-feature behavioural profile; elbow, silhouette, Ward dendrogram; validated with ARI against a hidden customer type |
| **Dimensionality reduction** | `experiments/pca_lwr.py` | **PCA** on the profile (variance, loadings, how many PCs keep the segment signal) and **Truncated SVD** on the TF-IDF text matrix |
| **Ensembles: bagging / boosting / Random Forest** | `experiments/ensembles.py` | Bagging, Random Forest, AdaBoost, (Hist)Gradient Boosting vs a single tree; feature importances |
| **Locally weighted regression** | `bankiq/models_lwr.py` + `pca_lwr.run_lwr` | **from-scratch** Gaussian-kernel LWR of monthly spend on income, bandwidth τ study vs linear / polynomial |
| **End-to-end ML app with front end** | `bankiq/service.py`, `bankiq/api/ml.py`, `web/static/app.js` (`#/intelligence`) | FastAPI endpoints + a dashboard: KPIs, category bars, monthly chart, segment, forecast, anomalies, insights, model card with every figure |

### Results (held-out test split; CV on the training split)

**Transaction classification** — 10 categories, 40k lines (32k train / 8k test), TF-IDF word + char n-grams + 9 numeric features (2,789 features; numeric block weighted 0.1)

| model | CV accuracy | test accuracy | macro-F1 |
|---|---|---|---|
| Rule-based regex (Vasool Raja `classify.py`, mapped to the 10 classes) | — | 71.5% | 0.794 |
| **Logistic Regression** (deployed) | **99.9%** | **99.9%** | **0.997** |
| Complement Naive Bayes | 93.5% | 93.4% | 0.899 |
| Decision Tree (depth 30) | 97.0% | 96.7% | 0.972 |
| kNN (k=7, cosine, SVD-200) | 97.3% | 97.4% | 0.977 |
| Bagging (50 trees) | 98.7% | 98.6% | 0.987 |
| **Random Forest (200)** | **99.6%** | **99.7%** | **0.996** |
| AdaBoost (30, SVD-200) | 84.4% | 80.1% | 0.802 |
| Gradient Boosting (SVD-200) | 99.6% | 99.9% | 0.998 |

The rule baseline is perfect on the narrations it was written for and fails on the 35 % "long-tail" narrations (bank-specific formats, abbreviations, noise) — exactly where the ML models learn the pattern instead of the string.

**Next-month spend regression** — 5,485 customer-months (4,387 train / 1,098 test), 34 features, GroupKFold(5) by customer

| model | CV R² | test R² | RMSE | MAE |
|---|---|---|---|---|
| Naive (same as this month) | — | 0.832 | ₹13,590 | ₹7,255 |
| Linear Regression | 0.863 | 0.869 | ₹11,990 | ₹6,653 |
| Ridge (α=1) | 0.863 | 0.869 | ₹11,990 | ₹6,652 |
| Lasso (α=10) | 0.863 | 0.869 | ₹11,993 | ₹6,636 |
| Polynomial deg-2 + Ridge | 0.852 | 0.857 | ₹12,529 | ₹6,654 |
| Decision Tree (depth 8) | 0.839 | 0.847 | ₹12,929 | ₹6,944 |
| Random Forest (300) | 0.875 | 0.870 | ₹11,915 | ₹6,313 |
| **Gradient Boosting (400) (deployed)** | **0.875** | **0.871** | **₹11,881** | **₹6,105** |

Gradient Boosting cuts the naive error by 13%; previous and current spend carry ~80% of the importance, then the month’s income credits and category mix — with one year of data the calendar features add little, which is why multi-year histories head the future scope.

**Customer segmentation** — 500 customers × 13 continuous behavioural features (median-month statistics; the binary EMI flag is excluded because it dominates Euclidean distance). The silhouette plateaus at k = 5–6 and the smallest k is kept: **k = 5**. K-Means and Ward agree (ARI 0.93) and recover the generator's hidden archetypes with **ARI 0.93** without seeing them: *High-value / business* (53, mostly business); *Low-activity* (51, mostly low_activity); *Cash-reliant* (129, mostly pensioner); *Digital-first (UPI heavy)* (74, mostly student); *Regular salaried* (193, mostly salaried). PCA needs 9 of 13 components for 95 % variance, but 3 components already recover the segment (archetype F1 0.95, Fig 14). Full tables in `results/*.json` and in the Intelligence → *Model card* screen.

### Dataset

Public labelled Indian bank-statement data does not exist (statements are personal data), so `bankiq/data/generator.py` builds a **labelled synthetic dataset**: 500 customers × 12 months (Jan–Dec 2025) → ~128,000 lines over five bank formats (SBI, HDFC, ICICI, Canara, Axis), 10 categories, 5 hidden customer archetypes (salaried, pensioner, student, business, low-activity), seasonality (festival months, school fees), one-off big-ticket months, long-tail narration templates and character noise. The label is the generating category — it is *not* derived from the narration, which is why a regex baseline can be measured honestly against it. `make data` regenerates it deterministically (`data/ml/transactions.csv`, `customers.csv`).

---

## 2. How it fits together

```
Statement (CSV / PDF / photo)
  ↓  vasool.parsers  →  Transaction lines
  ├──────────────── RULE ENGINE (unchanged) ─────────────────┐
  │  classify (regex) → twin → 19 RBI rules → findings → evidence pack → guardian → case │
  └────────────────────────────────────────────────────────────┘
  └──────────────── INTELLIGENCE LAYER (new, bankiq/) ────────┐
     features.py   clean narration → TF-IDF word+char n-grams + numeric features
                   month_panel (customer-month) · customer_profile (14 behavioural features)
     service.py    ML category (+ rule category side by side) → category mix → monthly panel
                   → K-Means segment → next-month forecast → anomaly z-scores → insights
     api/ml.py     GET /api/ml/status · /results · /figures/{png}
                   POST /api/ml/analyze (file) · /analyze-json
                   GET /api/accounts/{id}/intelligence (session-protected)
     web           #/intelligence dashboard (vanilla JS, Tamil / English)
  └────────────────────────────────────────────────────────────┘
```

The ML layer **never files a claim** — findings and the evidence pack still come only from the rule engine. The classifier's job is to describe the account (where the money goes, what is unusual, what to expect next month) and to show, line by line, where the hand-written rules and the learned model disagree.

---

## 3. Run it

```bash
pip install -r requirements-dev.txt          # Python 3.10+; tesseract-ocr only for passbook photos
make train                                   # generates the dataset and runs every experiment (~12 min on 2 cores)
                                             #   → results/*.json, results/figures/fig1–15.png, models/*.joblib
python -m uvicorn api.main:app --reload --port 8000     # → http://localhost:8000  → Intelligence tab
python -m pytest -q                          # 101 original tests + 13 ML-layer tests = 114
```

`VASOOL_AUTH=off` disables sign-in for a local demo. `make train-fast` skips the slower ensemble / PCA studies. Docker: `docker compose up --build` (the image trains the models at build time; pass `--build-arg BANKIQ_SKIP_TRAIN=1` and mount `models/` to skip).

### Demo (2 minutes)

Intelligence → **Sample: hdfc priya salary 2026** → KPIs (debits, income, charges, segment, forecast) → insights → category bars. Then **Sample: axis kavya longtail 2026** → *show disagreements only*: 30 of 41 lines — merchant-only and bank-code narrations the regexes file as generic transfers, which the model assigns to income, EMI, UPI, ATM, refund, interest and charges. Then the Canara pension sample (five charges, the ₹50,000 college fee flagged), the Model card (Fig 5 / Fig 11 / Fig 15) and Findings → the rule engine's claims on the same statement. Every sample is synthetic and labelled DEMONSTRATION DATA.

---

## 4. Repository

```
bankiq/                      the intelligence layer (new)
  data/generator.py          labelled synthetic dataset (500 customers × 12 months, 10 categories)
  features.py                narration cleaning, TF-IDF featurizer, customer-month panel, customer profile
  rulemap.py                 Vasool Raja regex classes → the 10 ML categories (the baseline)
  models_lwr.py              locally weighted regression from scratch (NumPy)
  experiments/               eda · classification · ensembles · regression · clustering · pca_lwr · run_all
  service.py                 analyze(rows) → categories, panel, segment, forecast, anomalies, insights
  api/ml.py                  FastAPI router (mounted in api/main.py)
notebooks/                   01_eda … 07_service_demo — thin notebooks over the experiment modules
results/                     *.json metrics + figures/fig1–fig15 (written by the experiments, never by hand)
models/                      txn_classifier_{logreg,rf,gb}.joblib · spend_regressor · segments_kmeans · txn_svd
tests/test_intelligence.py   generator, features, rule map, LWR, service, endpoints, auth
docs/                        Phase I/II/III documents, literature summary, slides, viva Q&A, ARCHITECTURE, DEMO
vasool/, api/main.py, web/   the Vasool Raja engine, API and UI (rulebook, twin, cases, guardian, assistant)
```

## 5. Testing

`python -m pytest -q` runs the 101 Vasool Raja tests plus `tests/test_intelligence.py`: generator determinism and label sanity, narration masking, featurizer shape, panel/profile invariants, rule mapping, LWR exactness on a line, end-to-end `service.analyze` accuracy against ground truth, `/api/ml/*` endpoints (public), `/api/accounts/{id}/intelligence` (401/404 without a session), bad-upload rejection.

## 6. Limitations (honest)

* The training data is **synthetic**. The generator is realistic about formats, seasonality and noise, but a model trained on it must be re-validated on real statements before any production use; `/api/ml/analyze` on the sample statements is the closest check in this repo.
* The naive "same as last month" forecast is a strong baseline on stable accounts; the regression models' gain is largest in seasonal months and for accounts with EMIs/irregular credits.
* Anomaly flags are statistical (robust z-score within a category), not fraud detection.
* All Vasool Raja limitations still apply (upload-only data access, no automated submission, conservative OCR).

## Licence

Copyright © 2026 Sandhru Duraisamy; the Vasool Raja components © 2026 Mad Angles (Nandana R, Naveen Kumar D, Nethra Devi R, Sandhru Duraisamy), Coimbatore Institute of Technology. **All rights reserved**; source published for evaluation and portfolio viewing (see `LICENSE`). The rulebook cites RBI circulars, which remain RBI publications.
