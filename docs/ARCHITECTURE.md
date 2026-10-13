# Architecture

## One sentence

A statement goes in; a **twin** of the account's rule-relevant state is rebuilt; every rule in force on each transaction's date compares *what should have happened* with *what did*; the differences become labelled, cited, prioritised findings; a human turns them into a case; the case runs on the statutory clock until the money is back or the bank proves it was right.

## Pipeline

```
file ──▶ parsers ──▶ classify ──▶ pairing ──▶ twin ──▶ rules ──▶ priority ──▶ findings
 PDF/CSV   rows       channel/kind   debit↔reversal  monthly ATM   expected vs   amount ×      🔴 🟡 ⚪
 XLSX/img             merchant       ref/amount/     counts,       actual per    confidence ×  + questions
                      own-bank ATM   partial sums    balance path, rule in force effort ×      + evidence
                                                     txn gaps      on that date  legal weight
                                                                                       │
             ┌─────────────────────────────────────────────────────────────────────────┘
             ▼
        human tap ──▶ case (state machine) ──▶ complaint pack ──▶ 30-day clock ──▶ closed loop
        guardian /       FOUND→PREPARED→          bank letter +       tick() daily     next statement
        holder           AWAITING→SENT→…          ombudsman draft +   DEADLINE_PASSED  detect_recovery()
                                                  evidence table
```

Every stage is a pure function of its inputs except storage and channels. Re-running a scan with the same file, profile, date and answers yields identical findings with identical ids (ids are hashes of rule + evidence + label).

## The twin (`vasool/twin.py`)

`TwinContext` holds what a rule needs and a statement cannot show directly:

* **ATM usage per month, split own/other bank.** Unknown ATMs count as own-bank — more free transactions, fewer claims, fewer false positives. Balance enquiries count, as RBI says.
* **Balance path** — lowest balance per month, so the minimum-balance rules can be *confirmed* from the statement when the balance never dipped.
* **Customer-initiated transaction gaps** — for the inoperative-account rule (730 days).
* **Charge history by kind** — for the "increase needs one month's notice" rule.
* **Pairing result** — see below.
* **Answers** — the customer's replies to *needs checking* questions, keyed `question_id:txn_id`.

## Pairing (`vasool/pairing.py`)

The hard part of the ₹100/day rule. Order: same reference → same amount + channel within 60 days → partial/batched reversals (up to three credits summing to the debit). An ordinary UPI payment with no reversal is a **successful payment**, not a claim. A debit becomes a failed-transaction candidate only if the narration says so, a reversal proves it, or the customer confirms it. Same-amount retries within two days are *asked about* (`suspicious_debits`), never claimed.

## Rules (`vasool/rules/`)

One evaluator per rule id. Each returns `Finding`s with: label, confidence, amount, evidence (transaction ids), calculation text, expected, actual, bilingual summaries, questions, prevention, group key. Rules with `status: suggest` in the rulebook **cannot** emit RECOVERABLE — `RuleEvaluator.finding()` downgrades them to UNCLEAR.

Effective dates are enforced per transaction: the ATM cap evaluator picks `RBI-ATM-2021-CAP` or `RBI-ATM-2025-CAP` by the charge's date. Adding a rule = add JSON + an evaluator + a test.

`_dedupe` keeps one RECOVERABLE finding per evidence line (largest amount) and drops UNCLEAR/AVOIDABLE findings on lines already recoverable under another rule.

## Priority (`vasool/priority.py`)

`score = 0.40·amount + 0.25·confidence + 0.20·legal_strength + 0.15·effort (+0.10 if older than 10 months)`

* `RECOVER_NOW` — ≥ ₹500, or score ≥ 0.75 and ≥ ₹100
* `COMBINE` — group total ≥ ₹300, or an UNCLEAR item ≥ ₹100 (one answer settles it)
* `NOT_WORTH_IT` — we keep watching; it joins a bundle if more appear
* `PREVENT` — nothing to recover; how to stop the next one

## Cases (`vasool/cases.py`)

A guarded state machine (`ALLOWED` transitions). `SENT_TO_BANK` stamps `sent_on`, `bank_reply_due = +30d` and `ombudsman_deadline = +90d` from the rulebook's process rule. `tick()` moves to `DEADLINE_PASSED` automatically. `detect_recovery()` matches a later credit (±2%, refund-like narration) to close the loop. `user_status()` gives the customer-facing sentence — the legal ladder is never shown.

