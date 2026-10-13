const D = require("./docgen");
const papers = require("./papers");
const { run, p, center, h1, h2, h3, bullets, numbered, table, pageBreak, spacer, buildDoc, save } = D;
const OUT = process.env.DV_OUT || "/home/claude/docs_build_biq/out";

const TITLE = "Bank IQ: A Machine Learning Intelligence Layer for Bank-Statement Analytics — Transaction Classification, Customer Segmentation and Spend Forecasting on a Regulatory Digital Twin";

const cover = [
  ...spacer(3),
  center("22MDC56 – MACHINE LEARNING LABORATORY", { bold: true, size: 26, color: "1F3864" }),
  center("PROJECT WORK – PHASE I", { bold: true, size: 26, color: "1F3864" }),
  center("Problem Identification and Literature Survey", { size: 24, after: 400 }),
  ...spacer(1),
  center(TITLE, { bold: true, size: 28, color: "1F3864", after: 400 }),
  center("Domain: Machine Learning – Banking / Financial Services Analytics", { size: 24, italics: true, after: 600 }),
  ...spacer(2),
  center("Submitted by", { size: 22 }),
  center("SANDHRU D.", { bold: true, size: 26 }),
  center("Register No.: ____________________", { size: 22, after: 300 }),
  center("M.Sc. Decision and Computing Sciences – V Semester", { size: 22 }),
  center("Academic Year 2026–27 (Odd Semester)", { size: 22, after: 400 }),
  center("Under the guidance of", { size: 22 }),
  center("____________________________", { size: 22 }),
  center("(Project Guide)", { size: 20, italics: true, after: 600 }),
  ...spacer(2),
  center("Coimbatore Institute of Technology, Coimbatore", { bold: true, size: 24 }),
  center("Phase I Review: 16 September 2026", { size: 22 }),
  pageBreak(),
];

const abstract = [
  h1("Abstract"),
  p("A bank statement is the most complete record most people have of their own money, yet it answers almost nothing by itself: where did the money go, is this charge normal, what kind of customer am I, what will next month cost. Banks answer these questions internally with hand-written rules — regular expressions over the narration text — which break on the long tail of abbreviations, bank-specific codes and OCR noise, and which cannot learn. Bank IQ is a machine-learning intelligence layer built on top of an existing rule-based system, Vasool Raja — a Regulatory Digital Twin that parses a statement (CSV, PDF or passbook photo), rebuilds the account and runs 19 RBI customer-protection rules to find money the bank owes. The rule engine is kept unchanged; the new layer applies the classical machine-learning syllabus to the same transactions."),
  p("The layer is trained on a labelled synthetic dataset of about 130,000 Indian bank-statement lines (500 customers × 12 months, 10 transaction categories, five hidden customer archetypes, seasonality and noisy long-tail narrations), because no public labelled statement data exists. It (1) classifies every line into ten categories with TF-IDF word and character n-grams plus numeric features, comparing Decision Tree, Naive Bayes, kNN and Logistic Regression under stratified 5-fold cross-validation against the regex rule baseline; (2) applies bagging, Random Forest, AdaBoost and gradient boosting; (3) predicts next-month spend from a customer-month panel with linear, regularised, polynomial and tree-based regression under GroupKFold-by-customer cross-validation; (4) segments customers with K-Means and Ward hierarchical clustering, validated by silhouette and Adjusted Rand Index; (5) studies PCA and Truncated SVD; (6) implements locally weighted regression from scratch; and (7) deploys everything as FastAPI endpoints and an Intelligence dashboard in the existing Tamil/English web app, where ML categories, segment, forecast, anomaly flags and plain-language business insights appear beside the rule engine's findings."),
  p([run("Keywords: ", { bold: true }), run("Transaction Classification, TF-IDF, Naive Bayes, Decision Tree, kNN, Logistic Regression, Random Forest, Gradient Boosting, Regression, Cross-Validation, K-Means, Hierarchical Clustering, PCA, Locally Weighted Regression, Anomaly Detection, Bank Statements, FastAPI")]),
];

