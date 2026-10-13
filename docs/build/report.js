const fs = require("fs");
const path = require("path");
const D = require("./docgen");
const papers = require("./papers");
const { run, p, center, h1, h2, h3, bullets, numbered, table, caption, image, pageBreak, spacer, buildDoc, save, TableOfContents, Paragraph, AlignmentType } = D;

const REPO = process.env.BIQ_REPO || "/home/claude/bank-iq";
const OUT = process.env.DV_OUT || "/home/claude/docs_build_biq/out";
const J = (n) => JSON.parse(fs.readFileSync(path.join(REPO, "results", n + ".json")));
const eda = J("eda"), reg = J("regression"), cls = J("classification"), clu = J("clustering"), pca = J("pca"), ens = J("ensembles"), lwr = J("lwr");
const FIGD = path.join(REPO, "results", "figures");
const fig = (name, w, h, cap) => image(path.join(FIGD, name + ".png"), w, h, cap);
const f2 = (x) => (x == null ? "–" : Number(x).toFixed(2)), f3 = (x) => (x == null ? "–" : Number(x).toFixed(3)), pc = (x) => (x == null ? "–" : (100 * x).toFixed(1) + "%"), inr = (x) => "₹" + Math.round(Number(x)).toLocaleString("en-IN");
const TITLE = "Bank IQ: A Machine Learning Intelligence Layer for Bank-Statement Analytics — Transaction Classification, Customer Segmentation and Spend Forecasting on a Regulatory Digital Twin";
const code = (lines) => lines.map((l) => new Paragraph({ children: [new D.TextRun({ text: l, font: "Consolas", size: 17 })], spacing: { after: 0, line: 240 }, shading: { type: "clear", fill: "F4F4F2" } }));
const CATS = cls.class_order; const PRETTY = { UPI_PAYMENT: "UPI payment", CARD_POS: "Card / POS", ATM_WITHDRAWAL: "ATM withdrawal", TRANSFER_OUT: "Transfer out", LOAN_EMI: "Loan EMI", BANK_CHARGE: "Bank charge", INCOME_CREDIT: "Income credit", TRANSFER_IN: "Transfer in", REFUND_REVERSAL: "Refund / reversal", INTEREST_CREDIT: "Interest credit" };
const RB = cls.models["Rule-based (regex)"], best = cls.best, bk = clu.best_k, regBest = reg.best, ensBest = ens.best;
const naive = reg.models["Naive (same as this month)"], rbest = reg.models[regBest]; const imp0 = Object.entries(reg.gb_importance);
const seg = clu.profiles;
const n_tx = eda.rows, n_cu = eda.customers;

// ------------------------------------------------------------------ front
const front = [
  ...spacer(2),
  center("22MDC56 – MACHINE LEARNING LABORATORY", { bold: true, size: 24, color: "1F3864" }),
  center("PROJECT REPORT", { bold: true, size: 28, color: "1F3864", after: 300 }),
  center(TITLE, { bold: true, size: 28, color: "1F3864", after: 300 }),
  center("Domain: Machine Learning – Banking / Financial Services Analytics", { size: 24, italics: true, after: 500 }),
  center("Submitted by", { size: 22 }), center("SANDHRU D.", { bold: true, size: 26 }), center("Register No.: ____________________", { size: 22, after: 300 }),
  center("Under the guidance of", { size: 22 }), center("____________________________", { size: 22 }), center("(Project Guide)", { size: 20, italics: true, after: 500 }),
  center("M.Sc. Decision and Computing Sciences – V Semester", { size: 22 }), center("Coimbatore Institute of Technology, Coimbatore", { bold: true, size: 24 }), center("Academic Year 2026–27", { size: 22 }),
  pageBreak(),
  center("BONAFIDE CERTIFICATE", { bold: true, size: 26, color: "1F3864", after: 400 }),
  p(`Certified that this project report titled “${TITLE}” is the bonafide work of SANDHRU D. (Register No. ____________) who carried out the project work under my supervision during the academic year 2026–27 for the course 22MDC56 Machine Learning Laboratory, M.Sc. Decision and Computing Sciences, Coimbatore Institute of Technology.`),
  ...spacer(3), p("____________________________                                          ____________________________", { align: AlignmentType.LEFT }),
  p("Project Guide                                                                         Head of the Department", { align: AlignmentType.LEFT }), ...spacer(2),
  p("Submitted for the project viva-voce examination held on ____________.", { align: AlignmentType.LEFT }), ...spacer(2),
  p("____________________________                                          ____________________________", { align: AlignmentType.LEFT }),
  p("Internal Examiner                                                                      External Examiner", { align: AlignmentType.LEFT }),
  pageBreak(),
  center("ACKNOWLEDGEMENT", { bold: true, size: 26, color: "1F3864", after: 300 }),
  p("I express my sincere gratitude to my project guide, ____________________, for the guidance, review and encouragement throughout this work, and to the Head of the Department and the faculty of the Department of Computing, Coimbatore Institute of Technology, for the laboratory facilities and the course structure that made an end-to-end project possible. I thank my Vasool Raja team-mates — Nandana R, Naveen Kumar D and Nethra Devi R — on whose hackathon work the rule engine and application that this project extends were built, and my family and friends for their support."),
  p("Sandhru D.", { align: AlignmentType.RIGHT }), pageBreak(),
  h1("Abstract"),
  p(`A bank statement records everything that happens to an account but explains nothing: which lines are charges, where the money goes, whether a debit is unusual, what next month will cost. Existing tools, including the author's own hackathon project Vasool Raja — a Regulatory Digital Twin that runs 19 RBI customer-protection rules over a parsed statement — classify transactions with hand-written regular expressions, which are exact on familiar formats and silent on the long tail of abbreviations, bank-specific codes and OCR noise. Bank IQ keeps that rule engine unchanged and adds a classical machine-learning intelligence layer trained on a labelled synthetic dataset of ${n_tx.toLocaleString("en-IN")} Indian bank-statement lines (${n_cu} customers × 12 months, 10 categories, 5 hidden customer archetypes, seasonality and noisy narrations).`),
  p(`Every line is represented by TF-IDF word and character n-grams plus nine numeric features. Under stratified 5-fold cross-validation the regex baseline reaches ${pc(RB.accuracy)} accuracy (macro-F1 ${f3(RB.f1_macro)}) on the held-out test split; Complement Naive Bayes ${pc(cls.models["Naive Bayes (Complement)"].accuracy)}, kNN ${pc(cls.models["kNN (k=7, SVD-200)"].accuracy)}, a Decision Tree ${pc(cls.models["Decision Tree"].accuracy)} and Logistic Regression ${pc(cls.models["Logistic Regression"].accuracy)} (macro-F1 ${f3(cls.models["Logistic Regression"].f1_macro)}); Random Forest reaches ${pc(ens.models["Random Forest (200)"].accuracy)} and bagging, AdaBoost and gradient boosting are compared against the single tree. Next-month spend is predicted from a 34-feature customer-month panel under GroupKFold-by-customer cross-validation: ${regBest} reaches test R² ${f3(rbest.r2)} and RMSE ${inr(rbest.rmse)} against ${f3(naive.r2)} and ${inr(naive.rmse)} for the naive “same as this month” baseline. K-Means and Ward clustering on a 13-feature behavioural profile choose k = ${bk} by silhouette and recover the hidden customer archetypes with Adjusted Rand Index ${f2(clu.ari_vs_archetype_kmeans[bk])}; PCA needs ${pca.n_components_95} of ${pca.n_features} components for 95% variance; a from-scratch locally weighted regression of spend on income is studied across bandwidths. The layer is deployed as FastAPI endpoints and an Intelligence dashboard inside the existing Tamil/English application — ML categories beside rule categories, segment, forecast, explainable anomaly flags and plain-language business insights — with 13 new tests, seven notebooks and a Docker build.`),
  p([run("Keywords: ", { bold: true }), run("Transaction Classification, TF-IDF, Naive Bayes, Decision Tree, kNN, Logistic Regression, Bagging, Random Forest, AdaBoost, Gradient Boosting, Regression, Cross-Validation, K-Means, Hierarchical Clustering, PCA, Locally Weighted Regression, Anomaly Detection, FastAPI")]),
  pageBreak(), h1("Table of Contents"), new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  p("(Right-click → Update Field in Word to refresh page numbers.)", { italics: true, size: 18 }), pageBreak(),
];