## Guardian (`vasool/guardian.py`)

Two artefacts per approval request, in this order: a holder voice script (Tamil/English, IVR options) and a guardian message carrying only amount, rule ids and an approve token — never balance or spending. `Channel` is a protocol; `ConsoleChannel` logs; a Twilio/Exotel adapter implements the same two methods. Approval tokens are single-use.

## Assistant (`vasool/assistant.py`)

Intent detection (regex, EN/TA/Tanglish) over findings, cases and rules. Every answer is assembled from data and reports `grounded_on` ids. An optional `Rephraser` (env `VASOOL_LLM=on` + provider key) may rewrite the text for readability with a prompt that forbids adding facts; on any error the grounded text is returned unchanged.

## Merging statements (`vasool/merge.py`)

An account is one transaction history built from many files. `merge_transactions(existing, incoming)` unions them: a line's identity is *(date, normalised narration, debit, credit, balance)* — balance is dropped from the key only when one side has none (passbook photo vs CSV). Existing lines keep their ids, because finding ids and the user's answers hang off transaction ids; new lines get fresh ids; `seq` is renumbered so same-day order stays stable. If the new slice's first balance does not follow from the old slice's last, a warning names the jump (missing period, or a different account). `coverage()` merges statement periods and lists gaps ≥ 7 days; the API turns each gap into a warning because month-counted rules (ATM, minimum balance) can only judge months they can see. A file whose detected bank or account-number suffix differs from the account is refused (409) rather than merged.

## Printable complaint (`vasool/printable.py`)

Self-contained HTML with print CSS (`@page A4`, `break-inside: avoid` on each claim and table row). Two documents: the bank complaint (To/From/Date/Subject, numbered claims each with RBI reference, rule requirement, statement fact, calculation and amount; request; signature block; bank acknowledgement box; Annexure A with the evidence lines copied verbatim) and the RBI Ombudsman draft laid out as the cms.rbi.org.in fields. The screen-only strip carries the print button and a Tamil/English checklist (two copies, get one stamped, who signs, when to escalate). Only evidence lines are printed — ordinary spending never leaves the app. `?print=1` calls `window.print()` on load; the browser's *Save as PDF* is the PDF.

## Storage (`vasool/store.py`)

SQLite, JSON documents per row, audit table, single-use approvals, `delete_account()` erases every table (DPDP). Swap for Postgres by reimplementing `Store`.

Tables: `accounts` (profile, the merged transaction list, answers, as_of), `statements` (one row per uploaded file: filename, kind, period, line counts, new/duplicate counts, the ids of the lines it contributed — so a statement can be removed again — and parse warnings), `findings`, `cases`, `guardians`, `notifications`, `approvals`, `audit`. `list_accounts()` is the History screen: per account, statements, period, total found, cases open, amount recovered.

## API (`api/main.py`)

FastAPI. Nothing changes state without an explicit human action. `/api/scan` (one or many files; with `account_id` they are merged into that account) → account; `POST /accounts/{id}/statements` → merge + rescan; `GET/DELETE …/statements[/{sid}]`; `GET /accounts` → history; `/answers` → rescan; `/cases/{id}/complaint.html` and `ombudsman.html` → print-ready pages; `/cases` → prepared pack; `/request-approval` → call + message; `/approvals/{token}` → sent; `/event` → guarded transitions; `/check-recovery` → closed loop; `/ask` → grounded answer; `/claims/*` → user-initiated rules; `DELETE /accounts/{id}`.

## Web (`web/static/`)

No build step. Hash router, EN/TA dictionary, `speechSynthesis` for Tamil output, `SpeechRecognition` for voice input where the browser has it, one primary button per screen. Design tokens match the deck: deep green, gold, one red.

## What would change for production

* Account Aggregator ingestion via a partner FIU (consent → monthly statements → same `scan.rescan`).
* Bank-SMS notification reader on Android as a second automatic pipe.
* Real voice/WhatsApp channel adapters; WhatsApp-first onboarding; missed-call IVR.
* Rulebook Ops: watcher on RBI notifications → PR → legal review → tests → release; every rule `suggest` until reviewed.
* Precision gate: ≥95% on 🔴 before a rule may generate complaints; human review queue for the first 200 cases of any rule and any case above ₹10,000.
* Multi-bank parser corpus and golden set growth from real (consented, anonymised) statements.
