const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const REPO = process.env.BIQ_REPO || "/home/claude/bank-iq";
const OUT = process.env.DV_OUT || "/home/claude/docs_build_biq/out";
const J = (n) => JSON.parse(fs.readFileSync(path.join(REPO, "results", n + ".json")));
const eda = J("eda"), reg = J("regression"), cls = J("classification"), clu = J("clustering"), pca = J("pca"), ens = J("ensembles"), lwr = J("lwr");
const FIG = (n) => path.join(REPO, "results", "figures", n + ".png");
const SHOT = (n) => path.join(REPO, "docs", "screenshots", n + ".png");
const f2 = (v) => Number(v).toFixed(2), f3 = (v) => Number(v).toFixed(3), pc = (v) => (100 * v).toFixed(1) + "%", inr = (x) => "₹" + Math.round(Number(x)).toLocaleString("en-IN");
const RB = cls.models["Rule-based (regex)"], LR = cls.models["Logistic Regression"], RF = ens.models["Random Forest (200)"], bk = clu.best_k, naive = reg.models["Naive (same as this month)"], rbest = reg.models[reg.best];
const PRETTY = { UPI_PAYMENT: "UPI", CARD_POS: "Card/POS", ATM_WITHDRAWAL: "ATM", TRANSFER_OUT: "Transfer out", LOAN_EMI: "Loan EMI", BANK_CHARGE: "Bank charge", INCOME_CREDIT: "Income", TRANSFER_IN: "Transfer in", REFUND_REVERSAL: "Refund", INTEREST_CREDIT: "Interest" };

const NAVY = "14301F", TEAL = "144C31", MINT = "4FBF8A", INK = "1B1B1B", MUTED = "5A6270", LIGHT = "EEF4EF", WHITE = "FFFFFF", GREEN = "1E8E3E", AMBER = "E8A000", RED = "D93025";
const HFONT = "Cambria", BFONT = "Calibri";
const pres = new pptxgen(); pres.layout = "LAYOUT_WIDE"; pres.title = "Bank IQ – Project Presentation";
const title = (s, t, o = {}) => s.addText(t, { x: 0.6, y: 0.35, w: 12.1, h: 0.8, fontFace: HFONT, fontSize: 30, bold: true, color: o.color || NAVY, isTextBox: true, margin: 0 });
const sub = (s, t) => s.addText(t, { x: 0.6, y: 1.1, w: 12.1, h: 0.4, fontFace: BFONT, fontSize: 14, color: MUTED, italic: true, isTextBox: true, margin: 0 });
const footer = (s, n) => s.addText(`Bank IQ · 22MDC56 Machine Learning Laboratory · ${n}`, { x: 0.6, y: 7.05, w: 12.1, h: 0.3, fontFace: BFONT, fontSize: 9, color: MUTED, isTextBox: true, margin: 0, align: "right" });
const body = (s, items, x, y, w, h, o = {}) => s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })), { x, y, w, h, fontFace: BFONT, fontSize: o.fontSize || 14, color: o.color || INK, isTextBox: true, margin: 0, valign: "top" });
const card = (s, x, y, w, h, head, text, o = {}) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: o.fill || LIGHT }, line: { color: o.fill || LIGHT }, rectRadius: 0.1 });
  if (o.icon) { s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: y + 0.2, w: 0.5, h: 0.5, fill: { color: o.iconFill || TEAL }, line: { color: o.iconFill || TEAL } }); s.addText(o.icon, { x: x + 0.2, y: y + 0.2, w: 0.5, h: 0.5, fontFace: BFONT, fontSize: 14, bold: true, color: WHITE, align: "center", valign: "middle", isTextBox: true, margin: 0 }); }
  s.addText(head, { x: x + (o.icon ? 0.8 : 0.2), y: y + 0.18, w: w - (o.icon ? 1.0 : 0.4), h: 0.5, fontFace: BFONT, fontSize: o.headSize || 15, bold: true, color: o.headColor || NAVY, isTextBox: true, margin: 0, valign: "middle" });
  s.addText(text, { x: x + 0.2, y: y + 0.75, w: w - 0.4, h: h - 0.9, fontFace: BFONT, fontSize: o.fontSize || 12, color: INK, isTextBox: true, margin: 0, valign: "top" });
};
const stat = (s, x, y, w, v, label, color = TEAL) => { s.addText(v, { x, y, w, h: 0.9, fontFace: HFONT, fontSize: 36, bold: true, color, isTextBox: true, margin: 0, align: "center" }); s.addText(label, { x, y: y + 0.9, w, h: 0.5, fontFace: BFONT, fontSize: 11, color: MUTED, isTextBox: true, margin: 0, align: "center" }); };
const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: TEAL } } });
const tbl = (s, rows, x, y, w, colW, o = {}) => s.addTable(rows, { x, y, w, colW, fontFace: BFONT, fontSize: o.fontSize || 11, color: INK, border: { type: "solid", color: "D5DDE5", pt: 0.75 }, rowH: o.rowH || 0.36, margin: 0.05, valign: "middle" });
let n = 0;