// ------------------------------------------------------------------ 1
const ch1 = [
  h1("1. Introduction"),
  h2("1.1 Background"),
  p("Every bank account produces a stream of transaction lines, each described by a short cryptic narration. Personal-finance apps, bank analytics teams and consumer-protection tools all need the same first step — turn each line into a category — and then the same next steps: aggregate categories into monthly behaviour, compare the customer with others, anticipate the next month, and notice what is unusual. Vasool Raja does the consumer-protection part deterministically: it parses a statement, rebuilds the account as a digital twin and evaluates RBI rules to produce findings with evidence chains. Its transaction classifier is a set of regular expressions."),
  h2("1.2 Motivation"),
  p("Regular expressions cannot learn. On the narration formats they were written for they are perfect; on everything else — merchant-only lines, abbreviations, OCR output from a passbook — they are silent or wrong. Machine learning replaces the string with the pattern: a classifier trained on labelled examples generalises to formats it has never seen. Once lines are categorised reliably, the same account history supports customer-level analytics the rule engine never had: a behavioural segment, a spend forecast, an anomaly flag and a set of insights a person can act on. The project applies the complete classical machine-learning syllabus to one real product, with the existing regex classifier as the baseline every model must beat."),
  h2("1.3 Problem Statement"),
  p("Given the transaction lines of a bank account (date, narration, debit, credit, balance) as produced by the Vasool Raja parsers, build, compare and deploy classical machine-learning models that classify each line into one of ten transaction categories more accurately than the rule-based classifier; predict a customer's next-month spend; segment customers by behaviour without demographic data; flag unusually large debits in an explainable way; and present the outputs as business insights on a dashboard integrated with the existing application, with the rule engine remaining the only component that files a claim."),
  h2("1.4 Objectives"),
  ...numbered(["A labelled, reproducible dataset of Indian bank-statement lines and its EDA.", "A preprocessing pipeline: narration cleaning, TF-IDF word/char n-grams, numeric features, customer-month panel, customer behavioural profile.",
    "Transaction classification with Decision Tree, Naive Bayes, kNN and Logistic Regression under stratified 5-fold CV against the regex baseline; ensembles (Bagging, Random Forest, AdaBoost, Gradient Boosting).",
    "Next-month spend regression with Linear, Ridge, Lasso, polynomial, tree, forest and boosting models under GroupKFold cross-validation against a naive baseline.",
    "Customer segmentation with K-Means and Ward clustering, validated by silhouette and ARI; PCA and Truncated SVD studies; locally weighted regression from scratch.",
    "An intelligence service and API, an Intelligence dashboard in the existing bilingual app, tests, notebooks and a Docker build."]),
  h2("1.5 Scope"),
  p("In scope: the ten-category taxonomy, single-account analytics, the classical models above and the dashboard. Out of scope: deep learning and large language models, labelled fraud detection, real customer data (models are validated on the synthetic test split and demonstrated on the app's synthetic sample statements), and any change to the rule engine."),
  h2("1.6 Organisation of the Report"),
  p("Chapter 2 surveys the literature; Chapters 3–5 cover analysis, design and implementation; Chapter 6 the dataset, preprocessing and EDA; Chapter 7 model building; Chapter 8 results per syllabus concept; Chapter 9 business insights; Chapter 10 deployment and demonstration; Chapter 11 concludes."),
];

// ------------------------------------------------------------------ 2
const ch2 = [h1("2. Literature Survey"), p("Sixteen references were reviewed in the order the techniques appear in the pipeline: text representation, single-model learners, ensembles, non-parametric regression, clustering and validation, dimensionality reduction, evaluation protocol and financial anomaly detection.")];
for (const pp of papers) { ch2.push(h2(`2.${pp.n} ${pp.title}`)); ch2.push(p([run(`${pp.authors}, `), run(`${pp.venue}, ${pp.year}.`, { italics: true })], { after: 60 })); ch2.push(p([run("Summary: ", { bold: true }), run(pp.summary)])); ch2.push(p([run("Relevance: ", { bold: true }), run(pp.relevance)])); ch2.push(p([run("Limitation: ", { bold: true }), run(pp.limitation)])); }
ch2.push(h2("2.17 Comparative Analysis and Research Gap"));
ch2.push(table([["No.", "Paper (Year)", "Technique", "Strength", "Limitation"], ...papers.map((pp) => [String(pp.n), `${pp.title.split(":")[0]} (${pp.year})`, pp.technique, pp.short[0], pp.short[1]])], [600, 3000, 1900, 2100, 2000], { size: 17 }));
ch2.push(caption("Table 2.1: Comparison of surveyed literature"));
ch2.push(p("The surveyed methods are mature individually; none is applied together to bank-statement data against the rule systems banks actually run, none builds classification, segmentation, forecasting and anomaly flags on one pipeline, none is deployed beside a consumer-protection rule engine, and no public labelled statement dataset exists. Bank IQ addresses each: a documented labelled generator, a side-by-side evaluation against the regex baseline with per-class gains, customer-level analytics with grouped cross-validation, and a deployed dashboard with a clear rule that models inform and rules decide."));

// ------------------------------------------------------------------ 3
const ch3 = [
  h1("3. System Analysis"),
  h2("3.1 Existing System"),
  p("Vasool Raja's classify.py assigns a kind (CHARGE, ATM, REVERSAL, INTEREST, DEBIT, CREDIT …) and a channel (UPI, POS, ATM, NEFT …) to each transaction with regular expressions, then runs the rulebook. Mapped to the ten ML categories (bankiq/rulemap.py), it reaches " + pc(RB.accuracy) + " accuracy on the labelled test set. It cannot improve from examples, has no notion of a customer's behaviour, trend or expected spend, and is not evaluated."),
  ...bullets(["Silent on the long tail: merchant-only lines, abbreviations and OCR noise fall to UNKNOWN or the wrong class.", "No customer-level analytics: no segment, forecast or anomaly flag.", "Every new bank format needs a new regex; no measured accuracy."]),
  h2("3.2 Proposed System"),
  p("Bank IQ adds a package bankiq/ beside the untouched engine: a labelled dataset generator, a feature module, six experiment scripts, an intelligence service, an API router and an Intelligence screen. The engine's parsers feed both the rulebook and the ML layer; the dashboard shows the two classifications side by side and never lets the model file a claim."),
  h2("3.3 Feasibility"),
  p("Technical: scikit-learn covers every model; the full experiment suite runs in about 25 minutes on two CPU cores and the service answers a 300-line statement in under a second. Operational: the layer is pure Python with no external service; models are joblib files loaded once. Economic: open-source stack, laptop hardware."),
  h2("3.4 Requirements"),
  table([["Type", "Requirement"], ["Functional", "Generate dataset; featurise; train and evaluate classifiers, ensembles, regressors, clusterers, PCA, LWR; analyse a statement (file or stored account) → categories, panel, segment, forecast, anomalies, insights; dashboard; model card"],
    ["Non-functional", "Reproducible (fixed seeds, one command); honest evaluation (held-out test, grouped CV, hidden archetype for clustering); explainable outputs; Tamil/English UI; no change to the rule engine"],
    ["Software", "Python 3.10+, scikit-learn 1.4+, pandas, NumPy, SciPy, matplotlib, joblib, FastAPI, pytest, Jupyter, Docker"], ["Hardware", "Any laptop; 2 cores, 4 GB RAM"]], [2000, 7600], { size: 18 }),
  caption("Table 3.1: Requirements"),
];