const intro = [
  h1("1. Introduction"),
  h2("1.1 Background"),
  p("Every bank account in India produces a stream of transaction lines — UPI payments, card purchases, ATM withdrawals, transfers, EMIs, charges, salary and pension credits, refunds and interest — each described by a short, cryptic narration such as “UPI/DR/616812345/ANNAPOORNA STORES/CNRB/an***@okaxis” or “CHRG MIN BAL NON MAINT MAY26”. Personal-finance apps, bank analytics teams and consumer-protection tools all need the same first step: turn each line into a meaningful category, then aggregate categories into behaviour — monthly spend by type, income, charges, unusual items — and finally into decisions: which customers behave alike, what should next month look like, what deserves attention."),
  p("Vasool Raja, a hackathon project built by the author's team, does the consumer-protection part with deterministic rules: it parses a statement, rebuilds the account as a digital twin and evaluates 19 RBI rules, each at its own effective date, to produce findings with evidence chains. Its transaction classifier is a set of hand-written regular expressions. Those regexes are exact on the formats they were written for and silent on everything else — which, on real statements, is a large share of lines. Machine learning is the natural next step: learn the categories from labelled examples so that noisy, truncated and bank-specific narrations are handled, and then use the categorised history for segmentation, forecasting and anomaly detection."),
  h2("1.2 Motivation"),
  p("The motivation is to apply the full classical machine-learning syllabus — regression with cross-validation; Decision Tree, Naive Bayes and kNN classification; K-Means and hierarchical clustering; dimensionality reduction; bagging, boosting and Random Forest; locally weighted regression; an end-to-end application with a front end — to one real product rather than to seven unrelated toy datasets, and to measure each technique against a meaningful baseline: the regex rules that already exist. The result should be something a user can open, upload a statement to, and read insights from, with the rule engine still the only component that files a claim."),
];

const problem = [
  h1("2. Problem Identification"),
  h2("2.1 Problem Statement"),
  p("Given the transaction lines of a bank account (date, narration, debit, credit, balance) as produced by the Vasool Raja parsers, build, compare and deploy classical machine-learning models that (a) classify each line into one of ten transaction categories more accurately than the existing rule-based classifier, especially on narrations the rules do not cover; (b) predict a customer's total spend in the next month from the current month's behaviour; (c) group customers into behavioural segments without using any demographic attribute; (d) flag unusually large debits in an explainable way; and (e) present the outputs as business insights on a dashboard integrated with the existing application, so that the intelligence layer complements, and never replaces, the rule engine."),
  h2("2.2 Key Challenges"),
  ...bullets([
    "No public labelled dataset: bank statements are personal data. A realistic, labelled synthetic dataset must be designed so that labels are not derivable from the narration string alone (otherwise the regex baseline would be trivially perfect).",
    "Noisy short text: narrations are abbreviated (CHRG, WDL, RVSL), truncated, bank-specific and full of reference numbers; word tokens alone are brittle, so character n-grams and reference-number masking are needed.",
    "Ten imbalanced classes: bank charges and interest credits are rare but the most important for the product; macro-F1 and per-class F1, not accuracy, must drive model choice.",
    "Leakage in the regression: a customer's months are correlated, so folds must be grouped by customer (GroupKFold) rather than split at random.",
    "Honest clustering evaluation: segments must be judged by silhouette and by agreement with a hidden customer type that is never used as a feature.",
    "Integration: the ML layer must plug into an existing FastAPI service with session authentication and a vanilla-JavaScript bilingual UI without modifying the rule engine.",
  ]),
  h2("2.3 Objectives"),
  ...numbered([
    "Generate and document a labelled dataset of Indian bank-statement lines with ten categories, five customer archetypes, seasonality and long-tail narrations; perform EDA.",
    "Build a preprocessing pipeline: narration cleaning, TF-IDF word (1–2) and character (3–5) n-grams, numeric transaction features; a customer-month panel; a customer behavioural profile.",
    "Classify transactions with Decision Tree, Complement Naive Bayes, kNN and Logistic Regression under stratified 5-fold cross-validation, against the regex rule baseline; report accuracy, macro-F1, per-class F1 and confusion matrices.",
    "Apply Bagging, Random Forest, AdaBoost and gradient boosting and quantify the gain over a single tree; extract feature importances.",
    "Predict next-month spend with Linear, Ridge, Lasso, polynomial, Decision Tree, Random Forest and Gradient Boosting regressors under GroupKFold cross-validation; compare with a naive baseline (RMSE, MAE, R²).",
    "Segment customers with K-Means and Ward clustering; choose k by elbow and silhouette; validate with ARI; name and profile the segments.",
    "Apply PCA to the customer profile and Truncated SVD to the text features; implement locally weighted regression from scratch for spend versus income.",
    "Deploy the intelligence layer as FastAPI endpoints and an Intelligence dashboard (KPIs, category bars, monthly chart, segment, forecast, anomalies, insights, model card) in the existing Bank IQ web app, with tests, notebooks and Docker.",
  ]),
  h2("2.4 Scope"),
  p("In scope: the ten-category transaction taxonomy, customer-level analytics from a single account's history, the classical models listed above, and the dashboard. Out of scope: deep learning and large language models, fraud detection with labelled fraud data, real customer data (the models are validated on the synthetic test split and demonstrated on the app's synthetic sample statements), and any change to the rule engine, which remains the only source of findings and claims."),
];