// 1 title
{ const s = pres.addSlide(); n++; s.background = { color: NAVY };
  s.addText("Bank IQ", { x: 0.8, y: 1.4, w: 11.7, h: 1.2, fontFace: HFONT, fontSize: 60, bold: true, color: WHITE, isTextBox: true, margin: 0 });
  s.addText("A Machine Learning Intelligence Layer for Bank-Statement Analytics — transaction classification, customer segmentation and spend forecasting on a Regulatory Digital Twin", { x: 0.8, y: 2.6, w: 11.7, h: 1.3, fontFace: BFONT, fontSize: 22, color: "CFE8D8", isTextBox: true, margin: 0 });
  s.addText("Rules decide. Models learn. Both shown side by side.", { x: 0.8, y: 3.95, w: 11.7, h: 0.5, fontFace: BFONT, fontSize: 16, italic: true, color: MINT, isTextBox: true, margin: 0 });
  s.addText([{ text: "22MDC56 Machine Learning Laboratory · Project Work", options: { breakLine: true } }, { text: "Sandhru D.  ·  Register No. ____________  ·  M.Sc. Decision and Computing Sciences, V Semester", options: { breakLine: true } }, { text: "Guide: ____________________  ·  Coimbatore Institute of Technology  ·  2026–27", options: {} }], { x: 0.8, y: 5.2, w: 11.7, h: 1.3, fontFace: BFONT, fontSize: 14, color: WHITE, isTextBox: true, margin: 0 });
  s.addNotes("One line: Bank IQ takes a bank statement, keeps the existing RBI rule engine, and adds a classical ML layer that categorises every line better than the regexes, segments the customer, forecasts next month and flags unusual debits — deployed as a dashboard."); }

// 2 problem
{ const s = pres.addSlide(); n++; title(s, "Problem identification"); sub(s, "A statement records everything and explains nothing — and the rule-based classifier cannot learn");
  card(s, 0.6, 1.7, 2.9, 2.4, "Categorise", "Which line is a charge, a refund, income? Today: regular expressions — exact on known formats, silent on the long tail.", { icon: "🏷" });
  card(s, 3.7, 1.7, 2.9, 2.4, "Segment", "Which customers behave alike? Today: nothing — the engine works line by line.", { icon: "👥" });
  card(s, 6.8, 1.7, 2.9, 2.4, "Forecast", "What will next month cost? Today: nothing.", { icon: "📈" });
  card(s, 9.9, 1.7, 2.8, 2.4, "Notice", "Which debit is unusual? Today: only what a rule names.", { icon: "🚩" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.4, w: 12.1, h: 2.3, fill: { color: WHITE }, line: { color: "D5DDE5", width: 1 }, rectRadius: 0.1 });
  s.addText("Problem statement", { x: 0.9, y: 4.55, w: 11.5, h: 0.4, fontFace: BFONT, fontSize: 14, bold: true, color: NAVY, isTextBox: true, margin: 0 });
  s.addText("Given the transaction lines of a bank account (date, narration, debit, credit, balance), build, compare and deploy classical ML models that classify each line into ten categories more accurately than the existing regex classifier, predict next-month spend, segment customers by behaviour, flag unusual debits explainably, and present the results as business insights inside the existing app — with the rule engine still the only thing that files a claim.", { x: 0.9, y: 4.95, w: 11.5, h: 1.3, fontFace: BFONT, fontSize: 12, color: INK, isTextBox: true, margin: 0 });
  s.addText(`Base: Vasool Raja (HackVerse 2.0, team Mad Angles) — parsers, digital twin, 19 RBI rules, Tamil/English app, 101 tests. Unchanged. Everything in bankiq/ is new.`, { x: 0.9, y: 6.2, w: 11.5, h: 0.4, fontFace: BFONT, fontSize: 11, italic: true, color: MUTED, isTextBox: true, margin: 0 });
  footer(s, n); s.addNotes("Make the baseline concrete: the regex classifier is measured at 72% on labelled data. That number is the villain of the story."); }