// ------------------------------------------------------------------ 4
const ch4 = [
  h1("4. System Design"),
  h2("4.1 Architecture"),
  ...code(["Statement (CSV / PDF / passbook photo)", "  └─ vasool.parsers ──► transaction lines (date, narration, debit, credit, balance)",
    "       ├─ RULE ENGINE (unchanged): classify (regex) → twin → 19 RBI rules → findings → evidence pack → guardian → case",
    "       └─ INTELLIGENCE LAYER (bankiq/):",
    "            features.py   clean narration → TF-IDF word(1-2) + char_wb(3-5) + 9 numeric features",
    "                          month_panel (customer-month, 34 features) · customer_profile (14 features)",
    "            service.py    ML category (+ rule category) → category mix → monthly panel → K-Means segment",
    "                          → next-month forecast (Gradient Boosting) → anomaly z-scores → insights",
    "            api/ml.py     GET /api/ml/status · /results · /figures/{png}   POST /api/ml/analyze · /analyze-json",
    "                          GET /api/accounts/{id}/intelligence (session-protected)",
    "            web           #/intelligence dashboard (vanilla JS, Tamil / English)"]),
  caption("Figure 4.1: Architecture — the rule engine and the intelligence layer share the parsers"),
  h2("4.2 Module Design"),
  table([["Module", "Responsibility", "Key functions"],
    ["bankiq/data/generator.py", "Labelled synthetic dataset", "generate(n_customers, months), load(); templates T (regular) and H (long tail); ARCHETYPES; SEASON"],
    ["bankiq/features.py", "All features", "clean_narration, numeric_features, TransactionFeaturizer (fit/transform → sparse), month_panel, customer_profile"],
    ["bankiq/rulemap.py", "Regex baseline", "rule_category(narration, debit, credit) — Vasool Raja Kind/Channel → ten categories"],
    ["bankiq/experiments/*", "One script per concept", "eda, classification, ensembles, regression, clustering, pca_lwr, run_all → results/*.json, figures, models"],
    ["bankiq/models_lwr.py", "From scratch", "LocallyWeightedRegression(tau).fit/predict, rmse"],
    ["bankiq/service.py", "Inference", "models() (lazy joblib), classify (+ direction mask), analyze(rows), results_summary()"],
    ["bankiq/api/ml.py", "HTTP", "router (/api/ml, public) and account_router (/api/accounts/{id}/intelligence, session)"],
    ["web/static/app.js", "UI", "screenIntel / bindIntel / renderIntel / renderModelCard; i18n keys intel.*"]], [2400, 2600, 4600], { size: 17 }),
  caption("Table 4.1: Modules"),
  h2("4.3 Data Design"),
  p("transactions.csv: customer_id, date, narration, debit, credit, balance, bank, category, archetype. customers.csv: customer_id, bank, archetype, monthly_income, opening_balance, has_emi. The customer-month panel adds spend, prev_spend, income, credits, n_txn, n_debit, avg_debit, max_debit, end/min balance, month_idx, next_month (+sin/cos), amt_<category> × 10, n_<category> × 10 and the target next_spend. The customer profile holds monthly_spend, monthly_income, txn_per_month, avg_txn, upi/card/atm/transfer share, charges and refunds per month, has_emi, avg and min balance, spend_income_ratio."),
  h2("4.4 API Design"),
  table([["Endpoint", "Auth", "Returns"], ["GET /api/ml/status", "public", "available flag, model files"], ["GET /api/ml/results", "public", "every results/*.json + figure list (model card)"], ["GET /api/ml/figures/{name}.png", "public", "experiment figure"],
    ["POST /api/ml/analyze (multipart file)", "public", "parse with vasool.parsers → full analysis"], ["POST /api/ml/analyze-json {rows}", "public", "analysis of already-parsed rows"], ["GET /api/accounts/{id}/intelligence", "session; owner only", "analysis of the stored account history"]], [3600, 1700, 4300], { size: 18 }),
  caption("Table 4.2: Endpoints"),
  h2("4.5 User Interface Design"),
  p("The Intelligence screen follows the app's existing screen/bind pattern and i18n dictionary. Top to bottom: source selector (my account / upload / sample buttons); five KPI tiles (transactions and period, total debits and income, charges and refunds, segment, forecast vs naive); business insights; category bars with ML labels; an inline-SVG monthly income-vs-spend chart; the behavioural profile table; the unusual-debits table; every line with its ML category, confidence and the rule's category, with a “show disagreements only” filter; and a collapsible model card that renders the experiment tables and figures from /api/ml/results."),
];