const systems = [
  h1("3. Existing System and Proposed System"),
  h2("3.1 Existing System"),
  p("Vasool Raja classifies each transaction with regular expressions in vasool/classify.py (kind and channel), then runs the rulebook. The classifier is deterministic and explainable, but:"),
  ...bullets([
    "It recognises only the narration formats its authors had seen; merchant-only lines, abbreviations and OCR noise fall to UNKNOWN or to the wrong class. Mapped to the ten ML categories, it reaches about 72% accuracy on the labelled test set.",
    "It cannot improve from examples; every new bank format needs a new regex.",
    "It stops at the line: there is no notion of a customer's behaviour, segment, trend or expected spend, and no anomaly detection beyond the rulebook.",
    "Its outputs are not evaluated: no held-out accuracy, no per-class view of what it misses.",
  ]),
  h2("3.2 Proposed System"),
  p("Bank IQ keeps everything in Vasool Raja and adds a package bankiq/ with a labelled dataset, features, experiments, a service and an API router, plus an Intelligence screen in the web app:"),
  ...numbered([
    "Data module: deterministic generator (500 customers × 12 months; ten categories; archetypes salaried / pensioner / student / business / low-activity; seasonality; long-tail templates; noise) → data/ml/transactions.csv; EDA figures.",
    "Feature module: narration cleaning with reference-number masking; TF-IDF word + char n-grams; nine numeric features; customer-month panel (34 features incl. per-category amounts/counts and calendar month); 14-feature customer profile.",
    "Classification module: regex baseline (rulemap.py) vs Logistic Regression, Complement NB, Decision Tree, kNN; stratified 5-fold CV; sweeps of k and tree depth.",
    "Ensemble module: Bagging, Random Forest, AdaBoost, HistGradientBoosting vs single tree; n-gram importances.",
    "Regression module: next-month spend; naive baseline; seven regressors; GroupKFold by customer; feature importance.",
    "Clustering module: K-Means vs Ward on standardised profiles; elbow, silhouette, dendrogram, ARI vs hidden archetype; segment naming.",
    "Dimensionality-reduction and LWR module: PCA on profiles (variance, loadings, segment recovery), Truncated SVD on text, Gaussian-kernel LWR from scratch with a bandwidth study.",
    "Service and API: service.analyze(rows) → ML category (+ rule category side by side), category mix, monthly panel, segment, forecast, anomalies, insights; endpoints /api/ml/status, /results, /figures, /analyze, /analyze-json and /api/accounts/{id}/intelligence.",
    "Application: Intelligence tab in the existing Tamil/English app; model card with every experiment figure; pytest suite; seven notebooks; Dockerfile and Makefile.",
  ]),
  h3("Advantages"),
  ...bullets(["Every category now has a measured accuracy, and the dashboard shows exactly where the learned model and the hand-written rules disagree.", "Customer-level outputs — segment, trend, forecast, anomalies — that the rule engine never had.", "Separation of duties: models describe and predict; rules decide and file claims.", "Reproducible in one command and testable; the whole stack runs on a laptop."]),
];

const lit = [h1("4. Literature Survey"), p("Sixteen references were reviewed in the order the techniques appear in the pipeline: text representation, single-model learners, ensembles, non-parametric regression, clustering and its validation, dimensionality reduction, evaluation protocol, and anomaly detection in finance.")];
for (const pp of papers) {
  lit.push(h2(`4.${pp.n} ${pp.title}`));
  lit.push(p([run(`${pp.authors}, `), run(`${pp.venue}, ${pp.year}.`, { italics: true })], { after: 80 }));
  lit.push(p([run("Summary: ", { bold: true }), run(pp.summary)]));
  lit.push(p([run("Relevance to this project: ", { bold: true }), run(pp.relevance)]));
  lit.push(p([run("Limitation: ", { bold: true }), run(pp.limitation)]));
}
const comparison = [pageBreak(), h1("5. Comparative Analysis of Surveyed Literature"),
  table([["No.", "Paper (Year)", "Technique", "Strength", "Limitation"], ...papers.map((pp) => [String(pp.n), `${pp.title.split(":")[0]} (${pp.year})`, pp.technique, pp.short[0], pp.short[1]])], [600, 3000, 1900, 2100, 2000], { size: 17 }),
  D.caption("Table 5.1: Comparison of surveyed literature")];