// 3 objectives
{ const s = pres.addSlide(); n++; title(s, "Objectives — one per syllabus concept"); sub(s, "All seven met, each against a baseline");
  const o = [["1 Regression + CV", "Next-month spend: Linear, Ridge, Lasso, Poly, DT, RF, GB — GroupKFold by customer; naive baseline"], ["2 DT · NB · kNN", "Transaction category (10 classes): + Logistic Regression; stratified 5-fold CV; regex baseline; per-class F1"], ["3 K-Means vs Ward", "Customer segments on 13 behavioural features — elbow, silhouette, dendrogram, ARI vs hidden type"],
    ["4 PCA / SVD", "PCA on profiles (variance, loadings, segment recovery); Truncated SVD on TF-IDF text"], ["5 Ensembles", "Bagging, Random Forest, AdaBoost, Gradient Boosting vs single tree; n-gram importances"], ["6 LWR (from scratch)", "Gaussian-kernel locally weighted regression of spend on income; bandwidth τ"]];
  o.forEach((c, i) => card(s, 0.6 + (i % 3) * 4.1, 1.65 + Math.floor(i / 3) * 2.2, 3.9, 2.0, c[0], c[1], { icon: String(i + 1), fontSize: 12 }));
  card(s, 0.6, 6.05, 12.1, 0.85, "7 End-to-end application", "FastAPI endpoints + Intelligence dashboard in the existing Tamil/English app: KPIs, insights, category mix, monthly chart, segment, forecast, anomalies, model card", { icon: "7", fontSize: 11, headSize: 13 });
  footer(s, n); s.addNotes("CO mapping if asked: CO1 techniques, CO2 compare by metrics, CO3 choose a model for the business, CO4 interpret, CO5 deploy with a front end."); }

// 4 literature
{ const s = pres.addSlide(); n++; title(s, "Literature survey — 16 references, one gap"); sub(s, "Text representation → learners → ensembles → non-parametric → clustering → evaluation → financial anomalies");
  tbl(s, [[hdr("Area"), hdr("Key references"), hdr("What we use")],
    ["Text features", "Salton & Buckley 1988 (TF-IDF); Cavnar & Trenkle 1994 (char n-grams); Rennie et al. 2003 (Complement NB)", "TF-IDF word 1–2 + char 3–5 grams; Complement NB"],
    ["Single learners", "Quinlan 1986 (trees); Cover & Hart 1967 (kNN)", "Decision Tree, kNN with sweeps"],
    ["Ensembles", "Breiman 1996, 2001; Freund & Schapire 1997; Friedman 2001", "Bagging, RF, AdaBoost, Gradient Boosting"],
    ["Non-parametric", "Cleveland 1979 (LOWESS)", "LWR from scratch"],
    ["Clustering + DR", "MacQueen 1967; Ward 1963; Rousseeuw 1987; Jolliffe & Cadima 2016", "K-Means, Ward, silhouette, PCA/SVD"],
    ["Evaluation / finance", "Kohavi 1995 (CV); Ahmed et al. 2016 (financial anomaly survey)", "Stratified & grouped CV; robust z-score flags"]], 0.6, 1.65, 12.1, [2.2, 6.0, 3.9], { fontSize: 11, rowH: 0.5 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.2, w: 12.1, h: 1.6, fill: { color: LIGHT }, line: { color: LIGHT }, rectRadius: 0.1 });
  s.addText("Gap", { x: 0.85, y: 5.3, w: 2, h: 0.4, fontFace: BFONT, fontSize: 14, bold: true, color: NAVY, isTextBox: true, margin: 0 });
  s.addText("Each paper studies one technique; none is applied to bank-statement data against the regex rule systems banks actually run; classification, segmentation, forecasting and anomaly flags are never built on one pipeline; nothing is deployed beside a consumer-protection rule engine; and no public labelled statement dataset exists. Bank IQ addresses all four.", { x: 0.85, y: 5.7, w: 11.6, h: 1.0, fontFace: BFONT, fontSize: 12, color: INK, isTextBox: true, margin: 0 });
  footer(s, n); s.addNotes("Ten of these are in the department-format summary; sixteen in the report."); }

// 5 architecture
{ const s = pres.addSlide(); n++; title(s, "System architecture"); sub(s, "The rule engine and the intelligence layer share the parsers; only the rule engine files claims");
  const steps = [["Statement", "CSV · PDF · passbook photo → vasool.parsers → lines"], ["Features", "clean narration → TF-IDF word + char n-grams + 9 numeric · customer-month panel (34) · customer profile (14)"], ["Models", "LogReg / NB / DT / kNN / RF / GB classifiers · 7 regressors · K-Means / Ward · PCA / SVD · LWR"], ["Service", "analyze(): categories (+ rule side by side) → mix → panel → segment → forecast → anomalies → insights"], ["App", "/api/ml/* + /api/accounts/{id}/intelligence · Intelligence screen (Tamil/English) · model card"]];
  steps.forEach((c, i) => { card(s, 0.6 + i * 2.45, 1.7, 2.3, 2.6, c[0], c[1], { icon: String(i + 1), fontSize: 10.5, headSize: 13 }); if (i < 4) s.addText("→", { x: 2.85 + i * 2.45, y: 2.7, w: 0.3, h: 0.5, fontSize: 20, color: TEAL, bold: true, isTextBox: true, margin: 0 }); });
  card(s, 0.6, 4.6, 5.9, 2.2, "Rule engine (unchanged)", "classify (regex) → twin → 19 RBI rules → findings → evidence pack → guardian → case. The ML layer never creates a finding.", { icon: "⚖", iconFill: NAVY, fontSize: 12 });
  card(s, 6.8, 4.6, 5.9, 2.2, "Reproducible", "make train → results/*.json, 15 figures, 6 joblib models (~25 min). Every table in the report, slides and model card is generated, not typed. 114 tests.", { icon: "✓", iconFill: GREEN, fontSize: 12 });
  footer(s, n); s.addNotes("Emphasise separation of duties: models describe and predict; rules decide."); }