// ------------------------------------------------------------------ 5
const ch5 = [
  h1("5. Implementation"),
  h2("5.1 Technology Stack"),
  table([["Layer", "Technology", "Role"], ["Language", "Python 3.11, JavaScript (no build step)", "Backend and UI"], ["Data", "pandas, NumPy", "Generator, panel, profile"],
    ["Text", "TfidfVectorizer (word 1–2, token [A-Z0-9]+; char_wb 3–5), TruncatedSVD", "Narration features"],
    ["Models", "scikit-learn 1.4+: LogisticRegression, ComplementNB, DecisionTree*, KNeighbors*, Bagging, RandomForest*, AdaBoost, HistGradientBoosting, Linear/Ridge/Lasso, PolynomialFeatures, GradientBoostingRegressor, KMeans, AgglomerativeClustering, PCA", "All syllabus models"],
    ["From scratch", "NumPy", "Locally weighted regression"], ["Evaluation", "StratifiedKFold, GroupKFold, metrics, SciPy dendrogram, matplotlib", "Metrics and 15 figures"],
    ["Serving", "joblib, FastAPI, Uvicorn", "Models, API"], ["Engineering", "pytest, Docker, Makefile, Jupyter", "Tests, deployment, notebooks"]], [1700, 5000, 2900], { size: 17 }),
  caption("Table 5.1: Technology stack"),
  h2("5.2 Project Structure"),
  ...code(["bankiq/            data/generator.py · features.py · rulemap.py · models_lwr.py · service.py · api/ml.py", "                   experiments/ eda · classification · ensembles · regression · clustering · pca_lwr · run_all",
    "notebooks/         01_eda … 07_service_demo      results/ *.json + figures/fig1–15      models/ *.joblib", "tests/test_intelligence.py (13 tests)      docs/ (this report, Phase I, literature summary, slides, viva)",
    "vasool/ api/main.py web/   the Vasool Raja engine, API and UI (unchanged except the mounted router and the new screen)"]),
  h2("5.3 Key Code"),
  h3("Narration cleaning and features (bankiq/features.py)"),
  ...code(["s = _LD.sub(\" \", s.upper())            # JAN26 -> JAN 26 ; 4123XXXX7710 -> 4123 XXXX 7710", "s = _NUM.sub(\" NUM \", s)               # any 2+ digit run -> one token: reference numbers carry no meaning",
    "self.word = TfidfVectorizer(ngram_range=(1, 2), token_pattern=r\"[A-Z0-9]+\", min_df=2, sublinear_tf=True)", "self.char = TfidfVectorizer(analyzer=\"char_wb\", ngram_range=(3, 5), min_df=3, sublinear_tf=True, max_features=20000)",
    "X = sparse.hstack([self.word.transform(txt), self.char.transform(txt), sparse.csr_matrix(self.scaler.transform(num))])"]),
  h3("Honest cross-validation (bankiq/experiments/classification.py, regression.py)"),
  ...code(["cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)              # classifiers", "cvr = cross_validate(model, Xtr, ytr, cv=cv, scoring=[\"accuracy\", \"f1_macro\"])   # on the training split only",
    "gkf = GroupKFold(n_splits=5); cross_validate(m, Xtr, ytr, cv=gkf, groups=customer_ids)   # regression: no customer in two folds"]),
  h3("Locally weighted regression (bankiq/models_lwr.py)"),
  ...code(["w = np.exp(-((self.x_ - x0) ** 2) / (2 * self.tau ** 2))       # Gaussian kernel weights", "theta = np.linalg.solve(XtW @ X + self.ridge * np.eye(2), XtW @ self.y_)   # weighted least squares at x0", "return theta[0] + theta[1] * x0"]),
  h3("Direction constraint at inference (bankiq/service.py)"),
  ...code(["mask = credit_line[:, None] ? is_credit_category : is_debit_category    # a credit can only be a credit category", "proba = proba * mask / proba.sum(axis=1)                                  # renormalise, then argmax"]),
  h2("5.4 Configuration and Reproducibility"),
  p("All experiments use random_state = 42; `make data` regenerates the dataset, `make train` runs every experiment and writes results/*.json, results/figures and models/*.joblib; every table and figure in this report, the slides and the model card are generated from those files, never typed. `make test` runs the full suite (101 Vasool Raja tests + 13 intelligence tests). The Docker image trains the models at build time."),
];

// ------------------------------------------------------------------ 6
const cc = eda.category_counts;
const ch6 = [
  h1("6. Data Preprocessing and Exploratory Data Analysis"),
  h2("6.1 Dataset"),
  p(`No public labelled dataset of Indian bank narrations exists, so bankiq/data/generator.py builds one deterministically: ${n_cu} customers drawn from five archetypes (salaried 38%, pensioner 20%, student 15%, business 12%, low-activity 15%) across seven bank formats, 12 months of 2025 each, about ${n_tx.toLocaleString("en-IN")} lines in ten categories. Every line's label is the generating category — not a function of its narration — so the regex baseline can be measured honestly. 35% of lines use long-tail templates (merchant-only, bank-specific codes, unusual wording) and a noise step adds truncation, double spaces and stray reference codes. Monthly budgets follow a seasonal profile (festival season ×1.25, school fees ×1.15, year-start ×0.9) with an 8% chance of a one-off big-ticket month, and balances are kept plausible by scaling discretionary debits to the budget.`),
  table([["Category", "Share", "Example narrations"], ...CATS.map((c) => [PRETTY[c], cc[c] != null ? pc(cc[c] / Object.values(cc).reduce((a, b) => a + b, 0)) : "–", { UPI_PAYMENT: "UPI/DR/NUM/ZOMATO/SBI/zomato@ybl · PAYTM*SWIGGY · GPAY DMART", CARD_POS: "POS NUM NETFLIX CBE · ECOM PUR/AMAZON*IN · MYNTRA.COM", ATM_WITHDRAWAL: "ATM WDL CANARA CBE · NFS/ATM WDL/SBI … · CSH WDL", TRANSFER_OUT: "NEFT DR-RAVI KUMAR · IMPS/P2A/… · RENT PRIYA S", LOAN_EMI: "ACH D- BAJAJ FIN EMI · NACH DR TVS CREDIT", BANK_CHARGE: "CHRG MIN BAL NON MAINT · SMS ALERT CHRG · GST ON CHARGES · AMB SHORTFALL", INCOME_CREDIT: "SALARY-JAN25-ACME TECH · NEFT CR-PENSION-TN TREASURY · PAYROLL", TRANSFER_IN: "UPI/CR/…/APPA · BY TRANSFER-KUMAR S · CASH DEP", REFUND_REVERSAL: "REV/UPI/… · ATM WDL REV · CASHBACK AMAZON", INTEREST_CREDIT: "SB INT CREDIT · INT.PD:30-06-2025 · QTRLY INT" }[c]])], [2200, 1200, 6200], { size: 17 }),
  caption("Table 6.1: Categories, class share and example narrations"),
  h2("6.2 Preprocessing Steps"),
  ...numbered(["Narration cleaning: upper-case; split letter–digit boundaries (JAN26 → JAN 26); mask every run of two or more digits as NUM; collapse separators. Reference numbers, years and masked card digits become one token.",
    "Text features: word TF-IDF over 1–2-grams (token pattern [A-Z0-9]+, min_df 2, sublinear tf) and character-within-word-boundary TF-IDF over 3–5-grams (min_df 3, 20,000 max) — fitted on the training split only.",
    "Numeric features (9): amount, log amount, is_debit, is_round, day, weekday, month_end, has_paise, share of the customer-month total; standardised with a scaler fitted on train.",
    "Sparse horizontal stack → " + cls.n_features.toLocaleString("en-IN") + " features; TruncatedSVD(200) for the distance-based and boosted models.",
    "Customer-month panel: per customer and month, totals, counts, balances, per-category amounts and counts, calendar month of the month being predicted (as integer and sin/cos), target = next month's spend; last month of each customer dropped.",
    "Customer profile: 14 behavioural features per customer (median-month statistics), standardised; the 13 continuous ones are used for clustering and PCA; the hidden archetype is kept only for evaluation.",
    "Splits: 40,000-line stratified sample → 80/20 stratified split for classification; GroupShuffleSplit by customer (80/20) for regression; all 500 customers for clustering."]),
  h2("6.3 Exploratory Analysis"),
  ...fig("fig1_dataset", 600, 300, "Figure 6.1: Class balance, amount distributions and narration lengths"),
  ...fig("fig2_trends", 600, 240, "Figure 6.2: Monthly spend and income trends, seasonality by archetype"),
  ...fig("fig3_customer_profiles", 600, 260, "Figure 6.3: Customer profiles by archetype"),
  ...fig("fig4_panel_correlation", 520, 420, "Figure 6.4: Correlation of the customer-month panel features"),
  p("Observations: bank charges and interest credits are rare but many-templated; amounts span four orders of magnitude, so log-amount and is_round carry signal (ATM withdrawals are round, charges have paise); the festival months show the seasonal bump in every archetype; spend is strongly autocorrelated month to month, which is why the naive forecast is a serious baseline; UPI share and ATM share separate students and pensioners cleanly in the profile."),
];

