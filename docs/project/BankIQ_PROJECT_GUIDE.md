# Bank IQ — what is in this package and how to use it

Bank IQ is a **copy of Vasool Raja** (your original is untouched) with a classical-ML intelligence layer added for the 22MDC56 Machine Learning Laboratory. Everything ML is in a new package `bankiq/`; the rule engine, parsers, twin, guardian flow and the Tamil/English app are the originals, rebranded.

## Files delivered

| File | What it is | Rubric component |
|---|---|---|
| `BankIQ_repo.zip` | the full repository (code, dataset generator, trained models, results, figures, notebooks, tests, docs) | Phase II: UI + backend, preprocessing + EDA, model building, results; Phase III: deployment, GitHub |
| `BankIQ_Phase_I_Problem_Identification_and_Literature_Survey.docx` | Phase I document (abstract, problem, objectives, 16-paper survey, gap, tools, work plan) | Phase I (5 marks) |
| `BankIQ_Summary_on_Research_Articles.docx` | the department-format literature summary ([1]–[10], gap analysis, references) | Phase I |
| `BankIQ_Project_Report.docx` | ~30-page report: every chapter, every table and figure generated from `results/*.json` | Phase III report (5 marks) |
| `BankIQ_Presentation.pptx` | 18 slides with speaker notes | Phase III presentation (5 marks) |
| `BankIQ_Viva_QA.docx` | ~50 likely questions with crisp answers, demo script, numbers to remember | Phase III viva (5 marks) |

Fill in the register number, guide's name and GitHub URL (search for `____` and `<your-user>`).

## Run it (10 minutes)

```bash
unzip BankIQ_repo.zip && cd bank-iq
pip install -r requirements-dev.txt
# trained models, results and figures are already included; to regenerate everything:
make train                                      # ~12 min
VASOOL_AUTH=off python -m uvicorn api.main:app --port 8000
# open http://localhost:8000 → Intelligence tab → Sample: hdfc priya salary 2026
python -m pytest -q                             # 114 tests
```

Push `bank-iq/` to a **new** GitHub repository (do not push over Vasool Raja). The README credits Vasool Raja and your team-mates.

## How the syllabus maps to the code

| Syllabus concept | Script | Figures |
|---|---|---|
| Regression + cross-validation | `bankiq/experiments/regression.py` (7 regressors, GroupKFold by customer, naive baseline) | Fig 9, 10 |
| Decision Tree, Naive Bayes, kNN | `experiments/classification.py` (+ Logistic Regression, vs regex rules, stratified 5-fold CV) | Fig 5, 6, 7 |
| K-Means & hierarchical | `experiments/clustering.py` (K-Means vs Ward, elbow, silhouette, dendrogram, ARI) | Fig 11, 12, 13 |
| Dimensionality reduction | `experiments/pca_lwr.py` (PCA on profiles, Truncated SVD on text) | Fig 14 |
| Ensembles | `experiments/ensembles.py` (Bagging, RF, AdaBoost, Gradient Boosting) | Fig 8 |
| Locally weighted regression | `bankiq/models_lwr.py` (from scratch) + `pca_lwr.run_lwr` | Fig 15 |
| End-to-end app + visualisation | `bankiq/service.py`, `bankiq/api/ml.py`, `web/static/app.js` (`#/intelligence`) | dashboard |

## The story to tell in the review

1. Vasool Raja classifies transactions with regexes: 71% on labelled data, blind on the long tail.
2. Bank IQ learns the categories: 99.7% (Logistic Regression), 99.6% (Random Forest) — biggest gains on transfers, EMIs and merchant lines (the rules were only ever written for charges and refunds, where they are strongest).
3. From categorised history: customer segments (K-Means vs Ward), next-month forecast (Gradient Boosting beats the naive guess), unusual-debit flags, business insights.
4. All deployed in the existing app; **models inform, rules decide** — the ML layer never files a claim.
5. Honest limits: synthetic training data; validated on the app's sample statements (99% agreement with the rules on rule-friendly formats — the check that caught and fixed a numeric-feature flaw), and shown off on the long-tail sample where the rules fail on 30 of 41 lines.

## Things you may want to change

* `bankiq/data/generator.py` — add your own bank's narration formats to the templates and run `make train`.
* `bankiq/experiments/clustering.py::name_segments` — segment names.
* `web/static/app.js` — the `intel.*` strings (English and Tamil).