// 6 dataset
{ const s = pres.addSlide(); n++; title(s, "Dataset and preprocessing"); sub(s, `${eda.rows.toLocaleString("en-IN")} labelled lines · ${eda.customers} customers × ${eda.months} months · 10 categories · 5 hidden archetypes`);
  s.addImage({ path: FIG("fig1_dataset"), x: 0.6, y: 1.6, w: 7.2, h: 3.6 });
  body(s, ["No public labelled statement data (personal data) → documented, deterministic generator; label = generating category, never a function of the narration", "35% long-tail narrations + noise (truncation, codes) — where regexes fail", "Seasonality (festival ×1.25, school fees ×1.15) + one-off big-ticket months", "Cleaning: letter–digit split, mask ≥2-digit runs → NUM", `TF-IDF word 1–2 + char_wb 3–5 + 9 numeric → ${cls.n_features.toLocaleString("en-IN")} sparse features; SVD-200 for kNN / boosting`, "Customer-month panel (34 features, target = next spend); 14-feature profile"], 8.0, 1.6, 4.7, 5.2, { fontSize: 11.5 });
  footer(s, n); s.addNotes("Be explicit: synthetic but honest — labels independent of narration, so the regex baseline can be measured."); }

// 7 EDA
{ const s = pres.addSlide(); n++; title(s, "Exploratory data analysis"); sub(s, "Spend is sticky and seasonal; UPI and ATM shares separate customer types; charges are rare but many-templated");
  s.addImage({ path: FIG("fig2_trends"), x: 0.6, y: 1.6, w: 7.4, h: 2.75 });
  s.addImage({ path: FIG("fig3_customer_profiles"), x: 0.6, y: 4.4, w: 7.4, h: 2.5 });
  body(s, [`${pc(eda.debit_share)} of lines are debits; UPI is the most frequent category, bank charges and interest the rarest`, "Amounts span 4 orders of magnitude → log amount, is_round, has_paise carry signal", "Monthly spend autocorrelated → naive forecast is a serious baseline", "Festival-season bump in every archetype → calendar features", "Students: UPI-heavy; pensioners: ATM-heavy; business: large transfers"], 8.2, 1.6, 4.5, 5.2, { fontSize: 12 });
  footer(s, n); s.addNotes("Point at the seasonal bump: that's what makes regression beyond naive worthwhile."); }

// 8 classification
{ const s = pres.addSlide(); n++; title(s, "Concept 2 · DT, Naive Bayes, kNN vs the regex baseline"); sub(s, "Stratified 5-fold CV on 32,000 train lines · 8,000 held-out · 10 classes · macro-F1 drives selection");
  const rows = [[hdr("Model"), hdr("CV acc"), hdr("Test acc"), hdr("Macro-F1")], ...Object.entries(cls.models).map(([k, m]) => [k, m.cv_accuracy == null ? "–" : pc(m.cv_accuracy), pc(m.accuracy), f3(m.f1_macro)])];
  tbl(s, rows, 0.6, 1.6, 5.6, [2.9, 0.9, 0.9, 0.9], { fontSize: 10.5, rowH: 0.36 });
  s.addImage({ path: FIG("fig5_classification"), x: 6.4, y: 1.6, w: 6.3, h: 2.0 });
  s.addImage({ path: FIG("fig7_sweeps"), x: 6.4, y: 3.7, w: 6.3, h: 2.0 });
  body(s, [`Regex rules: ${pc(RB.accuracy)} — perfect on known formats, blind on the long tail (lowest F1: ${cls.class_order.map((c) => [c, RB.per_class_f1[c]]).sort((a, b) => a[1] - b[1]).slice(0, 2).map((x) => PRETTY[x[0]]).join(", ")})`, `Logistic Regression ${pc(LR.accuracy)} / macro-F1 ${f3(LR.f1_macro)} — deployed`, `Complement NB ${pc(cls.models["Naive Bayes (Complement)"].accuracy)} in ${cls.models["Naive Bayes (Complement)"].fit_seconds}s (fastest, weakest) · tree ${pc(cls.models["Decision Tree"].accuracy)} · kNN ${pc(cls.models["kNN (k=7, SVD-200)"].accuracy)} on SVD-200 + cosine`], 0.6, 4.2, 5.6, 2.6, { fontSize: 11 });
  footer(s, n); s.addNotes("Why Complement NB: TF-IDF counts and imbalanced classes. Why kNN on SVD: Euclidean distance in 2,800 sparse dims is meaningless."); }

