/* Bank IQ — web app (no build step). Talks to /api. */
(() => {
  "use strict";

  // ------------------------------------------------------------------ i18n
  const T = {
    en: {
      tagline: "We watch. You don't have to.",
      "nav.intel": "Intelligence",
      "intel.h": "Intelligence", "intel.banner": "Rules decide. Models learn. Both are shown side by side.",
      "intel.lede": "A classical machine-learning layer trained on 130,000 synthetic Indian bank transactions: logistic-regression categorisation of every line, K-Means customer segments, a next-month spend forecast and an explainable anomaly flag. The rule engine is still the only thing that files a claim.",
      "intel.nomodels": "Trained models not found. Run `python -m bankiq.experiments.run_all` once, then reload.",
      "intel.source": "What should I analyse?", "intel.useacct": "Analyse my account", "intel.noacct": "Scan a statement to analyse your own account, or try a sample →",
      "intel.upload": "Upload a statement", "intel.sample": "Sample", "intel.busy": "Running the models…", "intel.loaded": "{n} transactions analysed · {s}", "intel.loading": "Loading experiment results…",
      "intel.k.txn": "Transactions", "intel.months": "months", "intel.k.spend": "Total debits", "intel.k.income": "recognised income", "intel.k.charges": "Bank charges found", "intel.k.refunds": "refunds / reversals",
      "intel.k.segment": "Customer segment", "intel.k.segid": "cluster", "intel.k.forecast": "Next-month spend (forecast)", "intel.k.naive": "naive guess",
      "intel.insights": "Business insights", "intel.cats": "Where the money goes (ML categories)", "intel.monthly": "Monthly income vs spend", "intel.monthly.note": "Income = salary / pension credits recognised by the classifier. Hover a bar for the exact amount.",
      "intel.income": "income", "intel.spend": "spend", "intel.profile": "Behavioural profile", "intel.anom": "Unusual debits", "intel.anom.none": "No debit stands out from its category's usual size.",
      "intel.anom.note": "Robust z-score of log(amount) within each ML category; flagged when more than 3 MADs above the median. Explainable, no black box.",
      "intel.txns": "Every line, classified", "intel.disagree": "ML and regex rules disagree on {n} of {m}", "intel.onlydiff": "show disagreements only",
      "intel.t.date": "Date", "intel.t.narr": "Narration", "intel.t.amt": "Amount", "intel.t.typ": "Typical", "intel.t.rule": "Rule says", "intel.models": "Models",
      "intel.card": "Model card", "intel.card.sum": "how the models were trained and evaluated", "intel.card.lede": "Every number below comes from results/*.json written by the experiment scripts (held-out test split; 5-fold cross-validation on the training split).",
      "intel.card.cls": "Transaction classification", "intel.card.reg": "Next-month spend regression", "intel.card.clu": "Segmentation",
      "nav.home": "Home", "nav.scan": "Scan", "nav.findings": "Findings", "nav.twin": "My Twin", "nav.cases": "Cases", "nav.history": "History", "nav.ask": "Ask", "nav.rules": "Rulebook", "nav.settings": "Settings", "nav.guardian": "Guardian", "nav.privacy": "Privacy",
      "foot.rule": "AI explains. Rules decide. Evidence proves.",
      "dash.q": "Is my bank account being charged fairly?", "dash.overview": "Account overview", "dash.period": "Statement period", "dash.txns": "Transactions analysed", "dash.charges": "Charges analysed", "dash.reversals": "Reversals detected", "dash.rules": "Rules evaluated", "dash.last": "Last scan", "dash.months": "Months covered",
      "dash.potential": "POTENTIAL RECOVERY", "dash.findings": "{n} findings", "dash.action": "{n} action required", "dash.confirm": "{n} need confirmation", "dash.info": "{n} informational", "dash.review": "Review my findings", "dash.twin": "See my digital twin", "dash.demo": "DEMONSTRATION DATA — a synthetic statement, not a real customer.", "dash.scan.more": "Scan another statement", "dash.accounts": "Your accounts",
      "dash.honest": "A potential claim is what the evidence supports. It becomes money only when the bank or the RBI Ombudsman decides.",
      "scan.h": "Bank IQ Scan", "scan.1": "Reading statement…", "scan.1d": "{n} transactions parsed", "scan.2": "Understanding account activity…", "scan.2d": "account state reconstructed · {n} months · {b} balance points", "scan.3": "Matching transactions and reversals…", "scan.3d": "{p} reversal pair(s) · {u} unreversed failure(s)", "scan.4": "Checking applicable rules…", "scan.4d": "{n} RBI rules evaluated, each at its effective date", "scan.5": "Checking edge cases…", "scan.5d": "partial reversals, retries, free-ATM counts, prior-month balances", "scan.6": "Generating findings…", "scan.6d": "{n} finding(s) · {f} statement line(s) flagged · {u} not flagged", "scan.done": "SCAN COMPLETE", "scan.open": "Open findings",
      "chain.h": "Evidence chain", "chain.1": "What happened", "chain.2": "What should have happened", "chain.3": "What we found", "chain.4": "Why it was flagged", "chain.5": "Evidence — statement lines", "chain.6": "Rule in force", "chain.7": "Calculation", "chain.8": "Potential claim", "chain.info": "Informational finding", "chain.foot": "TRANSACTION → ACCOUNT STATE → RULE MATCH → CALCULATION → EVIDENCE → FINDING → POTENTIAL CLAIM. Without every link: no claim.",
      "chain.inforce": "in force", "chain.cond": "condition", "chain.status.CONFIRMED": "Confirmed from evidence", "chain.status.NEEDS_CHECKING": "Requires your confirmation", "chain.status.INFO": "Informational",
      "mytwin.h": "My banking digital twin", "mytwin.lede": "Everything below is reconstructed from the lines you uploaded — nothing is estimated. The engine judged every line; here is what it saw.",
      "mytwin.pipe": "Customer → Account → Transactions → Balance history → Charges → Reversals → Account state → Rule engine → Findings",
      "mytwin.balance": "Balance history", "mytwin.pairs": "Failed debits and their reversals", "mytwin.charges": "Charges the bank made", "mytwin.lines": "Every statement line, and why it was or wasn't flagged", "mytwin.flagged": "flagged", "mytwin.clean": "not flagged", "mytwin.whynot": "Why wasn't this flagged?", "mytwin.why": "Why was this flagged?", "mytwin.close": "Close", "mytwin.within": "within T+{n}", "mytwin.beyond": "{d} days · beyond T+{n}", "mytwin.open": "open {d} days · T+{n} passed", "mytwin.minreq": "required minimum ₹{r}", "mytwin.lowest": "lowest ₹{l}",
      "scope.h": "What this prototype checks", "scope.line": "{i} RBI customer-protection rules implemented and tested · {l} listed · {m} mapped in the design. This is not complete RBI coverage.", "scope.note": "Every implemented rule links to its circular and effective window. Rules that are mapped but not implemented are never applied.",
      "valid.h": "System validation", "valid.lede": "Real results from the test suite, written by scripts/validate.py — never typed by hand.", "valid.passed": "tests passed", "valid.none": "Not run yet on this machine: python scripts/validate.py", "valid.ran": "last run",
      "ai.banner": "AI explains. Rules decide. Evidence proves.", "ai.lede": "Every answer is built from your account's findings and the rulebook. The assistant cannot create a claim, and says so when the evidence is not enough.",
      "priv.h": "Privacy centre", "priv.what": "What we collect", "priv.what.d": "Only the transaction lines of the statement you upload (date, narration, debit, credit, balance) and the answers you give. The file itself is not kept.", "priv.why": "Why", "priv.why.d": "To run the RBI rules on your account state and to build the evidence pack for a complaint you choose to make.", "priv.keep": "How long", "priv.keep.d": "Until you delete it. Everything lives in one local database on this machine; nothing is uploaded to us.", "priv.who": "Who can see it", "priv.who.d": "You. Your guardian sees only the amount, the rule and one button — never balances or spending. No bank is ever contacted by this software.", "priv.delete": "Delete my data", "priv.deleted": "All data for this account has been deleted.", "priv.never": "Never asked for", "priv.controls": "Controls in this build",
      "guard.flow": "Customer → Consent → Trusted guardian → Review → Approve action", "guard.status": "Guardian status", "guard.none": "No guardian on file", "guard.scope": "Access scope", "guard.scope.d": "Amount · rule reference · one approve button. Never: balance, salary, spending, other transactions.", "guard.consent": "Consent", "guard.revoke": "Revoke access", "guard.revoked": "Guardian access revoked.", "guard.audit": "Audit history",
      "auth.h": "Sign in to Bank IQ", "auth.lede": "Your statements are stored only on this machine, encrypted (AES-256-GCM). Your password is never stored — only a salted PBKDF2 hash.", "auth.login": "Phone or email", "auth.name": "Your name", "auth.pass": "Password (6+ characters)", "auth.signin": "Sign in", "auth.signup": "Create account", "auth.toggle.up": "New here? Create an account", "auth.toggle.in": "Already have an account? Sign in", "auth.out": "Sign out", "auth.never": "We never ask for your net-banking password, OTP, PIN or CVV — only a statement you download yourself.",
      "alert.h": "Act before the clock runs out", "alert.lede": "Small claims are not ignored: every finding carries an act-by date. Inside {n} days it turns red, is promoted to Recover now whatever the amount, and an alert is sent.", "alert.chip": "⏰ act by {d} · {n} days", "alert.over": "⏰ act-by {d} passed · {n} days ago — file now", "alert.open": "⏰ open failure · ₹{p}/day accruing", "alert.sent": "Alert sent to Telegram", "alert.sim": "Alert simulated ({r})", "n.tg.on": "Telegram alerts are ON — red alerts go to chat {c}", "n.tg.off": "Telegram alerts are OFF (add VASOOL_TELEGRAM_TOKEN and VASOOL_TELEGRAM_CHAT in .env).", "n.tgtest": "Send test alert",
      "case.ready": "CASE READY", "case.pack": "Evidence pack (print / PDF)", "case.inside": "Inside the pack: case ID · each item with date, amount, RBI rule and effective window · the arithmetic · the statement lines as Annexure A · requested resolution · the 30-day clock.",
      "home.multi": "You can select several files at once — different months or quarters of the same account.",
      "home.current": "Open account: {a}", "home.addto": "Add a statement to it", "home.new": "This form starts a new account.",
      "st.h": "Statements", "st.lede": "Every statement of this account we have seen. Rules run on the whole history — a June penalty is judged on May's balances.",
      "st.add": "Add another statement", "st.added": "+{n} new lines · {d} duplicates skipped", "st.lines": "{n} lines", "st.new": "{n} new", "st.dup": "{n} duplicate", "st.remove": "Remove", "st.covers": "Covered: {a} → {b}", "st.gap": "Gap: {a} → {b} — upload that statement too",
      "hist.h": "History", "hist.lede": "Every account scanned on this device, with what was found and what came back. Open one to continue where you left off.", "hist.none": "Nothing scanned yet.",
      "hist.open": "Open", "hist.current": "Open now", "hist.found": "potential", "hist.recovered": "recovered", "hist.stmts": "{n} statement(s)", "hist.cases": "{n} case(s)", "hist.opencases": "{n} open",
      "case.print": "Evidence pack (print / PDF)", "case.printomb": "Print Ombudsman draft", "case.printhint": "A4 letter with Annexure A — take 2 copies to the branch, get one stamped.",
      "time.h": "Every day the bank waits", "time.lede": "Drag the date. Unreversed failed transactions accrue ₹100 a day under RBI/2019-20/67 — the twin recomputes every claim for that day.", "time.asof": "As of", "time.today": "today",
      "twin.h": "The twin", "twin.open": "See the twin", "twin.actual": "ACTUAL FINANCIAL STATE", "twin.expected": "EXPECTED REGULATORY STATE", "twin.delta": "REGULATORY DELTA", "twin.claim": "POTENTIAL CLAIM", "twin.replay": "Replay", "twin.back": "Back to findings",
      "twin.debited": "debited · failed", "twin.due": "reversal due (T+{n})", "twin.perday": "₹{p}/day owed from here", "twin.reversed": "reversed", "twin.noreversal": "no reversal as of {d}", "twin.comp0": "compensation credited: ₹0", "twin.late": "{n} days late", "twin.day": "Day {n}",
      "twin.mb.expected": "balance stays at or above ₹{r} all of {m} → no penalty allowed", "twin.mb.actual": "penalty ₹{p} charged on {d}", "twin.mb.lowest": "lowest balance in {m}: ₹{l}", "twin.mb.blind": "The twin cannot see {m} — that month is not in any uploaded statement. Add it and the verdict can change.", "twin.mb.add": "Add that statement", "twin.mb.required": "required ₹{r}",
      "twin.chain": "TRANSACTION + ACCOUNT STATE + RULE IN FORCE + CALCULATION + EVIDENCE → VERDICT. Without all five: no claim.",
      "call.placed": "📞 Calling {to}…", "call.sim": "Call simulated ({r})", "n.voice.on": "Voice is ON — a real Tamil call goes out from {f}", "n.voice.off": "Voice is OFF — the call is simulated on screen (add VASOOL_TWILIO_* to .env).", "n.testcall": "Test call", "home.phone": "Your phone (for the Tamil call)",
      "mail.sent": "Email delivered to {to}", "mail.sim": "Email simulated ({r})", "mail.also": "Also emailed to {to}",
      "g.email": "Email (the real one-button message goes here)", "n.h": "Real delivery", "n.on": "Email is ON — messages go out for real (from {f})", "n.off": "Email is OFF — the guardian message and complaint are simulated on screen.",
      "n.demo": "Safety: every mail is redirected to {to}", "n.demo.phone": "Safety: every call is redirected to {to}", "n.how": "To turn it on, create a .env file next to run.bat with VASOOL_SMTP_USER, VASOOL_SMTP_PASS (Gmail app password) and VASOOL_DEMO_TO. Nothing is ever sent to a bank.", "n.test": "Send test mail", "n.bank": "The bank itself is never emailed by this demo.",
      "ap.h": "Bank IQ asks for your OK", "ap.for": "For {h}'s account at {b}", "ap.yes": "✓ Yes, send the complaint", "ap.no": "Not now", "ap.done": "Approved. Thank you — the evidence pack is ready for the branch; we're watching the 30-day clock.", "ap.used": "This request was already answered.", "ap.note": "No balance or spending details are shown. Only the complaint goes to the bank.",
      "foot.privacy": "We check transactions. We don't sell them. No passwords, ever.",
      "home.h1": "What if your bank owed you money right now?",
      "home.lede": "Give us one statement or a passbook photo. We run the RBI rulebook on it and tell you what your bank may owe you — with the rule beside every rupee. Nothing is sent to anyone unless you say so.",
      "home.drop": "Drop a statement here — PDF, CSV or a passbook photo", "home.or": "or try a sample",
      "home.bank": "Bank", "home.type": "Account type", "home.city": "City", "home.minbal": "Minimum balance your bank requires (₹)", "home.name": "Your name", "home.scan": "Check my account",
      "home.privacy": "Processed on this server, stored only as normalised transactions, deletable any time. We never ask for net-banking passwords or PINs.",
      "found.h": "potential recovery", "found.sub": "{n} potential claim(s) supported by the statement", "found.unclear": "{n} need one answer from you", "found.avoid": "{n} you can stop next time",
      "found.charges": "Bank charges in this period: {a}", "found.none": "Everything looks okay. Nothing needs your attention.", "found.watch": "We'll keep watching.",
      "found.getback": "Get it back", "found.effort": "Builds the evidence pack · your effort: about 2 minutes",
      "sec.now": "Worth acting on now", "sec.ask": "One answer from you settles these", "sec.combine": "Small — we'll bundle them", "sec.skip": "Too small to bother you — we keep watching", "sec.prevent": "Allowed — but you can stop the next one",
      "why": "Evidence chain", "hide": "Hide", "expected": "Should have happened", "actual": "What happened", "calc": "Calculation", "rule": "Your right", "source": "RBI source", "confidence": "Confidence", "evidence": "Statement lines",
      "prevent": "How to stop the next one", "answer": "Answer:", "yes": "Yes", "no": "No", "not_sure": "Not sure",
      "case.h": "Your case", "case.prepared": "Complaint prepared. Nothing has been sent.", "case.guardian": "Ask my guardian", "case.send": "Send it myself", "case.preview": "Read the complaint",
      "case.callh": "Amma's phone rings", "case.play": "Play the call", "case.stop": "Stop", "case.press1": "Press 1 — call {g}", "case.press2": "Press 2 — not now",
      "case.wa": "WhatsApp to {g}", "case.approve": "Approve as {g}", "case.sent": "Approved. Evidence pack ready to submit — nothing is transmitted by this app. We're watching the 30-day clock.", "case.days": "{d} days left for the bank to reply",
      "case.bankreplied": "Bank replied", "case.recovered": "Money came back", "case.bankright": "Bank showed it was valid", "case.escalate": "Escalate to RBI Ombudsman", "case.check": "Check next statement for the refund",
      "case.download": "Complaint text", "case.omb": "Ombudsman draft", "case.timeline": "What happened so far",
      "cases.h": "Cases", "cases.none": "No cases yet. When something is found, 'Get it back' creates one.",
      "ask.h": "Ask Bank IQ", "ask.ph": "Why did the bank charge me ₹295?", "ask.send": "Ask", "ask.hint": "Ask in Tamil or English. Try: what happened? · how much? · what should I do? · where is my KFS?",
      "rules.h": "The rulebook", "rules.lede": "Every rule Bank IQ checks, with its RBI source and effective date. Open data — anyone can audit it.",
      "settings.h": "Settings", "g.h": "Guardian (காப்பாளர்)", "g.lede": "One person you trust. We call you first, then send them one message with one button. They never see your balance or spending.",
      "g.name": "Name", "g.rel": "Relation", "g.phone": "Phone", "g.consent": "Your consent, in your words (spoken or typed)", "g.save": "Save guardian",
      "s.delete": "Delete all my data", "s.deleted": "Deleted.", "s.basic": "Letter to convert to a zero-charge Basic account",
      "noacct": "Scan a statement first.", "err": "Something went wrong: ",
      "priority.RECOVER_NOW": "Recover now", "priority.COMBINE": "Combine", "priority.NOT_WORTH_IT": "We keep watching", "priority.PREVENT": "Prevent",
      "label.RECOVERABLE": "Potential claim · rule broken", "label.AVOIDABLE": "Allowed · avoidable", "label.UNCLEAR": "Needs one answer",
      "conf.CONFIRMED": "Confirmed", "conf.NEEDS_CHECKING": "Needs checking", "conf.INFO": "Information",
      "suspicious": "This looks like a payment that may have failed and been retried. Did it fail?",
      "state": { FOUND: "Found", PREPARED: "Prepared", AWAITING_APPROVAL: "Awaiting approval", SENT_TO_BANK: "Ready to submit", BANK_REPLIED: "Bank replied", DEADLINE_PASSED: "Deadline passed", ESCALATED_OMBUDSMAN: "Escalated", RECOVERED: "Recovered", CLOSED_BANK_RIGHT: "Bank was right", CLOSED_BY_USER: "Closed" },
    },
    ta: {
      tagline: "நாங்க பாத்துக்கறோம். நீங்க கவலைப்பட வேண்டாம்.",
      "nav.intel": "Intelligence",
      "intel.h": "Intelligence", "intel.banner": "Rules முடிவு பண்ணும். Models கத்துக்கும். ரெண்டையும் பக்கத்துல காட்டுறோம்.",
      "intel.source": "எதை analyse பண்ணணும்?", "intel.useacct": "என் account-ஐ analyse பண்ணு", "intel.noacct": "உங்க account-க்கு முதல்ல statement scan பண்ணுங்க, இல்லைன்னா sample try பண்ணுங்க →",
      "intel.upload": "Statement upload பண்ணு", "intel.sample": "Sample", "intel.busy": "Models ஓடுது…", "intel.loaded": "{n} transactions analyse ஆச்சு · {s}",
      "intel.k.txn": "Transactions", "intel.months": "மாசம்", "intel.k.spend": "மொத்த debit", "intel.k.income": "வருமானம்", "intel.k.charges": "Bank charges", "intel.k.refunds": "refunds",
      "intel.k.segment": "Customer segment", "intel.k.forecast": "அடுத்த மாசம் செலவு (கணிப்பு)", "intel.k.naive": "சாதாரண guess",
      "intel.insights": "Business insights", "intel.cats": "பணம் எங்க போகுது (ML categories)", "intel.monthly": "மாசாந்திர வருமானம் vs செலவு", "intel.income": "வருமானம்", "intel.spend": "செலவு",
      "intel.profile": "Behaviour profile", "intel.anom": "வழக்கத்துக்கு மாறான debits", "intel.txns": "ஒவ்வொரு line-ம், classify பண்ணி", "intel.onlydiff": "disagreements மட்டும்",
      "intel.t.date": "தேதி", "intel.t.narr": "Narration", "intel.t.amt": "தொகை", "intel.t.rule": "Rule சொல்றது",
      "nav.home": "Home", "nav.scan": "Scan", "nav.findings": "கண்டுபிடிச்சது", "nav.twin": "என் Twin", "nav.cases": "Cases", "nav.history": "History", "nav.ask": "கேளுங்க", "nav.rules": "Rulebook", "nav.settings": "Settings", "nav.guardian": "காப்பாளர்", "nav.privacy": "Privacy",
      "foot.rule": "AI விளக்கும். Rules முடிவு பண்ணும். Evidence நிரூபிக்கும்.",
      "dash.q": "என் bank account-ல charge சரியா போடுறாங்களா?", "dash.overview": "Account overview", "dash.period": "Statement காலம்", "dash.txns": "பார்த்த transactions", "dash.charges": "பார்த்த charges", "dash.reversals": "கண்ட reversals", "dash.rules": "பார்த்த rules", "dash.last": "கடைசி scan", "dash.months": "மாசங்கள்",
      "dash.potential": "POTENTIAL RECOVERY · திரும்ப வரலாம்", "dash.findings": "{n} findings", "dash.action": "{n} இப்பவே", "dash.confirm": "{n}-க்கு உங்க பதில் வேணும்", "dash.info": "{n} தகவல்", "dash.review": "என் findings-ஐ பாரு", "dash.twin": "என் digital twin-ஐ பாரு", "dash.demo": "DEMONSTRATION DATA — synthetic statement, உண்மையான customer இல்ல.", "dash.scan.more": "இன்னொரு statement scan பண்ணு", "dash.accounts": "உங்க accounts",
      "dash.honest": "Potential claim-னா evidence support பண்றது. Bank அல்லது RBI Ombudsman முடிவு பண்ணா தான் பணம்.",
      "scan.h": "Bank IQ Scan", "scan.1": "Statement படிக்கிறோம்…", "scan.1d": "{n} transactions parse ஆச்சு", "scan.2": "Account activity புரிஞ்சுக்கிறோம்…", "scan.2d": "account state ready · {n} மாசம் · {b} balance points", "scan.3": "Transactions-ஐயும் reversals-ஐயும் match பண்றோம்…", "scan.3d": "{p} reversal pair · {u} reverse ஆகாத failure", "scan.4": "Rules check பண்றோம்…", "scan.4d": "{n} RBI rules, ஒவ்வொண்ணும் அதோட தேதியில", "scan.5": "Edge cases பாக்கறோம்…", "scan.5d": "partial reversal, retry, free-ATM count, முந்தைய மாச balance", "scan.6": "Findings தயார் பண்றோம்…", "scan.6d": "{n} finding · {f} line flag · {u} flag இல்ல", "scan.done": "SCAN முடிஞ்சது", "scan.open": "Findings-ஐ பாரு",
      "chain.h": "Evidence chain", "chain.1": "நடந்தது", "chain.2": "நடந்திருக்க வேண்டியது", "chain.3": "நாங்க கண்டது", "chain.4": "ஏன் flag ஆச்சு", "chain.5": "Evidence — statement lines", "chain.6": "அமலில் இருக்கற rule", "chain.7": "கணக்கு", "chain.8": "Potential claim", "chain.info": "தகவல் finding", "chain.foot": "TRANSACTION → ACCOUNT STATE → RULE → CALCULATION → EVIDENCE → FINDING → POTENTIAL CLAIM. ஒண்ணு இல்லாட்டியும் claim இல்ல.",
      "chain.inforce": "அமலில்", "chain.cond": "condition", "chain.status.CONFIRMED": "Evidence-ல உறுதி", "chain.status.NEEDS_CHECKING": "உங்க பதில் வேணும்", "chain.status.INFO": "தகவல்",
      "mytwin.h": "என் banking digital twin", "mytwin.lede": "கீழ இருக்கறது எல்லாம் நீங்க upload பண்ண lines-ல இருந்து — எதுவும் அனுமானம் இல்ல. Engine ஒவ்வொரு line-ஐயும் பாத்தது; அது பாத்தது இது.",
      "mytwin.pipe": "Customer → Account → Transactions → Balance history → Charges → Reversals → Account state → Rule engine → Findings",
      "mytwin.balance": "Balance history", "mytwin.pairs": "Fail ஆன debits-ம் அதோட reversals-ம்", "mytwin.charges": "Bank போட்ட charges", "mytwin.lines": "ஒவ்வொரு line-ம், ஏன் flag ஆச்சு / ஆகல", "mytwin.flagged": "flag", "mytwin.clean": "flag இல்ல", "mytwin.whynot": "ஏன் இது flag ஆகல?", "mytwin.why": "ஏன் இது flag ஆச்சு?", "mytwin.close": "மூடு", "mytwin.within": "T+{n}-க்குள்ள", "mytwin.beyond": "{d} நாள் · T+{n} தாண்டி", "mytwin.open": "{d} நாளா open · T+{n} முடிஞ்சது", "mytwin.minreq": "தேவை ₹{r}", "mytwin.lowest": "குறைந்தது ₹{l}",
      "scope.h": "இந்த prototype என்ன check பண்ணும்", "scope.line": "{i} RBI customer-protection rules implement ஆயி test ஆச்சு · {l} list-ல · {m} design-ல map ஆச்சு. இது முழு RBI coverage இல்ல.", "scope.note": "Implement ஆன ஒவ்வொரு rule-ம் அதோட circular-க்கும் தேதிக்கும் link ஆகும். Map மட்டும் ஆன rules எப்பவும் apply ஆகாது.",
      "valid.h": "System validation", "valid.lede": "Test suite-ஓட உண்மையான results — scripts/validate.py எழுதினது, கையால இல்ல.", "valid.passed": "tests pass", "valid.none": "இந்த machine-ல இன்னும் ஓடல: python scripts/validate.py", "valid.ran": "கடைசி run",
      "ai.banner": "AI விளக்கும். Rules முடிவு பண்ணும். Evidence நிரூபிக்கும்.", "ai.lede": "ஒவ்வொரு பதிலும் உங்க account findings-லயும் rulebook-லயும் இருந்து. Assistant claim உருவாக்காது; evidence போதலைன்னா அப்படியே சொல்லும்.",
      "priv.h": "Privacy centre", "priv.what": "என்ன சேகரிக்கிறோம்", "priv.what.d": "நீங்க upload பண்ற statement-ஓட transaction lines மட்டும் (தேதி, narration, debit, credit, balance), உங்க பதில்கள். File-ஐ வெச்சுக்கறது இல்ல.", "priv.why": "ஏன்", "priv.why.d": "உங்க account state-ல RBI rules ஓட்டவும், நீங்க விரும்பினா complaint-க்கு evidence pack தயார் பண்ணவும்.", "priv.keep": "எவ்வளவு நாள்", "priv.keep.d": "நீங்க அழிக்கற வரை. எல்லாம் இந்த machine-ல ஒரே local database-ல; எங்களுக்கு எதுவும் upload ஆகாது.", "priv.who": "யார் பாக்கலாம்", "priv.who.d": "நீங்க. காப்பாளர் தொகை, rule, ஒரு button மட்டும் பாப்பாங்க — balance, செலவு இல்ல. இந்த software எந்த bank-ஐயும் தொடர்பு கொள்ளாது.", "priv.delete": "என் data-ஐ அழி", "priv.deleted": "இந்த account-ஓட data எல்லாம் அழிச்சாச்சு.", "priv.never": "எப்பவும் கேக்க மாட்டோம்", "priv.controls": "இந்த build-ல இருக்கற controls",
      "guard.flow": "Customer → சம்மதம் → காப்பாளர் → Review → Approve", "guard.status": "காப்பாளர் status", "guard.none": "காப்பாளர் இல்ல", "guard.scope": "என்ன பாக்கலாம்", "guard.scope.d": "தொகை · rule reference · ஒரு approve button. எப்பவும் இல்ல: balance, சம்பளம், செலவு, மத்த transactions.", "guard.consent": "சம்மதம்", "guard.revoke": "Access-ஐ நீக்கு", "guard.revoked": "காப்பாளர் access நீக்கியாச்சு.", "guard.audit": "Audit history",
      "auth.h": "Bank IQ-ல sign in", "auth.lede": "உங்க statements இந்த machine-ல மட்டும், encrypt ஆயி (AES-256-GCM) இருக்கும். Password சேமிக்கப்படாது — salted PBKDF2 hash மட்டும்.", "auth.login": "Phone அல்லது email", "auth.name": "உங்க பேர்", "auth.pass": "Password (6+ எழுத்து)", "auth.signin": "Sign in", "auth.signup": "Account உருவாக்கு", "auth.toggle.up": "புதுசா? Account உருவாக்குங்க", "auth.toggle.in": "Account இருக்கா? Sign in", "auth.out": "Sign out", "auth.never": "Net-banking password, OTP, PIN, CVV எப்பவும் கேக்க மாட்டோம் — நீங்களே download பண்ற statement மட்டும்.",
      "alert.h": "Clock முடியறதுக்குள்ள action", "alert.lede": "சின்ன claim-ஐயும் விடமாட்டோம்: ஒவ்வொரு finding-க்கும் act-by தேதி இருக்கு. {n} நாளுக்குள்ள வந்தா சிவப்பு ஆகும், தொகை எவ்வளவானாலும் 'இப்பவே'-க்கு போகும், alert அனுப்பப்படும்.", "alert.chip": "⏰ {d}-க்குள்ள · {n} நாள்", "alert.over": "⏰ {d} தாண்டிடுச்சு · {n} நாள் — இப்பவே file பண்ணுங்க", "alert.open": "⏰ reverse ஆகல · நாளுக்கு ₹{p} சேருது", "alert.sent": "Telegram-க்கு alert போச்சு", "alert.sim": "Alert simulate ({r})", "n.tg.on": "Telegram alerts ON — chat {c}-க்கு போகும்", "n.tg.off": "Telegram alerts OFF (.env-ல VASOOL_TELEGRAM_TOKEN, VASOOL_TELEGRAM_CHAT போடுங்க).", "n.tgtest": "Test alert அனுப்பு",
      "case.ready": "CASE READY", "case.pack": "Evidence pack (print / PDF)", "case.inside": "Pack-ல: case ID · ஒவ்வொரு item-க்கும் தேதி, தொகை, RBI rule, தேதி வரம்பு · கணக்கு · statement lines Annexure A-ஆ · கேக்கற தீர்வு · 30 நாள் clock.",
      "home.multi": "ஒரே account-ஓட பல மாசம் / quarter statement-களை ஒரே நேரத்துல select பண்ணலாம்.",
      "home.current": "Open-ல இருக்கற account: {a}", "home.addto": "இதுக்கு இன்னொரு statement சேர்", "home.new": "இந்த form புது account-ஐ ஆரம்பிக்கும்.",
      "st.h": "Statements", "st.lede": "இந்த account-ஓட எல்லா statement-ம். Rules முழு history மேல ஓடும் — June penalty May balance வெச்சு பாக்கப்படும்.",
      "st.add": "இன்னொரு statement சேர்", "st.added": "+{n} புது lines · {d} duplicate தவிர்த்தாச்சு", "st.lines": "{n} lines", "st.new": "{n} புதுசு", "st.dup": "{n} duplicate", "st.remove": "நீக்கு", "st.covers": "இருக்கறது: {a} → {b}", "st.gap": "இடைவெளி: {a} → {b} — அந்த statement-ஐயும் upload பண்ணுங்க",
      "hist.h": "History", "hist.lede": "இந்த device-ல scan பண்ண எல்லா account-ம் — என்ன கிடைச்சது, என்ன திரும்ப வந்தது. விட்ட இடத்துல இருந்து தொடர ஒண்ணை open பண்ணுங்க.", "hist.none": "இன்னும் எதுவும் scan பண்ணல.",
      "hist.open": "Open", "hist.current": "இப்போ open", "hist.found": "கிடைச்சது", "hist.recovered": "திரும்ப வந்தது", "hist.stmts": "{n} statement", "hist.cases": "{n} case", "hist.opencases": "{n} open",
      "case.print": "Evidence pack (print / PDF)", "case.printomb": "Ombudsman draft print", "case.printhint": "A4 letter + Annexure A — 2 copy எடுத்து branch-க்கு போங்க, ஒண்ணுல seal வாங்குங்க.",
      "time.h": "Bank தாமதிக்கற ஒவ்வொரு நாளும்", "time.lede": "தேதியை இழுங்க. Reverse ஆகாத failed transaction-க்கு RBI/2019-20/67 படி நாளுக்கு ₹100 சேரும் — twin அந்த நாளுக்கு எல்லா claim-ஐயும் மறுபடி கணக்கிடும்.", "time.asof": "இந்த தேதி வரை", "time.today": "இன்று",
      "twin.h": "Twin", "twin.open": "Twin-ஐ பாரு", "twin.actual": "நடந்தது · ACTUAL", "twin.expected": "நடந்திருக்க வேண்டியது · EXPECTED", "twin.delta": "வித்தியாசம் · DELTA", "twin.claim": "POTENTIAL CLAIM", "twin.replay": "மறுபடி", "twin.back": "Findings-க்கு",
      "twin.debited": "debit · fail", "twin.due": "reversal due (T+{n})", "twin.perday": "இங்கிருந்து நாளுக்கு ₹{p}", "twin.reversed": "reverse ஆச்சு", "twin.noreversal": "{d} வரை reversal இல்ல", "twin.comp0": "compensation வந்தது: ₹0", "twin.late": "{n} நாள் late", "twin.day": "நாள் {n}",
      "twin.mb.expected": "{m} முழுசும் balance ₹{r}-க்கு மேல → penalty போடக்கூடாது", "twin.mb.actual": "{d} அன்று ₹{p} penalty", "twin.mb.lowest": "{m}-ல குறைந்த balance: ₹{l}", "twin.mb.blind": "{m} மாசத்தை twin பாக்க முடியல — அந்த statement upload ஆகல. சேர்த்தா verdict மாறலாம்.", "twin.mb.add": "அந்த statement-ஐ சேர்", "twin.mb.required": "தேவை ₹{r}",
      "twin.chain": "TRANSACTION + ACCOUNT STATE + RULE + CALCULATION + EVIDENCE → VERDICT. ஐந்தும் இல்லாம claim இல்ல.",
      "call.placed": "📞 {to}-க்கு call போகுது…", "call.sim": "Call simulate ({r})", "n.voice.on": "Voice ON — {f}-ல இருந்து உண்மையான தமிழ் call போகும்", "n.voice.off": "Voice OFF — call screen-ல simulate மட்டும் (.env-ல VASOOL_TWILIO_* போடுங்க).", "n.testcall": "Test call", "home.phone": "உங்க phone (தமிழ் call-க்கு)",
      "mail.sent": "{to}-க்கு email போயிடுச்சு", "mail.sim": "Email simulate பண்ணினோம் ({r})", "mail.also": "{to}-க்கும் email போச்சு",
      "g.email": "Email (உண்மையான one-button message இங்க போகும்)", "n.h": "உண்மையான delivery", "n.on": "Email ON — message-கள் உண்மையா போகும் ({f}-ல இருந்து)", "n.off": "Email OFF — காப்பாளர் message, complaint எல்லாம் screen-ல simulate மட்டும்.",
      "n.demo": "பாதுகாப்பு: எல்லா mail-ம் {to}-க்கு மட்டும் போகும்", "n.demo.phone": "பாதுகாப்பு: எல்லா call-ம் {to}-க்கு மட்டும் போகும்", "n.how": "ON பண்ண run.bat பக்கத்துல .env file-ல VASOOL_SMTP_USER, VASOOL_SMTP_PASS (Gmail app password), VASOOL_DEMO_TO போடுங்க. Bank-க்கு எப்பவும் அனுப்ப மாட்டோம்.", "n.test": "Test mail அனுப்பு", "n.bank": "இந்த demo bank-க்கு நேரடியா mail பண்ணாது.",
      "ap.h": "Bank IQ உங்க OK கேக்குது", "ap.for": "{b}-ல {h}-ஓட account-க்கு", "ap.yes": "✓ சரி, complaint அனுப்பு", "ap.no": "இப்போ வேண்டாம்", "ap.done": "Bank-க்கு போயிடுச்சு. நன்றி — 30 நாள் clock-ஐ நாங்க பாத்துக்கறோம்.", "ap.used": "இந்த request-க்கு ஏற்கனவே பதில் சொல்லியாச்சு.", "ap.note": "Balance, செலவு விவரம் எதுவும் இதுல இல்ல. Complaint மட்டும் bank-க்கு போகும்.",
      "foot.privacy": "Transactions-ஐ check பண்றோம்; விக்கறது இல்ல. Password எப்பவும் கேக்க மாட்டோம்.",
      "home.h1": "உங்க bank உங்களுக்கு பணம் கடன் பட்டிருந்தா?",
      "home.lede": "ஒரு statement அல்லது passbook photo கொடுங்க. RBI rulebook-ஐ அதுல ஓட்டி, bank உங்களுக்கு என்ன தரணும்-னு சொல்றோம் — ஒவ்வொரு ரூபாய்க்கும் rule பக்கத்துலயே. நீங்க சொல்லாம யாருக்கும் எதுவும் அனுப்ப மாட்டோம்.",
      "home.drop": "Statement-ஐ இங்க போடுங்க — PDF, CSV அல்லது passbook photo", "home.or": "அல்லது sample-ஐ பாருங்க",
      "home.bank": "Bank", "home.type": "Account வகை", "home.city": "ஊர்", "home.minbal": "Bank கேக்கற minimum balance (₹)", "home.name": "உங்க பேர்", "home.scan": "என் account-ஐ check பண்ணு",
      "home.privacy": "இந்த server-ல process ஆகும்; transactions மட்டும் சேமிக்கப்படும்; எப்போ வேணா அழிக்கலாம். Net-banking password, PIN எப்பவும் கேக்க மாட்டோம்.",
      "found.h": "திரும்ப வரலாம்", "found.sub": "{n} potential claim — statement-ல ஆதாரம் இருக்கு", "found.unclear": "{n}-க்கு உங்க ஒரு பதில் வேணும்", "found.avoid": "{n}-ஐ அடுத்த முறை தடுக்கலாம்",
      "found.charges": "இந்த காலத்துல bank charges: {a}", "found.none": "எல்லாம் சரியா இருக்கு. எதுவும் பண்ண வேண்டாம்.", "found.watch": "நாங்க பாத்துட்டே இருப்போம்.",
      "found.getback": "திரும்ப வாங்கு", "found.effort": "உங்க வேலை: சுமார் 2 நிமிஷம்",
      "sec.now": "இப்பவே கேக்கலாம்", "sec.ask": "உங்க ஒரு பதில் போதும்", "sec.combine": "சின்னது — சேர்த்து ஒரே complaint", "sec.skip": "ரொம்ப சின்னது — நாங்க பாத்துக்கறோம்", "sec.prevent": "சரி தான் — ஆனா அடுத்ததை தடுக்கலாம்",
      "why": "Evidence chain", "hide": "மூடு", "expected": "நடந்திருக்க வேண்டியது", "actual": "நடந்தது", "calc": "கணக்கு", "rule": "உங்க உரிமை", "source": "RBI source", "confidence": "நம்பகம்", "evidence": "Statement lines",
      "prevent": "அடுத்ததை தடுக்க", "answer": "பதில்:", "yes": "ஆமா", "no": "இல்ல", "not_sure": "தெரியல",
      "case.h": "உங்க case", "case.prepared": "Complaint தயார். இன்னும் எதுவும் அனுப்பல.", "case.guardian": "என் காப்பாளரை கேளு", "case.send": "நானே அனுப்பறேன்", "case.preview": "Complaint-ஐ படி",
      "case.callh": "அம்மா phone அடிக்குது", "case.play": "Call-ஐ கேளு", "case.stop": "நிறுத்து", "case.press1": "1 அழுத்து — {g}-ஐ கூப்பிடு", "case.press2": "2 அழுத்து — இப்போ வேண்டாம்",
      "case.wa": "{g}-க்கு WhatsApp", "case.approve": "{g}-ஆ OK சொல்லு", "case.sent": "OK ஆச்சு. Evidence pack தயார் — இந்த app அனுப்பாது. 30 நாள் clock-ஐ பாத்துக்கறோம்.", "case.days": "Bank பதில் சொல்ல {d} நாள் இருக்கு",
      "case.bankreplied": "Bank பதில் சொல்லிடுச்சு", "case.recovered": "பணம் வந்துடுச்சு", "case.bankright": "Bank சரி-ன்னு காட்டிடுச்சு", "case.escalate": "RBI Ombudsman-க்கு", "case.check": "அடுத்த statement-ல refund-ஐ check பண்ணு",
      "case.download": "Complaint text", "case.omb": "Ombudsman draft", "case.timeline": "இதுவரை நடந்தது",
      "cases.h": "Cases", "cases.none": "இன்னும் case இல்ல. எதாவது கிடைச்சா 'திரும்ப வாங்கு' case உருவாக்கும்.",
      "ask.h": "Bank IQ-கிட்ட கேளுங்க", "ask.ph": "ஏன் bank ₹295 cut பண்ணுச்சு?", "ask.send": "கேளு", "ask.hint": "தமிழ்ல அல்லது English-ல கேளுங்க. உதாரணம்: என்ன ஆச்சு? · எவ்வளவு? · நான் என்ன பண்ணணும்? · KFS எங்க?",
      "rules.h": "Rulebook", "rules.lede": "Bank IQ check பண்ற ஒவ்வொரு rule-ம், RBI source-ம் தேதியும். Open data — யார் வேணா audit பண்ணலாம்.",
      "settings.h": "Settings", "g.h": "காப்பாளர் (Guardian)", "g.lede": "நீங்க நம்புற ஒருத்தர். முதல்ல உங்களுக்கு phone பண்ணுவோம், அப்புறம் அவங்களுக்கு ஒரு message. உங்க balance, செலவு அவங்களுக்கு தெரியாது.",
      "g.name": "பேர்", "g.rel": "உறவு", "g.phone": "Phone", "g.consent": "உங்க சம்மதம், உங்க வார்த்தையில", "g.save": "காப்பாளரை சேமி",
      "s.delete": "என் data எல்லாத்தையும் அழி", "s.deleted": "அழிச்சாச்சு.", "s.basic": "Zero-charge Basic account-க்கு மாத்த letter",
      "noacct": "முதல்ல statement-ஐ scan பண்ணுங்க.", "err": "ஏதோ தப்பு: ",
      "priority.RECOVER_NOW": "இப்பவே", "priority.COMBINE": "சேர்த்து", "priority.NOT_WORTH_IT": "பாத்துக்கறோம்", "priority.PREVENT": "தடுக்கலாம்",
      "label.RECOVERABLE": "Potential claim · rule மீறல்", "label.AVOIDABLE": "சரி · தடுக்கலாம்", "label.UNCLEAR": "ஒரு பதில் வேணும்",
      "conf.CONFIRMED": "உறுதி", "conf.NEEDS_CHECKING": "Check பண்ணணும்", "conf.INFO": "தகவல்",
      "suspicious": "இது fail ஆயி மறுபடி பண்ண payment மாதிரி இருக்கு. Fail ஆச்சா?",
      "state": { FOUND: "கண்டுபிடிச்சது", PREPARED: "தயார்", AWAITING_APPROVAL: "OK-க்கு காத்திருக்கு", SENT_TO_BANK: "Submit பண்ண தயார்", BANK_REPLIED: "Bank பதில்", DEADLINE_PASSED: "Deadline முடிஞ்சது", ESCALATED_OMBUDSMAN: "Ombudsman", RECOVERED: "வந்துடுச்சு", CLOSED_BANK_RIGHT: "Bank சரி", CLOSED_BY_USER: "மூடியது" },
    },
  };
  const S = window.__VR = { lang: localStorage.getItem("vr.lang") || "ta", accountId: localStorage.getItem("vr.account") || null, data: null, cases: [], openWhy: new Set(), chat: [] };
  const t = (k, vars) => { let s = (T[S.lang][k] ?? T.en[k] ?? k); if (typeof s === "string" && vars) for (const [a, b] of Object.entries(vars)) s = s.replaceAll(`{${a}}`, b); return s; };
  const inr = (x) => { const n = Number(x || 0); const frac = Math.abs(n - Math.round(n)) > 0.004; return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: frac ? 2 : 0, maximumFractionDigits: 2 }); };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  // ------------------------------------------------------------------ api
  async function api(path, opts = {}) {
    const r = await fetch("/api" + path, opts);
    if (r.status === 401 && !path.startsWith("/auth/")) { S.user = null; if (!location.hash.startsWith("#/login")) { S.after = location.hash; location.hash = "#/login"; } throw new Error("login required"); }
    if (!r.ok) { let m = r.statusText; try { const j = await r.json(); const d = j.detail ?? j; m = typeof d === "string" ? d : (d.message ? d.message + (d.warnings?.length ? " · " + d.warnings.join(" · ") : "") : JSON.stringify(d)); } catch { } throw new Error(m); }
    const ct = r.headers.get("content-type") || "";
    return ct.includes("json") ? r.json() : r.text();
  }
  const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

  function toast(msg, ms = 2600) { const el = $("#toast"); el.textContent = msg; el.hidden = false; clearTimeout(el._t); el._t = setTimeout(() => (el.hidden = true), ms); }

  // ------------------------------------------------------------------ speech
  function speak(text, lang) {
    try {
      if (!("speechSynthesis" in window)) return false;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = lang === "ta" ? "ta-IN" : "en-IN";
      const voices = window.speechSynthesis.getVoices();
      const v = voices.find((v) => v.lang.toLowerCase().startsWith(lang === "ta" ? "ta" : "en-in")) || voices.find((v) => v.lang.toLowerCase().startsWith("en"));
      if (v) u.voice = v;
      u.rate = 0.92;
      window.speechSynthesis.speak(u);
      return true;
    } catch { return false; }
  }
  function listen(onText) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast("Voice input isn't available in this browser — type instead."); return null; }
    const r = new SR(); r.lang = S.lang === "ta" ? "ta-IN" : "en-IN"; r.interimResults = false; r.maxAlternatives = 1;
    r.onresult = (e) => onText(e.results[0][0].transcript);
    r.onerror = () => toast("Couldn't hear that. Try again.");
    r.start();
    return r;
  }

  // ------------------------------------------------------------------ shell
  function applyLang() {
    $("#lang-ta").setAttribute("aria-pressed", S.lang === "ta");
    $("#lang-en").setAttribute("aria-pressed", S.lang === "en");
    $$("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
    document.documentElement.lang = S.lang;
  }
  function setLang(l) { S.lang = l; localStorage.setItem("vr.lang", l); applyLang(); route(); }
  $("#lang-ta").onclick = () => setLang("ta");
  $("#lang-en").onclick = () => setLang("en");

  async function loadAccount() {
    if (!S.accountId) return null;
    try { S.data = await api(`/accounts/${S.accountId}`); S.cases = S.data.cases || []; return S.data; }
    catch { S.accountId = null; localStorage.removeItem("vr.account"); return null; }
  }

  // ------------------------------------------------------------------ screens
  async function screenHome() {
    const samples = S.samples = await api("/samples").catch(() => []);
    const lang = S.lang;
    const dash = S.data ? await dashboard() : "";
    return `
    <div class="stack">
      ${dash || `<section class="card dark">
        <div class="eyebrow">Bank IQ Scan</div>
        <h1 style="margin-top:8px">${esc(t("home.h1"))}</h1>
        <p style="margin-top:12px;max-width:62ch;color:#DCE8E0">${esc(t("home.lede"))}</p>
      </section>`}
      ${S.data ? `<div class="section-title"><h2>${esc(t("dash.scan.more"))}</h2></div>` : ""}
      <div id="scanprogress" hidden></div>
      <form id="scanform" class="card stack">
        <label class="drop" id="drop">
          <input type="file" id="file" name="file" multiple accept=".csv,.tsv,.txt,.pdf,.xlsx,.jpg,.jpeg,.png,.webp">
          <div><strong id="dropname">${esc(t("home.drop"))}</strong></div>
          <div class="muted" style="margin-top:6px">PDF · CSV · XLSX · JPG/PNG · ${esc(t("home.multi"))}</div>
        </label>
        <div class="row">
          <span class="muted">${esc(t("home.or"))}</span>
          ${samples.map((s) => `<button type="button" class="btn sm sample" data-name="${esc(s.name)}">${esc(s.name.replace(/_/g, " ").replace(/\.(csv|tsv)$/, ""))}</button>`).join("")}
        </div>
        <div class="grid2">
          <label class="field">${esc(t("home.bank"))}<select name="bank"><option value="">Auto-detect</option>${["SBI", "HDFC", "ICICI", "AXIS", "CANARA", "PNB", "BOB", "UNION", "KOTAK", "INDIAN BANK", "IOB", "BOI", "TMB", "CUB", "KVB", "FEDERAL"].map((b) => `<option>${b}</option>`).join("")}</select></label>
          <label class="field">${esc(t("home.type"))}<select name="account_type"><option value="SAVINGS">Savings</option><option value="SALARY">Salary</option><option value="PENSION">Pension</option><option value="BSBDA">Basic (BSBDA / Jan Dhan)</option><option value="CURRENT">Current</option></select></label>
          <label class="field">${esc(t("home.city"))}<select name="city_tier"><option value="NON_METRO">Non-metro (Coimbatore, Madurai…)</option><option value="METRO">Metro (Chennai, Bengaluru, Mumbai…)</option></select></label>
          <label class="field">${esc(t("home.minbal"))}<input name="min_balance_required" type="number" min="0" step="1" placeholder="e.g. 500 / 1000 / 10000"></label>
          <label class="field">${esc(t("home.name"))}<input name="holder_name" placeholder="Selvi R"></label>
          <label class="field">${esc(t("home.phone"))}<input name="holder_phone" placeholder="+91 98765 43210"></label>
          <label class="field">As of (for demo)<input name="as_of" type="date" value="${new Date().toISOString().slice(0, 10)}"></label>
        </div>
        <div class="row" style="justify-content:space-between">
          <span class="muted" style="max-width:56ch;font-size:.85rem">${esc(t("home.privacy"))}</span>
          <button class="btn primary" type="submit" id="scanbtn">${esc(t("home.scan"))}</button>
        </div>
      </form>
      ${S.accountId && S.data ? `<section class="card soft row" style="justify-content:space-between"><div><div class="eyebrow">${esc(t("home.current", { a: acctLabel(S.data) }))}</div><div class="muted" style="font-size:.9rem">${esc(t("home.new"))}</div></div><div class="row"><a class="btn" href="#/findings">↩ ${esc(t("nav.findings"))}</a><a class="btn gold" href="#/findings#statements">${esc(t("home.addto"))}</a></div></section>` : ""}
      ${await accountsList()}
    </div>`;
  }

  // ---- dashboard (home, once an account is open) --------------------------------
  const isDemo = (d) => (d.statements || []).some((x) => /^(canara|sbi|hdfc|indianbank|passbook)/.test(x.filename || ""));
  async function dashboard() {
    const d = S.data, s = d.summary, F = d.findings;
    let tw = null; try { tw = S.twin = await api(`/accounts/${S.accountId}/twin`); } catch { }
    const c = tw?.counts || {};
    const rec = F.filter((f) => f.label === "RECOVERABLE"), action = rec.filter((f) => f.priority === "RECOVER_NOW" || f.priority === "COMBINE"), unc = F.filter((f) => f.label === "UNCLEAR"), info = F.filter((f) => f.label === "AVOIDABLE" || (f.label === "RECOVERABLE" && f.priority === "NOT_WORTH_IT"));
    const last = (d.statements || []).map((x) => x.uploaded_at || "").sort().pop() || "";
    const tile = (k, v) => `<div class="tile"><div class="eyebrow">${esc(t(k))}</div><div class="v">${v}</div></div>`;
    return `
      <section class="card dark">
        <div class="eyebrow">${esc(t("dash.q"))}</div>
        <div class="row" style="align-items:flex-end;gap:28px;margin-top:8px">
          <div><div class="hero-amount" style="font-size:clamp(2.2rem,7vw,3.6rem)">${inr(s.total_recoverable)}</div><div class="eyebrow" style="color:var(--mint)">${esc(t("dash.potential"))}</div></div>
          <div class="stack" style="gap:4px;color:#DCE8E0">
            <div><b>${esc(t("dash.findings", { n: F.length }))}</b></div>
            <div>🔴 ${esc(t("dash.action", { n: action.length }))}</div>
            <div>🟡 ${esc(t("dash.confirm", { n: unc.length }))}</div>
            <div>🟢 ${esc(t("dash.info", { n: info.length }))}</div>
            ${F.some((f) => f.alert) ? `<div style="color:#FFB4A8;font-weight:600">⏰ ${F.filter((f) => f.alert).length} ${esc(t("alert.h").toLowerCase())}</div>` : ""}
          </div>
        </div>
        <p class="muted" style="color:#9DB8A8;margin:10px 0 0;max-width:70ch;font-size:.9rem">${esc(t("dash.honest"))}</p>
        <div class="row" style="margin-top:12px"><a class="btn gold" href="#/findings" style="font-size:1.05rem;padding:12px 22px">${esc(t("dash.review"))} →</a><a class="btn" style="background:transparent;color:#fff;border-color:rgba(255,255,255,.4)" href="#/twin">${esc(t("dash.twin"))}</a></div>
        ${isDemo(d) ? `<div class="demo-tag">${esc(t("dash.demo"))}</div>` : ""}
      </section>
      <section class="card">
        <div class="section-title" style="margin-top:0"><h2>${esc(t("dash.overview"))}</h2><span class="count">${esc(acctLabel(d))}</span></div>
        <div class="tiles">
          ${tile("dash.period", `<span class="mono" style="font-size:.95rem">${esc(s.period.from)} → ${esc(s.period.to)}</span>`)}
          ${tile("dash.txns", c.transactions ?? s.transactions)}
          ${tile("dash.charges", c.charges ?? "—")}
          ${tile("dash.reversals", c.pairs != null ? `${c.pairs} <span class="muted" style="font-size:.8rem">+${c.unreversed_failed} open</span>` : "—")}
          ${tile("dash.rules", c.rules_evaluated ?? "—")}
          ${tile("dash.months", c.months ?? "—")}
          ${tile("dash.last", `<span class="mono" style="font-size:.9rem">${esc(last.slice(0, 16).replace("T", " ") || "—")}</span>`)}
        </div>
      </section>`;
  }
  async function accountsList() {
    const accts = await api("/accounts").catch(() => []);
    if (!accts.length) return "";
    return `<div class="section-title"><h2>${esc(t("dash.accounts"))}</h2><span class="count">${accts.length}</span></div>` + accts.map((a) => { const cur = a.id === S.accountId; const p = a.profile || {}; return `
      <article class="card ${cur ? "soft" : ""}" data-id="${esc(a.id)}">
        <div class="row" style="justify-content:space-between;align-items:flex-start">
          <div>
            <div class="pillrow">${cur ? `<span class="chip green">${esc(t("hist.current"))}</span>` : ""}<span class="chip grey mono">${esc(a.id)}</span><span class="chip grey">${esc(t("hist.stmts", { n: a.statements }))}</span>${a.cases ? `<span class="chip ${a.open_cases ? "amb" : "grey"}">${esc(t("hist.cases", { n: a.cases }))}</span>` : ""}</div>
            <h3 style="margin-top:6px">${esc(p.bank || "?")}${p.account_last4 ? " ····" + esc(p.account_last4) : ""}${p.holder_name ? " · " + esc(p.holder_name) : ""}</h3>
            <div class="muted mono" style="font-size:.8rem">${esc(a.period.from || "")} → ${esc(a.period.to || "")} · ${a.transactions} lines</div>
          </div>
          <div style="text-align:right">
            <div class="display" style="font-size:1.4rem;color:var(--green);font-family:var(--head);font-weight:700">${inr(a.total_recoverable)} <span class="muted" style="font-size:.75rem;font-weight:400">${esc(t("hist.found"))}</span></div>
            <div class="row" style="justify-content:flex-end;margin-top:6px"><button class="btn sm ${cur ? "" : "primary"} h-open" data-id="${esc(a.id)}">${esc(cur ? t("nav.findings") : t("hist.open"))} →</button><button class="btn sm ghost h-del" data-id="${esc(a.id)}" style="color:var(--red)">✕</button></div>
          </div>
        </div>
      </article>`; }).join("");
  }

  // ---- the scan experience: a real timeline, real numbers, no fake statistics -------------
  async function runScanExperience(request) {
    const box = $("#scanprogress"), form = $("#scanform");
    const steps = [1, 2, 3, 4, 5, 6];
    box.hidden = false; form.hidden = true;
    box.innerHTML = `<section class="card scanning"><div class="eyebrow">${esc(t("scan.h"))}</div><ol class="steps">${steps.map((i) => `<li id="step${i}"><span class="dot"></span><div><b>${esc(t("scan." + i))}</b><small id="step${i}d"></small></div></li>`).join("")}</ol><div id="scandone" hidden><div class="done-h">${esc(t("scan.done"))}</div><a class="btn gold" href="#/findings" id="scanopen">${esc(t("scan.open"))} →</a></div></section>`;
    window.scrollTo({ top: box.offsetTop - 80, behavior: "smooth" });
    let i = 0; const tick = () => { if (i < 4) { $(`#step${i + 1}`).classList.add("run"); i++; } };
    tick(); const timer = setInterval(tick, 420);
    let d, tw;
    try { d = await request(); } catch (e) { clearInterval(timer); box.hidden = true; form.hidden = false; throw e; }
    S.accountId = d.account_id; localStorage.setItem("vr.account", d.account_id); S.data = d; S.cases = d.cases || [];
    try { tw = S.twin = await api(`/accounts/${d.account_id}/twin`); } catch { tw = { counts: {} }; }
    clearInterval(timer);
    const c = tw.counts || {};
    const detail = { 1: t("scan.1d", { n: c.transactions ?? d.transactions.length }), 2: t("scan.2d", { n: c.months ?? "?", b: (tw.balance_path || []).length }), 3: t("scan.3d", { p: c.pairs ?? 0, u: c.unreversed_failed ?? 0 }), 4: t("scan.4d", { n: c.rules_evaluated ?? "?" }), 5: t("scan.5d"), 6: t("scan.6d", { n: d.findings.length, f: c.flagged_lines ?? "?", u: c.unflagged_lines ?? "?" }) };
    for (const k of steps) { await new Promise((r) => setTimeout(r, 260)); const li = $(`#step${k}`); li.classList.remove("run"); li.classList.add("ok"); $(`#step${k}d`).textContent = detail[k]; }
    $("#scandone").hidden = false;
    setTimeout(() => { if (location.hash === "#/" || location.hash === "") location.hash = "#/findings"; }, 1600);
    return d;
  }
  const acctLabel = (d) => `${d.profile?.bank || d.summary?.bank || ""}${d.profile?.account_last4 ? " ····" + d.profile.account_last4 : ""}${d.profile?.holder_name ? " · " + d.profile.holder_name : ""}`;

  function bindHome() {
    const form = $("#scanform"), drop = $("#drop"), file = $("#file");
    let sampleName = null;
    file.onchange = () => { sampleName = null; const n = file.files.length; $("#dropname").textContent = n > 1 ? `${n} files: ` + [...file.files].map((f) => f.name).join(", ") : file.files[0]?.name || t("home.drop"); };
    ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", (e) => { file.files = e.dataTransfer.files; file.onchange(); });
    $$(".sample").forEach((b) => (b.onclick = () => { sampleName = b.dataset.name; $("#dropname").textContent = "Sample: " + sampleName; $$(".sample").forEach((x) => x.classList.remove("gold")); b.classList.add("gold");
      // sensible demo defaults per sample
      const f = form.elements;
      if (sampleName.startsWith("canara")) { f.bank.value = "CANARA"; f.account_type.value = "PENSION"; f.city_tier.value = "NON_METRO"; f.min_balance_required.value = 500; f.holder_name.value = "Selvi R"; f.as_of.value = "2026-09-13"; }
      if (sampleName.startsWith("sbi")) { f.bank.value = "SBI"; f.account_type.value = "SAVINGS"; f.city_tier.value = "NON_METRO"; f.min_balance_required.value = 0; f.holder_name.value = "Arun K"; f.as_of.value = "2025-07-01"; }
      if (sampleName.startsWith("hdfc")) { f.bank.value = "HDFC"; f.account_type.value = "SALARY"; f.city_tier.value = "METRO"; f.min_balance_required.value = 10000; f.holder_name.value = "Priya S"; f.as_of.value = "2026-04-01"; }
      if (sampleName.startsWith("indianbank")) { f.bank.value = "INDIAN BANK"; f.account_type.value = "SAVINGS"; f.city_tier.value = "NON_METRO"; f.min_balance_required.value = 500; f.holder_name.value = "Murugan P"; f.as_of.value = "2026-09-13"; }
    }));
    form.onsubmit = async (e) => {
      e.preventDefault();
      const f = form.elements;
      const fd = new FormData();
      if (sampleName) { fd.append("file", await (await fetch(`/api/samples/${sampleName}`)).blob(), sampleName); }
      else if (file.files.length) { [...file.files].forEach((f) => fd.append("files", f, f.name)); }
      else { toast(t("home.drop")); return; }
      fd.append("profile", JSON.stringify({ bank: f.bank.value, account_type: f.account_type.value, city_tier: f.city_tier.value, min_balance_required: f.min_balance_required.value ? Number(f.min_balance_required.value) : null, holder_name: f.holder_name.value, holder_phone: f.holder_phone.value, language: S.lang }));
      if (f.as_of.value) fd.append("as_of", f.as_of.value);
      $("#scanbtn").disabled = true; $("#scanbtn").textContent = "Bank IQ Scan…";
      try {
        const d = await runScanExperience(() => api("/scan", { method: "POST", body: fd }));
        if ((d.upload || []).length > 1) toast(d.upload.map((u) => `${u.filename}: +${u.new}${u.duplicates ? " · " + u.duplicates + " dup" : ""}`).join("  |  "), 5000);
      } catch (err) { toast(t("err") + err.message, 6000); $("#scanbtn").disabled = false; $("#scanbtn").textContent = t("home.scan"); }
    };
    bindHistory();
  }

  // ---- findings ------------------------------------------------------------
  const txnById = () => Object.fromEntries((S.data?.transactions || []).map((x) => [x.id, x]));
  const rulesCache = {};
  async function getRule(id) { if (!rulesCache[id]) rulesCache[id] = await api(`/rules/${id}`); return rulesCache[id]; }

  function findingCard(f) {
    const lang = S.lang, red = f.label === "RECOVERABLE", amb = f.label === "AVOIDABLE";
    const chipCls = red ? "red" : amb ? "amb" : "grey";
    const open = S.openWhy.has(f.id);
    const qs = (f.questions || []).map((q) => `
      <div class="qbtns" data-q="${esc(q.id)}" data-txn="${esc(f.evidence[0] || "")}">
        <span class="muted">${esc(lang === "ta" ? q.ta : q.en)}</span>
        ${(q.options || ["yes", "no", "not_sure"]).map((o) => `<button class="btn sm ans" data-val="${esc(o)}">${esc(t(o))}</button>`).join("")}
      </div>`).join("");
    return `
    <article class="card finding" data-id="${esc(f.id)}">
      <div>
        <div class="pillrow"><span class="chip ${chipCls}">${esc(t("label." + f.label))}</span><span class="chip grey">${esc(t("conf." + f.confidence))}</span><span class="chip green">${esc(t("priority." + f.priority))}</span><span class="chip grey mono">${esc(f.rule_id)}</span>${f.alert ? `<span class="chip red alert">${esc(f.twin && f.twin.kind === "tat" && f.twin.reversed === false ? t("alert.open", { p: f.twin.per_day }) : f.days_left < 0 ? t("alert.over", { d: f.act_by, n: -f.days_left }) : t("alert.chip", { d: f.act_by, n: f.days_left }))}</span>` : (f.act_by && f.label !== "AVOIDABLE" ? `<span class="chip grey">${esc(t("alert.chip", { d: f.act_by, n: f.days_left }))}</span>` : "")}</div>
        <p class="summary" style="margin-top:8px">${esc(lang === "ta" ? f.summary_ta : f.summary_en)}</p>
        ${amb && (f.prevention_en || f.prevention_ta) ? `<p class="muted" style="font-size:.92rem">↳ ${esc(lang === "ta" ? f.prevention_ta : f.prevention_en)}</p>` : ""}
      </div>
      <div class="amt ${amb ? "" : ""}">${f.amount ? inr(f.amount) : ""}</div>
      <div class="actions">
        <button class="btn sm why-toggle">${open ? esc(t("hide")) : esc(t("why"))}</button>
        <button class="btn sm ghost speak" data-text="${esc(lang === "ta" ? f.summary_ta : f.summary_en)}">🔊</button>
        ${f.twin && f.twin.kind ? `<button class="btn sm gold twin-open" data-id="${esc(f.id)}">⇄ ${esc(t("twin.open"))}</button>` : ""}
        ${qs}
      </div>
      ${open ? `<div class="why" data-why="${esc(f.id)}"><div class="muted">…</div></div>` : ""}
    </article>`;
  }

  async function renderWhy(f, el) {
    const rule = await getRule(f.rule_id);
    const byId = txnById();
    const rows = f.evidence.map((id) => byId[id]).filter(Boolean);
    const L = S.lang, right = L === "ta" ? rule.right_ta || rule.right_en : rule.right_en;
    const step = (n, title, body, cls = "") => `<li class="${cls}"><span class="n">${n}</span><div><b>${esc(title)}</b><div>${body}</div></div></li>`;
    const table = `<div class="evidence"><table><thead><tr><th>Date</th><th>Narration</th><th class="r">Debit</th><th class="r">Credit</th><th class="r">Balance</th><th>Ref</th></tr></thead><tbody>
        ${rows.map((r) => `<tr><td>${esc(r.date)}</td><td>${esc(r.narration)}</td><td class="r">${r.debit ? inr(r.debit) : ""}</td><td class="r">${r.credit ? inr(r.credit) : ""}</td><td class="r">${r.balance != null ? inr(r.balance) : ""}</td><td>${esc(r.ref)}</td></tr>`).join("")}
      </tbody></table></div>`;
    const claim = f.label === "RECOVERABLE";
    el.innerHTML = `
      <div class="eyebrow" style="margin-bottom:6px">${esc(t("chain.h"))} · ${esc(t("chain.status." + f.confidence))}</div>
      <ol class="chain">
        ${step(1, t("chain.1"), esc(f.actual))}
        ${step(2, t("chain.2"), esc(f.expected))}
        ${step(3, t("chain.3"), esc(L === "ta" ? f.summary_ta : f.summary_en))}
        ${step(4, t("chain.4"), `${esc(right)}${f.priority_reasons?.length ? `<div class="muted" style="font-size:.85rem;margin-top:4px">${esc(t("chain.cond"))}: ${esc(f.priority_reasons.join(" · "))}</div>` : ""}`)}
        ${step(5, t("chain.5"), table)}
        ${step(6, t("chain.6"), `<span class="chip grey mono">${esc(rule.id)}</span> ${esc(rule.title)}<div class="src" style="margin-top:4px"><a href="${esc(rule.source.url)}" target="_blank" rel="noopener">${esc(rule.source.circular)}</a> · ${esc(rule.source.date)} · ${esc(t("chain.inforce"))} ${esc(rule.effective_from)}${rule.effective_to ? " → " + esc(rule.effective_to) : " → present"}</div>`)}
        ${step(7, t("chain.7"), `<span class="mono">${esc(f.calculation)}</span>`)}
        ${step(8, claim ? t("chain.8") : t("chain.info"), `<b style="font-size:1.25rem;color:var(--green)">${f.amount ? inr(f.amount) : "—"}</b> <span class="muted">· ${esc(t("conf." + f.confidence))} · ${f.evidence.length} evidence line(s)</span>${f.prevention_en ? `<div class="muted" style="margin-top:4px">${esc(t("prevent"))}: ${esc(L === "ta" ? f.prevention_ta : f.prevention_en)}</div>` : ""}`, claim ? "claim" : "")}
      </ol>
      <div class="mono muted" style="font-size:.72rem;margin-top:8px">${esc(t("chain.foot"))}</div>`;
  }

  function screenFindings() {
    if (!S.data) return `<div class="empty">${esc(t("noacct"))} <a href="#/">Scan</a></div>`;
    const d = S.data, s = d.summary, F = d.findings;
    const rec = F.filter((f) => f.label === "RECOVERABLE"), unc = F.filter((f) => f.label === "UNCLEAR"), avo = F.filter((f) => f.label === "AVOIDABLE");
    const now = rec.filter((f) => f.priority === "RECOVER_NOW"), comb = rec.filter((f) => f.priority === "COMBINE"), skip = rec.filter((f) => f.priority === "NOT_WORTH_IT");
    const byId = txnById();
    const sus = (d.suspicious_debits || []).map((id) => byId[id]).filter(Boolean).filter((x) => !(d.account_answers || {})[`txn_failed:${x.id}`]);
    const q = d.questions_for_suspicious;
    const section = (key, arr) => arr.length ? `<div class="section-title"><h2>${esc(t(key))}</h2><span class="count">${arr.length}</span></div>${arr.map(findingCard).join("")}` : "";
    const openCase = S.cases.find((c) => !["RECOVERED", "CLOSED_BANK_RIGHT", "CLOSED_BY_USER"].includes(c.state));
    const cov = d.coverage || {};
    const hasTat = F.some((f) => f.twin && f.twin.kind === "tat" && !f.twin.reversed);
    return `
    <div class="stack">
      <section class="card ${s.total_recoverable > 0 ? "dark" : "soft"}">
        <div class="eyebrow">Bank IQ Scan · ${esc(s.bank || "")} ${d.profile.account_last4 ? "····" + esc(d.profile.account_last4) : ""} · ${esc(cov.from || s.period.from || "")} → ${esc(cov.to || s.period.to || "")}${(d.statements || []).length > 1 ? " · " + esc(t("hist.stmts", { n: d.statements.length })) : ""}</div>
        ${s.total_recoverable > 0 ? `
          <div class="hero-amount" style="margin-top:10px"><span id="hero-n" data-v="${s.total_recoverable}">${inr(s.total_recoverable)}</span> <span style="font-size:.45em">${esc(t("found.h"))}</span></div>
          <p style="margin-top:8px;color:#DCE8E0">${esc(t("found.sub", { n: rec.length }))}${unc.length ? " · " + esc(t("found.unclear", { n: unc.length })) : ""}${avo.length ? " · " + esc(t("found.avoid", { n: avo.length })) : ""}</p>
          <p class="muted" style="color:#9DB8A8;font-size:.88rem;max-width:70ch">${esc(t("dash.honest"))}</p>
          <p class="muted" style="color:#9DB8A8">${esc(t("found.charges", { a: inr(s.total_bank_charges_in_period) }))}</p>
          <div class="row" style="margin-top:8px">
            ${openCase ? `<a class="btn gold" href="#/case/${esc(openCase.id)}">${esc(t("case.h"))} ${esc(openCase.id)} →</a>` : `<button class="btn gold" id="getback" style="font-size:1.1rem;padding:14px 24px">${esc(t("found.getback"))}</button>`}
            <span style="color:#DCE8E0">${esc(t("found.effort"))}</span>
          </div>` : `
          <h1 style="margin-top:8px;color:var(--green)">${esc(t("found.none"))}</h1>
          <p class="muted">${esc(t("found.watch"))}${unc.length ? " · " + esc(t("found.unclear", { n: unc.length })) : ""}</p>`}
        ${s.warnings?.length ? `<p class="muted" style="font-size:.82rem;margin-top:8px">${s.warnings.map(esc).join("<br>")}</p>` : ""}
      </section>
      ${(() => { const al = F.filter((f) => f.alert); return al.length ? `<section class="card alertbar"><div class="section-title" style="margin-top:0"><h2>🔴 ${esc(t("alert.h"))}</h2><span class="count">${al.length}</span></div><p style="margin:0">${esc(t("alert.lede", { n: d.alert_days || 60 }))}</p><div class="pillrow" style="margin-top:8px">${al.map((f) => `<span class="chip red">${inr(f.amount)} · ${esc(f.rule_id)} · ${f.days_left}d</span>`).join("")}</div></section>` : ""; })()}
      ${hasTat ? timeCard(d) : ""}
      ${sus.length ? `<section class="card warn"><h3>${esc(t("suspicious"))}</h3>${sus.map((x) => `<div class="qbtns" data-q="txn_failed" data-txn="${esc(x.id)}" style="margin-top:8px"><span class="mono">${esc(x.date)} · ${esc(x.narration)} · ${inr(x.debit)}</span>${["yes", "no", "not_sure"].map((o) => `<button class="btn sm ans" data-val="${o}">${esc(t(o))}</button>`).join("")}</div>`).join("")}</section>` : ""}
      ${section("sec.now", now)}
      ${section("sec.ask", unc)}
      ${section("sec.combine", comb)}
      ${section("sec.skip", skip)}
      ${section("sec.prevent", avo)}
      ${statementsCard(d)}
    </div>`;
  }

  function timeCard(d) {
    const from = (d.coverage && d.coverage.to) || d.summary.period.to || d.as_of, today = new Date().toISOString().slice(0, 10);
    const max = addDays(today > from ? today : from, 400), cur = d.as_of || today;
    const perDay = d.findings.filter((f) => f.twin && f.twin.kind === "tat" && !f.twin.reversed).reduce((a, f) => a + f.twin.per_day, 0);
    return `
    <section class="card time" id="timecard">
      <div class="section-title" style="margin-top:0"><h2>${esc(t("time.h"))}</h2><span class="count">+${inr(perDay)}/day</span></div>
      <p class="muted" style="margin:0 0 8px">${esc(t("time.lede"))}</p>
      <div class="row" style="gap:14px">
        <span class="mono muted" style="min-width:150px">${esc(t("time.asof"))} <b id="asof-label" style="color:var(--ink)">${esc(cur)}</b></span>
        <input type="range" id="asof" min="${dayNum(from)}" max="${dayNum(max)}" value="${dayNum(cur)}" step="1" style="flex:1;accent-color:var(--gold)">
        <button class="btn sm ghost" id="asof-today">${esc(t("time.today"))}</button>
      </div>
    </section>`;
  }
  const dayNum = (iso) => Math.round(new Date(iso + "T00:00:00Z").getTime() / 86400000);
  const isoOf = (n) => new Date(n * 86400000).toISOString().slice(0, 10);
  const addDays = (iso, n) => isoOf(dayNum(iso) + n);
  function countUp(el, from, to, ms = 900) {
    const t0 = performance.now();
    const step = (now) => { const k = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - k, 3); el.textContent = inr(from + (to - from) * e); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }

  function statementsCard(d) {
    const st = d.statements || [], cov = d.coverage || { gaps: [] };
    return `
    <section class="card stack" id="statements">
      <div class="section-title" style="margin-top:0"><h2>${esc(t("st.h"))}</h2><span class="count">${st.length}</span></div>
      <p class="muted" style="margin:0">${esc(t("st.lede"))}</p>
      ${st.map((x) => `<div class="row stmt" style="justify-content:space-between;border-top:1px dashed var(--line);padding-top:8px">
          <div><div><b>${esc(x.filename)}</b> <span class="chip grey">${esc(x.source_kind || "")}</span></div>
          <div class="muted mono" style="font-size:.8rem">${esc(x.period_from || "?")} → ${esc(x.period_to || "?")} · ${esc(t("st.lines", { n: x.txn_count }))} · ${esc(t("st.new", { n: x.new_count }))}${x.dup_count ? " · " + esc(t("st.dup", { n: x.dup_count })) : ""}</div>
          ${x.warnings?.length ? `<div class="muted" style="font-size:.8rem;color:var(--gold)">${x.warnings.map(esc).join("<br>")}</div>` : ""}</div>
          <button class="btn sm ghost rm-stmt" data-id="${esc(x.id)}" style="color:var(--red)">✕ ${esc(t("st.remove"))}</button>
        </div>`).join("")}
      ${cov.gaps?.length ? `<div class="card warn" style="padding:10px 14px">${cov.gaps.map(([a, b]) => esc(t("st.gap", { a, b }))).join("<br>")}</div>` : ""}
      <div class="row">
        <label class="btn primary" style="font-size:1rem;padding:10px 16px">＋ ${esc(t("st.add"))}<input type="file" id="addstmt" hidden multiple accept=".csv,.tsv,.txt,.pdf,.xlsx,.jpg,.jpeg,.png,.webp"></label>
        ${(() => { const sm = (S.samples || []).filter((x) => x.name.split("_")[0] === (d.profile.bank || "").toLowerCase().replace(" ", "") && !st.some((y) => y.filename === x.name)); return sm.length ? `<span class="muted" style="font-size:.85rem">${esc(t("home.or"))}</span>` + sm.map((x) => `<button class="btn sm add-sample" data-name="${esc(x.name)}">${esc(x.name.replace(/_/g, " ").replace(/\.(csv|tsv)$/, ""))}</button>`).join("") : ""; })()}
      </div>
    </section>`;
  }

  async function addStatements(files) {
    const fd = new FormData();
    files.forEach(([blob, name]) => fd.append("files", blob, name));
    try {
      const d = await api(`/accounts/${S.accountId}/statements`, { method: "POST", body: fd });
      S.data = d; S.cases = d.cases || [];
      const n = d.upload.reduce((a, u) => a + u.new, 0), k = d.upload.reduce((a, u) => a + u.duplicates, 0);
      toast(t("st.added", { n, d: k }), 4500);
      await route();
    } catch (e) { toast(t("err") + e.message, 6000); }
  }

  function bindFindings() {
    $$(".why-toggle").forEach((b) => (b.onclick = async () => {
      const card = b.closest(".finding"), id = card.dataset.id;
      if (S.openWhy.has(id)) S.openWhy.delete(id); else S.openWhy.add(id);
      await route();
      const el = $(`[data-why="${id}"]`);
      if (el) { const f = S.data.findings.find((x) => x.id === id); renderWhy(f, el); }
    }));
    $$("[data-why]").forEach((el) => { const f = S.data.findings.find((x) => x.id === el.dataset.why); if (f) renderWhy(f, el); });
    $$(".speak").forEach((b) => (b.onclick = () => speak(b.dataset.text, S.lang)));
    $$(".ans").forEach((b) => (b.onclick = async () => {
      const wrap = b.closest(".qbtns"); const key = wrap.dataset.txn ? `${wrap.dataset.q}:${wrap.dataset.txn}` : wrap.dataset.q;
      try { S.data = await post(`/accounts/${S.accountId}/answers`, { answers: { [key]: b.dataset.val } }); S.cases = S.data.cases || []; toast("✓"); route(); }
      catch (e) { toast(t("err") + e.message); }
    }));
    const hero = $("#hero-n");
    if (hero && S.prevTotal != null && S.prevTotal !== Number(hero.dataset.v)) countUp(hero, S.prevTotal, Number(hero.dataset.v));
    if (hero) S.prevTotal = Number(hero.dataset.v);
    const asof = $("#asof");
    if (asof) {
      asof.oninput = () => { $("#asof-label").textContent = isoOf(Number(asof.value)); };
      const commit = async (iso) => { try { S.data = await post(`/accounts/${S.accountId}/as-of`, { as_of: iso }); S.cases = S.data.cases || []; route(); const al = S.data.alerts || []; if (al.length) toast(al[0].sent ? "🔴 " + t("alert.sent") + ` (${al.length})` : "🔴 " + t("alert.sim", { r: al[0].reason }), 6000); } catch (e) { toast(t("err") + e.message); } };
      asof.onchange = () => commit(isoOf(Number(asof.value)));
      $("#asof-today").onclick = () => commit(new Date().toISOString().slice(0, 10));
    }
    $$(".twin-open").forEach((b) => (b.onclick = () => { location.hash = `#/twin/${b.dataset.id}`; }));
    const add = $("#addstmt");
    if (add) add.onchange = () => addStatements([...add.files].map((f) => [f, f.name]));
    $$(".add-sample").forEach((b) => (b.onclick = async () => { b.disabled = true; const blob = await (await fetch(`/api/samples/${b.dataset.name}`)).blob(); await addStatements([[blob, b.dataset.name]]); }));
    $$(".rm-stmt").forEach((b) => (b.onclick = async () => {
      if (!confirm(t("st.remove") + "?")) return;
      try { const d = await api(`/accounts/${S.accountId}/statements/${b.dataset.id}`, { method: "DELETE" }); if (d.summary) { S.data = d; S.cases = d.cases || []; } else { S.accountId = null; S.data = null; localStorage.removeItem("vr.account"); location.hash = "#/"; return; } route(); }
      catch (e) { toast(t("err") + e.message); }
    }));
    const gb = $("#getback");
    if (gb) gb.onclick = async () => {
      gb.disabled = true;
      try { const c = await post(`/accounts/${S.accountId}/cases`, {}); location.hash = `#/case/${c.id}`; }
      catch (e) { toast(t("err") + e.message); gb.disabled = false; }
    };
  }

  // ---- case ---------------------------------------------------------------
  const ORDER = ["FOUND", "PREPARED", "AWAITING_APPROVAL", "SENT_TO_BANK", "BANK_REPLIED", "ESCALATED_OMBUDSMAN", "RECOVERED"];
  function tracker(c) {
    const steps = [["FOUND", t("state").FOUND], ["SENT_TO_BANK", t("state").SENT_TO_BANK], ["BANK_REPLIED", t("state").BANK_REPLIED], ["ESCALATED_OMBUDSMAN", t("state").ESCALATED_OMBUDSMAN], ["RECOVERED", t("state").RECOVERED]];
    const idx = ORDER.indexOf(c.state);
    const pos = (k) => ORDER.indexOf(k);
    return `<div class="track">${steps.map(([k, label], i) => { const cls = c.state === k || (k === "FOUND" && ["PREPARED", "AWAITING_APPROVAL"].includes(c.state)) ? "on" : pos(k) < idx ? "done" : ""; return `<span class="${cls}">${esc(label)}</span>${i < steps.length - 1 ? "<i>→</i>" : ""}`; }).join("")}</div>`;
  }

  async function screenCase(id) {
    let c; try { c = await api(`/cases/${id}`); } catch { return `<div class="empty">Case not found.</div>`; }
    if (!S.data) await loadAccount();
    const g = S.data?.guardian;
    const gname = g?.name || "";
    const notif = await api(`/accounts/${c.account_id}/notifications`).catch(() => []);
    const lastCall = notif.find((n) => n.kind === "voice_call" && n.case_id === c.id);
    const lastMsg = notif.find((n) => n.kind === "guardian_message" && n.case_id === c.id);
    const lastMail = notif.find((n) => n.kind === "email_guardian" && n.case_id === c.id);
    const pre = ["FOUND", "PREPARED"].includes(c.state), waiting = c.state === "AWAITING_APPROVAL", sent = c.state === "SENT_TO_BANK";
    const closed = ["RECOVERED", "CLOSED_BANK_RIGHT", "CLOSED_BY_USER"].includes(c.state);
    return `
    <div class="stack">
      <section class="card dark">
        <div class="eyebrow">${esc(t("case.h"))} · ${esc(c.id)}</div>
        <div class="hero-amount" style="margin-top:8px;font-size:clamp(2rem,6vw,3.2rem)">${inr(c.amount)}</div>
        <p style="margin-top:6px;color:#DCE8E0;font-size:1.05rem">${esc(c.status_text)}</p>
        ${c.days_left != null && sent ? `<p style="color:#9DB8A8">${esc(t("case.days", { d: c.days_left }))} · ${esc(c.bank_reply_due)}</p>` : ""}
        ${tracker(c)}
      </section>

      ${pre ? `
      <section class="card stack">
        <div class="eyebrow">${esc(t("case.ready"))}</div>
        <h2 style="margin-top:4px">${esc(t("case.prepared"))}</h2>
        <p class="muted" style="margin:0;font-size:.9rem">${esc(t("case.inside"))}</p>
        <div class="row">
          <button class="btn primary" id="askg">${g ? esc(t("case.guardian")) : esc(t("case.guardian"))}</button>
          <button class="btn" id="sendself">${esc(t("case.send"))}</button>
          <button class="btn ghost" id="preview">${esc(t("case.preview"))}</button>
        </div>
        ${!g ? `<p class="muted">${esc(t("g.lede"))} <a href="#/settings">${esc(t("g.h"))} →</a></p>` : ""}
        <pre id="previewbox" class="mono" hidden style="white-space:pre-wrap;background:var(--grey-soft);padding:14px;border-radius:10px;max-height:50vh;overflow:auto"></pre>
      </section>` : ""}

      ${waiting || (lastCall && !closed) ? `
      <section class="grid2">
        <div class="phone">
          <div class="from">${esc(t("case.callh"))} <span class="pulse"></span></div>
          <div class="bubble" id="callbubble">${esc(lastCall?.text || "")}</div>
          <div class="keys">
            <button class="btn sm gold" id="playcall">🔊 ${esc(t("case.play"))}</button>
            <button class="btn sm" id="stopcall">${esc(t("case.stop"))}</button>
          </div>
          <div class="keys">
            ${gname ? `<button class="btn sm" id="press1">1 · ${esc(t("case.press1", { g: gname }))}</button>` : ""}
            <button class="btn sm ghost" id="press2">2 · ${esc(t("case.press2"))}</button>
          </div>
        </div>
        ${lastMsg ? `
        <div class="phone">
          <div class="from">${esc(t("case.wa", { g: gname }))}</div>
          <div class="bubble wa">${esc(lastMsg.text)}</div>
          ${lastMail ? `<div class="muted" style="font-size:.8rem;margin-top:8px">${lastMail.sent ? "📧 " + esc(t("mail.also", { to: lastMail.to })) : "📧 " + esc(t("mail.sim", { r: lastMail.reason || "" }))}</div>` : ""}
          <div class="keys">${waiting ? `<button class="btn sm primary" id="approve" data-token="${esc(lastMsg.token)}">✓ ${esc(t("case.approve", { g: gname }))}</button>` : `<span class="chip green">✓ ${esc(c.guardian_approved_by || "approved")}</span>`}</div>
        </div>` : waiting ? `<div class="card stack"><div class="eyebrow">${esc(S.lang === "ta" ? "காப்பாளர் இல்ல" : "No guardian on file")}</div><p class="muted" style="margin:0">${esc(S.lang === "ta" ? "நீங்களே OK சொல்லலாம். அல்லது Settings-ல ஒரு காப்பாளரை சேர்த்தா, அவங்க phone-க்கு ஒரு button message போகும்." : "You can approve it yourself. Or add a guardian in Settings and they get a one-button message on their phone.")} <a href="#/settings">${esc(t("g.h"))} →</a></p><button class="btn primary" id="approve-self" data-token="${esc(notif.find((n) => n.token && n.case_id === c.id)?.token || "")}">✓ OK — ${esc(S.lang === "ta" ? "நானே அனுப்பறேன்" : "send it")}</button></div>` : ""}
      </section>` : ""}

      ${!pre && !closed && !waiting ? `
      <section class="card stack">
        <h3>${esc(t("case.timeline"))}</h3>
        <div class="row">
          ${sent || c.state === "DEADLINE_PASSED" ? `<button class="btn sm ev" data-state="BANK_REPLIED">${esc(t("case.bankreplied"))}</button>` : ""}
          ${["SENT_TO_BANK", "BANK_REPLIED", "DEADLINE_PASSED", "ESCALATED_OMBUDSMAN"].includes(c.state) ? `<button class="btn sm ev gold" data-state="RECOVERED">${esc(t("case.recovered"))}</button>` : ""}
          ${["BANK_REPLIED", "DEADLINE_PASSED"].includes(c.state) ? `<button class="btn sm ev" data-state="ESCALATED_OMBUDSMAN">${esc(t("case.escalate"))}</button>` : ""}
          ${["SENT_TO_BANK", "BANK_REPLIED", "ESCALATED_OMBUDSMAN"].includes(c.state) ? `<button class="btn sm ev" data-state="CLOSED_BANK_RIGHT">${esc(t("case.bankright"))}</button>` : ""}
          ${["SENT_TO_BANK", "BANK_REPLIED", "DEADLINE_PASSED", "ESCALATED_OMBUDSMAN"].includes(c.state) ? `<label class="btn sm">${esc(t("case.check"))}<input type="file" id="checkfile" hidden accept=".csv,.tsv,.pdf,.xlsx"></label>` : ""}
        </div>
      </section>` : ""}

      <section class="card stack">
        <div class="row">
          <a class="btn gold" href="/api/cases/${esc(c.id)}/complaint.html?lang=${S.lang}&print=1" target="_blank" rel="noopener">🖨 ${esc(t("case.print"))}</a>
          <a class="btn" href="/api/cases/${esc(c.id)}/ombudsman.html?lang=${S.lang}" target="_blank" rel="noopener">${esc(t("case.printomb"))}</a>
          <a class="btn sm ghost" href="/api/cases/${esc(c.id)}/complaint.txt" target="_blank">${esc(t("case.download"))}</a><a class="btn sm ghost" href="/api/cases/${esc(c.id)}/ombudsman.txt" target="_blank">${esc(t("case.omb"))}</a>
        </div>
        <p class="muted" style="margin:0;font-size:.88rem">${esc(t("case.printhint"))}</p>
        <div class="timeline">${c.events.map((e) => `<div class="ev"><span class="t">${esc(e.at.replace("T", " "))}</span><span><b>${esc(t("state")[e.state] || e.state)}</b> — ${esc(e.note)} <span class="muted">(${esc(e.actor)})</span></span></div>`).join("")}</div>
      </section>
    </div>`;
  }

  const waitingNow = (id) => location.hash === `#/case/${id}` && $("#approve, #approve-self");
  function bindCase(id) {
    const askg = $("#askg");
    if (askg) askg.onclick = async () => { askg.disabled = true; try { const r = await post(`/cases/${id}/request-approval?lang=${S.lang}`); await route(); if (r.call && r.call.placed) toast(t("call.placed", { to: r.call.to }), 6000); else if (r.email) toast(r.email.sent ? "📧 " + t("mail.sent", { to: r.email.to }) : t("mail.sim", { r: r.email.reason }), 6000); setTimeout(() => speak(r.holder_call.text, r.holder_call.lang), 400); } catch (e) { toast(t("err") + e.message); askg.disabled = false; } };
    const ss = $("#sendself");
    if (ss) ss.onclick = async () => { try { await post(`/cases/${id}/send`); toast(t("case.sent")); route(); } catch (e) { toast(t("err") + e.message); } };
    const pv = $("#preview");
    if (pv) pv.onclick = async () => { const box = $("#previewbox"); box.hidden = !box.hidden; if (!box.textContent) box.textContent = await api(`/cases/${id}/complaint.txt`); };
    const play = $("#playcall"); if (play) play.onclick = () => { if (!speak($("#callbubble").textContent, S.lang)) toast("No speech voice available in this browser."); };
    const stop = $("#stopcall"); if (stop) stop.onclick = () => window.speechSynthesis?.cancel();
    const p1 = $("#press1"); if (p1) p1.onclick = () => toast(S.lang === "ta" ? "Kumar-ஐ கூப்பிடறோம்…" : "Calling your guardian…");
    const p2 = $("#press2"); if (p2) p2.onclick = () => toast(S.lang === "ta" ? "சரி. நாங்க பாத்துக்கறோம்." : "No problem. We'll keep watching.");
    $$("#approve, #approve-self").forEach((b) => (b.onclick = async () => { try { const r = await post(`/approvals/${b.dataset.token}?approver=${encodeURIComponent(S.data?.guardian?.name || "holder")}`); toast(t("case.sent") + (r.email?.sent ? " 📧 " + t("mail.sent", { to: r.email.to }) : ""), 5000); route(); } catch (e) { toast(t("err") + e.message); } }));
    // live: when the guardian approves from their phone, this screen moves on by itself
    if (waitingNow(id)) { clearInterval(S._poll); S._poll = setInterval(async () => { try { const c = await api(`/cases/${id}`); if (c.state !== "AWAITING_APPROVAL") { clearInterval(S._poll); toast(t("case.sent"), 4000); route(); } } catch { clearInterval(S._poll); } }, 2500); }
    $$(".ev").forEach((b) => (b.onclick = async () => { try { await post(`/cases/${id}/event`, { state: b.dataset.state, note: "marked in app", actor: "user" }); route(); } catch (e) { toast(t("err") + e.message); } }));
    const cf = $("#checkfile");
    if (cf) cf.onchange = async () => { const fd = new FormData(); fd.append("file", cf.files[0]); try { const r = await api(`/cases/${id}/check-recovery`, { method: "POST", body: fd }); toast(r.recovered ? "✓ " + r.status_text : r.status_text, 4000); route(); } catch (e) { toast(t("err") + e.message); } };
  }

  function screenCases() {
    if (!S.data) return `<div class="empty">${esc(t("noacct"))} <a href="#/">Scan</a></div>`;
    if (!S.cases.length) return `<div class="stack"><h1>${esc(t("cases.h"))}</h1><div class="empty">${esc(t("cases.none"))}</div></div>`;
    return `<div class="stack"><h1>${esc(t("cases.h"))}</h1>${S.cases.map((c) => `<a class="card" href="#/case/${esc(c.id)}" style="text-decoration:none;color:inherit"><div class="row" style="justify-content:space-between"><div><div class="eyebrow">${esc(c.id)}</div><div style="font-size:1.05rem;margin-top:4px">${esc(c.status_text)}</div>${c.days_left != null ? `<div class="muted">${esc(t("case.days", { d: c.days_left }))}</div>` : ""}</div><div class="amt display" style="font-size:1.6rem;color:var(--green)">${inr(c.amount)}</div></div><div style="margin-top:10px">${tracker(c)}</div></a>`).join("")}</div>`;
  }

  // ---- Twin View ---------------------------------------------------------------
  async function screenTwin(fid) {
    if (!S.data) await loadAccount();
    const f = S.data?.findings.find((x) => x.id === fid);
    if (!f || !f.twin?.kind) return `<div class="empty">Twin not available for this finding.</div>`;
    const rule = await getRule(f.rule_id);
    const w = f.twin, L = S.lang;
    const head = `
      <section class="card dark">
        <div class="eyebrow">${esc(t("twin.h"))} · ${esc(f.rule_id)} · ${esc(rule.source.circular)}</div>
        <h1 style="margin-top:6px;font-size:1.6rem">${esc(t("twin.actual"))} <span style="color:var(--mint)">↔</span> ${esc(t("twin.expected"))}</h1>
        <p style="color:#DCE8E0;margin:6px 0 0">${esc(L === "ta" ? f.summary_ta : f.summary_en)}</p>
      </section>`;
    const chain = `<p class="muted mono" style="font-size:.78rem;margin:0">${esc(t("twin.chain"))}</p>`;
    const back = `<div class="row"><a class="btn" href="#/findings">← ${esc(t("twin.back"))}</a><button class="btn sm ghost" id="twin-replay">↻ ${esc(t("twin.replay"))}</button></div>`;
    if (w.kind === "tat") return `<div class="stack">${head}${twinTat(f, w)}${chain}${back}</div>`;
    if (w.kind === "minbal") return `<div class="stack">${head}${twinMinbal(f, w)}${chain}${back}</div>`;
    return `<div class="empty">Twin not available.</div>`;
  }

  function twinTat(f, w) {
    const start = dayNum(w.debit_date), end = Math.max(dayNum(w.reversal_date || w.as_of), dayNum(w.deadline) + 1);
    const span = Math.max(end - start, 1), W = 1000, PAD = 70, X = (iso) => PAD + (dayNum(iso) - start) / span * (W - 2 * PAD);
    const xDebit = X(w.debit_date), xDue = X(w.deadline), xEnd = X(w.reversal_date || w.as_of);
    const ticks = []; for (let n = start; n <= end; n += Math.max(1, Math.round(span / 8))) ticks.push(isoOf(n));
    const lane = (y, label, up) => `<text x="${PAD}" y="${y - (up ? 54 : 34)}" class="lane">${esc(label)}</text><line x1="${PAD}" x2="${W - PAD}" y1="${y}" y2="${y}" class="axis"/>`;
    const mark = (x, y, cls, txt, above, lift = 0) => `<circle cx="${x}" cy="${y}" r="7" class="dot ${cls}"/><text x="${x}" y="${above ? y - 14 - lift : y + 24}" text-anchor="${above && x < PAD + 60 ? "start" : "middle"}" class="lbl ${cls}">${esc(txt)}</text>`;
    const days = w.days_late, total = w.delta, expectedTotal = w.reversed ? w.expected_compensation : w.expected_compensation + w.amount;
    return `
    <section class="card twinview">
      <svg viewBox="0 0 ${W} 330" width="100%" preserveAspectRatio="xMidYMid meet" id="twin-svg">
        <defs><pattern id="hz" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="var(--red)" stroke-width="2" opacity=".35"/></pattern></defs>
        ${ticks.map((d) => `<text x="${X(d)}" y="318" text-anchor="middle" class="tick">${esc(d.slice(5))}</text><line x1="${X(d)}" x2="${X(d)}" y1="60" y2="300" class="grid"/>`).join("")}
        ${lane(110, t("twin.expected"), true)}
        ${mark(xDebit, 110, "ink", `₹${w.amount} ${t("twin.debited")}`, true)}
        ${mark(xDue, 110, "gold", t("twin.due", { n: w.tat_days }), true, 20)}
        <rect x="${xDue}" y="104" width="0" height="12" class="band gold" id="band-exp"/>
        <text x="${(xDue + xEnd) / 2}" y="140" text-anchor="middle" class="lbl gold">${esc(t("twin.perday", { p: w.per_day }))}</text>
        ${lane(250, t("twin.actual"))}
        ${mark(xDebit, 250, "ink", `₹${w.amount} ${t("twin.debited")}`, false)}
        ${w.reversed ? mark(xEnd, 250, "green", `${t("twin.reversed")} · ${w.reversal_date}`, false) : `<circle cx="${xEnd}" cy="250" r="7" class="dot red hollow"/><text x="${xEnd}" y="274" text-anchor="end" class="lbl red">${esc(t("twin.noreversal", { d: w.as_of }))}</text>`}
        <text x="${xDebit}" y="298" class="lbl muted" text-anchor="start">${esc(t("twin.comp0"))}</text>
        <rect x="${xDue}" y="122" width="0" height="116" fill="url(#hz)" id="band-delta"/>
        <line x1="${xDue}" x2="${xDue}" y1="104" y2="256" class="vline"/>
        <text x="${(xDue + xEnd) / 2}" y="186" text-anchor="middle" class="late" id="late-lbl"></text>
      </svg>
      <div class="twin-math">
        <div><span class="eyebrow">${esc(t("twin.expected"))}</span><b>${inr(expectedTotal)}</b><small>${days} × ₹${w.per_day}${w.reversed ? "" : " + ₹" + w.amount + " principal"}</small></div>
        <div class="op">−</div>
        <div><span class="eyebrow">${esc(t("twin.actual"))}</span><b>${inr(w.actual_compensation)}</b><small>${esc(t("twin.comp0"))}</small></div>
        <div class="op">=</div>
        <div class="delta"><span class="eyebrow">${esc(t("twin.delta"))}</span><b id="twin-counter" data-total="${total}" data-days="${days}">₹0</b><small id="twin-day"></small></div>
        <div class="op">→</div>
        <div class="claim"><span class="eyebrow">${esc(t("twin.claim"))}</span><b>${inr(total)}</b><small>${esc(f.confidence)} · ${f.evidence.length} evidence line(s)</small></div>
      </div>
    </section>`;
  }

  function twinMinbal(f, w) {
    const req = w.required, path = w.path || [];
    if (!path.length) return `
    <section class="card twinview stack">
      <div class="twin-math"><div><span class="eyebrow">${esc(t("twin.expected"))}</span><b style="font-size:1.1rem">${esc(t("twin.mb.expected", { r: req, m: w.month }))}</b></div><div class="op">vs</div><div><span class="eyebrow">${esc(t("twin.actual"))}</span><b style="font-size:1.1rem">${esc(t("twin.mb.actual", { p: w.penalty, d: w.charge_date }))}</b></div></div>
      <div class="card warn"><b>${esc(t("twin.mb.blind", { m: w.month }))}</b><div style="margin-top:8px"><a class="btn gold" href="#/findings#statements">＋ ${esc(t("twin.mb.add"))}</a></div></div>
    </section>`;
    const W = 1000, PAD = 70, H = 300, vals = path.map((p) => p[1]), lo = Math.min(...vals, req) * 0.9, hi = Math.max(...vals, req) * 1.05;
    const X = (i) => PAD + i / Math.max(path.length - 1, 1) * (W - 2 * PAD), Y = (v) => 40 + (1 - (v - lo) / (hi - lo)) * (H - 80);
    const pts = path.map((p, i) => `${X(i)},${Y(p[1])}`).join(" ");
    const ok = w.lowest != null && w.lowest >= req;
    return `
    <section class="card twinview">
      <svg viewBox="0 0 ${W} ${H + 30}" width="100%" id="twin-svg">
        <line x1="${PAD}" x2="${W - PAD}" y1="${Y(req)}" y2="${Y(req)}" class="req"/><text x="${W - PAD}" y="${Y(req) - 8}" text-anchor="end" class="lbl gold">${esc(t("twin.mb.required", { r: req }))} · ${esc(t("twin.expected"))}</text>
        <polyline points="${pts}" class="path" id="mb-path"/>
        ${path.map((p, i) => `<circle cx="${X(i)}" cy="${Y(p[1])}" r="4" class="dot ${p[1] < req ? "red" : "green"}"/>`).join("")}
        ${path.filter((_, i) => i % Math.max(1, Math.round(path.length / 8)) === 0).map((p, i, a) => `<text x="${X(path.indexOf(p))}" y="${H + 18}" text-anchor="middle" class="tick">${esc(p[0].slice(5))}</text>`).join("")}
        <text x="${PAD}" y="24" class="lane">${esc(t("twin.actual"))} · ${esc(w.month)}</text>
        <text x="${W - PAD}" y="24" text-anchor="end" class="lbl ${ok ? "green" : "red"}">${esc(t("twin.mb.lowest", { m: w.month, l: w.lowest }))}</text>
      </svg>
      <div class="twin-math">
        <div><span class="eyebrow">${esc(t("twin.expected"))}</span><b style="font-size:1.05rem">${esc(t("twin.mb.expected", { r: req, m: w.month }))}</b></div>
        <div class="op">vs</div>
        <div><span class="eyebrow">${esc(t("twin.actual"))}</span><b style="font-size:1.05rem">${esc(t("twin.mb.actual", { p: w.penalty, d: w.charge_date }))}</b><small>${esc(t("twin.mb.lowest", { m: w.month, l: w.lowest }))}</small></div>
        <div class="op">→</div>
        <div class="${ok ? "claim" : ""}"><span class="eyebrow">${esc(f.label === "RECOVERABLE" ? t("twin.claim") : t("label." + f.label))}</span><b>${f.amount ? inr(f.amount) : "—"}</b><small>${esc(t("conf." + f.confidence))}</small></div>
      </div>
    </section>`;
  }

  function bindTwin() {
    const play = () => {
      const c = $("#twin-counter"), be = $("#band-exp"), bd = $("#band-delta"), ll = $("#late-lbl"), dl = $("#twin-day");
      if (c && be) {
        const total = Number(c.dataset.total), days = Number(c.dataset.days);
        const svg = $("#twin-svg"), xDue = Number(be.getAttribute("x")), xEnd = Number($(".dot.green, .dot.hollow", svg)?.getAttribute("cx") || xDue);
        const width = Math.max(0, xEnd - xDue), ms = Math.min(4000, 400 + days * 180), t0 = performance.now();
        const step = (now) => {
          const k = Math.min(1, (now - t0) / ms), d = Math.round(k * days);
          be.setAttribute("width", width * k); bd.setAttribute("width", width * k);
          c.textContent = inr(total * k); dl.textContent = t("twin.day", { n: d }); ll.textContent = t("twin.late", { n: d });
          if (k < 1) requestAnimationFrame(step); else { c.textContent = inr(total); ll.textContent = t("twin.late", { n: days }); }
        };
        requestAnimationFrame(step);
      }
      const mp = $("#mb-path");
      if (mp) { const len = mp.getTotalLength(); mp.style.strokeDasharray = len; mp.style.strokeDashoffset = len; mp.getBoundingClientRect(); mp.style.transition = "stroke-dashoffset 2.2s ease-out"; mp.style.strokeDashoffset = "0"; }
    };
    play();
    const r = $("#twin-replay"); if (r) r.onclick = () => route();
  }

  // ---- approve (opened from the guardian's phone) --------------------------
  async function screenApprove(token) {
    let a; try { a = await api(`/approvals/${token}`); } catch { return `<div class="empty">Invalid link.</div>`; }
    const L = a.lang === "ta" ? "ta" : "en"; const tt = (k, v) => { const s = T[L][k] ?? T.en[k]; return v ? Object.entries(v).reduce((x, [p, q]) => x.replaceAll(`{${p}}`, q), s) : s; };
    return `
    <div class="stack" style="max-width:520px;margin:0 auto">
      <section class="card dark">
        <div class="eyebrow">Bank IQ · ${esc(a.case_id)}</div>
        <h1 style="margin-top:8px;font-size:1.6rem">${esc(tt("ap.h"))}</h1>
        <p style="color:#DCE8E0;margin-top:6px">${esc(tt("ap.for", { h: a.holder || "-", b: a.bank || "-" }))}</p>
        <div class="hero-amount" style="font-size:2.6rem;margin-top:6px">${inr(a.amount)}</div>
      </section>
      <section class="card stack">
        <div class="phone" style="max-width:none"><div class="bubble wa" style="margin-top:0">${esc(a.message)}</div></div>
        <p class="muted" style="margin:0;font-size:.88rem">${esc(tt("ap.note"))}</p>
        ${a.used || a.state !== "AWAITING_APPROVAL" ? `<p class="chip green" style="font-size:.9rem;padding:8px 12px">✓ ${esc(a.used ? tt("ap.done") : tt("ap.used"))}</p>` : `
        <button class="btn gold" id="ap-yes" style="font-size:1.2rem;padding:16px 22px;width:100%">${esc(tt("ap.yes"))}</button>
        <button class="btn ghost" id="ap-no" style="width:100%">${esc(tt("ap.no"))}</button>`}
        <div id="ap-result"></div>
      </section>
    </div>`;
  }
  function bindApprove(token) {
    const y = $("#ap-yes"), n = $("#ap-no");
    if (y) y.onclick = async () => { y.disabled = true; try { const a = await api(`/approvals/${token}`); const r = await post(`/approvals/${token}?approver=${encodeURIComponent(a.guardian?.name || "guardian")}`); const L = a.lang === "ta" ? "ta" : "en"; $("#ap-result").innerHTML = `<div class="card soft" style="margin-top:10px"><b>✓ ${esc(T[L]["ap.done"])}</b>${r.email?.sent ? `<div class="muted" style="font-size:.85rem">📧 ${esc(T[L]["mail.sent"].replace("{to}", r.email.to))}</div>` : ""}</div>`; y.hidden = true; if (n) n.hidden = true; speak(T[L]["ap.done"], L); } catch (e) { toast(t("err") + e.message); y.disabled = false; } };
    if (n) n.onclick = () => { $("#ap-result").innerHTML = `<p class="muted">${esc(S.lang === "ta" ? "சரி. நாங்க பாத்துக்கறோம்." : "No problem. We'll keep watching.")}</p>`; };
  }

  // ---- history -----------------------------------------------------------
  async function screenHistory() {
    const accts = await api("/accounts").catch(() => []);
    if (!accts.length) return `<div class="stack"><h1>${esc(t("hist.h"))}</h1><div class="empty">${esc(t("hist.none"))} <a href="#/">Scan</a></div></div>`;
    return `<div class="stack"><h1>${esc(t("hist.h"))}</h1><p class="muted">${esc(t("hist.lede"))}</p>
      ${accts.map((a) => { const cur = a.id === S.accountId; const p = a.profile || {}; return `
      <article class="card ${cur ? "soft" : ""}" data-id="${esc(a.id)}">
        <div class="row" style="justify-content:space-between;align-items:flex-start">
          <div>
            <div class="pillrow">${cur ? `<span class="chip green">${esc(t("hist.current"))}</span>` : ""}<span class="chip grey mono">${esc(a.id)}</span><span class="chip grey">${esc(t("hist.stmts", { n: a.statements }))}</span>${a.cases ? `<span class="chip ${a.open_cases ? "amb" : "grey"}">${esc(t("hist.cases", { n: a.cases }))}${a.open_cases ? " · " + esc(t("hist.opencases", { n: a.open_cases })) : ""}</span>` : ""}</div>
            <h2 style="margin-top:8px">${esc(p.bank || "?")}${p.account_last4 ? " ····" + esc(p.account_last4) : ""}${p.holder_name ? " · " + esc(p.holder_name) : ""}</h2>
            <div class="muted mono" style="font-size:.82rem">${esc(a.period.from || "")} → ${esc(a.period.to || "")} · ${a.transactions} lines · ${esc(p.account_type || "")} · ${esc((a.updated_at || a.created_at || "").slice(0, 16).replace("T", " "))}</div>
          </div>
          <div style="text-align:right">
            <div class="amt display" style="font-size:1.7rem;color:var(--green);font-family:var(--head);font-weight:700">${inr(a.total_recoverable)} <span class="muted" style="font-size:.8rem;font-weight:400">${esc(t("hist.found"))}</span></div>
            ${a.recovered ? `<div class="muted" style="font-size:.9rem">${inr(a.recovered)} ${esc(t("hist.recovered"))}</div>` : ""}
            <div class="row" style="justify-content:flex-end;margin-top:8px">
              <button class="btn sm ${cur ? "" : "primary"} h-open" data-id="${esc(a.id)}">${esc(cur ? t("nav.findings") : t("hist.open"))} →</button>
              <button class="btn sm ghost h-del" data-id="${esc(a.id)}" style="color:var(--red)">✕</button>
            </div>
          </div>
        </div>
      </article>`; }).join("")}
    </div>`;
  }
  function bindHistory() {
    $$(".h-open").forEach((b) => (b.onclick = async () => { S.accountId = b.dataset.id; localStorage.setItem("vr.account", S.accountId); S.data = null; S.openWhy = new Set(); await loadAccount(); location.hash = "#/findings"; }));
    $$(".h-del").forEach((b) => (b.onclick = async () => { if (!confirm(t("s.delete") + "?")) return; try { await api(`/accounts/${b.dataset.id}`, { method: "DELETE" }); if (S.accountId === b.dataset.id) { S.accountId = null; S.data = null; S.cases = []; localStorage.removeItem("vr.account"); } toast(t("s.deleted")); route(); } catch (e) { toast(t("err") + e.message); } }));
  }

  // ---- ask ---------------------------------------------------------------
  function screenAsk() {
    return `
    <div class="stack">
      <h1>${esc(t("ask.h"))}</h1>
      <section class="card soft" style="padding:12px 16px"><b>${esc(t("ai.banner"))}</b><div class="muted" style="font-size:.9rem">${esc(t("ai.lede"))}</div></section>
      <p class="muted">${esc(t("ask.hint"))}</p>
      <div class="chat" id="chat">${S.chat.map((m) => `<div class="msg ${m.me ? "me" : "bot"}">${esc(m.text)}${m.sources?.length ? `<span class="g">RBI: ${m.sources.map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title.split(" ")[0])}</a>`).join(" · ")}</span>` : ""}${m.sugg?.length ? `<span class="sugg">${m.sugg.map((x) => `<button class="btn sm ghost sug">${esc(x)}</button>`).join("")}</span>` : ""}${m.kind && m.kind !== "chat" ? `<span class="g">${esc({account: S.lang === "ta" ? "உங்க account-ல இருந்து" : "from your account", knowledge: S.lang === "ta" ? "bank rules-ல இருந்து" : "from banking rules", claim_check: S.lang === "ta" ? "rulebook-ஓட சரிபார்த்தது" : "checked against the rulebook", llm: "assistant", fallback: ""}[m.kind] || "")}</span>` : ""}</div>`).join("") || `<div class="msg bot">${esc(S.lang === "ta" ? "வணக்கம். உங்க account பத்தியோ, bank rules பத்தியோ எதுவும் கேளுங்க." : "Hello. Ask me about your account, a charge, or any banking rule.")}</div>`}</div>
      <form class="askbar" id="askform">
        <button type="button" class="mic" id="mic" aria-label="Speak">🎙</button>
        <input id="q" placeholder="${esc(t("ask.ph"))}" autocomplete="off">
        <button class="btn primary" type="submit">${esc(t("ask.send"))}</button>
      </form>
      <div class="row">${(S.lang === "ta" ? ["என்ன ஆச்சு?", "நான் என்ன பண்ணணும்?", "statement எப்படி download பண்றது?", "SMS-க்கு charge பண்ணலாமா?", "ATM-ல எத்தனை free?", "RBI-ல எப்படி complaint பண்றது?"] : ["what happened?", "what should I do?", "how do I download my statement?", "can the bank charge for SMS?", "how many free ATM transactions?", "how do I complain to the RBI Ombudsman?", "is it true all ATM use is free?"]).map((s) => `<button class="btn sm ghost sug">${esc(s)}</button>`).join("")}</div>
    </div>`;
  }
  function bindAsk() {
    const form = $("#askform"), q = $("#q");
    const send = async (text) => {
      if (!text.trim()) return;
      S.chat.push({ me: true, text }); await route();
      try { const a = await post(S.accountId ? `/accounts/${S.accountId}/ask` : `/ask`, { question: text, lang: S.lang }); S.chat.push({ me: false, text: a.text, g: a.grounded_on, kind: a.kind, sources: a.sources, sugg: a.suggestions }); await route(); speak(a.text.split("\n")[0], a.lang); }
      catch (e) { S.chat.push({ me: false, text: t("err") + e.message }); route(); }
      const chat = $("#chat"); if (chat) chat.scrollTop = chat.scrollHeight;
    };
    form.onsubmit = (e) => { e.preventDefault(); const v = q.value; q.value = ""; send(v); };
    $$(".sug").forEach((b) => (b.onclick = () => send(b.textContent)));
    const mic = $("#mic");
    mic.onclick = () => { mic.classList.add("on"); const r = listen((txt) => { mic.classList.remove("on"); send(txt); }); if (r) r.onend = () => mic.classList.remove("on"); else mic.classList.remove("on"); };
    const chat = $("#chat"); if (chat) chat.scrollTop = chat.scrollHeight;
  }

  // ---- intelligence (Bank IQ ML layer) -------------------------------------
  const CAT_COLORS = { UPI_PAYMENT: "#2a78d6", CARD_POS: "#eb6834", ATM_WITHDRAWAL: "#1baf7a", TRANSFER_OUT: "#eda100", LOAN_EMI: "#e87ba4", BANK_CHARGE: "#e34948", INCOME_CREDIT: "#008300", TRANSFER_IN: "#6c5ce7", REFUND_REVERSAL: "#00a8b5", INTEREST_CREDIT: "#8d99ae" };
  const INS_ICON = { trend: "📈", category: "🧾", mix: "🥧", charges: "⚠️", savings: "💰", segment: "👥", forecast: "🔮", anomaly: "🚩", model: "🤖" };
  const pct = (x) => `${Math.round((x || 0) * 100)}%`;
  function monthChart(months) {
    if (!months?.length) return "";
    const W = 640, H = 260, padL = 46, padB = 28, padT = 14, n = months.length;
    const max = Math.max(...months.map((m) => Math.max(m.spend, m.income)), 1);
    const bw = (W - padL - 10) / n, y = (v) => padT + (H - padT - padB) * (1 - v / max);
    const bars = months.map((m, i) => {
      const x = padL + i * bw;
      return `<rect x="${x + bw * 0.12}" y="${y(m.income)}" width="${bw * 0.34}" height="${H - padB - y(m.income)}" fill="#008300" opacity=".85"><title>${esc(m.month)} income ${inr(m.income)}</title></rect>
              <rect x="${x + bw * 0.52}" y="${y(m.spend)}" width="${bw * 0.34}" height="${H - padB - y(m.spend)}" fill="#2a78d6"><title>${esc(m.month)} spend ${inr(m.spend)}</title></rect>
              <text x="${x + bw / 2}" y="${H - 8}" font-size="10" text-anchor="middle" fill="#666">${esc(m.month.slice(2))}</text>`;
    }).join("");
    const ticks = [0, 0.5, 1].map((f) => `<line x1="${padL}" x2="${W - 10}" y1="${y(max * f)}" y2="${y(max * f)}" stroke="#ddd" stroke-dasharray="3 4"/><text x="${padL - 4}" y="${y(max * f) + 4}" font-size="9" text-anchor="end" fill="#666">${Math.round(max * f / 1000)}k</text>`).join("");
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" style="display:block" role="img" aria-label="monthly income and spend">${ticks}${bars}
      <rect x="${padL}" y="2" width="9" height="9" fill="#008300"/><text x="${padL + 13}" y="10" font-size="10" fill="#444">${esc(t("intel.income"))}</text>
      <rect x="${padL + 70}" y="2" width="9" height="9" fill="#2a78d6"/><text x="${padL + 83}" y="10" font-size="10" fill="#444">${esc(t("intel.spend"))}</text></svg>`;
  }
  function renderIntel(d) {
    const kpi = (label, val, sub) => `<div class="tile"><div class="eyebrow">${esc(label)}</div><div class="num" style="font-size:1.35rem">${val}</div>${sub ? `<div class="muted" style="font-size:.8rem">${sub}</div>` : ""}</div>`;
    const f = d.forecast || {};
    const cats = d.categories || []; const maxc = Math.max(...cats.map((c) => c.amount), 1);
    const show = S.intelOnlyDiff ? d.transactions.filter((x) => !x.agree) : d.transactions;
    return `
      <div class="tiles">
        ${kpi(t("intel.k.txn"), d.n_transactions, `${esc(d.period.from)} → ${esc(d.period.to)} · ${d.period.months} ${esc(t("intel.months"))}`)}
        ${kpi(t("intel.k.spend"), inr(d.totals.debits), `${esc(t("intel.k.income"))} ${inr(d.totals.income)}`)}
        ${kpi(t("intel.k.charges"), inr(d.totals.charges), `${esc(t("intel.k.refunds"))} ${inr(d.totals.refunds)}`)}
        ${kpi(t("intel.k.segment"), esc(d.segment.name), `K-Means · ${esc(t("intel.k.segid"))} ${d.segment.id}`)}
        ${kpi(t("intel.k.forecast"), f.next_month_spend == null ? "—" : inr(f.next_month_spend), `${esc(t("intel.k.naive"))} ${inr(f.naive)} · ${esc(f.model || "")}`)}
      </div>
      <section class="card"><div class="eyebrow">${esc(t("intel.insights"))}</div>
        <ul class="stack" style="list-style:none;padding:0;margin:8px 0 0;gap:8px">${(d.insights || []).map((i) => `<li style="display:flex;gap:10px;align-items:flex-start"><span style="flex:0 0 auto">${INS_ICON[i.kind] || "•"}</span><span style="flex:1 1 auto">${esc(i.text)}</span></li>`).join("")}</ul>
      </section>
      <div class="grid2">
        <section class="card"><div class="eyebrow">${esc(t("intel.cats"))}</div>
          <div class="stack" style="gap:6px;margin-top:8px">${cats.map((c) => `<div><div class="row" style="justify-content:space-between;font-size:.88rem"><span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${CAT_COLORS[c.category] || "#999"};margin-right:6px"></span>${esc(c.label)} <span class="muted">× ${c.count}</span></span><b>${inr(c.amount)} <span class="muted" style="font-weight:400">${pct(c.share)}</span></b></div><div style="height:7px;background:var(--line,#eee);border-radius:4px;overflow:hidden"><div style="width:${Math.max(2, c.amount / maxc * 100)}%;height:100%;background:${CAT_COLORS[c.category] || "#999"}"></div></div></div>`).join("")}</div>
        </section>
        <section class="card"><div class="eyebrow">${esc(t("intel.monthly"))}</div><div style="margin-top:8px">${monthChart(d.months)}</div>
          <div class="muted" style="font-size:.8rem;margin-top:6px">${esc(t("intel.monthly.note"))}</div></section>
      </div>
      <div class="grid2">
        <section class="card"><div class="eyebrow">${esc(t("intel.profile"))} · ${esc(d.segment.name)}</div>
          <table class="mono" style="width:100%;font-size:.8rem;margin-top:8px;border-collapse:collapse">${Object.entries(d.profile).map(([k, v]) => `<tr><td style="padding:2px 0;color:#666">${esc(k.replaceAll("_", " "))}</td><td style="text-align:right">${k.includes("share") || k.includes("ratio") ? (k.includes("ratio") ? v.toFixed(2) : pct(v)) : (k.startsWith("has") ? (v ? "yes" : "no") : (k.includes("per_month") || k.includes("txn") ? v.toFixed(1) : inr(Math.round(v))))}</td></tr>`).join("")}</table>
        </section>
        <section class="card"><div class="eyebrow">${esc(t("intel.anom"))}</div>
          ${d.anomalies?.length ? `<div class="evidence" style="margin-top:8px;overflow:auto"><table><thead><tr><th>${esc(t("intel.t.date"))}</th><th>${esc(t("intel.t.narr"))}</th><th>${esc(t("intel.t.amt"))}</th><th>${esc(t("intel.t.typ"))}</th><th>×</th></tr></thead><tbody>${d.anomalies.map((a) => `<tr><td>${esc(a.date)}</td><td>${esc(a.narration)}</td><td>${inr(a.amount)}</td><td>${inr(a.typical)} <span class="muted">${esc(a.category.replaceAll("_", " ").toLowerCase())}</span></td><td><b>${a.times_typical}×</b></td></tr>`).join("")}</tbody></table></div>` : `<p class="muted" style="margin:8px 0 0">${esc(t("intel.anom.none"))}</p>`}
          <div class="muted" style="font-size:.8rem;margin-top:6px">${esc(t("intel.anom.note"))}</div>
        </section>
      </div>
      <section class="card"><div class="row" style="justify-content:space-between;flex-wrap:wrap"><div class="eyebrow">${esc(t("intel.txns"))} · ${esc(t("intel.disagree", { n: d.rule_disagreements, m: d.n_transactions }))}</div>
        <label class="row" style="gap:6px;font-size:.85rem"><input type="checkbox" id="intel-diff" ${S.intelOnlyDiff ? "checked" : ""}> ${esc(t("intel.onlydiff"))}</label></div>
        <div class="evidence" style="margin-top:8px;overflow:auto;max-height:420px"><table><thead><tr><th>${esc(t("intel.t.date"))}</th><th>${esc(t("intel.t.narr"))}</th><th>${esc(t("intel.t.amt"))}</th><th>ML</th><th>conf</th><th>${esc(t("intel.t.rule"))}</th></tr></thead><tbody>
          ${show.slice(0, 300).map((x) => `<tr ${x.agree ? "" : 'style="background:#fff7e6"'}><td>${esc(x.date)}</td><td>${esc(x.narration)}</td><td>${x.debit ? "−" + inr(x.debit) : "+" + inr(x.credit)}</td><td><span class="chip" style="background:${CAT_COLORS[x.category]}22;border-color:${CAT_COLORS[x.category]}">${esc(x.label)}</span></td><td>${pct(x.confidence)}</td><td class="muted">${esc(x.rule_category.replaceAll("_", " ").toLowerCase())}${x.agree ? "" : " ≠"}</td></tr>`).join("")}
        </tbody></table></div>${show.length > 300 ? `<div class="muted" style="font-size:.8rem">${show.length - 300} more…</div>` : ""}
      </section>
      <p class="muted" style="font-size:.8rem">${esc(t("intel.models"))}: ${esc(d.models.classifier)} · ${esc(d.models.regressor)} · ${esc(d.models.segmenter)}</p>`;
  }
  function renderModelCard(r) {
    if (!r?.experiments) return "";
    const ex = r.experiments; const rows = [];
    const cl = ex.classification?.models || {}; const en = ex.ensembles?.models || {};
    for (const [n, m] of Object.entries({ ...cl, ...en })) rows.push(`<tr><td>${esc(n)}</td><td>${m.cv_accuracy == null ? "—" : (m.cv_accuracy * 100).toFixed(1) + "%"}</td><td>${(m.accuracy * 100).toFixed(1)}%</td><td>${m.f1_macro.toFixed(3)}</td></tr>`);
    const rg = ex.regression?.models || {};
    const rrows = Object.entries(rg).map(([n, m]) => `<tr><td>${esc(n)}</td><td>${m.cv_r2 == null ? "—" : m.cv_r2.toFixed(3)}</td><td>${m.r2.toFixed(3)}</td><td>${inr(m.rmse)}</td><td>${inr(m.mae)}</td></tr>`);
    const figs = ["fig5_classification.png", "fig6_confusion.png", "fig8_ensembles.png", "fig9_regression.png", "fig11_cluster_selection.png", "fig12_dendrogram_segments.png", "fig13_segment_profiles.png", "fig14_pca.png", "fig15_lwr.png"].filter((f) => (r.figures || []).includes(f));
    return `
      <section class="card"><div class="eyebrow">${esc(t("intel.card"))}</div>
        <p class="muted" style="font-size:.88rem">${esc(t("intel.card.lede"))}</p>
        <div class="grid2">
          <div><b>${esc(t("intel.card.cls"))}</b> <span class="muted">(${ex.classification?.n_train?.toLocaleString("en-IN")} train / ${ex.classification?.n_test?.toLocaleString("en-IN")} test, 5-fold CV)</span>
            <div class="evidence" style="overflow:auto"><table><thead><tr><th>model</th><th>CV acc</th><th>test acc</th><th>macro-F1</th></tr></thead><tbody>${rows.join("")}</tbody></table></div></div>
          <div><b>${esc(t("intel.card.reg"))}</b> <span class="muted">(${ex.regression?.cv || ""})</span>
            <div class="evidence" style="overflow:auto"><table><thead><tr><th>model</th><th>CV R²</th><th>test R²</th><th>RMSE</th><th>MAE</th></tr></thead><tbody>${rrows.join("")}</tbody></table></div>
            ${ex.clustering ? `<p style="font-size:.88rem;margin:8px 0 0"><b>${esc(t("intel.card.clu"))}</b> k=${ex.clustering.best_k} · silhouette ${ex.clustering.kmeans_silhouette[ex.clustering.best_k].toFixed(3)} · ARI vs hidden type ${ex.clustering.ari_vs_archetype_kmeans[ex.clustering.best_k].toFixed(2)}</p>` : ""}
            ${ex.pca ? `<p style="font-size:.88rem;margin:4px 0 0"><b>PCA</b> ${ex.pca.n_components_95} of ${ex.pca.n_features} components explain 95% of profile variance</p>` : ""}</div>
        </div>
        <div class="row" style="flex-wrap:wrap;gap:8px;margin-top:10px">${figs.map((f) => `<button class="btn sm ghost fig-btn" data-f="${esc(f)}">${esc(f.replace(/^fig(\d+)_/, "Fig $1 · ").replace(".png", "").replaceAll("_", " "))}</button>`).join("")}</div>
        <div id="fig-box" style="margin-top:8px"></div>
      </section>`;
  }
  async function screenIntel() {
    if (!S.intelStatus) S.intelStatus = await api("/ml/status").catch(() => ({ available: false }));
    if (!S.samples) S.samples = await api("/samples").catch(() => []);
    const d = S.intel;
    return `
    <div class="stack">
      <h1>${esc(t("intel.h"))}</h1>
      <section class="card soft" style="padding:12px 16px"><b>${esc(t("intel.banner"))}</b><div class="muted" style="font-size:.9rem">${esc(t("intel.lede"))}</div></section>
      ${S.intelStatus.available ? "" : `<div class="empty">${esc(t("intel.nomodels"))}</div>`}
      <section class="card"><div class="eyebrow">${esc(t("intel.source"))}</div>
        <div class="row" style="flex-wrap:wrap;gap:8px;margin-top:8px">
          ${S.accountId ? `<button class="btn primary" id="intel-acct">${esc(t("intel.useacct"))}</button>` : `<span class="muted">${esc(t("intel.noacct"))}</span>`}
          <label class="btn" for="intel-file">${esc(t("intel.upload"))}</label><input type="file" id="intel-file" accept=".csv,.tsv,.txt,.pdf,.xlsx,.png,.jpg,.jpeg" hidden>
          ${(S.samples || []).filter((s) => !/\.(png|jpg)$/i.test(s.name || s)).map((s) => `<button class="btn sm ghost intel-sample" data-f="${esc(s.name || s)}">${esc(t("intel.sample"))}: ${esc((s.name || s).replace(/_/g, " ").replace(/\.\w+$/, ""))}</button>`).join("")}
        </div>
        <div id="intel-status" class="muted" style="font-size:.85rem;margin-top:6px">${S.intelBusy ? esc(t("intel.busy")) : (d ? esc(t("intel.loaded", { n: d.n_transactions, s: d.source?.filename || d.customer || "" })) : "")}</div>
      </section>
      ${d ? renderIntel(d) : ""}
      <details ${d ? "" : "open"}><summary class="eyebrow" style="cursor:pointer">${esc(t("intel.card"))} · ${esc(t("intel.card.sum"))}</summary><div id="model-card" style="margin-top:8px">${S.intelResults ? renderModelCard(S.intelResults) : `<p class="muted">${esc(t("intel.loading"))}</p>`}</div></details>
    </div>`;
  }
  function bindIntel() {
    const run = async (fn) => {
      S.intelBusy = true; S.intel = null; await route();
      try { S.intel = await fn(); } catch (e) { toast(t("err") + e.message, 5000); }
      S.intelBusy = false; await route();
    };
    const acct = $("#intel-acct"); if (acct) acct.onclick = () => run(() => api(`/accounts/${S.accountId}/intelligence`));
    const file = $("#intel-file"); if (file) file.onchange = () => { const f = file.files[0]; if (!f) return; const fd = new FormData(); fd.append("file", f); run(() => api("/ml/analyze", { method: "POST", body: fd })); };
    $$(".intel-sample").forEach((b) => (b.onclick = () => run(async () => { const r = await fetch(`/api/samples/${encodeURIComponent(b.dataset.f)}`); const blob = await r.blob(); const fd = new FormData(); fd.append("file", new File([blob], b.dataset.f)); return api("/ml/analyze", { method: "POST", body: fd }); })));
    const diff = $("#intel-diff"); if (diff) diff.onchange = () => { S.intelOnlyDiff = diff.checked; route(); };
    const bindFigs = () => $$(".fig-btn").forEach((b) => (b.onclick = () => { $("#fig-box").innerHTML = `<img src="/api/ml/figures/${esc(b.dataset.f)}" alt="${esc(b.dataset.f)}" style="width:100%;border:1px solid var(--line,#eee);border-radius:8px">`; }));
    if (!S.intelResults) api("/ml/results").then((r) => { S.intelResults = r; const box = $("#model-card"); if (box) { box.innerHTML = renderModelCard(r); bindFigs(); } }).catch(() => { });
    else bindFigs();
  }

  // ---- rules -------------------------------------------------------------
  async function screenRules() {
    const rules = await api("/rules");
    const cats = [...new Set(rules.map((r) => r.category))];
    const sc = await api("/scope").catch(() => null), v = await api("/validation").catch(() => null);
    return `<div class="stack"><h1>${esc(t("rules.h"))}</h1><p class="muted">${esc(t("rules.lede"))} <a href="#/rules" target="_blank" rel="noopener">rulebook/rules.json</a></p>
      ${sc ? `<section class="card warn"><div class="eyebrow">${esc(t("scope.h"))}</div><p style="margin:6px 0 4px;font-weight:600">${esc(t("scope.line", { i: sc.implemented, l: sc.listed, m: sc.mapped }))}</p><p class="muted" style="margin:0;font-size:.9rem">${esc(t("scope.note"))}</p></section>` : ""}
      ${validationCard(v)}
      ${cats.map((c) => `<div class="section-title"><h2>${esc(c.replace("_", " "))}</h2><span class="count">${rules.filter((r) => r.category === c).length}</span></div>
        ${rules.filter((r) => r.category === c).map((r) => `<article class="card rule"><div class="pillrow"><span class="chip ${r.status === "active" ? "green" : "amb"}">${esc(r.status)}</span><span class="chip grey mono">${esc(r.id)}</span><span class="chip grey">${esc(r.compensation_type)}</span></div><h3>${esc(r.title)}</h3><p>${esc(S.lang === "ta" ? r.right_ta || r.right_en : r.right_en)}</p><div class="src"><a href="${esc(r.source.url)}" target="_blank" rel="noopener">${esc(r.source.circular)}</a> · ${esc(r.source.date)} · in force ${esc(r.effective_from)}${r.effective_to ? " → " + esc(r.effective_to) : " → present"}</div><div class="src">formula: ${esc(r.formula)}</div></article>`).join("")}`).join("")}
    </div>`;
  }

  function validationCard(v) {
    if (!v) return "";
    if (!v.available) return `<section class="card"><div class="eyebrow">${esc(t("valid.h"))}</div><p class="muted" style="margin:6px 0 0">${esc(t("valid.none"))}</p></section>`;
    return `<section class="card">
      <div class="section-title" style="margin-top:0"><h2>${esc(t("valid.h"))}</h2><span class="count">${esc(t("valid.ran"))} ${esc((v.ran_at || "").slice(0, 16).replace("T", " "))} · python ${esc(v.python || "")}</span></div>
      <p class="muted" style="margin:0 0 10px;font-size:.9rem">${esc(t("valid.lede"))}</p>
      <div class="row" style="align-items:flex-start;gap:24px">
        <div><div class="display" style="font-family:var(--head);font-size:2.6rem;font-weight:700;color:${v.failed ? "var(--red)" : "var(--green)"}">${v.passed}<span class="muted" style="font-size:1rem">/${v.total}</span></div><div class="eyebrow">${esc(t("valid.passed"))}</div></div>
        <div class="tiles" style="flex:1">${v.groups.map((g) => `<div class="tile"><div class="eyebrow" style="color:${g.failed ? "var(--red)" : "var(--green)"}">${g.failed ? "✕" : "✓"} ${esc(g.title)}</div><div class="v" style="font-size:1.1rem">${g.passed}${g.failed ? ` <span style="color:var(--red)">· ${g.failed} failed</span>` : ""}</div><small class="muted">${esc(g.what)}</small></div>`).join("")}</div>
      </div>
    </section>`;
  }

  // ---- My Twin (account level) ------------------------------------------------------
  async function screenMyTwin() {
    if (!S.data) return `<div class="empty">${esc(t("noacct"))} <a href="#/">Scan</a></div>`;
    const tw = S.twin = await api(`/accounts/${S.accountId}/twin`);
    const c = tw.counts, L = S.lang, d = S.data, F = d.findings;
    const flaggedBy = {}; F.forEach((f) => f.evidence.forEach((id) => (flaggedBy[id] = flaggedBy[id] || []).push(f)));
    const node = (label, v, sub = "") => `<div class="pnode"><div class="eyebrow">${esc(label)}</div><div class="v">${v}</div>${sub ? `<small class="muted">${sub}</small>` : ""}</div><i>→</i>`;
    // balance chart
    const path = tw.balance_path, W = 1000, H = 260, PAD = 56;
    let chart = "";
    if (path.length > 1) {
      const vals = path.map((p) => p[1]), req = tw.min_balance_required, lo = Math.min(...vals, req ?? Infinity) * 0.95, hi = Math.max(...vals) * 1.05;
      const X = (i) => PAD + i / (path.length - 1) * (W - 2 * PAD), Y = (v) => 24 + (1 - (v - lo) / (hi - lo || 1)) * (H - 60);
      const pts = path.map((p, i) => `${X(i)},${Y(p[1])}`).join(" ");
      const ticks = path.filter((_, i) => i % Math.max(1, Math.round(path.length / 8)) === 0);
      chart = `<svg viewBox="0 0 ${W} ${H}" width="100%" class="balchart">
        ${req != null ? `<line x1="${PAD}" x2="${W - PAD}" y1="${Y(req)}" y2="${Y(req)}" class="req"/><text x="${W - PAD}" y="${Y(req) - 6}" text-anchor="end" class="lbl gold">${esc(t("mytwin.minreq", { r: req }))}</text>` : ""}
        <polyline points="${pts}" class="path"/>
        ${path.map((p, i) => `<circle cx="${X(i)}" cy="${Y(p[1])}" r="3.5" class="dot ${flaggedBy[(d.transactions.find((x) => x.date === p[0] && x.balance === p[1]) || {}).id] ? "red" : "green"}"><title>${esc(p[0])} · ${inr(p[1])}</title></circle>`).join("")}
        ${ticks.map((p) => `<text x="${X(path.indexOf(p))}" y="${H - 8}" text-anchor="middle" class="tick">${esc(p[0].slice(5))}</text>`).join("")}
        ${Object.entries(tw.month_min_balance).map(([m, v]) => { const i = path.findIndex((p) => p[0].startsWith(m) && p[1] === v); return i < 0 ? "" : `<text x="${X(i)}" y="${Y(v) + 16}" text-anchor="middle" class="tick">${esc(t("mytwin.lowest", { l: v }))}</text>`; }).join("")}
      </svg>`;
    }
    const pairRow = (p) => { const bad = p.days != null && p.tat_days != null && p.days > p.tat_days; return `<div class="row pair" style="justify-content:space-between"><div><span class="mono">${esc(p.debit.date)}</span> ${esc(p.debit.channel)} <b>${inr(p.debit.debit)}</b> <span class="muted">→</span> ${p.credits.map((x) => `<span class="mono">${esc(x.date)}</span> +${inr(x.credit)}`).join(", ")}</div><div><span class="chip ${bad ? "red" : "green"}">${bad ? esc(t("mytwin.beyond", { d: p.days, n: p.tat_days })) : esc(t("mytwin.within", { n: p.tat_days }))}</span>${p.finding_ids.map((id) => `<a class="chip amb" href="#/twin/${esc(id)}">⇄ ${esc(id)}</a>`).join("")}</div></div>`; };
    const openRow = (u) => `<div class="row pair" style="justify-content:space-between"><div><span class="mono">${esc(u.txn.date)}</span> ${esc(u.txn.channel)} <b>${inr(u.txn.debit)}</b> <span class="muted">${esc(u.txn.narration)}</span></div><div><span class="chip red">${esc(t("mytwin.open", { d: u.days_open, n: u.tat_days }))}</span>${u.finding_ids.map((id) => `<a class="chip amb" href="#/twin/${esc(id)}">⇄ ${esc(id)}</a>`).join("")}</div></div>`;
    const kindChip = (k) => `<span class="chip ${/CHARGE|GST|PENAL/.test(k) ? "amb" : k === "REVERSAL" ? "green" : "grey"}">${esc(k.replace(/_/g, " ").toLowerCase())}</span>`;
    return `
    <div class="stack">
      <section class="card dark">
        <div class="eyebrow">${esc(t("nav.twin"))}</div>
        <h1 style="margin-top:6px;font-size:1.7rem">${esc(t("mytwin.h"))}</h1>
        <p style="color:#DCE8E0;max-width:70ch">${esc(t("mytwin.lede"))}</p>
        ${isDemo(d) ? `<div class="demo-tag">${esc(t("dash.demo"))}</div>` : ""}
      </section>
      <section class="card">
        <div class="pipeline">
          ${node("Customer", esc(d.profile.holder_name || "—"))}
          ${node("Account", esc(d.profile.bank || "") + (d.profile.account_last4 ? " ····" + esc(d.profile.account_last4) : ""), esc(d.profile.account_type || ""))}
          ${node("Transactions", c.transactions, `${c.debits} debit · ${c.credits} credit`)}
          ${node("Balance history", path.length, `${c.months} month(s)`)}
          ${node("Charges", c.charges, inr(c.charges_total))}
          ${node("Reversals", c.pairs, `${c.unreversed_failed} unreversed`)}
          ${node("Account state", `${tw.as_of}`, `as of · min-balance ${tw.min_balance_required != null ? inr(tw.min_balance_required) : "—"}`)}
          ${node("Rule engine", c.rules_evaluated, "RBI rules · deterministic")}
          <div class="pnode last"><div class="eyebrow">Findings</div><div class="v" style="color:var(--green)">${c.findings}</div><small class="muted">${c.flagged_lines} ${esc(t("mytwin.flagged"))} · ${c.unflagged_lines} ${esc(t("mytwin.clean"))}</small></div>
        </div>
      </section>
      ${chart ? `<section class="card"><div class="section-title" style="margin-top:0"><h2>${esc(t("mytwin.balance"))}</h2><span class="count">${path.length} points</span></div>${chart}</section>` : ""}
      <section class="card stack"><div class="section-title" style="margin-top:0"><h2>${esc(t("mytwin.pairs"))}</h2><span class="count">${tw.pairs.length + tw.unreversed.length}</span></div>${tw.pairs.map(pairRow).join("")}${tw.unreversed.map(openRow).join("")}${!tw.pairs.length && !tw.unreversed.length ? `<p class="muted" style="margin:0">—</p>` : ""}</section>
      <section class="card stack"><div class="section-title" style="margin-top:0"><h2>${esc(t("mytwin.charges"))}</h2><span class="count">${tw.charges.length} · ${inr(c.charges_total)}</span></div>${tw.charges.map((x) => `<div class="row pair" style="justify-content:space-between"><div><span class="mono">${esc(x.date)}</span> ${kindChip(x.kind)} <span class="muted">${esc(x.narration)}</span></div><div><b>${inr(x.debit)}</b> ${x.finding_ids.length ? `<span class="chip red">${esc(t("mytwin.flagged"))}</span>` : `<span class="chip green">${esc(t("mytwin.clean"))}</span>`}</div></div>`).join("")}</section>
      <section class="card">
        <div class="section-title" style="margin-top:0"><h2>${esc(t("mytwin.lines"))}</h2><span class="count">${d.transactions.length}</span></div>
        <div class="evidence"><table><thead><tr><th>Date</th><th>Narration</th><th></th><th class="r">Debit</th><th class="r">Credit</th><th class="r">Balance</th><th></th></tr></thead><tbody>
          ${d.transactions.map((r) => { const fl = flaggedBy[r.id]; return `<tr class="${fl ? "flag" : ""}"><td>${esc(r.date)}</td><td style="white-space:normal;max-width:360px">${esc(r.narration)}</td><td>${kindChip(r.kind)}</td><td class="r">${r.debit ? inr(r.debit) : ""}</td><td class="r">${r.credit ? inr(r.credit) : ""}</td><td class="r">${r.balance != null ? inr(r.balance) : ""}</td><td><button class="btn sm ${fl ? "ghost" : ""} whynot" data-id="${esc(r.id)}">${fl ? "🔴 " + esc(t("mytwin.why")) : esc(t("mytwin.whynot"))}</button></td></tr><tr class="whyrow" id="why-${esc(r.id)}" hidden><td colspan="7"></td></tr>`; }).join("")}
        </tbody></table></div>
      </section>
    </div>`;
  }
  function bindMyTwin() {
    $$(".whynot").forEach((b) => (b.onclick = async () => {
      const row = $(`#why-${b.dataset.id}`), cell = row.firstElementChild;
      if (!row.hidden) { row.hidden = true; return; }
      cell.innerHTML = `<span class="muted">…</span>`; row.hidden = false;
      try {
        const w = await api(`/accounts/${S.accountId}/transactions/${b.dataset.id}/why-not`);
        cell.innerHTML = `<div class="whybox"><ul class="checks">${w.checks.map((c) => `<li class="${c.ok ? "ok" : "no"}">${c.ok ? "✓" : "✕"} ${esc(S.lang === "ta" ? c.text_ta : c.text_en)}</li>`).join("")}</ul><div class="row" style="justify-content:space-between"><b>${esc(S.lang === "ta" ? w.result_ta : w.result_en)}</b>${w.finding_ids.map((id) => `<a class="btn sm gold" href="#/twin/${esc(id)}">⇄ ${esc(id)}</a>`).join("")}</div></div>`;
      } catch (e) { cell.innerHTML = `<span class="muted">${esc(t("err"))}${esc(e.message)}</span>`; }
    }));
  }

  // ---- Guardian screen ------------------------------------------------------------------
  async function screenGuardian() {
    const g = S.data?.guardian;
    const audit = S.data ? await api(`/accounts/${S.accountId}/audit`).catch(() => []) : [];
    const gaudit = (Array.isArray(audit) ? audit : []).filter((a) => /guardian|approval|request_approval/.test(a.action || "")).slice(0, 8);
    return `<div class="stack"><h1>${esc(t("g.h"))}</h1><p class="muted">${esc(t("g.lede"))}</p>
      <section class="card"><div class="flowline">${t("guard.flow").split(" → ").map((x, i, a) => `<span class="${g ? "done" : i === 0 ? "on" : ""}">${esc(x)}</span>${i < a.length - 1 ? "<i>→</i>" : ""}`).join("")}</div></section>
      <section class="grid2">
        <div class="card"><div class="eyebrow">${esc(t("guard.status"))}</div><div style="margin-top:6px">${g ? `<b>${esc(g.name)}</b> · ${esc(g.relation)} · ${esc(g.phone)}${g.email ? " · " + esc(g.email) : ""}<div style="margin-top:6px"><span class="chip green">${esc(t("guard.consent"))} ${g.consent_recorded_at ? esc(g.consent_recorded_at.slice(0, 10)) : "—"}</span></div>` : `<span class="muted">${esc(t("guard.none"))}</span>`}</div>${g ? `<div style="margin-top:10px"><button class="btn sm" id="revoke" style="color:var(--red)">${esc(t("guard.revoke"))}</button></div>` : ""}</div>
        <div class="card"><div class="eyebrow">${esc(t("guard.scope"))}</div><p style="margin:6px 0 0">${esc(t("guard.scope.d"))}</p></div>
      </section>
      <section class="card stack">
        ${S.data ? `<form id="gform" class="grid2">
          <label class="field">${esc(t("g.name"))}<input name="name" value="${esc(g?.name || "")}" placeholder="Kumar"></label>
          <label class="field">${esc(t("g.rel"))}<select name="relation">${["son", "daughter", "husband", "wife", "trusted person"].map((r) => `<option ${g?.relation === r ? "selected" : ""}>${r}</option>`).join("")}</select></label>
          <label class="field">${esc(t("g.phone"))}<input name="phone" value="${esc(g?.phone || "")}" placeholder="+91 98765 43210"></label>
          <label class="field">${esc(t("g.email"))}<input name="email" type="email" value="${esc(g?.email || "")}" placeholder="kumar@gmail.com"></label>
          <label class="field">Language<select name="language"><option value="ta" ${g?.language !== "en" ? "selected" : ""}>தமிழ்</option><option value="en" ${g?.language === "en" ? "selected" : ""}>English</option></select></label>
          <label class="field" style="grid-column:1/-1">${esc(t("g.consent"))}<textarea name="consent" style="min-height:70px;font-family:var(--body)" placeholder="En account-la edhavadhu thappa nadandha, en payyan Kumar-ku solunga.">${esc(g?.consent_note || "")}</textarea></label>
          <div><button class="btn primary" type="submit">${esc(t("g.save"))}</button></div>
        </form>` : `<p class="muted">${esc(t("noacct"))}</p>`}
      </section>
      ${gaudit.length ? `<section class="card"><div class="eyebrow">${esc(t("guard.audit"))}</div><div class="timeline" style="margin-top:6px">${gaudit.map((a) => `<div class="ev"><span class="t">${esc((a.at || "").replace("T", " ").slice(0, 16))}</span><span><b>${esc(a.action)}</b> — ${esc(a.detail || "")}</span></div>`).join("")}</div></section>` : ""}
    </div>`;
  }
  function bindGuardian() {
    const f = $("#gform");
    if (f) f.onsubmit = async (e) => { e.preventDefault(); const el = f.elements; try { await post(`/accounts/${S.accountId}/guardian`, { name: el.name.value, relation: el.relation.value, phone: el.phone.value, email: el.email.value, language: el.language.value, consent_transcript: el.consent.value }); await loadAccount(); toast("✓"); route(); } catch (err) { toast(t("err") + err.message); } };
    const r = $("#revoke");
    if (r) r.onclick = async () => { if (!confirm(t("guard.revoke") + "?")) return; try { await api(`/accounts/${S.accountId}/guardian`, { method: "DELETE" }); await loadAccount(); toast(t("guard.revoked")); route(); } catch (e) { toast(t("err") + e.message); } };
  }

  // ---- Privacy centre --------------------------------------------------------------------
  function screenPrivacy() {
    const L = S.lang;
    const controls = L === "ta" ? ["Sign-in கட்டாயம்: password salted PBKDF2-HMAC-SHA256 hash-ஆ மட்டும் (200,000 rounds); session HttpOnly cookie", "Database-ல எல்லாம் AES-256-GCM encrypt — statements, findings, cases, காப்பாளர்; key database-க்கு வெளியே", "ஒவ்வொரு account-ம் ஒரு user-க்கு மட்டும்; வேற user-க்கு 404", "Upload: PDF / CSV / XLSX / படம் மட்டும், 15 MB வரை", "Statement file சேமிக்கப்படாது — transaction lines மட்டும்", "Local SQLite database; எங்க server-க்கு எதுவும் போகாது", "Secrets .env-ல மட்டும்; code-ல key இல்ல", "VASOOL_DEMO_TO / VASOOL_DEMO_PHONE: எல்லா mail / call-ம் ஒரே safe address-க்கு", "எந்த bank-க்கும் email / call இல்ல — design-ல hard-coded", "Security headers: nosniff, no framing, no referrer, API no-store", "ஒவ்வொரு மாற்றமும் audit log-ல", "ஒரே button-ல எல்லா data-ஐயும் அழிக்கலாம்"]
      : ["Sign-in required: passwords stored only as salted PBKDF2-HMAC-SHA256 hashes (200,000 rounds); sessions are HttpOnly cookies", "Everything in the database is encrypted at rest with AES-256-GCM — statements, findings, cases, guardian; the key lives outside the database", "Each account belongs to one user; another user gets 404, not 403 — existence is never confirmed", "Uploads: PDF / CSV / XLSX / image only, 15 MB limit, checked server-side", "The statement file is never stored — only its transaction lines", "One local SQLite database on this machine; nothing is sent to us", "Secrets live only in .env; no keys in code or logs", "VASOOL_DEMO_TO / VASOOL_DEMO_PHONE redirect every mail and call to one safe address", "No bank is ever emailed or called — hard-coded, not configurable", "Security headers on every response: nosniff, no framing, no referrer, API responses never cached", "Every state change is written to the audit log", "One button deletes everything for the account"];
    const item = (k) => `<div class="card"><div class="eyebrow">${esc(t(k))}</div><p style="margin:6px 0 0">${esc(t(k + ".d"))}</p></div>`;
    return `<div class="stack"><h1>${esc(t("priv.h"))}</h1><p class="muted">${esc(t("foot.privacy"))}</p>
      <section class="grid2" style="grid-template-columns:repeat(2,minmax(0,1fr))">${item("priv.what")}${item("priv.why")}${item("priv.keep")}${item("priv.who")}</section>
      <section class="card"><div class="eyebrow">${esc(t("priv.never"))}</div><div class="row" style="margin-top:8px">${["net-banking password", "OTP", "ATM PIN", "CVV", "Aadhaar / PAN"].map((x) => `<span class="chip green">✓ ${esc(L === "ta" ? x : x)} — ${esc(L === "ta" ? "கேக்க மாட்டோம்" : "never")}</span>`).join("")}</div></section>
      <section class="card"><div class="eyebrow">${esc(t("priv.controls"))}</div><ul class="checks" style="margin-top:8px">${controls.map((x) => `<li class="ok">✓ ${esc(x)}</li>`).join("")}</ul></section>
      ${S.data ? `<section class="card row" style="justify-content:space-between"><div><b>${esc(acctLabel(S.data))}</b><div class="muted" style="font-size:.85rem">${esc(S.accountId)}</div></div><div class="row"><a class="btn sm" href="/api/accounts/${esc(S.accountId)}/audit" target="_blank">${esc(t("guard.audit"))}</a><button class="btn sm" id="delete" style="color:var(--red)">${esc(t("priv.delete"))}</button></div></section>` : ""}
    </div>`;
  }
  function bindPrivacy() {
    const d = $("#delete");
    if (d) d.onclick = async () => { if (!confirm(t("priv.delete") + "?")) return; await api(`/accounts/${S.accountId}`, { method: "DELETE" }); S.accountId = null; S.data = null; S.cases = []; localStorage.removeItem("vr.account"); toast(t("priv.deleted")); location.hash = "#/"; };
  }

  // ---- login / signup ----------------------------------------------------------------------
  function screenLogin() {
    const up = S.authMode === "signup";
    return `
    <div class="stack" style="max-width:480px;margin:0 auto">
      <section class="card dark"><div class="eyebrow">Bank IQ</div><h1 style="margin-top:6px;font-size:1.6rem">${esc(t("auth.h"))}</h1><p style="color:#DCE8E0;margin:8px 0 0">${esc(t("auth.lede"))}</p></section>
      <form id="authform" class="card stack">
        <label class="field">${esc(t("auth.login"))}<input name="login" autocomplete="username" placeholder="+91 98765 43210 / you@gmail.com" required minlength="3"></label>
        ${up ? `<label class="field">${esc(t("auth.name"))}<input name="name" autocomplete="name" placeholder="Selvi R" required></label>` : ""}
        <label class="field">${esc(t("auth.pass"))}<input name="password" type="password" autocomplete="${up ? "new-password" : "current-password"}" required minlength="6"></label>
        <button class="btn primary" type="submit">${esc(up ? t("auth.signup") : t("auth.signin"))}</button>
        <button class="btn ghost" type="button" id="authtoggle">${esc(up ? t("auth.toggle.in") : t("auth.toggle.up"))}</button>
        <p class="muted" style="margin:0;font-size:.85rem">🔒 ${esc(t("auth.never"))}</p>
      </form>
    </div>`;
  }
  function bindLogin() {
    $("#authtoggle").onclick = () => { S.authMode = S.authMode === "signup" ? "login" : "signup"; route(); };
    $("#authform").onsubmit = async (e) => {
      e.preventDefault(); const f = e.target.elements;
      try {
        const body = { login: f.login.value.trim(), password: f.password.value };
        if (S.authMode === "signup") body.name = f.name.value.trim();
        const r = await post(S.authMode === "signup" ? "/auth/signup" : "/auth/login", body);
        S.user = r.user; renderUser(); toast("✓ " + (r.user.name || r.user.login));
        const target = S.after && !S.after.startsWith("#/login") ? S.after : "#/"; S.after = null;
        if (location.hash === target || (!location.hash && target === "#/")) route(); else location.hash = target;
      } catch (err) { toast(t("err") + err.message, 5000); }
    };
  }
  function renderUser() {
    const el = $("#userchip"); if (!el) return;
    el.innerHTML = S.user && S.auth ? `<span class="muted" style="color:#DCE8E0;font-size:.85rem">${esc(S.user.name || S.user.login)}</span> <button class="langbtn" id="logout">${esc(t("auth.out"))}</button>` : "";
    const lo = $("#logout"); if (lo) lo.onclick = async () => { await post("/auth/logout").catch(() => { }); S.user = null; S.accountId = null; S.data = null; S.cases = []; localStorage.removeItem("vr.account"); renderUser(); location.hash = "#/login"; };
  }
  const PUBLIC_ROUTES = ["#/login", "#/rules", "#/privacy", "#/intelligence"];

  // ---- settings ------------------------------------------------------------
  async function screenSettings() {
    const g = S.data?.guardian;
    const n = (S.health = S.health || await api("/health").catch(() => ({}))).notify || {};
    return `<div class="stack"><h1>${esc(t("settings.h"))}</h1>
      <section class="card stack ${n.email ? "soft" : ""}"><h2>${esc(t("n.h"))}</h2>
        <p style="margin:0">${n.email ? "📧 " + esc(t("n.on", { f: n.from })) : esc(t("n.off"))}</p>
        ${n.demo_to ? `<p class="muted" style="margin:0">🔒 ${esc(t("n.demo", { to: n.demo_to }))}</p>` : ""}
        <p class="muted" style="margin:0;font-size:.88rem">${esc(t("n.bank"))} ${n.email ? "" : esc(t("n.how"))}</p>
        ${n.email ? `<div class="row"><input id="testto" placeholder="${esc(n.demo_to || "someone@gmail.com")}" style="max-width:280px"><button class="btn sm" id="testmail">${esc(t("n.test"))}</button></div>` : ""}
        <p style="margin:8px 0 0">${n.voice ? "📞 " + esc(t("n.voice.on", { f: n.from })) : esc(t("n.voice.off"))}</p>
        ${n.demo_phone ? `<p class="muted" style="margin:0">🔒 ${esc(t("n.demo.phone", { to: n.demo_phone }))}</p>` : ""}
        ${n.voice ? `<div class="row"><input id="testcallto" placeholder="${esc(n.demo_phone || "+91 98765 43210")}" style="max-width:280px"><button class="btn sm" id="testcall">${esc(t("n.testcall"))}</button></div>` : ""}
        <p style="margin:8px 0 0">${n.telegram ? "🔴 " + esc(t("n.tg.on", { c: n.telegram_chat })) : esc(t("n.tg.off"))}</p>
        ${n.telegram ? `<div class="row"><button class="btn sm" id="testtg">${esc(t("n.tgtest"))}</button></div>` : ""}
      </section>
      <section class="card"><div class="eyebrow">${esc(t("g.h"))}</div><p style="margin:6px 0 0"><a href="#/guardian">${esc(t("nav.guardian"))} →</a> · <a href="#/privacy">${esc(t("priv.h"))} →</a></p></section>
      ${S.data ? `<section class="card stack"><h2>Basic account</h2><p class="muted">${esc(S.lang === "ta" ? "Minimum balance இல்லாத, charge இல்லாத Basic Savings account-க்கு மாத்த உங்களுக்கு உரிமை இருக்கு. 7 நாளுக்குள்ள bank பண்ணணும்." : "You have the right to a zero-charge Basic Savings account with no minimum balance. The bank must convert within 7 days of asking.")}</p><a class="btn" href="/api/accounts/${esc(S.accountId)}/basic-account-letter" target="_blank">${esc(t("s.basic"))}</a></section>
` : ""}
    </div>`;
  }
  function bindSettings() {
    const tc = $("#testcall");
    if (tc) tc.onclick = async () => { tc.disabled = true; try { const r = await post(`/notify/test-call`, { to: $("#testcallto").value, lang: S.lang }); toast(r.placed ? t("call.placed", { to: r.to }) : t("call.sim", { r: r.reason }), 6000); } catch (e) { toast(t("err") + e.message); } tc.disabled = false; };
    const tg = $("#testtg");
    if (tg) tg.onclick = async () => { tg.disabled = true; try { const r = await post(`/notify/test-alert`); toast(r.sent ? t("alert.sent") : t("alert.sim", { r: r.reason }), 6000); } catch (e) { toast(t("err") + e.message); } tg.disabled = false; };
    const tm = $("#testmail");
    if (tm) tm.onclick = async () => { tm.disabled = true; try { const r = await post(`/notify/test`, { to: $("#testto").value }); toast(r.sent ? t("mail.sent", { to: r.to }) : t("mail.sim", { r: r.reason }), 6000); } catch (e) { toast(t("err") + e.message); } tm.disabled = false; };
    const f = $("#gform");
    if (f) f.onsubmit = async (e) => { e.preventDefault(); const el = f.elements; try { await post(`/accounts/${S.accountId}/guardian`, { name: el.name.value, relation: el.relation.value, phone: el.phone.value, email: el.email.value, language: el.language.value, consent_transcript: el.consent.value }); await loadAccount(); toast("✓"); route(); } catch (err) { toast(t("err") + err.message); } };
    const d = $("#delete");
    if (d) d.onclick = async () => { if (!confirm(t("s.delete") + "?")) return; await api(`/accounts/${S.accountId}`, { method: "DELETE" }); S.accountId = null; S.data = null; S.cases = []; localStorage.removeItem("vr.account"); toast(t("s.deleted")); location.hash = "#/"; };
  }

  // ------------------------------------------------------------------ router
  let routing = false;
  async function route() {
    if (routing) { setTimeout(route, 30); return; }
    routing = true;
    clearInterval(S._poll);
    try {
      const hash = (location.hash || "#/").replace(/#statements$/, "");
      const anchor = /#statements$/.test(location.hash);
      $$(".nav a").forEach((a) => a.classList.toggle("active", hash === a.getAttribute("href") || (a.getAttribute("href") === "#/cases" && hash.startsWith("#/case")) || (a.getAttribute("href") === "#/twin" && hash.startsWith("#/twin/"))));
      const app = $("#app");
      if (S.auth === undefined) { try { const m = await api("/auth/me"); S.auth = m.auth; S.user = m.user; } catch { S.auth = true; S.user = null; } renderUser(); }
      if (S.auth && !S.user && !PUBLIC_ROUTES.includes(hash) && !hash.startsWith("#/approve/")) { if (hash !== "#/login") S.after = hash; app.innerHTML = screenLogin(); bindLogin(); return; }
      if (hash === "#/login") { if (S.user) { location.hash = "#/"; return; } app.innerHTML = screenLogin(); bindLogin(); return; }
      if (!S.data && S.accountId) await loadAccount();
      let html = "", bind = null;
      if (hash === "#/") { if (S.accountId) await loadAccount(); html = await screenHome(); bind = bindHome; }
      else if (hash === "#/findings") { if (S.accountId) await loadAccount(); if (!S.samples) S.samples = await api("/samples").catch(() => []); html = screenFindings(); bind = bindFindings; }
      else if (hash.startsWith("#/case/")) { const id = hash.split("/")[2]; html = await screenCase(id); bind = () => bindCase(id); }
      else if (hash === "#/cases") { if (S.accountId) await loadAccount(); html = screenCases(); }
      else if (hash === "#/history") { html = await screenHistory(); bind = bindHistory; }
      else if (hash === "#/twin") { if (S.accountId) await loadAccount(); html = await screenMyTwin(); bind = bindMyTwin; }
      else if (hash === "#/guardian") { if (S.accountId) await loadAccount(); html = await screenGuardian(); bind = bindGuardian; }
      else if (hash === "#/privacy") { html = screenPrivacy(); bind = bindPrivacy; }
      else if (hash === "#/ask") { html = screenAsk(); bind = bindAsk; }
      else if (hash === "#/intelligence") { html = await screenIntel(); bind = bindIntel; }
      else if (hash === "#/rules") { html = await screenRules(); }
      else if (hash === "#/settings") { html = await screenSettings(); bind = bindSettings; }
      else if (hash.startsWith("#/twin/")) { const fid = hash.split("/")[2]; html = await screenTwin(fid); bind = bindTwin; }
      else if (hash.startsWith("#/approve/")) { const tok = hash.split("/")[2]; html = await screenApprove(tok); bind = () => bindApprove(tok); }
      else { html = `<div class="empty">Not found.</div>`; }
      app.innerHTML = html;
      if (bind) bind();
      if (anchor && $("#statements")) $("#statements").scrollIntoView({ behavior: "smooth" }); else window.scrollTo({ top: 0 });
    } catch (e) { $("#app").innerHTML = `<div class="empty">${esc(t("err"))}${esc(e.message)}</div>`; }
    finally { routing = false; }
  }
  window.addEventListener("hashchange", route);
  applyLang();
  api("/health").then((h) => ($("#foot-version").textContent = `v${h.version} · rulebook ${h.rulebook} · ${h.rules} rules`)).catch(() => { });
  if ("speechSynthesis" in window) window.speechSynthesis.onvoiceschanged = () => { };
  route();
})();
