const D = require("./docgen");
const papers = require("./papers");
const { run, p, center, buildDoc, save, AlignmentType } = D;
const OUT = process.env.DV_OUT || "/home/claude/docs_build_biq/out";
const pick = [13, 15, 14, 1, 2, 4, 6, 8, 9, 12].map((n) => papers.find((x) => x.n === n));

const items = [
  "Documents are represented as vectors of term weights; the paper compares term-frequency, inverse-document-frequency and length-normalisation schemes and finds tf·idf with cosine normalisation best. This is how every bank-statement narration is represented in our system: a TF-IDF vector in which rare, informative tokens such as SALARY, NACH or REV outweigh the reference numbers and bank codes that appear in almost every line.",
  "Character n-gram frequency profiles categorise text robustly in the presence of spelling errors, truncation and OCR noise. Narrations are abbreviated and truncated (CHRG, WDL, RVSL) and passbook pages come through OCR, so we add character 3–5-grams to the word features; this is what lets the classifier recover meaning that hand-written regular expressions and whole-word tokens miss.",
  "Multinomial Naive Bayes under-performs on text because of skewed class sizes and weight-magnitude errors; Complement Naive Bayes with TF-IDF transforms and weight normalisation closes most of the gap to discriminative models. Gave us the Naive Bayes variant for our ten imbalanced categories: Complement NB on the TF-IDF features is the fastest model in the comparison and a strong baseline at 94% accuracy.",
  "Decision trees are built top-down by picking, at each node, the attribute that best separates the classes (information gain); a fully grown tree memorises noise. Gave us the single-tree classifier and regressor, and the depth sweep in our results shows the over-fitting the paper warns about: training F1 keeps rising with depth while cross-validated F1 plateaus.",
  "The nearest-neighbour rule classifies a point by the majority label of its k closest training points and its error is at most twice the Bayes error. Gave us the kNN baseline and a practical lesson: Euclidean distance on sparse TF-IDF vectors is uninformative, so we run kNN on a 200-dimensional SVD projection with cosine distance (97% accuracy) and sweep k to show the bias–variance effect.",
  "Random forests grow many decision trees on bootstrap samples with a random subset of features at each split and average them, which de-correlates the trees and gives variable-importance scores. Random Forest is one of our best transaction classifiers (99.9% test accuracy) and a strong spend regressor; its importances tell us which n-grams and amounts the model relies on.",
  "Gradient boosting builds an additive model in which each new tree fits the negative gradient of the loss of the current ensemble, with shrinkage and subsampling to regularise. Gradient Boosting is the best next-month spend regressor and the one deployed for the forecast; it is also the only model family that exploits the seasonal month features the linear models cannot.",
  "K-means assigns each point to the nearest of k centroids and recomputes the centroids until within-cluster variance stops falling. It is our customer-segmentation method on a 14-feature behavioural profile; the silhouette curve chooses k = 5, and the clusters are named as business segments (high-value / business, regular salaried, cash-reliant, digital-first, low-activity).",
  "Ward's hierarchical method merges, at each step, the two clusters whose union increases the total within-cluster sum of squares the least, producing a dendrogram. Used as the second clustering algorithm on the same profiles; the dendrogram gives an independent view of the number of segments and the Adjusted Rand Index between K-Means and Ward (≈0.9) shows the two agree.",
  "Kohavi's study compares hold-out, k-fold, leave-one-out and bootstrap accuracy estimates and recommends stratified k-fold cross-validation for model selection. Defined our evaluation protocol: stratified 5-fold cross-validation on the training split for classifiers, GroupKFold by customer for the regression so a customer's months never leak across folds, and a held-out test split reported once.",
];

const gap = [
  "Each reference studies one technique in isolation — text representation, one classifier, one ensemble, one clustering method, one evaluation protocol. None applies them together to bank-statement data, and none measures a learned classifier against the hand-written rule system that banks and personal-finance tools actually run. Bank IQ keeps an existing regex rule engine (Vasool Raja) as the baseline and reports, per category, where the learned models gain.",
  "Transaction categorisation, customer segmentation, spend forecasting and anomaly flagging are treated as separate problems; we build all four on one feature pipeline from one account's history, so the segment, the forecast and the anomaly flags are consistent with the categories the classifier assigns.",
  "No public labelled dataset of Indian bank narrations exists because statements are personal data. We design and document a reproducible labelled generator (500 customers × 12 months, 10 categories, 5 hidden archetypes, seasonality, long-tail narrations) whose labels are independent of the narration string, so that evaluation against the rule baseline is meaningful.",
  "Published work stops at the model. We deploy the intelligence layer as FastAPI endpoints and an Intelligence dashboard inside an existing bilingual (Tamil/English) application, beside the rule engine's findings, with a clear separation: models inform and predict; rules decide and file claims.",
  "To keep evaluation honest, hyperparameters are chosen on cross-validated training folds, the test split is touched once, the clustering is validated against a hidden customer type never used as a feature, and the whole pipeline re-runs from one command with every number in the report generated, not typed.",
];

const sec = [
  center("22MDC56 – MACHINE LEARNING LABORATORY", { bold: true, size: 26 }),
  center("SUMMARY ON RESEARCH ARTICLES", { bold: true, size: 26 }),
  center("BANK-STATEMENT ANALYTICS WITH MACHINE LEARNING", { bold: true, size: 24, after: 300 }),
  p([run("Team members:", { bold: true })], { align: AlignmentType.LEFT, after: 60 }),
  p("1. Sandhru D. [________________]", { align: AlignmentType.LEFT, after: 40 }),
  p("2. ____________________ [________________]", { align: AlignmentType.LEFT, after: 40 }),
  p("3. ____________________ [________________]", { align: AlignmentType.LEFT, after: 240 }),
  center("LITERATURE SURVEY FOR “BANK IQ: A MACHINE LEARNING INTELLIGENCE LAYER FOR BANK-STATEMENT ANALYTICS — TRANSACTION CLASSIFICATION, CUSTOMER SEGMENTATION AND SPEND FORECASTING ON A REGULATORY DIGITAL TWIN”", { bold: true, size: 24, after: 240 }),
  ...items.map((t, i) => p([run(`[${i + 1}] `, { bold: true }), run(t)], { after: 160 })),
  ...D.spacer(1),
  p([run("GAP ANALYSIS:", { bold: true, size: 24 })], { align: AlignmentType.LEFT, after: 120 }),
  ...gap.map((g) => p(g, { after: 120 })),
  ...D.spacer(1),
  p([run("REFERENCES:", { bold: true, size: 24 })], { align: AlignmentType.LEFT, after: 120 }),
  ...pick.map((pp, i) => p([run(`${i + 1}. `), run(`${pp.authors}, “${pp.title},” ${pp.venue}, ${pp.year}.`)], { after: 100, size: 21 })),
];
save(buildDoc([sec], { title: "Bank IQ – Summary on Research Articles", header: "22MDC56 – Machine Learning Laboratory – Summary on Research Articles" }), `${OUT}/BankIQ_Summary_on_Research_Articles.docx`);