// 9 confusion
{ const s = pres.addSlide(); n++; title(s, "Where the learned model gains"); sub(s, "Row-normalised confusion: rules vs best model — the rules fail where they were never written (transfers, EMIs, merchant lines)");
  s.addImage({ path: FIG("fig6_confusion"), x: 0.6, y: 1.55, w: 8.3, h: 3.5 });
  const g = cls.ml_gain_over_rules_per_class; const top = Object.entries(g).sort((a, b) => b[1] - a[1]).slice(0, 5);
  tbl(s, [[hdr("Category"), hdr("Rule F1"), hdr("ML F1"), hdr("Gain")], ...top.map(([c, v]) => [PRETTY[c], f3(RB.per_class_f1[c]), f3(cls.models[cls.best].per_class_f1[c]), "+" + f3(v)])], 9.1, 1.55, 3.6, [1.4, 0.75, 0.75, 0.7], { fontSize: 10.5, rowH: 0.36 });
  body(s, [`Rules: weakest on transfers out (F1 ${f3(RB.per_class_f1.TRANSFER_OUT)}), EMIs, UPI/card merchant lines; strongest on charges (${f3(RB.per_class_f1.BANK_CHARGE)}) — what they were built for. Model: every class ≥ ${f3(Math.min(...Object.values(cls.models[cls.best].per_class_f1)))}`, "Rule-friendly sample statements: 99% agreement (validation). Long-tail sample (merchant-only, bank codes): 30 of 41 lines differ and the rules are the ones that fail — PAYROLL, BAJAJ FIN, SWIGGY CHENNAI, CSH WDL, QTRLY INT all become generic transfers", `Real-format check: ${cls.sample_statement_check.n_lines} sample-statement lines → numeric block down-weighted to 0.1 (agreement with rules ${pc(cls.sample_statement_check.num_weight_sweep_logreg["1.0"])} → ${pc(cls.sample_statement_check.num_weight_sweep_logreg["0.1"])}); direction mask: a credit line can only be a credit category`], 0.6, 5.2, 12.1, 1.7, { fontSize: 12 });
  footer(s, n); s.addNotes("This slide is the business case for ML: better recall on charges feeds the rule engine's core purpose."); }

// 10 ensembles
{ const s = pres.addSlide(); n++; title(s, "Concept 5 · Ensemble learning"); sub(s, `Bagging · Random Forest · AdaBoost · Gradient Boosting vs one tree · best: ${ens.best}`);
  const rows = [[hdr("Model"), hdr("CV acc"), hdr("Test acc"), hdr("Macro-F1"), hdr("Fit s")], ...Object.entries(ens.models).map(([k, m]) => [k, pc(m.cv_accuracy), pc(m.accuracy), f3(m.f1_macro), String(m.fit_seconds)])];
  tbl(s, rows, 0.6, 1.6, 5.9, [2.6, 0.85, 0.85, 0.85, 0.75], { fontSize: 10.5, rowH: 0.36 });
  s.addImage({ path: FIG("fig8_ensembles"), x: 6.7, y: 1.6, w: 6.0, h: 1.9 });
  body(s, [`Bagging: ${pc(ens.models["Decision Tree (single)"].accuracy)} → ${pc(ens.models["Bagging (50 trees)"].accuracy)} by averaging tree variance`, `Random Forest de-correlates trees too: ${pc(RF.accuracy)}, macro-F1 ${f3(RF.f1_macro)}`, `Boosting on SVD-200: ${pc(ens.models["Gradient Boosting (SVD-200)"].accuracy)}; AdaBoost stumps weakest (${pc(ens.models["AdaBoost (30, SVD-200)"].accuracy)}) and slow on 10 classes`, `Forest's top n-grams are human-readable: ${ens.rf_top_features.slice(0, 4).map((x) => x.feature).join(", ")}`], 6.7, 3.7, 6.0, 3.1, { fontSize: 12 });
  footer(s, n); s.addNotes("Bagging = variance reduction; RF = bagging + feature randomisation; boosting = sequential bias reduction."); }

