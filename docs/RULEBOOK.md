# The rulebook

`rulebook/rules.json` is the product. Everything else is machinery around it.

## Shape of a rule

| Field | Meaning |
|---|---|
| `id` | Stable identifier, `REGULATOR-TOPIC-YEAR-QUALIFIER` |
| `status` | `active` — may generate a claim · `suggest` — raises *needs checking* only until a second reviewer confirms text and dates · `retired` |
| `right_en` / `right_ta` | The rule as a plain-language *right*, first thing the customer sees |
| `source` | Circular number, title, date, URL — every rule links to its source |
| `effective_from` / `effective_to` | The window in which the rule applies; the engine judges each transaction by the rules in force on its date |
| `evaluable_from` | What the engine needs: `statement`, `profile`, `user` (a question), `document` (e.g. KFS), `case` |
| `parameters` | The numbers (TAT days, ₹/day, caps, free limits) |
| `formula` | Human-readable arithmetic — what the evaluator implements |
| `evidence_required` | What the complaint will attach |
| `questions` | Bilingual questions with options when the statement can't show a fact |
| `compensation_type` | `statutory` · `refund` · `prevent` · `process` |

## Rules in this version (2026.09.13)

| id | status | window | in one line |
|---|---|---|---|
| RBI-TAT-2019-ATM | active | 2019-10-15 → | Failed ATM cash not reversed by T+5 → ₹100/day, automatic |
| RBI-TAT-2019-UPI | active | 2019-10-15 → | Failed UPI/IMPS/card transfer not reversed by T+1 → ₹100/day |
| RBI-TAT-2019-POS | active | 2019-10-15 → | Failed PoS/e-com card txn not reversed by T+5 → ₹100/day |
| RBI-MINBAL-2014-NOTICE | active | 2015-04-01 → | Penalty needs prior notice + one month to restore |
| RBI-MINBAL-2014-PROPORTION | active | 2015-04-01 → | Penalty proportionate to shortfall |
| RBI-MINBAL-2014-NEGATIVE | active | 2015-04-01 → | Charge may not push balance negative |
| RBI-ATM-2025-FREE | active | 2025-05-01 → | 5 free own-bank, 3/5 other-bank; enquiries count |
| RBI-ATM-2025-CAP | active | 2025-05-01 → | Max ₹23 (+tax) per transaction beyond free |
| RBI-ATM-2021-CAP | active | 2022-01-01 → 2025-04-30 | Max ₹21 (historical) |
| RBI-SMS-2015-USAGE | active | 2015-07-01 → 2026-12-31 | SMS charges only on actual usage, if disclosed |
| RBI-SMS-2027-BAN | active | 2027-01-01 → | No charge for regulatory SMS alerts |
| RBI-DISCLOSE-2015-NOTICE | suggest | 2015-07-01 → | Charge increases need one month's notice |
| RBI-INOP-2024-NOPENALTY | active | 2024-04-01 → | No penalty / reactivation charge on inoperative accounts |
| RBI-BSBDA-2026-ZEROCHARGE | active | 2026-04-01 → | Basic account: no charges; conversion within 7 days |
| RBI-CARD-2022-CLOSURE | active | 2022-07-01 → | Card closure within 7 working days else ₹500/day |
| RBI-LIAB-2017-ZERO | active | 2017-07-06 → | Unauthorised txn reported ≤3 working days → zero liability; shadow credit ≤10 working days |
| RBI-KFS-2024-NOEXTRA | active | 2024-10-01 → | No loan charge outside the Key Fact Statement |
| RBI-PENAL-2023-NOCAP | suggest | 2024-04-01 → | Penal charges disclosed, not capitalised |
| RBI-GOLD-2025-RELEASE | active | 2026-04-01 → | Gold returned ≤7 working days after repayment else ₹5,000/day |
| RBI-LOCKER-2021-LIABILITY | suggest | 2022-01-01 → | Locker loss: liability up to 100× annual rent |
| RBI-OMBUDSMAN-2026-CLOCK | active | 2026-07-01 → | Bank replies in 30 days; Ombudsman within 90 days after; free |
| RBI-IO-2026-AUTOESCALATE | active | 2026-01-14 → | Rejections auto-escalate to Internal Ombudsman in 20 days |

## How a rule changes (Rulebook Ops)

1. A watcher (or a person) spots an RBI notification touching customer charges, TAT, cards, loans or grievance.
2. Open a PR: edit `rules.json` — new `effective_from`, or a new rule with `supersedes`, and close the old rule's `effective_to`.
3. Add or update the evaluator and a golden test with a transaction on each side of the boundary.
4. A second reader opens the source URL and confirms text + dates. Until then the rule is `suggest`.
5. Bump `version`. CI validates the schema and runs the tests.

The ₹21 → ₹23 ATM cap on 1 May 2025 is the worked example: two rules, adjacent windows, one test that puts a ₹25 charge on 24 April and a ₹23 charge on 22 May.

## Things this rulebook deliberately does not claim

* A per-day compensation for delayed shadow credit (none is prescribed; it is a deficiency of service).
* A fixed number of days for gold-loan auction notice (the direction says "adequate notice").
* Any compensation for app/UPI downtime as such (only failed transactions are compensated).
* That the SMS ban applies before 1 January 2027 (it was issued 24 June 2026).