// ------------------------------------------------------------------ 7
const ch7 = [
  h1("7. Model Building"),
  p("Seven model families are built under one evaluation harness. Classifiers are scored with stratified 5-fold cross-validation on the training split and once on the held-out test split (accuracy, macro-F1, weighted-F1, per-class F1, confusion matrix); regressors with GroupKFold(5) by customer (R², RMSE, MAE, MAPE); clusterers with inertia, silhouette and ARI against the hidden archetype."),
  table([["Concept", "Models", "Features", "Selection"],
    ["Classification", "Rule baseline; Logistic Regression (C=5, balanced); Complement NB (α=0.1, text only); Decision Tree (depth 30, balanced); kNN (k=7, cosine, distance-weighted)", "sparse TF-IDF + numeric; SVD-200 for kNN", "k ∈ {1,3,7,15,31}; depth ∈ {5,10,20,30,50,∞}"],
    ["Ensembles", "Bagging (50 trees, 80% rows, 50% features); Random Forest (200, balanced_subsample); AdaBoost (30 × depth-2); HistGradientBoosting (100 iters, depth 6)", "sparse for trees; SVD-200 for boosting", "macro-F1"],
    ["Regression", "Naive; Linear; Ridge (α=1); Lasso (α=10); Polynomial-2 + Ridge (α=50); Decision Tree (depth 8); Random Forest (300, depth 12); Gradient Boosting (400, depth 3, lr 0.05)", "34 panel features", "CV R²; test R²"],
    ["Clustering", "K-Means (n_init 10) and Ward, k = 2…8", "13 standardised continuous profile features", "silhouette plateau → smallest k; elbow; ARI"],
    ["Dimensionality reduction", "PCA on profiles; TruncatedSVD 10…200 on text", "profiles; TF-IDF", "explained variance; downstream F1"],
    ["LWR", "Gaussian kernel, τ ∈ {2,5,10,25,60} vs linear and cubic", "monthly income → spend", "test RMSE"]], [1700, 4300, 1900, 1700], { size: 16 }),
  caption("Table 7.1: Model inventory"),
  h2("7.1 Design Decisions"),
  ...bullets(["Character n-grams, not only words: narrations are abbreviated and truncated; char_wb 3–5-grams are what make LOAN INST, NACH DR and ACH D- look alike.", "Complement NB instead of Gaussian NB: the features are TF-IDF counts and the classes are imbalanced — exactly the case Rennie et al. address; it runs on the non-negative text block only.",
    "kNN on SVD-200 with cosine distance: Euclidean distance on 2,800 sparse dimensions is meaningless; the projection makes neighbours meaningful and prediction fast.", "class_weight='balanced' for the linear and tree models so that rare charge and interest classes are not sacrificed for accuracy.",
    "GroupKFold by customer for regression: months of one customer are correlated; random folds would leak identity and inflate R².", "The hidden archetype is never a feature; it is used only to score the clusters. Profile statistics are medians over months and the binary has_emi flag is left out of the clustering features.", "A direction mask at inference: a credit line may only receive a credit category, which removes a class of impossible errors on real statements."]),
  h2("7.2 Training"),
  p(`Training times on two cores: Logistic Regression ${cls.models["Logistic Regression"].fit_seconds}s (incl. CV), Decision Tree ${cls.models["Decision Tree"].fit_seconds}s, kNN ${cls.models["kNN (k=7, SVD-200)"].fit_seconds}s, Random Forest ${ens.models["Random Forest (200)"].fit_seconds}s, Bagging ${ens.models["Bagging (50 trees)"].fit_seconds}s, HistGradientBoosting ${ens.models["Gradient Boosting (SVD-200)"].fit_seconds}s, Gradient Boosting regressor ${rbest.fit_seconds}s. Saved models: txn_classifier_logreg (deployed classifier), txn_classifier_rf, txn_classifier_gb, spend_regressor (deployed forecaster), segments_kmeans (deployed segmenter), txn_svd.`),
];