// 11 regression
{ const s = pres.addSlide(); n++; title(s, "Concept 1 · Regression with cross-validation"); sub(s, `Next-month spend from this month's behaviour · GroupKFold(5) by customer · best: ${reg.best}`);
  const rows = [[hdr("Model"), hdr("CV R²"), hdr("Test R²"), hdr("RMSE"), hdr("MAE")], ...Object.entries(reg.models).map(([k, m]) => [k, m.cv_r2 == null ? "–" : f3(m.cv_r2), f3(m.r2), inr(m.rmse), inr(m.mae)])];
  tbl(s, rows, 0.6, 1.6, 6.3, [2.6, 0.8, 0.85, 1.05, 1.0], { fontSize: 10.5, rowH: 0.36 });
  s.addImage({ path: FIG("fig9_regression"), x: 7.1, y: 1.6, w: 5.6, h: 1.8 });
  s.addImage({ path: FIG("fig10_regression_importance"), x: 7.1, y: 3.5, w: 5.6, h: 3.1 });
  body(s, [`Naive "same as this month" already R² ${f3(naive.r2)} — spend is sticky`, `${reg.best}: R² ${f3(rbest.r2)}, RMSE ${inr(rbest.rmse)} — ${Math.round(100 * (1 - rbest.rmse / naive.rmse))}% below naive`, "Ridge = Lasso = OLS: 4,400 rows support 34 coefficients; poly over-fits slightly", "Importance: previous + current spend ≈ 80%; one year of data → calendar effects barely learnable (future: multi-year)", "GroupKFold: a customer's months never split across folds — no identity leakage"], 0.6, 4.85, 6.3, 2.0, { fontSize: 11 });
  footer(s, n); s.addNotes("If asked why R² is high: the target is autocorrelated; the honest comparison is against the naive baseline, which is why it is in the table."); }

// 12 clustering
{ const s = pres.addSlide(); n++; title(s, "Concept 3 · K-Means vs hierarchical clustering"); sub(s, `k = ${bk} (silhouette plateau ${clu.silhouette_plateau[0]}–${clu.silhouette_plateau[clu.silhouette_plateau.length - 1]}, smallest kept) · K-Means vs Ward ARI ${f2(clu.kmeans_vs_ward_ari)} · recovers the hidden customer type: ARI ${f2(clu.ari_vs_archetype_kmeans[bk])}`);
  s.addImage({ path: FIG("fig11_cluster_selection"), x: 0.6, y: 1.55, w: 7.6, h: 1.95 });
  s.addImage({ path: FIG("fig12_dendrogram_segments"), x: 0.6, y: 3.55, w: 7.6, h: 2.6 });
  tbl(s, [[hdr("Segment"), hdr("Size"), hdr("Spend/mo"), hdr("Type")], ...clu.profiles.map((x) => [x.segment, String(x.size), inr(x.monthly_spend), x.dominant_archetype])], 8.4, 1.55, 4.3, [1.75, 0.55, 1.0, 1.0], { fontSize: 9.5, rowH: 0.34 });
  body(s, ["13 continuous behavioural features (median-month statistics), standardised; archetype used only to score", "has_emi left out: a standardised binary dominates Euclidean distance and split every segment", "Cash-reliant = pensioners (41% ATM) · Digital-first = students (56% UPI, no EMI) · Low-activity = most charges, dormancy risk"], 8.4, 3.9, 4.3, 2.9, { fontSize: 11 });
  footer(s, n); s.addNotes("Silhouette chooses k; ARI validates against the truth the generator hid. Both algorithms agree."); }

// 13 PCA
{ const s = pres.addSlide(); n++; title(s, "Concept 4 · Dimensionality reduction"); sub(s, `PCA: ${pca.n_components_95} of ${pca.n_features} profile components for 95% variance — but 3 recover the segment · SVD on text`);
  s.addImage({ path: FIG("fig14_pca"), x: 0.6, y: 1.6, w: 12.1, h: 3.15 });
  tbl(s, [[hdr("PCs kept"), ...pca.components_tested.map((c) => hdr(String(c)))], ["RF archetype F1", ...pca.components_tested.map((c) => f3(pca.performance[String(c)]["RF archetype F1"]))], ["kNN archetype F1", ...pca.components_tested.map((c) => f3(pca.performance[String(c)]["kNN archetype F1"]))]], 0.6, 4.95, 6.2, [1.6, ...pca.components_tested.map(() => 0.92)], { fontSize: 10.5, rowH: 0.36 });
  body(s, [`Profile features only mildly correlated → ${pca.n_components_95} PCs for 95% variance`, `3 PCs already give archetype F1 ${f3(pca.performance["3"]["RF archetype F1"])} — the segment signal is 3-D`, `Text: SVD-100 keeps ${pc(pca.text_svd_sweep["100"].explained)} variance, logistic F1 ${f3(pca.text_svd_sweep["100"].logreg_f1)} vs ${f3(pca.text_full_features_f1)} on all ${cls.n_features.toLocaleString("en-IN")} features — speed for kNN/boosting at small cost`], 7.0, 4.95, 5.7, 2.0, { fontSize: 11 });
  footer(s, n); s.addNotes("Variance retained is not information retained — the archetype F1 row is the useful test."); }

