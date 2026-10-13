# Privacy & data handling

**What we take:** a statement file or passbook photo, an account profile (bank, account type, city tier, minimum balance, name, language), your answers to yes/no questions, and — if you choose — one guardian's name, relation, phone and your spoken/typed consent.

**What we never take:** net-banking passwords, PINs, OTPs, card numbers beyond what the bank prints on the statement.

**What we keep:** normalised transactions (date, narration, amounts, balance, reference), findings, cases, the guardian record, notification log, audit log. The uploaded file itself is parsed in memory and discarded.

**What the guardian sees:** that an issue exists, the amount, the rule ids, and an approve button. Never your balance, salary, spending or other transactions.

**Deletion:** `DELETE /api/accounts/{id}` (Settings → *Delete all my data*) erases every table for the account — findings, cases, guardian, notifications, approvals, audit.

**Processing:** on the server you run. The Docker image needs no outbound network. The optional language-model rephraser is off by default (`VASOOL_LLM=off`); when on, it receives only the already-grounded answer text.

**Purpose limitation:** data is used only to evaluate RBI rules against your account and to prepare complaints you approve. No sale, no sharing, no advertising, no scoring for third parties.

**DPDP Act 2023 mapping:** consent per data source at upload; purpose stated on screen; erasure on request; audit log of every action taken in the customer's name; guardian representation recorded with the holder's consent text and timestamp.