const gap = [
  h1("6. Research Gap and Contribution"),
  p("The surveyed methods are mature individually: text can be represented with TF-IDF and character n-grams [13], [15] and classified with Naive Bayes [14], trees [1], neighbours [2] or ensembles [3]–[6]; customers can be clustered [8]–[10] and compressed [11]; forecasts can be fitted globally or locally [7]; evaluation has a standard protocol [12]; and financial anomaly detection has a taxonomy [16]. What is missing is their combination on bank-statement data with an honest baseline:"),
  ...numbered([
    "Published transaction-categorisation work uses proprietary bank data and is rarely compared with the rule systems banks actually run; here the regex classifier is the measured baseline and the per-class gain is reported.",
    "Classification, segmentation, forecasting and anomaly detection are treated as separate problems; here they are built on one feature pipeline from one account history, so the segment, the forecast and the flags are consistent with the categories.",
    "Nothing in the literature is integrated into a consumer-protection tool; here the ML layer sits beside a deterministic rule engine, with a clear rule that models inform and rules decide.",
    "No public labelled statement dataset exists; the generator in this project is documented and reproducible, with labels independent of the narration string, so the evaluation is meaningful.",
  ]),
  p("Bank IQ contributes (i) a reproducible labelled dataset and feature pipeline for Indian bank narrations, (ii) a side-by-side evaluation of the syllabus techniques against a real rule baseline, (iii) customer-level analytics with cross-validation that respects customer grouping, and (iv) a deployed intelligence dashboard inside an existing bilingual application."),
];
const tools = [
  h1("7. Tools and Technologies"),
  table([["Layer", "Technology", "Purpose"],
    ["Language", "Python 3.11", "All code"], ["Data", "pandas, NumPy", "Generator, panel, profile"],
    ["Text features", "scikit-learn TfidfVectorizer (word + char_wb), TruncatedSVD", "Narration representation"],
    ["Models", "scikit-learn: LogisticRegression, ComplementNB, DecisionTree, kNN, Bagging, RandomForest, AdaBoost, HistGradientBoosting, Linear/Ridge/Lasso, GradientBoostingRegressor, KMeans, AgglomerativeClustering, PCA", "All syllabus models"],
    ["From scratch", "NumPy", "Locally weighted regression"],
    ["Visualisation", "matplotlib, SciPy dendrogram, inline SVG in the UI", "15 result figures + dashboard charts"],
    ["Application", "FastAPI, vanilla JavaScript (existing app), joblib", "Endpoints, Intelligence screen, saved models"],
    ["Engineering", "pytest, Docker, Makefile, Jupyter", "Tests, deployment, reproducibility, notebooks"],
  ], [1700, 4400, 3500], { size: 18 }), D.caption("Table 7.1: Tools and technologies"),
  h1("8. Work Plan"),
  table([["Phase", "Component", "Deliverables", "Schedule"],
    ["I", "Problem identification and literature survey", "This document; summary of research articles", "16 Sep 2026"],
    ["II", "User interface and backend connectivity", "Intelligence screen ↔ /api/ml ↔ saved models", "30 Sep 2026"],
    ["II", "Preprocessing and EDA", "Generator, cleaning, features, panel, profile; EDA notebook and figures", "30 Sep 2026"],
    ["II", "Model building", "Classification, ensembles, regression, clustering, PCA/SVD, LWR", "30 Sep 2026"],
    ["II", "Result analysis and business insights", "Cross-validated tables, figures, insights engine", "30 Sep 2026"],
    ["III", "Deployment and demo", "Docker, tests, demo script", "CAT II"], ["III", "Presentation and viva", "Slides, viva sheet", "CAT II"], ["III", "Report and GitHub", "Project report, repository", "CAT II"],
  ], [900, 2900, 4400, 1400], { size: 18 }), D.caption("Table 8.1: Phase-wise work plan"),
];
const refs = [h1("References"), ...papers.map((pp) => new D.Paragraph({ children: [run(`${pp.authors}, “${pp.title},” ${pp.venue}, ${pp.year}.`, { size: 20 })], numbering: { reference: "refs", level: 0 }, spacing: { after: 80 } }))];

save(buildDoc([[...cover, ...abstract, ...intro, ...problem, ...systems, ...lit, ...comparison, ...gap, ...tools, ...refs]], { title: "Bank IQ – Phase I", header: "22MDC56 – Machine Learning Laboratory – Phase I – Bank IQ" }),
  `${OUT}/BankIQ_Phase_I_Problem_Identification_and_Literature_Survey.docx`);