// ------------------------------------------------------------------ 8
const clsNames = Object.keys(cls.models), ensNames = Object.keys(ens.models), regNames = Object.keys(reg.models);
const ch8 = [
  h1("8. Testing, Results and Analysis"),
  h2("8.1 Software Testing"),
  p("tests/test_intelligence.py adds 13 pytest cases to the 101 existing ones: generator determinism and label sanity, narration masking, featurizer shape, panel and profile invariants, rule mapping, LWR exactness on a straight line, end-to-end service accuracy above 90% against ground truth, the public /api/ml endpoints, bad-upload rejection (415), and the account endpoint returning 401/404 without a session. All 114 pass."),
  h2("8.2 Evaluation Protocol"),
  p("Classifiers: stratified 80/20 split of a 40,000-line stratified sample; stratified 5-fold CV on the training 32,000 for model and hyperparameter comparison; the 8,000-line test split scored once. Regressors: GroupShuffleSplit by customer (80/20), GroupKFold(5) on the training customers. Clustering: all customers; silhouette and inertia for k; ARI against the hidden archetype and between algorithms. Nothing in the test split touches training, scaling or vocabulary."),
  h2("8.3 Concept 2 – Classification: Decision Tree, Naive Bayes, kNN (and the rule baseline)"),
  table([["Model", "CV accuracy", "Test accuracy", "Macro-F1", "Weighted-F1"], ...clsNames.map((n) => [n, cls.models[n].cv_accuracy == null ? "–" : `${pc(cls.models[n].cv_accuracy)} ± ${pc(cls.models[n].cv_accuracy_std)}`, pc(cls.models[n].accuracy), f3(cls.models[n].f1_macro), f3(cls.models[n].f1_weighted)])], [3000, 2000, 1700, 1500, 1400], { size: 18 }),
  caption("Table 8.1: Transaction classification (test split; CV on train)"),
  ...fig("fig5_classification", 600, 190, "Figure 8.1: Rule baseline vs ML classifiers; per-class F1 where ML learns what the rules miss"),
  ...fig("fig6_confusion", 560, 235, "Figure 8.2: Row-normalised confusion matrices — rules vs " + best),
  ...fig("fig7_sweeps", 560, 180, "Figure 8.3: kNN k sweep and Decision Tree depth vs over-fitting"),
  table([["Category", "Rule F1", best + " F1", "Gain"], ...CATS.map((c) => [PRETTY[c], f3(RB.per_class_f1[c]), f3(cls.models[best].per_class_f1[c]), (cls.ml_gain_over_rules_per_class[c] >= 0 ? "+" : "") + f3(cls.ml_gain_over_rules_per_class[c])])], [3000, 2000, 2600, 2000], { size: 18 }),
  caption("Table 8.2: Per-class F1 — where the learned model gains over the rules"),
  p(`The rule baseline is perfect on familiar formats and collapses on the long tail: ${pc(RB.accuracy)} accuracy, with its lowest F1 on ${CATS.map((c) => [c, RB.per_class_f1[c]]).sort((a, b) => a[1] - b[1]).slice(0, 2).map((x) => PRETTY[x[0]].toLowerCase()).join(" and ")}. Logistic Regression on the full sparse features is the best single model (${pc(cls.models["Logistic Regression"].accuracy)}, macro-F1 ${f3(cls.models["Logistic Regression"].f1_macro)}) and is the one deployed. Complement NB is the fastest (${cls.models["Naive Bayes (Complement)"].fit_seconds}s) at ${pc(cls.models["Naive Bayes (Complement)"].accuracy)}; the Decision Tree reaches ${pc(cls.models["Decision Tree"].accuracy)} but its training F1 keeps rising with depth while CV F1 plateaus (Figure 8.3); kNN only works once the sparse matrix is projected to 200 SVD dimensions with cosine distance — there it reaches ${pc(cls.models["kNN (k=7, SVD-200)"].accuracy)} — and the k sweep shows the usual bias–variance curve; Complement NB is the weakest learner because its independence assumption cannot combine the word, character and numeric evidence.`),
  h3("A check on real statement formats"),
  p(`The synthetic test split cannot reveal distribution shift, so the app's sample statements — ${cls.sample_statement_check.n_lines} lines in real HDFC, Canara, SBI and Indian Bank formats, written for the regex engine, so the rule category is a trustworthy reference there — are used as a tiny out-of-distribution check. It exposed one design flaw: with the nine standardised numeric columns at full weight next to unit-norm TF-IDF rows, logistic regression leaned on amount habits of the generator (salaries are never round numbers, charges are small) and agreed with the rules on only ${pc(cls.sample_statement_check.num_weight_sweep_logreg["1.0"])} of the sample lines; down-weighting the numeric block to 0.1 raised agreement to ${pc(cls.sample_statement_check.num_weight_sweep_logreg["0.1"])} at no cost on the synthetic test split, and is the value deployed.`),
  table([["Numeric-block weight", "Logistic agreement with rules on sample statements"], ...Object.entries(cls.sample_statement_check.num_weight_sweep_logreg).map(([w, v]) => [w, pc(v)])], [3500, 5000], { size: 18 }),
  caption("Table 8.2b: Choosing the numeric-block weight on real-format statements"),
  h2("8.4 Concept 5 – Ensemble Learning"),
  table([["Model", "CV accuracy", "Test accuracy", "Macro-F1", "Fit (s)"], ...ensNames.map((n) => [n, `${pc(ens.models[n].cv_accuracy)} ± ${pc(ens.models[n].cv_accuracy_std)}`, pc(ens.models[n].accuracy), f3(ens.models[n].f1_macro), String(ens.models[n].fit_seconds)])], [3000, 2000, 1700, 1500, 1400], { size: 18 }),
  caption("Table 8.3: Single tree vs ensembles (20,000-line sample)"),
  ...fig("fig8_ensembles", 600, 190, "Figure 8.4: Ensembles vs single tree; Random Forest's most important n-grams"),
  p(`Bagging lifts the single tree from ${pc(ens.models["Decision Tree (single)"].accuracy)} to ${pc(ens.models["Bagging (50 trees)"].accuracy)} by averaging out its variance; Random Forest, which also de-correlates the trees, reaches ${pc(ens.models["Random Forest (200)"].accuracy)} (macro-F1 ${f3(ens.models["Random Forest (200)"].f1_macro)}) — the best ensemble (${ensBest}). HistGradientBoosting on the SVD features reaches ${pc(ens.models["Gradient Boosting (SVD-200)"].accuracy)}; AdaBoost with depth-2 stumps is the weakest (${pc(ens.models["AdaBoost (30, SVD-200)"].accuracy)}) and slowest per unit of accuracy on a ten-class problem. The forest's top features are the tokens a human would pick — ${ens.rf_top_features.slice(0, 5).map((x) => x.feature).join(", ")} — which is why it is also easy to explain.`),
  h2("8.5 Concept 1 – Regression with Cross-Validation"),
  table([["Model", "CV R²", "Test R²", "RMSE", "MAE", "MAPE"], ...regNames.map((n) => [n, reg.models[n].cv_r2 == null ? "–" : `${f3(reg.models[n].cv_r2)} ± ${f3(reg.models[n].cv_r2_std)}`, f3(reg.models[n].r2), inr(reg.models[n].rmse), inr(reg.models[n].mae), pc(reg.models[n].mape)])], [2900, 1700, 1300, 1400, 1300, 1000], { size: 18 }),
  caption("Table 8.4: Next-month spend (customer-months; GroupKFold(5) by customer)"),
  ...fig("fig9_regression", 600, 190, "Figure 8.5: Model comparison and predicted vs actual for " + regBest),
  ...fig("fig10_regression_importance", 480, 265, "Figure 8.6: Gradient Boosting feature importance"),
  p(`Spend is sticky, so the naive forecast already explains ${pc(naive.r2)} of the variance; the linear family improves it to R² ${f3(reg.models["Linear Regression"].r2)} by combining this month's spend, income, EMI and category mix, and ${regBest} reaches ${f3(rbest.r2)} with RMSE ${inr(rbest.rmse)} — ${Math.round(100 * (1 - rbest.rmse / naive.rmse))}% below the naive error. Ridge and Lasso coincide with ordinary least squares because 4,400 rows comfortably support 34 coefficients; the polynomial expansion over-fits slightly; the single tree is the weakest learner. The importances explain the ordering: previous and current spend dominate (${Math.round(100 * (imp0[0][1] + imp0[1][1]))}% of the importance together), then the income credits of the month and the category mix; the calendar-month features carry little weight because one year of data lets every customer's seasonal months be seen only once — which is why the gain over the linear family is modest and why multi-year data is first in the future scope.`),
  h2("8.6 Concept 3 – Clustering: K-Means vs Hierarchical"),
  table([["k", "Inertia", "Silhouette K-Means", "Silhouette Ward", "ARI K-Means", "ARI Ward"], ...clu.k_range.map((k) => [String(k), Math.round(clu.kmeans_inertia[k]).toLocaleString("en-IN"), f3(clu.kmeans_silhouette[k]), f3(clu.ward_silhouette[k]), f3(clu.ari_vs_archetype_kmeans[k]), f3(clu.ari_vs_archetype_ward[k])])], [800, 1500, 2000, 1800, 1800, 1700], { size: 18 }),
  caption("Table 8.5: Choosing k (ARI against the hidden customer archetype)"),
  ...fig("fig11_cluster_selection", 600, 160, "Figure 8.7: Elbow, silhouette and ARI across k"),
  ...fig("fig12_dendrogram_segments", 600, 205, "Figure 8.8: Ward dendrogram and K-Means segments in PCA space"),
  table([["Segment", "Size", "Median spend / month", "Median income", "Txns / month", "UPI share", "ATM share", "Has EMI", "Dominant archetype"], ...seg.map((s) => [s.segment, `${s.size} (${pc(s.share)})`, inr(s.monthly_spend), inr(s.monthly_income), f2(s.txn_per_month), pc(s.upi_share), pc(s.atm_share), pc(s.has_emi), s.dominant_archetype])], [1700, 900, 1300, 1200, 900, 800, 800, 800, 1200], { size: 15 }),
  caption("Table 8.6: Segment profiles at k = " + bk),
  ...fig("fig13_segment_profiles", 600, 165, "Figure 8.9: Segment profiles"),
  p(`K-Means silhouette rises to a plateau at k = ${clu.silhouette_plateau[0]}–${clu.silhouette_plateau[clu.silhouette_plateau.length - 1]} (values within 0.005 of each other) and falls after it; the smallest k on the plateau is kept, k = ${bk}. At that k the two algorithms agree with ARI ${f2(clu.kmeans_vs_ward_ari)} and recover the generating archetypes with ARI ${f2(clu.ari_vs_archetype_kmeans[bk])} (K-Means) and ${f2(clu.ari_vs_archetype_ward[bk])} (Ward) without ever seeing them. Two feature decisions made this work: the per-customer statistics are medians over months, so one big-ticket month does not define a customer, and the binary has_emi flag is excluded from the clustering features because a standardised binary dominates Euclidean distance and split every segment in two. The segments are directly actionable: High-value / business (large, frequent, transfer-heavy), Regular salaried (EMIs, card and UPI), Cash-reliant (pensioners, ${pc(seg.find((s) => s.segment.startsWith("Cash"))?.atm_share || 0)} ATM share), Digital-first (students, ${pc(seg.find((s) => s.segment.startsWith("Digital"))?.upi_share || 0)} UPI share, no EMI) and Low-activity (few lines a month, the most charges per month, dormancy risk).`),
  h2("8.7 Concept 4 – Dimensionality Reduction"),
  ...fig("fig14_pca", 600, 160, "Figure 8.10: PCA on profiles; archetype recovery vs components; Truncated SVD on narrations"),
  table([["Components kept", "RF archetype F1", "kNN archetype F1"], ...pca.components_tested.map((c) => [String(c), f3(pca.performance[String(c)]["RF archetype F1"]), f3(pca.performance[String(c)]["kNN archetype F1"])])], [3000, 3000, 3000], { size: 18 }),
  caption("Table 8.7: Recovering the hidden customer type from the first principal components"),
  p(`PCA needs ${pca.n_components_95} of ${pca.n_features} components to retain 95% of the profile variance — the behavioural features are only mildly correlated — but a Random Forest on the first three components already recovers the archetype with F1 ${f3(pca.performance["3"]["RF archetype F1"])} against ${f3(pca.performance[String(pca.n_features)]["RF archetype F1"])} on all features: most of the segment signal lives in a 3-D subspace, which is what Figure 8.8 draws. On text, Truncated SVD of the ${cls.n_features.toLocaleString("en-IN")}-dimensional TF-IDF matrix keeps ${pc(pca.text_svd_sweep["100"].explained)} of the variance at 100 dimensions and a logistic model on it reaches macro-F1 ${f3(pca.text_svd_sweep["100"].logreg_f1)} against ${f3(pca.text_full_features_f1)} on the full matrix — dimensionality reduction buys speed for kNN and boosting at a small cost in accuracy.`),
  h2("8.8 Concept 6 – Locally Weighted Regression"),
  table([["Model", "Test RMSE (₹)"], ...Object.keys(lwr.models).map((n) => [n, inr(1000 * lwr.models[n].test_rmse_k)])], [4500, 3000], { size: 18 }),
  caption("Table 8.8: Monthly spend vs monthly income — global fits vs LWR by bandwidth"),
  ...fig("fig15_lwr", 600, 210, "Figure 8.11: Locally weighted regression (Gaussian kernel) against a global line; the bandwidth study"),
  p(`LWR re-fits a weighted least-squares line around every query income with weights exp(−(x−x₀)²/2τ²). The best bandwidth is ${lwr.best_lwr} (RMSE ${inr(1000 * lwr.models[lwr.best_lwr].test_rmse_k)} vs ${inr(1000 * lwr.models["Linear"].test_rmse_k)} for the global line): the spend–income relation is steeper for low incomes and flattens for high ones, which a single line cannot represent. Small τ follows noise in the sparse high-income tail; large τ converges to the global line — the bias–variance trade-off made visible.`),
  h2("8.9 Concept 7 – End-to-End Application"),
  p("service.analyze() runs the deployed classifier (with the direction constraint), builds the monthly panel and the profile, assigns the K-Means segment, forecasts next month with the Gradient Boosting regressor, flags debits whose log-amount is more than three MADs above their category median, and generates insights. On the four original sample statements — written for the regex engine — the classifier agrees with the rules on 99% of lines, which is the validation that it has not learned the generator's quirks. On the new long-tail sample (axis_kavya_longtail_2026.csv: merchant-only lines, bank codes, abbreviations) the two disagree on 30 of 41 lines, and it is the rules that fail: PAYROLL, BAJAJ FIN, SWIGGY CHENNAI, CSH WDL, CASHBACK AMAZON, QTRLY INT and DC ISSUANCE all fall to generic transfers for the regexes while the model assigns income, EMI, UPI, ATM, refund, interest and charge. Section 10 shows the screens."),
  h2("8.10 Limitations Observed"),
  ...bullets(["The dataset is synthetic; accuracy above 99% says the model has learned the generator's language, not that real statements would score the same. The sample-statement check (99% agreement with the rules on rule-friendly formats, after fixing the numeric-weight flaw it exposed) is the closest validation in this repo; real consented statements are the next step.",
    "The naive forecast is strong on stable accounts; the regression's gain is concentrated in seasonal months and accounts with irregular credits.", "The anomaly flag is statistical, not fraud detection.", "Models trained on one year cannot separate a calendar effect from a trend; two or more years would be needed."]),
];