// 14 LWR
{ const s = pres.addSlide(); n++; title(s, "Concept 6 · Locally weighted regression (from scratch)"); sub(s, "Gaussian kernel weights · weighted least squares at every query income · bandwidth τ sweep");
  s.addImage({ path: FIG("fig15_lwr"), x: 0.6, y: 1.6, w: 8.0, h: 2.85 });
  tbl(s, [[hdr("Model"), hdr("Test RMSE")], ...Object.keys(lwr.models).map((k) => [k, inr(1000 * lwr.models[k].test_rmse_k)])], 8.8, 1.6, 3.9, [2.3, 1.6], { fontSize: 10.5, rowH: 0.34 });
  body(s, ["w_i = exp(−(x_i − x₀)² / 2τ²);  θ = (XᵀWX)⁻¹XᵀWy;  ŷ₀ = [1, x₀]·θ — NumPy only", `Best ${lwr.best_lwr}: RMSE ${inr(1000 * lwr.models[lwr.best_lwr].test_rmse_k)} vs ${inr(1000 * lwr.models["Linear"].test_rmse_k)} for the global line`, "Spend rises steeply with income at the low end and flattens — one line cannot bend", "Small τ chases noise in the sparse high-income tail; large τ → the global line (bias–variance)"], 0.6, 4.6, 12.1, 2.3, { fontSize: 12 });
  footer(s, n); s.addNotes("Non-parametric: nothing is learned globally; each prediction re-fits. O(n) per query."); }

// 15 app
{ const s = pres.addSlide(); n++; title(s, "Concept 7 · The Intelligence dashboard"); sub(s, "FastAPI endpoints + a screen in the existing Tamil/English app · models inform, rules decide");
  if (fs.existsSync(SHOT("intelligence_top"))) s.addImage({ path: SHOT("intelligence_top"), x: 0.6, y: 1.6, w: 7.3, h: 4.9 });
  body(s, ["Source: my account · upload · samples", "KPIs: debits, income, charges, segment, forecast vs naive", "Insights engine: trend, biggest mover, largest outflow, charges → Findings, savings rate, segment, forecast, anomalies, rule disagreements", "Every line: ML category + confidence + rule category; 'show disagreements only'", "Unusual debits: robust z-score within category (log amount, 3 MADs)", "Model card: live tables from results/*.json + all 15 figures", "Endpoints: /api/ml/status · /results · /figures · /analyze · /analyze-json · /api/accounts/{id}/intelligence (session)"], 8.1, 1.6, 4.6, 5.2, { fontSize: 11 });
  footer(s, n); s.addNotes("Demo this live if possible: sample → disagreements → model card."); }

// 16 insights
{ const s = pres.addSlide(); n++; title(s, "Result analysis and business insights"); sub(s, "What the numbers mean for a customer, a bank and the rule engine");
  card(s, 0.6, 1.65, 3.9, 2.45, "Where the money goes", `Every line now has a trusted category (rules: ${pc(RB.accuracy)}; model: ${pc(LR.accuracy)}). Charges still reach the rule engine: F1 ${f3(RB.per_class_f1.BANK_CHARGE)} → ${f3(cls.models[cls.best].per_class_f1.BANK_CHARGE)}; the dashboard points them to Findings.`, { icon: "₹", iconFill: RED, fontSize: 11.5 });
  card(s, 4.7, 1.65, 3.9, 2.45, "Segments as actions", "Cash-reliant pensioners: free-ATM rules. Low-activity: most charges, dormancy / reactivation charges. Digital-first students: failed-UPI reversals. Salaried: EMIs, forecast audience. High-value: widest forecast intervals.", { icon: "👥", fontSize: 11.5 });
  card(s, 8.8, 1.65, 3.9, 2.45, "Expect next month", `Forecast shown beside the naive guess with the model named; ${Math.round(100 * (1 - rbest.rmse / naive.rmse))}% lower error on test; gains concentrate in seasonal months.`, { icon: "📈", iconFill: GREEN, fontSize: 11.5 });
  card(s, 0.6, 4.3, 5.9, 2.5, "Unusual debits", "Category-aware: ₹15,000 is normal for a transfer, abnormal for UPI. Insight says '4× the typical ATM withdrawal'. Hints, never claims.", { icon: "🚩", iconFill: AMBER, fontSize: 12 });
  card(s, 6.8, 4.3, 5.9, 2.5, "What not to trust", "99% on synthetic data = learned the generator's language; trust the per-class ordering and the sample-statement disagreements. Forecasts need ≥3 months. Nothing here is a claim.", { icon: "!", iconFill: NAVY, fontSize: 12 });
  footer(s, n); s.addNotes("The honest slide. Examiners like 'what not to trust'."); }

