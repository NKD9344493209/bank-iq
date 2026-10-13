# Demo script — 3 minutes, one flow

**Before:** `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`, open http://localhost:8000, **English** for the judges' reading (switch to தமிழ் for the call). Windows dark mode is fine — the app stays white and green. Rehearse the three lines in bold.

Flow: **Statement → Digital twin → Regulatory engine → Evidence → AI explanation → User confirmation → Evidence pack → Action.**

| t | Say | Do |
|---|---|---|
| 0:00 | "Amma's Canara pension passbook, three months. Synthetic — it says so on screen." | Home → *canara amma pension 2026* → type the demo phone → **Check my account** |
| 0:10 | "Watch the twin build: 23 lines, 3 months, 1 reversal pair and 1 open failure, 19 RBI rules — each at its own date." | the scan timeline fills with real numbers → **SCAN COMPLETE** |
| 0:25 | "**Is her account being charged fairly?** ₹5,027 potential — not guaranteed — 5 findings: 2 need action, 2 need one answer, 1 is only information." | Home dashboard (click **Home** once) → **Review my findings** |
| 0:40 | "Every rupee has its chain." | ₹3,800 card → **Evidence chain** → walk 1→8: what happened, what should have, what we found, why, statement line, rule in force with circular and date, calculation, potential claim |
| 1:00 | "This is the twin itself: the actual lane, the expected lane, the gap growing ₹100 a day." | **See the twin** → band fills → ← Back |
| 1:10 | "Every day the bank waits, the number grows." | drag the **as-of** slider a month ahead → the total rolls up; the reversed ATM one stays frozen → **today** |
| 1:25 | "And here is what we did *not* flag. ₹50,000 college fees — a big number, not a finding. This is why." | **My Twin** → scroll to the lines → **Why wasn't this flagged?** on the ₹50,000 line → checklist: no failure hint, no reversal, successful payment, size is never a reason |
| 1:45 | "The AI only explains. The engine decided." | **Ask** → *why was ₹295 charged?* → it names the rule and asks the one question → answer **No** on the Findings card → the ₹348 becomes a potential claim |
| 2:05 | "Get it back builds the evidence pack. Nothing is sent." | **Get it back** → **CASE READY** → *Evidence pack (print / PDF)* — glance at the A4: numbered claims, RBI reference, Annexure A |
| 2:20 | "Amma can't read this. Her phone rings first — in Tamil. Kumar gets one message with one button." | **Ask my guardian** → phone rings (speaker, one sentence) → Kumar's mail → **Approve** → status *Ready to submit* |
| 2:45 | "Rulebook: 19 rules implemented, 22 listed, 40 mapped — not all of RBI, and we say so. 101 tests, real results on screen." | **Rulebook** → scope box → System validation card |

**Say out loud, once:** *potential, not guaranteed* · *the app never contacts a bank; the pack is yours to hand in* · *no real claim filed yet*.

## Jury feedback from Evaluation 1 (25 Sep, noon) — and what changed by 3 PM

1. **"A ₹5 claim may run out of time while you wait to club it into a bigger amount."** → Every finding now carries an *act-by* date from the RBI Ombudsman limitation clock. Inside 60 days it turns red, is promoted to *Recover now* whatever the amount, and a **Telegram red alert** goes out once. Unreversed failures are always urgent. Show it: drag the as-of slider forward → the ₹27 turns red → the phone buzzes.
2. **"How securely do you store this? Why would a common person trust you with bank data?"** → Sign-in with PBKDF2-hashed passwords and HttpOnly sessions; every account belongs to one user; **everything in the database is AES-256-GCM encrypted**. Show it: open `data/vasool.db` in the SQLite viewer → ciphertext. Privacy centre lists exactly these controls.

## Real-phone setup (do this the night before)