// ------------------------------------------------------------------ 9
const ch9 = [
  h1("9. Result Analysis and Business Insights"),
  h2("9.1 Where the Money Goes — and Where the Rules Were Blind"),
  p(`Replacing the regex classifier with the learned one changes the category of roughly one line in four on the synthetic test set (${pc(1 - RB.accuracy)} rule error) and three in four on the long-tail sample statement, while leaving the rule-friendly statements untouched (99% agreement). The per-class gains (Table 8.2) tell a consistent story: the rules are weakest exactly where they were never written — transfers out (F1 ${f3(RB.per_class_f1.TRANSFER_OUT)}), loan EMIs (${f3(RB.per_class_f1.LOAN_EMI)}), UPI and card merchant lines (${f3(RB.per_class_f1.UPI_PAYMENT)}, ${f3(RB.per_class_f1.CARD_POS)}) — and strongest on bank charges (${f3(RB.per_class_f1.BANK_CHARGE)}) and refunds (${f3(RB.per_class_f1.REFUND_REVERSAL)}), the classes the rule engine was built to find. The model lifts every class to ${f3(Math.min(...Object.values(cls.models[best].per_class_f1)))} or better. For the product this means two things: the “where the money goes” view is now trustworthy for every line, and the charges the rule engine investigates still arrive — the dashboard lists ML-classified charges with a pointer to the Findings tab, and on the long-tail sample it recognises DC ISSUANCE and AMB SHORTFALL as charges the regexes filed as transfers.`),
  h2("9.2 Segments as Actions"),
  p("Cash-reliant pensioners withdraw at ATMs far more than other segments and Low-activity accounts carry the most charges per month: these are the groups RBI's free-ATM, minimum-balance and dormancy rules protect most, the group Bank IQ's guardian flow was designed for, and where reactivation charges — which RBI prohibits — are what to watch. Digital-first students have the highest UPI share and no EMI: their risks are failed-UPI reversals, not charges. High-value / business customers have the largest and most irregular flows, so their forecast intervals are widest and their anomaly flags least informative. Regular salaried customers carry the EMIs and are the natural audience for a spend forecast. A bank or a fintech would route service, alerts and products by these segments; a user sees which group their behaviour resembles."),
  h2("9.3 Expect Next Month"),
  p(`The forecast is presented beside the naive guess, with the model named, so the user sees both the number and how much the model adds. On the synthetic test set the model cuts error by ${Math.round(100 * (1 - rbest.rmse / naive.rmse))}%; its largest gains are in the months where behaviour changes — festival season, school-fee month — which the calendar features capture. In the insights the forecast is phrased as a range of expectation, not a promise.`),
  h2("9.4 Unusual Debits"),
  p("A robust z-score inside each ML category (log amount, median and MAD) flags debits more than three MADs above the category's own typical size. It is transparent — the insight says “4× the typical ATM withdrawal” — and category-aware: a ₹15,000 rent transfer is normal for transfers and abnormal for UPI payments. Flags are hints to look at the Findings tab, never claims."),
  h2("9.5 What Not to Trust"),
  ...bullets(["Accuracy near 100% on synthetic data; trust the per-class F1 ordering and the sample-statement disagreements more than the headline.", "Forecasts for accounts with fewer than three months of history; the panel is one row.", "Segment assignments for very short statements — the profile features are per-month averages and need several months.", "Any output as a claim: findings come only from the rule engine."]),
];

