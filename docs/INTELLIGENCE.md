# Bank IQ intelligence layer — developer notes

Everything ML lives in `bankiq/`. The Vasool Raja engine (`vasool/`, `api/main.py`, `web/`) is untouched except for the router mount at the end of `api/main.py`, the `/api/ml/` entry in `PUBLIC_PREFIXES`, the `#/intelligence` screen in `web/static/app.js` and the nav link in `index.html`.

## Reproduce every number

```bash
make data          # data/ml/transactions.csv + customers.csv (deterministic, seed 42)
make train         # eda → classification → ensembles → regression → clustering → pca_lwr   (~12–25 min)
make test          # 101 engine tests + 13 ML tests
python scripts/intelligence_shots.py http://localhost:8765   # screenshots (run the app with VASOOL_AUTH=off first)
```

Outputs: `results/*.json` (every metric the report, slides and model card use), `results/figures/fig1–15.png`, `models/*.joblib`.

## Experiments → syllabus concepts

| script | concept | main outputs |
|---|---|---|
| `eda.py` | preprocessing + EDA | eda.json, fig1–4 |
| `classification.py` | DT, NB, kNN (+ LogReg) vs regex baseline, stratified 5-fold CV, k/depth sweeps | classification.json, fig5–7, txn_classifier_logreg, txn_svd |
| `ensembles.py` | Bagging, RF, AdaBoost, HistGB vs single tree | ensembles.json, fig8, txn_classifier_rf/gb |
| `regression.py` | next-month spend, 7 regressors, GroupKFold by customer, naive baseline | regression.json, fig9–10, spend_regressor |
| `clustering.py` | K-Means vs Ward, elbow/silhouette/ARI, segment naming | clustering.json, fig11–13, segments_kmeans |
| `pca_lwr.py` | PCA on profiles, SVD on text, LWR from scratch | pca.json, lwr.json, fig14–15 |

## Service contract

`service.analyze(rows, customer_id)` where each row is `{date, narration, debit, credit, balance?}` returns: `n_transactions, period, totals, categories, credit_categories, months, segment, profile, forecast, anomalies, rule_disagreements, insights, transactions, models`. See `tests/test_intelligence.py::test_service_analyze_end_to_end` and Appendix A of the report.

## Design rules

* Models describe and predict; only the rule engine creates findings or claims.
* A credit line can only receive a credit category (direction mask in `service.classify`).
* The hidden archetype in the generator is never a feature — only an evaluation label.
* Test split touched once; GroupKFold for anything with repeated customers.