### The mail (guardian's one button)
1. Gmail account for the team → 2-Step Verification → Google Account › Security › **App passwords** → create one ("Mail") → 16 characters.
2. Copy `.env.example` to `.env` in the app folder and fill `VASOOL_SMTP_USER`, `VASOOL_SMTP_PASS`, and `VASOOL_DEMO_TO` = the teammate's Gmail (the phone shown to the judges). With `VASOOL_DEMO_TO` set, every mail goes there — no address typed anywhere else can leak out.
3. Laptop and that phone on the **same hotspot** (the phone's own hotspot — college Wi-Fi often blocks port 465 and device-to-device traffic). The server prints the laptop's IPv4; put it in `.env` as `VASOOL_PUBLIC_URL=http://<ip>:8000` so the button in the mail opens the app on the phone.
4. Settings → **Real delivery** → *Send test mail* → arrives in under 10 s. Open `http://<ip>:8000` on the phone once to confirm reach.

### Red alerts on Telegram
1. Telegram → **@BotFather** → `/newbot` → copy the token into `.env` as `VASOOL_TELEGRAM_TOKEN`.
2. Open your new bot in Telegram and send it any message. Then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy `"chat":{"id": …}` into `.env` as `VASOOL_TELEGRAM_CHAT`.
3. Restart → Settings → *Telegram alerts are ON* → **Send test alert** — it sends a full red alert built from a real finding (your most urgent one, else the demo statement), so the judges see the actual message shape: statement line, RBI rule + circular, arithmetic, act-by date, three steps.

### The call (Amma's phone rings)
1. twilio.com → free trial → verify your own mobile → **Get a trial number**.
2. Console home › *Account Info*: copy **Account SID**, **Auth Token**, and the trial **phone number** into `.env` as `VASOOL_TWILIO_SID`, `VASOOL_TWILIO_TOKEN`, `VASOOL_TWILIO_FROM` (the number in `+1…` form).
3. `VASOOL_DEMO_PHONE=+91xxxxxxxxxx` — the phone you will hold up. A trial account can only ring **verified** numbers, and this line redirects every call there anyway, so the demo cannot ring a stranger.
4. Restart the server → Settings → *Voice is ON* → **Test call** → the phone rings within seconds. A trial call starts with Twilio's own 5-second preamble ("you have a trial account…") — press any key on the phone and the Tamil voice follows. Say that out loud before the judges hear it.
5. If the hall has no data: the toast says *Call simulated (…)* and the on-screen Play-the-call button still speaks the same script — the demo does not break.

What is real vs simulated — say it out loud: *the call and the message to the family are real; the send to the bank is simulated — the complaint copy is mailed to the family with the bank's grievance address printed on it, and the printout goes to the branch.* Nothing in this build can email or call a bank.

## If the judges ask

**"Isn't this just a rule engine?"** — Yes, on purpose: the engine decides, the LLM only explains. Scan *sbi arun student 2025*: partial reversal within T+5 → no claim; ₹25 in April judged by the ₹21 cap then; 6th withdrawal marked allowed; the Zomato retry is *asked about*, never claimed.

**"Where's the twin?"** — Open any ⇄ button. Two states, one delta, and the delta *moves with time* (the slider). That is the definition on slide 3, running.

**"What about other months / accounts?"** — Statements card: any number of files, duplicates dropped, gaps named; the twin marks months it cannot see as blind. **History** tab: every account scanned.

**"What if I pay ₹50,000 college fees?"** — It's in Amma's statement. Not flagged. No anomaly detection.

**"Have you recovered real money?"** — No. Say so. The refund is marked by a button or by uploading a later statement.

## Two more ideas if there is time before the 25th
- **Live photo:** take a picture of a printed passbook page on the phone, send it to the laptop, scan it on stage (OCR path already works on `passbook_amma_page.png`).
- **Scan-your-own QR:** a QR on the last slide to the GitHub repo once it is public; judges scan a sample on their own phone at `http://<ip>:8000`.