// ------------------------------------------------------------------ 10
const ch10 = [
  h1("10. Deployment and Demonstration"),
  h2("10.1 Running the System"),
  ...code(["pip install -r requirements-dev.txt", "make train                  # dataset + every experiment → results/, models/   (~25 min)", "python -m uvicorn api.main:app --port 8000      # http://localhost:8000 → Intelligence tab (VASOOL_AUTH=off for a local demo)",
    "python -m pytest -q         # 114 tests", "docker compose up --build   # image trains the models at build time (BANKIQ_SKIP_TRAIN=1 to mount models/ instead)"]),
  h2("10.2 Screens"),
  ...(fs.existsSync(path.join(REPO, "docs", "screenshots", "intelligence_top.png")) ? image(path.join(REPO, "docs", "screenshots", "intelligence_top.png"), 600, 400, "Figure 10.1: Intelligence dashboard — KPIs, insights, category mix, monthly chart") : []),
  ...(fs.existsSync(path.join(REPO, "docs", "screenshots", "intelligence_table.png")) ? image(path.join(REPO, "docs", "screenshots", "intelligence_table.png"), 600, 400, "Figure 10.2: Every line classified — ML category, confidence and the rule's category; unusual debits") : []),
  ...(fs.existsSync(path.join(REPO, "docs", "screenshots", "intelligence_modelcard.png")) ? image(path.join(REPO, "docs", "screenshots", "intelligence_modelcard.png"), 600, 400, "Figure 10.3: Model card — cross-validated tables and experiment figures served by the API") : []),
  h2("10.3 Demonstration Script (3 minutes)"),
  ...numbered(["Open Intelligence → Sample: hdfc priya salary 2026. Read the KPIs: debits, recognised income, charges found, segment, forecast vs naive; note the model and the rules agree on every line of a statement written for the rules.", "Scroll the insights: trend, biggest mover, largest outflow, charges pointer, savings rate, segment, forecast, anomalies, rule disagreements.",
    "Sample: axis kavya longtail 2026 → tick “show disagreements only”: 30 of 41 lines — PAYROLL, BAJAJ FIN, SWIGGY CHENNAI, CSH WDL, CASHBACK, QTRLY INT, DC ISSUANCE — are generic transfers to the rules and the right category to the model.", "Sample: canara amma pension 2026: five charges, the ₹50,000 college fee flagged as unusual.",
    "Open the model card: Table 8.1 live from results/classification.json; click Fig 5, Fig 11, Fig 15.", "Switch to Findings: the rule engine's claims on the same statement — rules decide."]),
];

// ------------------------------------------------------------------ 11
const ch11 = [
  h1("11. Conclusion and Future Scope"),
  h2("11.1 Conclusion"),
  p(`Bank IQ applies every technique in the machine-learning laboratory syllabus to one product and measures each against a meaningful baseline. The learned transaction classifier lifts accuracy from ${pc(RB.accuracy)} (regex) to ${pc(cls.models["Logistic Regression"].accuracy)} (Logistic Regression) and ${pc(ens.models["Random Forest (200)"].accuracy)} (Random Forest), with the largest gains on the transfer, EMI and merchant classes the rules were never written for; ensembles beat the single tree; the next-month forecast cuts the naive error by ${Math.round(100 * (1 - rbest.rmse / naive.rmse))}% under customer-grouped cross-validation; K-Means and Ward agree on ${bk} segments that recover the hidden customer types (ARI ${f2(clu.ari_vs_archetype_kmeans[bk])}); PCA shows the segment signal is three-dimensional; locally weighted regression exposes the non-linear spend–income relation. All of it is deployed as endpoints and a bilingual dashboard beside an untouched rule engine, reproducible from one command and covered by tests.`),
  h2("11.2 Future Scope"),
  ...bullets(["Validate and fine-tune on real, consented statements (Account Aggregator) with active learning on the lines where model and rules disagree.", "Multi-year histories to separate seasonality from trend; prediction intervals for the forecast.", "A feedback loop from the rule engine's confirmed findings back into the classifier's training data.", "Hindi and Tamil narration tokens; passbook OCR-specific character models.", "Isolation-Forest / contextual anomaly models once labelled anomaly data exists."]),
];

const refs = [h1("References"), ...papers.map((pp) => new Paragraph({ children: [run(`${pp.authors}, “${pp.title},” ${pp.venue}, ${pp.year}.`, { size: 20 })], numbering: { reference: "refs", level: 0 }, spacing: { after: 80 } })),
  ...["F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825–2830, 2011.", "Reserve Bank of India, Master Circular on Customer Service in Banks and related circulars cited in rulebook/rules.json, https://www.rbi.org.in/, 2026.", "Mad Angles (Nandana R, Naveen Kumar D, Nethra Devi R, Sandhru Duraisamy), “Vasool Raja — Regulatory Digital Twin for bank customers,” HackVerse 2.0, Karpagam College of Engineering, 2026.", "FastAPI Documentation, https://fastapi.tiangolo.com/, 2026."].map((t) => new Paragraph({ children: [run(t, { size: 20 })], numbering: { reference: "refs", level: 0 }, spacing: { after: 80 } })),
  pageBreak(),
  h1("Appendix A – Sample API Response"),
  ...code(["POST /api/ml/analyze  (file = hdfc_priya_salary_2026.csv)", "{", "  \"n_transactions\": 15, \"period\": {\"from\": \"2026-01-01\", \"to\": \"2026-03-28\", \"months\": 3},", "  \"totals\": {\"debits\": 59067, \"credits\": 191000, \"income\": 186000, \"charges\": 1298, \"refunds\": 5000},",
    "  \"categories\": [{\"category\": \"TRANSFER_OUT\", \"label\": \"Transfer out\", \"amount\": 50000, \"count\": 4, \"share\": 0.85}, ...],", "  \"segment\": {\"id\": 1, \"name\": \"Regular salaried\"},",
    "  \"forecast\": {\"model\": \"Gradient Boosting (400)\", \"naive\": 15649, \"next_month_spend\": 18204, \"based_on_month\": \"2026-03\"},", "  \"anomalies\": [...], \"rule_disagreements\": 3,",
    "  \"insights\": [{\"kind\": \"trend\", \"text\": \"Spend in 2026-03 was ₹15,649, 27% lower than 2026-02 (₹21,357).\"}, ...],", "  \"transactions\": [{\"date\": \"2026-01-01\", \"narration\": \"SALARY-JAN26-ACME TECH PVT LTD\", \"credit\": 62000, \"category\": \"INCOME_CREDIT\", \"confidence\": 0.99, \"rule_category\": \"INCOME_CREDIT\", \"agree\": true}, ...]", "}"]),
];

save(buildDoc([[...front, ...ch1, ...ch2, ...ch3, ...ch4, ...ch5, ...ch6, ...ch7, ...ch8, ...ch9, ...ch10, ...ch11, ...refs]], { title: "Bank IQ – Project Report", header: "Bank IQ – 22MDC56 Machine Learning Laboratory – Project Report" }), `${OUT}/BankIQ_Project_Report.docx`);