// 17 deployment
{ const s = pres.addSlide(); n++; title(s, "Deployment, testing and demo"); sub(s, "One command to reproduce every number · one command to run the app");
  card(s, 0.6, 1.65, 3.9, 2.5, "Run", "make train → results/, models/ (~25 min)\nuvicorn api.main:app → :8000 → Intelligence\ndocker compose up --build (trains at build)", { icon: "▶", fontSize: 12 });
  card(s, 4.7, 1.65, 3.9, 2.5, "Tested", "101 Vasool Raja tests + 13 new: generator determinism, masking, featurizer, panel/profile, rule map, LWR exactness, service accuracy > 90%, endpoints, 415 on bad upload, 401/404 without session.", { icon: "✓", iconFill: GREEN, fontSize: 11.5 });
  card(s, 8.8, 1.65, 3.9, 2.5, "Repository", "bankiq/ (data, features, rulemap, experiments, service, api) · notebooks/01–07 · results/ · models/ · tests/ · docs/ (Phase I, literature, report, slides, viva)", { icon: "⌥", iconFill: NAVY, fontSize: 12 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.35, w: 12.1, h: 2.5, fill: { color: LIGHT }, line: { color: LIGHT }, rectRadius: 0.1 });
  s.addText("3-minute demo", { x: 0.85, y: 4.45, w: 5, h: 0.4, fontFace: BFONT, fontSize: 15, bold: true, color: NAVY, isTextBox: true, margin: 0 });
  body(s, ["Intelligence → Sample: hdfc priya salary → KPIs, insights, category mix (model and rules agree on every line)", "Sample: axis kavya longtail → 'show disagreements only': 30 of 41 lines — the regexes see generic transfers, the model sees income, EMI, UPI, ATM, refund, interest, charge", "Canara pension sample → Cash-reliant, five charges, ₹50,000 college fee flagged", "Model card → Table live from results JSON → Fig 5, Fig 11, Fig 15", "Findings tab → the rule engine's claims on the same statement"], 0.85, 4.9, 11.6, 1.9, { fontSize: 12 });
  footer(s, n); s.addNotes("Keep the demo to five steps; the long-tail sample with the disagreement filter is the moment that shows what ML adds."); }

// 18 conclusion
{ const s = pres.addSlide(); n++; s.background = { color: NAVY }; title(s, "Conclusion and future scope", { color: WHITE });
  body(s, ["All seven syllabus techniques applied to one real product, each against a baseline, under cross-validation that respects the data (stratified; grouped by customer)", `Transaction classifier: ${pc(RB.accuracy)} (regex) → ${pc(LR.accuracy)} (logistic) / ${pc(RF.accuracy)} (forest); biggest gains on transfers, EMIs and merchant lines`, `Forecast ${Math.round(100 * (1 - rbest.rmse / naive.rmse))}% below naive; K-Means and Ward agree on ${bk} segments that recover the hidden types (ARI ${f2(clu.ari_vs_archetype_kmeans[bk])}); PCA shows a 3-D segment signal; LWR exposes the bend in spend vs income`, "Deployed beside an untouched rule engine; reproducible; 114 tests"], 0.6, 1.6, 6.3, 4.0, { fontSize: 14, color: "CFE8D8" });
  s.addText("Future scope", { x: 7.2, y: 1.6, w: 5.5, h: 0.5, fontFace: BFONT, fontSize: 18, bold: true, color: MINT, isTextBox: true, margin: 0 });
  body(s, ["Real consented statements (Account Aggregator) + active learning on model–rule disagreements", "Multi-year histories; prediction intervals", "Confirmed findings fed back as training labels", "Tamil / Hindi tokens; OCR-specific character models", "Isolation Forest once labelled anomalies exist"], 7.2, 2.15, 5.5, 3.2, { fontSize: 14, color: WHITE });
  s.addText("github.com/<your-user>/bank-iq   ·   Thank you — questions?", { x: 0.6, y: 6.0, w: 12.1, h: 0.6, fontFace: BFONT, fontSize: 16, color: WHITE, isTextBox: true, margin: 0 });
  s.addNotes("Close with the one-line summary and invite questions."); }

pres.writeFile({ fileName: `${OUT}/BankIQ_Presentation.pptx` }).then((f) => console.log("wrote", f));
