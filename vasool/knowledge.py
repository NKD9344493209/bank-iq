"""Banking knowledge base for Ask Bank IQ.

General questions ("how do I download my statement?", "what is a KFS?",
"can the bank charge me for SMS?") are answered from this curated set, matched
by keyword overlap + fuzzy similarity. Entries link to rulebook ids where a
right is involved, so the answer can quote the rule and its source.

Everything here is general guidance about Indian banking; nothing here decides
whether *your* bank owes *you* money — only the rule engine does that.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

STOP = {"the", "a", "an", "to", "of", "is", "are", "my", "me", "i", "how", "do", "can", "what", "in", "for", "on", "it", "and", "or", "bank", "please", "pls", "tell", "about", "does", "did", "be", "with", "from", "this", "that", "should", "will", "get", "want", "need", "know", "en", "enna", "epdi", "eppadi", "la", "ku", "oda", "nu", "um"}

# Tanglish / Tamil → English concept synonyms used in matching
SYN = {
    "statement": ["statement", "passbook", "e-statement", "estatement", "account statement", "download statement", "ஸ்டேட்மென்ட்", "பாஸ்புக்", "passbook"],
    "download": ["download", "get", "print", "export", "pdf", "எடுக்க", "எடு"],
    "kfs": ["kfs", "key fact", "key facts", "keyfact"],
    "ombudsman": ["ombudsman", "rbi complaint", "cms", "escalate", "escalation", "grievance", "complain", "complaint", "புகார்"],
    "upi": ["upi", "gpay", "google pay", "phonepe", "paytm", "bhim"],
    "failed": ["failed", "fail", "stuck", "pending", "debited", "not credited", "not received", "reversal", "refund", "money gone", "money cut", "cut", "பணம் போச்சு", "poyiduchu", "varala", "வரல"],
    "atm": ["atm", "cash", "withdrawal", "withdraw", "not dispensed"],
    "charge": ["charge", "charges", "fee", "fees", "deduct", "deducted", "deduction", "penalty", "cut", "charged", "கட்டணம்"],
    "minbalance": ["minimum balance", "min balance", "mab", "amb", "average balance", "non maintenance", "low balance"],
    "sms": ["sms", "alert", "alerts", "message charge"],
    "bsbda": ["bsbda", "basic account", "basic savings", "jan dhan", "zero balance", "no minimum balance", "zero charge"],
    "card": ["card", "debit card", "credit card", "atm card"],
    "closure": ["close", "closure", "closing", "cancel", "cancellation"],
    "unauthorised": ["unauthorised", "unauthorized", "fraud", "fraudulent", "scam", "hacked", "phishing", "otp", "without my permission", "didn't do", "did not do", "மோசடி"],
    "loan": ["loan", "emi", "penal", "penalty interest", "foreclosure", "prepayment", "processing fee"],
    "gold": ["gold loan", "gold", "jewel loan", "pledge", "நகை"],
    "locker": ["locker", "safe deposit"],
    "dormant": ["dormant", "inoperative", "inactive", "frozen", "reactivate", "reactivation"],
    "nominee": ["nominee", "nomination"],
    "kyc": ["kyc", "re-kyc", "rekyc", "aadhaar", "pan", "video kyc"],
    "cheque": ["cheque", "check", "bounce", "bounced", "dishonour", "ecs", "nach", "mandate", "auto debit", "autopay"],
    "interest": ["interest", "savings interest", "fd", "fixed deposit", "rd", "recurring deposit", "rate"],
    "neft": ["neft", "imps", "rtgs", "transfer", "utr"],
    "guardian": ["guardian", "காப்பாளர்", "kaappaalar", "son", "daughter", "family", "amma", "appa", "help me", "represent"],
    "timeline": ["how long", "how many days", "when", "time", "days", "deadline", "எத்தனை நாள்", "eppo", "எப்போ"],
    "compensation": ["compensation", "₹100", "100 per day", "100/day", "per day", "penalty on bank", "owe", "owes"],
    "app": ["app", "net banking", "netbanking", "internet banking", "online", "yono", "imobile", "ai1", "mobile banking", "login"],
    "downtime": ["server down", "down", "outage", "not working", "app not working", "site down", "technical issue"],
    "creditscore": ["cibil", "credit score", "credit report"],
    "insurance": ["insurance", "policy", "claim", "premium", "mediclaim", "health insurance"],
    "tax": ["tds", "tax", "form 16", "15g", "15h", "itr"],
}


@dataclass
class Entry:
    id: str
    title: str
    concepts: list[str]                 # keys of SYN that must/should match
    questions: list[str]                # example phrasings (EN / Tanglish)
    answer_en: str
    answer_ta: str = ""
    rule_ids: list[str] = field(default_factory=list)
    steps_en: list[str] = field(default_factory=list)
    steps_ta: list[str] = field(default_factory=list)


KB: list[Entry] = [
    Entry(
        id="download-statement", title="How to download your bank statement",
        concepts=["statement", "download"],
        questions=["how to download bank statement", "where do i get my statement", "statement pdf epdi edukkurathu", "how to get account statement", "e-statement download", "statement download panna"],
        answer_en="You can get a statement in four ways. Any of them works with Bank IQ — PDF, CSV/XLSX, or a clear photo of the passbook page.",
        answer_ta="Statement-ஐ நாலு வழியில எடுக்கலாம். எதுவும் Bank IQ-ல வேலை செய்யும் — PDF, CSV/XLSX, அல்லது passbook page-ஓட தெளிவான photo.",
        steps_en=[
            "Bank app (SBI YONO, HDFC, ICICI iMobile, Canara ai1, Axis, Kotak…): Accounts → Statement / e-Statement → choose the period (last 3–6 months) → Download PDF or Excel. Some apps email it; the PDF password is usually your DOB or customer id in the format the bank shows.",
            "Net banking on a computer: Login → Accounts → Account Statement → select period → Download as PDF / Excel / CSV. CSV or Excel is best for Bank IQ.",
            "Passbook: get it printed at the branch or the passbook-printing kiosk, then photograph the page flat, in good light, no shadow. Upload the photo.",
            "ATM: many bank ATMs print a mini-statement (last 10 transactions) — useful to check one thing quickly, not for a full scan.",
        ],
        steps_ta=[
            "Bank app (YONO, HDFC, iMobile, Canara ai1…): Accounts → Statement / e-Statement → காலம் தேர்வு (கடைசி 3–6 மாசம்) → PDF அல்லது Excel download. PDF password பொதுவா உங்க DOB அல்லது customer id.",
            "Computer-ல net banking: Login → Accounts → Account Statement → period → Download PDF / Excel / CSV. Bank IQ-க்கு CSV/Excel best.",
            "Passbook: branch-லயோ kiosk-லயோ print பண்ணி, page-ஐ flat-ஆ நல்ல வெளிச்சத்துல photo எடுத்து upload பண்ணுங்க.",
            "ATM mini-statement: கடைசி 10 transactions மட்டும் — quick check-க்கு தான்.",
        ],
    ),
    Entry(
        id="what-is-kfs", title="What is a Key Fact Statement (KFS)?",
        concepts=["kfs"],
        questions=["what is kfs", "key fact statement meaning", "kfs na enna", "where to find kfs", "kfs document"],
        answer_en="The Key Fact Statement is a one-page summary every lender must give you for a loan: interest rate, all charges, the APR, penal charges and the repayment schedule. Since 1 October 2024 a lender may not charge anything that is not in the KFS without your explicit consent. That's why Bank IQ asks for it when it sees a loan charge.",
        answer_ta="Key Fact Statement-ன்னா loan-க்கு lender கட்டாயம் தர வேண்டிய ஒரு பக்க summary: வட்டி, எல்லா charges, APR, penal charges, EMI schedule. 2024 Oct 1-ல இருந்து KFS-ல இல்லாத எந்த charge-ம் உங்க ஒப்புதல் இல்லாம போட முடியாது.",
        rule_ids=["RBI-KFS-2024-NOEXTRA"],
        steps_en=["Open your bank/NBFC app → Loans / My Loan → select the loan → Documents / Loan Documents → 'Key Fact Statement' or 'KFS' → download.", "Can't find it? Search your email and SMS for 'KFS' or 'Key Fact'. You can also ask the branch — they must give it on request."],
        steps_ta=["Bank app → Loans / My Loan → loan-ஐ தேர்வு → Documents → 'Key Fact Statement' / 'KFS' → download.", "கிடைக்கலையா? Email, SMS-ல 'KFS' தேடுங்க. Branch-ல கேட்டா தரணும்."],
    ),
    Entry(
        id="failed-upi", title="UPI payment failed but money was debited",
        concepts=["upi", "failed"],
        questions=["upi failed money debited", "gpay payment failed but amount deducted", "phonepe stuck", "upi money not received by shop", "upi pending", "upi la panam poyiduchu varala"],
        answer_en="If a UPI payment fails, the debit must be auto-reversed by the next day (T+1). If it isn't, RBI says your bank owes you ₹100 for every day of delay — automatically, without a complaint. Most reversals happen within 1–3 days. If it's been longer: note the UTR (12-digit number in the app), raise it in the UPI app's help section or at upihelp.npci.org.in, and complain to your bank. Bank IQ can compute what you're owed from your statement.",
        answer_ta="UPI payment fail ஆனா அடுத்த நாளுக்குள்ள (T+1) பணம் தானா திரும்பணும். இல்லைன்னா ஒவ்வொரு நாளும் ₹100 bank உங்களுக்கு கடன் — complaint பண்ணாமலே. பொதுவா 1–3 நாள்ல வரும். அதுக்கு மேல போனா: UTR (12 இலக்க எண்) எடுத்து, UPI app help அல்லது upihelp.npci.org.in-ல complaint பண்ணுங்க, bank-க்கும் சொல்லுங்க.",
        rule_ids=["RBI-TAT-2019-UPI"],
    ),
    Entry(
        id="failed-atm", title="ATM did not give cash but account was debited",
        concepts=["atm", "failed"],
        questions=["atm didn't give cash but debited", "atm cash not dispensed", "atm transaction failed money deducted", "atm la kaasu varala"],
        answer_en="Your bank must reverse a failed ATM withdrawal within 5 days (T+5) on its own. After that it owes you ₹100 per day, automatically. Keep the ATM slip if you got one, note the date/time and the ATM location, and complain to your own bank (not the ATM's bank). A court recently ordered a bank to pay ₹59,600 on a ₹10,000 failed withdrawal it sat on for 296 days.",
        answer_ta="Fail ஆன ATM withdrawal-ஐ 5 நாளுக்குள்ள (T+5) bank தானா திருப்பணும். அப்புறம் ஒவ்வொரு நாளும் ₹100. Slip இருந்தா வெச்சுக்கோங்க, தேதி/நேரம்/ATM இடம் குறிச்சு, உங்க சொந்த bank-ல complaint பண்ணுங்க.",
        rule_ids=["RBI-TAT-2019-ATM"],
    ),
    Entry(
        id="atm-charges", title="How many free ATM transactions do I get?",
        concepts=["atm", "charge"],
        questions=["how many free atm transactions", "atm charges", "why atm fee", "atm withdrawal charge 23", "free atm limit", "atm la evlo free"],
        answer_en="Since 1 May 2025: 5 free transactions a month at your own bank's ATMs, and 3 (metro) or 5 (non-metro) at other banks' ATMs — balance enquiries count too. Beyond that a bank may charge at most ₹23 per transaction plus tax. A charge inside the free limit is wrong and recoverable. Basic Savings (BSBDA) accounts get their own free allowance.",
        answer_ta="2025 May 1-ல இருந்து: சொந்த bank ATM-ல மாசம் 5 free, வேற bank ATM-ல metro-ல 3 / மத்த ஊர்ல 5 free — balance check-கும் count ஆகும். அதுக்கு மேல max ₹23 + tax. Free limit-க்குள்ள charge போட்டா தப்பு, திரும்ப வாங்கலாம்.",
        rule_ids=["RBI-ATM-2025-FREE", "RBI-ATM-2025-CAP"],
    ),
    Entry(
        id="min-balance", title="Minimum balance penalty rules",
        concepts=["minbalance"],
        questions=["minimum balance charge rules", "why min balance penalty", "can bank charge for low balance", "mab charges", "non maintenance charge"],
        answer_en="A bank may charge for not keeping the minimum balance only if it (1) warned you first by SMS/email/letter, (2) gave you one month to top up, (3) keeps the penalty proportionate to how far you were short, and (4) never takes the balance below zero. Most public-sector banks have waived this charge since 2025. If you want to avoid it entirely, you have the right to convert to a Basic Savings account with no minimum balance — the bank must do it within 7 days of asking.",
        answer_ta="Minimum balance charge போட (1) முன்னாடி SMS/email/letter-ல எச்சரிக்கணும், (2) ஒரு மாசம் time தரணும், (3) குறைவுக்கு ஏத்த மாதிரி penalty இருக்கணும், (4) balance-ஐ minus-க்கு கொண்டு போக கூடாது. தவிர்க்க: Basic Savings account-ஆ மாத்த கேளுங்க — 7 நாளுக்குள்ள bank பண்ணணும்.",
        rule_ids=["RBI-MINBAL-2014-NOTICE", "RBI-MINBAL-2014-PROPORTION", "RBI-BSBDA-2026-ZEROCHARGE"],
    ),
    Entry(
        id="sms-charges", title="SMS alert charges",
        concepts=["sms", "charge"],
        questions=["can bank charge for sms", "sms alert charge", "sms charges illegal", "why sms charge deducted"],
        answer_en="Until 31 December 2026 a bank may charge for SMS alerts, but only on an actual-usage basis and only if the charge was disclosed to you. From 1 January 2027 banks may not charge at all for the SMS alerts RBI requires them to send. If you were never told about an SMS charge, it can be claimed back.",
        answer_ta="2026 Dec 31 வரை SMS alert-க்கு charge பண்ணலாம் — ஆனா உண்மையா அனுப்பின அளவுக்கு, முன்னாடி சொல்லியிருந்தா மட்டும். 2027 Jan 1-ல இருந்து RBI கட்டாயப்படுத்தின SMS-க்கு எந்த charge-ம் கூடாது.",
        rule_ids=["RBI-SMS-2015-USAGE", "RBI-SMS-2027-BAN"],
    ),
    Entry(
        id="bsbda", title="Basic Savings Bank Deposit Account (zero-balance account)",
        concepts=["bsbda"],
        questions=["what is basic savings account", "zero balance account", "how to convert to bsbda", "jan dhan account charges", "no minimum balance account"],
        answer_en="A Basic Savings Bank Deposit Account has no minimum balance, a free ATM/debit card, free digital transactions and no charges for the basic services. Any customer can ask to convert an existing savings account, and since 1 April 2026 the bank must complete it within 7 working days. You may hold only one BSBDA. Bank IQ can prepare the request letter (Settings → Basic account).",
        answer_ta="Basic Savings account-ல minimum balance இல்ல, free ATM card, free digital transactions, basic service-க்கு charge இல்ல. யார் வேணா மாத்த சொல்லலாம்; 2026 Apr 1-ல இருந்து 7 working days-க்குள்ள bank பண்ணணும். ஒரே ஒரு BSBDA தான் வெச்சுக்கலாம். Settings-ல letter தயார் பண்ணலாம்.",
        rule_ids=["RBI-BSBDA-2026-ZEROCHARGE"],
    ),
    Entry(
        id="ombudsman", title="How to complain to the RBI Ombudsman",
        concepts=["ombudsman"],
        questions=["how to complain to rbi", "rbi ombudsman process", "bank not responding to complaint", "where to escalate bank complaint", "rbi la complaint epdi", "cms rbi"],
        answer_en="Step 1: complain to the bank in writing (email/app/branch) and keep the reference number. The bank has 30 days to reply. Step 2: if there's no reply or you're not satisfied, file with the RBI Ombudsman — free — at cms.rbi.org.in, by email to crpc@rbi.org.in, or by calling 14448. You must file within 90 days of the bank's deadline or reply. The Ombudsman can award up to ₹30 lakh plus ₹3 lakh for harassment. Bank IQ prepares both the bank complaint and the Ombudsman draft, and tracks the 30-day clock.",
        answer_ta="Step 1: Bank-ல எழுத்துப்பூர்வமா complaint பண்ணி reference number வெச்சுக்கோங்க. 30 நாள்ல bank பதில் தரணும். Step 2: பதில் இல்லைன்னா / திருப்தி இல்லைன்னா RBI Ombudsman-கிட்ட free-யா complaint: cms.rbi.org.in, crpc@rbi.org.in, அல்லது 14448. Bank deadline-ல இருந்து 90 நாளுக்குள்ள file பண்ணணும்.",
        rule_ids=["RBI-OMBUDSMAN-2026-CLOCK"],
    ),
    Entry(
        id="bank-reply-time", title="How long does the bank have to reply?",
        concepts=["ombudsman", "timeline"],
        questions=["how many days bank has to reply", "complaint deadline", "how long to resolve bank complaint", "bank eppo reply pannum"],
        answer_en="30 days from the day you complained. If the bank rejects or partly rejects your complaint, its system must send it to its own Internal Ombudsman within 20 days, and its final reply must still reach you within 30. After that you have 90 days to go to the RBI Ombudsman.",
        answer_ta="Complaint பண்ண நாள்ல இருந்து 30 நாள். Reject பண்ணா 20 நாளுக்குள்ள அதன் Internal Ombudsman-க்கு தானா போகணும்; final பதில் 30 நாளுக்குள்ள. அப்புறம் 90 நாள் RBI Ombudsman-க்கு.",
        rule_ids=["RBI-OMBUDSMAN-2026-CLOCK", "RBI-IO-2026-AUTOESCALATE"],
    ),
    Entry(
        id="card-closure", title="Closing a credit card",
        concepts=["card", "closure"],
        questions=["how to close credit card", "credit card closure delay", "bank not closing my card", "card cancel panna"],
        answer_en="Ask in writing (email, app or the closure form) and clear all dues. The bank must close the card within 7 working days of your request. If it doesn't, RBI's rule is a penalty of ₹500 to you for every day of delay. Keep the request date and reference — Bank IQ can compute the penalty (Ask → claims).",
        answer_ta="எழுத்துப்பூர்வமா கேளுங்க (email/app/form), due எல்லாம் கட்டுங்க. 7 working days-க்குள்ள close பண்ணணும். இல்லைன்னா ஒவ்வொரு நாளும் ₹500 உங்களுக்கு. Request தேதி, reference வெச்சுக்கோங்க.",
        rule_ids=["RBI-CARD-2022-CLOSURE"],
    ),
    Entry(
        id="unauthorised", title="Money taken from my account without my permission",
        concepts=["unauthorised"],
        questions=["fraud transaction what to do", "money debited i didn't do it", "scam upi otp", "someone withdrew money", "unauthorised transaction rules", "hacked account"],
        answer_en="Report it to the bank immediately — within 3 working days you have zero liability if it was the bank's fault or a third-party breach, and the bank must credit the amount back (a 'shadow credit') within 10 working days. Call the bank's fraud number, block the card/UPI, and also report at cybercrime.gov.in or dial 1930. Keep the complaint number. If you shared the OTP/PIN yourself, liability rules are different — still report at once; the sooner you report, the lower your liability.",
        answer_ta="உடனே bank-க்கு சொல்லுங்க — 3 working days-க்குள்ள சொன்னா, bank தப்பு அல்லது third-party breach-ன்னா உங்க பொறுப்பு zero; 10 working days-க்குள்ள பணம் திரும்ப வரணும். Card/UPI block பண்ணுங்க; 1930 அல்லது cybercrime.gov.in-லயும் complaint பண்ணுங்க. OTP/PIN நீங்களே கொடுத்திருந்தா rules வேற — ஆனாலும் உடனே சொல்லுங்க.",
        rule_ids=["RBI-LIAB-2017-ZERO"],
    ),
    Entry(
        id="dormant", title="Dormant / inoperative account",
        concepts=["dormant"],
        questions=["account dormant what to do", "inoperative account charges", "reactivate account", "account frozen no transaction"],
        answer_en="An account with no customer transaction for two years becomes 'inoperative'. The bank may not charge a minimum-balance penalty on it and may not charge for reactivating it. To reactivate: visit the branch or use the app's KYC/reactivation option with your ID; it should be done within 3 working days. Interest keeps accruing on a savings account even while inoperative.",
        answer_ta="ரெண்டு வருஷம் நீங்க எதுவும் transaction பண்ணல-ன்னா account 'inoperative'. அதுல minimum balance penalty போடக்கூடாது, reactivate பண்ண charge கூடாது. Branch அல்லது app-ல KYC கொடுத்து reactivate பண்ணலாம்.",
        rule_ids=["RBI-INOP-2024-NOPENALTY"],
    ),
    Entry(
        id="gold-loan", title="Gold loan rules",
        concepts=["gold"],
        questions=["gold loan rules", "gold not returned after repayment", "gold loan auction", "jewel loan interest", "gold loan late payment"],
        answer_en="From 1 April 2026: the lender must return your gold within 7 working days of full repayment or pay you ₹5,000 for every day of delay; it must communicate in your language; it must give you notice before any auction; and all charges must be in the loan agreement and Key Fact Statement. Missing a due date: the penalty must be a flat, disclosed 'penal charge', not extra interest added to the loan. Set your own reminder — Bank IQ can hold the due date for you.",
        answer_ta="2026 Apr 1-ல இருந்து: முழுசா அடைச்ச 7 working days-க்குள்ள நகை திரும்ப தரணும், இல்லைன்னா ஒவ்வொரு நாளும் ₹5,000. உங்க மொழியில சொல்லணும். Auction-க்கு முன்னாடி notice தரணும். எல்லா charge-ம் KFS-ல இருக்கணும். Due date தவறினா flat penal charge தான், extra வட்டி கூடாது.",
        rule_ids=["RBI-GOLD-2025-RELEASE", "RBI-PENAL-2023-NOCAP"],
    ),
    Entry(
        id="locker", title="Bank locker rules",
        concepts=["locker"],
        questions=["locker rules", "bank locker theft", "locker rent", "locker liability"],
        answer_en="If locker contents are lost because of the bank's negligence, fire, theft, building collapse or fraud by its staff, the bank is liable for up to 100 times the annual locker rent. Natural calamities are excluded. You must have a signed locker agreement on the RBI-prescribed format; banks can't demand a fixed deposit beyond three years' rent as security.",
        answer_ta="Bank அலட்சியம், தீ, திருட்டு, கட்டிடம் இடிஞ்சு, அல்லது ஊழியர் மோசடியால locker-ல பொருள் போனா, வருட வாடகையின் 100 மடங்கு வரை bank பொறுப்பு. இயற்கை பேரிடர் தவிர.",
        rule_ids=["RBI-LOCKER-2021-LIABILITY"],
    ),
    Entry(
        id="cheque-bounce", title="Cheque bounce and auto-debit failure charges",
        concepts=["cheque", "charge"],
        questions=["cheque bounce charge", "ecs return charge", "auto debit failed charge", "nach bounce fee", "mandate failed penalty"],
        answer_en="Banks may charge for a bounced cheque or a failed auto-debit (ECS/NACH), but the charge must be disclosed in the schedule of charges and be reasonable. If the bounce was the bank's error (for example, funds were available), the charge should be reversed on complaint. A bounced cheque for insufficient funds can also carry legal consequences for the issuer under Section 138 — pay promptly if you issued it.",
        answer_ta="Cheque bounce / auto-debit fail-க்கு charge போடலாம், ஆனா schedule of charges-ல சொல்லியிருக்கணும், reasonable-ஆ இருக்கணும். Bank தப்பால bounce ஆனா (பணம் இருந்தும்) complaint பண்ணா திருப்பணும்.",
    ),
    Entry(
        id="neft-imps", title="NEFT / IMPS / RTGS transfer failed or stuck",
        concepts=["neft", "failed"],
        questions=["imps failed money debited", "neft not credited", "transfer stuck", "wrong account transfer", "utr number"],
        answer_en="IMPS: if the beneficiary's bank didn't credit, reversal is due by T+1, then ₹100/day. NEFT: a failed transfer must be returned within 2 hours of the batch or by the next day. If you sent money to the wrong account, tell your bank immediately with the UTR; the bank can request the other bank to reverse it, but it needs the recipient's consent — speed matters. Keep the UTR (the 12–22 character reference on the statement) for every complaint.",
        answer_ta="IMPS: beneficiary-க்கு credit ஆகலைன்னா T+1-க்குள்ள திரும்பணும், அப்புறம் ₹100/நாள். NEFT: fail ஆனா அடுத்த நாளுக்குள்ள திரும்பணும். தப்பான account-க்கு அனுப்பினா உடனே UTR-ஓட bank-க்கு சொல்லுங்க.",
        rule_ids=["RBI-TAT-2019-UPI"],
    ),
    Entry(
        id="downtime", title="Bank app / UPI server down",
        concepts=["downtime"],
        questions=["bank server down what to do", "app not working", "upi down", "can i get compensation for outage"],
        answer_en="There is no RBI rule that pays compensation for downtime itself. What is covered: any transaction that failed during the outage must be reversed on time (T+1 for UPI, T+5 for ATM) or the ₹100/day compensation applies. If an outage caused you a loss (a missed deadline, a penalty), you can still complain to the bank and, after 30 days, to the RBI Ombudsman as a 'deficiency in service'. Keep screenshots with the time.",
        answer_ta="Downtime-க்கு மட்டும் compensation-ன்னு RBI rule இல்ல. ஆனா அப்போ fail ஆன transaction T+1/T+5-க்குள்ள திரும்பணும், இல்லைன்னா ₹100/நாள். Downtime-ஆல நஷ்டம் வந்தா bank-ல complaint, 30 நாள் கழிச்சு RBI Ombudsman-ல 'deficiency in service'-ஆ. நேரத்தோட screenshot வெச்சுக்கோங்க.",
        rule_ids=["RBI-TAT-2019-UPI", "RBI-OMBUDSMAN-2026-CLOCK"],
    ),
    Entry(
        id="nominee", title="Nominee for a bank account",
        concepts=["nominee"],
        questions=["how to add nominee", "nominee rules bank account", "what is nomination"],
        answer_en="A nominee is the person the bank pays the account balance to if the holder dies — it avoids the family needing a succession certificate. You can add or change a nominee any time in the app (Profile → Nomination) or with Form DA1 at the branch. Since 2025 up to four nominees can be named for deposits. A nominee is different from Bank IQ's Guardian: the Guardian helps you while you're alive; the nominee receives money after.",
        answer_ta="Nominee-ன்னா account holder இறந்தா balance-ஐ bank கொடுக்கற ஆள். App-ல Profile → Nomination அல்லது branch-ல Form DA1-ல எப்போ வேணா மாத்தலாம். Bank IQ-ஓட காப்பாளர் வேற: நீங்க இருக்கும்போது உதவறவங்க.",
    ),
    Entry(
        id="kyc", title="KYC and re-KYC",
        concepts=["kyc"],
        questions=["kyc update", "re-kyc how to do", "account blocked for kyc", "video kyc"],
        answer_en="Re-KYC is the bank re-confirming your identity every 2–10 years depending on risk category. If nothing has changed, a self-declaration by email, app, letter or at any branch is enough — the bank can't insist you visit the home branch or resubmit documents. Banks must give notice before restricting an account for pending KYC. Never share OTPs or click 'KYC update' links from SMS — that is the most common fraud.",
        answer_ta="Re-KYC-ன்னா bank உங்க identity-ஐ மறுபடி confirm பண்றது. மாற்றம் இல்லைன்னா email/app/letter-ல self-declaration போதும்; home branch-க்கு வர சொல்ல முடியாது. KYC pending-க்கு account restrict பண்றதுக்கு முன்னாடி notice தரணும். SMS-ல வர 'KYC update' link-ஐ click பண்ணாதீங்க — அது மோசடி.",
    ),
    Entry(
        id="interest", title="Savings interest and fixed deposits",
        concepts=["interest"],
        questions=["savings account interest rate", "fd interest", "when is interest credited", "premature fd withdrawal penalty"],
        answer_en="Savings interest is calculated daily on the closing balance and credited at least quarterly. FD rates are fixed for the term; breaking an FD early usually costs a 0.5–1% penalty on the rate. If a matured FD is not renewed or withdrawn, the bank pays interest on it at the lower of the savings rate or the contracted rate until you claim it. Rates differ by bank and change often — check the bank's current schedule rather than relying on old numbers.",
        answer_ta="Savings வட்டி தினமும் closing balance-ல கணக்கிட்டு, குறைஞ்சது quarter-க்கு ஒரு முறை credit ஆகும். FD-ஐ முன்னாடியே உடைச்சா பொதுவா 0.5–1% penalty. Rate-கள் bank-க்கு bank மாறும்; bank-ஓட current schedule-ஐ பாருங்க.",
    ),
    Entry(
        id="credit-score", title="CIBIL / credit score",
        concepts=["creditscore"],
        questions=["how to check cibil score", "credit score low why", "free credit report"],
        answer_en="You're entitled to one free full credit report a year from each bureau (CIBIL, Experian, Equifax, CRIF) — get it from their websites. Late EMIs, high card utilisation and many loan enquiries lower the score. If a bank reported something wrong, raise a dispute with the bureau; since 2024 they must resolve it within 30 days and lenders must tell you when a default is reported.",
        answer_ta="ஒவ்வொரு bureau-லயும் (CIBIL, Experian, Equifax, CRIF) வருஷத்துக்கு ஒரு free report கிடைக்கும். EMI late, card-ஐ அதிகமா use பண்றது, நிறைய loan enquiry — score குறையும். தப்பா report பண்ணியிருந்தா bureau-ல dispute; 30 நாள்ல தீர்க்கணும்.",
    ),
    Entry(
        id="insurance-claim", title="Health insurance claim delay",
        concepts=["insurance"],
        questions=["insurance claim delayed", "cashless approval time", "mediclaim rejected", "insurance ombudsman"],
        answer_en="Bank IQ's engine covers bank rules today, not insurance — but here's the outline: IRDAI requires insurers to decide cashless requests within 3 hours and settle claims within 30 days of the last document, paying interest for delay. Complain to the insurer's grievance officer first, then to the Insurance Ombudsman (bimabharosa.irdai.gov.in) — free, for claims up to ₹50 lakh. Insurance is on our roadmap as the next rulebook.",
        answer_ta="Bank IQ engine இப்போ bank rules மட்டும்; insurance அடுத்த rulebook. Outline: IRDAI படி cashless-ஐ 3 மணி நேரத்துல முடிவு பண்ணணும், claim-ஐ கடைசி document-ல இருந்து 30 நாள்ல settle பண்ணணும். Insurer grievance officer → அப்புறம் Insurance Ombudsman (bimabharosa.irdai.gov.in), free.",
    ),
    Entry(
        id="tds", title="TDS on interest and Form 15G/15H",
        concepts=["tax", "interest"],
        questions=["tds on fd interest", "form 15g 15h", "why tds deducted"],
        answer_en="Banks deduct 10% TDS when your interest from that bank crosses ₹50,000 in a year (₹1 lakh for senior citizens, from FY 2025-26). If your total income is below the taxable limit, submit Form 15G (or 15H if 60+) at the start of the year and no TDS will be cut. TDS already deducted can be claimed back by filing your income-tax return.",
        answer_ta="ஒரு bank-ல வட்டி வருஷத்துக்கு ₹50,000 தாண்டினா (senior citizen ₹1 லட்சம்) 10% TDS பிடிப்பாங்க. வருமானம் taxable limit-க்கு கீழன்னா வருஷ ஆரம்பத்துல Form 15G (60+ன்னா 15H) கொடுத்தா TDS பிடிக்க மாட்டாங்க. பிடிச்சதை ITR file பண்ணி திரும்ப வாங்கலாம்.",
    ),
    Entry(
        id="guardian", title="What is the Guardian (காப்பாளர்)?",
        concepts=["guardian"],
        questions=["what is guardian", "can my son help me", "kaappaalar na enna", "who is guardian in vasool raja", "can someone complain on my behalf"],
        answer_en="A Guardian is one person you trust — son, daughter, husband, wife. When Bank IQ finds something, it calls you first in your language, then sends the Guardian one message with one button. Nothing is sent to the bank until they approve. They never see your balance or spending — only that an issue exists, the amount and the rule. RBI's Ombudsman scheme allows an authorised representative to complain on your behalf, and your recorded consent is what authorises them.",
        answer_ta="காப்பாளர்-ன்னா நீங்க நம்புற ஒருத்தர் — மகன், மகள், கணவர், மனைவி. பிரச்சனை வந்தா முதல்ல உங்களுக்கு உங்க மொழியில phone, அப்புறம் அவங்களுக்கு ஒரே ஒரு message, ஒரே ஒரு button. அவங்க OK சொன்னா தான் bank-க்கு போகும். Balance, செலவு அவங்களுக்கு தெரியாது.",
    ),
    Entry(
        id="complaint-what-to-write", title="What to write in a bank complaint",
        concepts=["ombudsman", "charge"],
        questions=["how to write complaint to bank", "complaint letter format", "what to include in bank complaint", "email to bank for refund"],
        answer_en="Keep it factual: account number (last 4 digits are enough in email), the exact statement lines (date, narration, amount), what RBI rule you rely on, the amount you want credited, and a line asking the bank to either credit it or produce the evidence it relies on (the notice, the disclosure, the reversal reference). Ask for a complaint reference number and mention that you'll approach the RBI Ombudsman if there's no reply in 30 days. Bank IQ generates exactly this letter for every case.",
        answer_ta="உண்மையா, சுருக்கமா: account-ஓட கடைசி 4 இலக்கம், statement lines (தேதி, narration, தொகை), எந்த RBI rule, எவ்வளவு credit வேணும், 'credit பண்ணுங்க அல்லது ஆதாரம் காட்டுங்க'-ன்னு ஒரு வரி. Reference number கேளுங்க; 30 நாள்ல பதில் இல்லைன்னா RBI Ombudsman-னு சொல்லுங்க. Bank IQ இதே letter-ஐ தயார் பண்ணுது.",
        rule_ids=["RBI-OMBUDSMAN-2026-CLOCK"],
    ),
    Entry(
        id="compensation-100", title="What is the ₹100 per day compensation?",
        concepts=["compensation"],
        questions=["what is 100 per day rule", "rbi 100 rupees compensation", "bank owes me 100 per day", "tat compensation meaning"],
        answer_en="RBI's 2019 circular on failed transactions sets a deadline for the bank to reverse a failed debit — T+1 for UPI/IMPS/card transfers, T+5 for ATM and card purchases — and says that for every day beyond it the bank must credit ₹100 to the customer, on its own, without a complaint. It is uncapped: a ₹1,200 withdrawal stuck for 40 days means ₹4,000 owed. Almost nobody receives it because almost nobody knows to look. That is the rule Bank IQ was built around.",
        answer_ta="RBI 2019 circular படி fail ஆன debit-ஐ bank திருப்ப deadline இருக்கு — UPI/IMPS-க்கு T+1, ATM/card-க்கு T+5 — அதுக்கு அப்புறம் ஒவ்வொரு நாளும் ₹100 bank தானா credit பண்ணணும். Cap இல்ல: ₹1,200 40 நாள் stuck-ன்னா ₹4,000. யாருக்கும் தெரியாததால யாரும் வாங்கறது இல்ல.",
        rule_ids=["RBI-TAT-2019-ATM", "RBI-TAT-2019-UPI"],
    ),
    Entry(
        id="what-is-vasool", title="What is Bank IQ and what can it do?",
        concepts=[],
        questions=["what is vasool raja", "what can you do", "help", "how does this work", "what do you do", "who are you"],
        answer_en="I'm Bank IQ — the money guardian. Give me a bank statement or passbook photo and I run the RBI rulebook on it: failed transactions, wrong charges, penalties, and what the bank owes you. I prepare the complaint, track the 30-day clock and can involve a family Guardian. Ask me about your findings ('why was ₹295 charged?'), your case ('what's the status?'), or general banking ('how do I download my statement?', 'can the bank charge for SMS?').",
        answer_ta="நான் Bank IQ — money guardian. Statement அல்லது passbook photo கொடுத்தா RBI rulebook-ஐ ஓட்டி, fail ஆன transactions, தப்பான charges, penalties, bank உங்களுக்கு என்ன தரணும்-னு சொல்றேன். Complaint தயார் பண்றேன், 30 நாள் clock-ஐ பாக்கறேன், காப்பாளரை சேர்க்கறேன். கேளுங்க: 'ஏன் ₹295 cut ஆச்சு?', 'case status என்ன?', 'statement எப்படி download பண்றது?'",
    ),
]

# ----- claim checker: common wrong beliefs, mapped to the truth ------------- #
@dataclass
class Claim:
    id: str
    patterns: list[str]        # regex on the lowercased question
    verdict: str               # "wrong" | "partly" | "right"
    truth_en: str
    truth_ta: str = ""
    rule_ids: list[str] = field(default_factory=list)


CLAIMS: list[Claim] = [
    Claim("sms-illegal-now", [r"sms.*(illegal|banned|not allowed|cannot|can't).*(now|already|2026)", r"(banned|illegal).*sms"], "partly",
          "Not yet. The ban on charging for regulatory SMS alerts was issued on 24 June 2026 but takes effect on 1 January 2027. Until then a disclosed, usage-based SMS charge is allowed.",
          "இன்னும் இல்ல. SMS charge ban 2026 June 24-ல வந்தது, ஆனா 2027 Jan 1-ல இருந்து தான் அமல். அதுவரை சொல்லப்பட்ட usage-based SMS charge சரி.", ["RBI-SMS-2027-BAN"]),
    Claim("atm-unlimited-free", [r"(all|every|unlimited).*atm.*free", r"atm.*(always|completely) free"], "wrong",
          "No. You get 5 free transactions a month at your own bank's ATMs and 3 (metro) / 5 (non-metro) at other banks'; after that up to ₹23 plus tax per transaction is allowed. Balance enquiries count too.",
          "இல்ல. சொந்த bank ATM-ல மாசம் 5, வேற bank-ல 3/5 free; அதுக்கு மேல ₹23 + tax வரை charge பண்ணலாம்.", ["RBI-ATM-2025-FREE", "RBI-ATM-2025-CAP"]),
    Claim("atm-charge-any", [r"bank can charge (anything|any amount|whatever).*atm", r"atm.*(50|100) (rupees|rs)"], "wrong",
          "No. Beyond the free limit the cap is ₹23 per transaction plus tax (it was ₹21 before 1 May 2025). Anything above that is recoverable.",
          "இல்ல. Free limit-க்கு மேல cap ₹23 + tax (2025 May 1-க்கு முன்னாடி ₹21). அதுக்கு மேல போட்டா திரும்ப வாங்கலாம்.", ["RBI-ATM-2025-CAP"]),
    Claim("minbal-no-notice", [r"(bank|they) can (charge|deduct|cut).*(min|minimum|low) balance.*(without|no) (notice|warning|telling)", r"min(imum)? balance.*(without|no) (notice|warning)"], "wrong",
          "No. Before a minimum-balance penalty the bank must warn you (SMS/email/letter) and give you one month to restore the balance; the penalty must be proportionate to the shortfall and can never take the account below zero.",
          "இல்ல. Minimum balance penalty-க்கு முன்னாடி எச்சரிக்கை + ஒரு மாசம் time தரணும்; penalty குறைவுக்கு ஏத்ததா இருக்கணும்; balance minus-க்கு போக கூடாது.", ["RBI-MINBAL-2014-NOTICE"]),
    Claim("failed-must-complain", [r"(have to|must|need to) complain.*(get|for).*(reversal|money back|refund).*(atm|upi)", r"(atm|upi).*(reversal|refund).*only if.*complain"], "wrong",
          "No. For a failed ATM/UPI transaction the reversal and the ₹100/day compensation are automatic — the RBI circular puts the onus on the bank, no complaint needed. Complaining is what you do when the bank fails to do it.",
          "இல்ல. Fail ஆன ATM/UPI-க்கு reversal-ம் ₹100/நாள்-ம் automatic — RBI circular படி bank-ஓட பொறுப்பு. Bank பண்ணலைன்னா தான் complaint.", ["RBI-TAT-2019-ATM"]),
    Claim("compensation-capped", [r"(100|compensation).*(max|maximum|cap|capped|only up to|limit)"], "wrong",
          "There is no cap. ₹100 for every day of delay beyond the deadline, however long — a ₹10,000 ATM failure that sat for 296 days was awarded ₹29,600 in compensation by a consumer commission in 2026.",
          "Cap இல்ல. Deadline-க்கு அப்புறம் ஒவ்வொரு நாளும் ₹100, எத்தனை நாளானாலும்.", ["RBI-TAT-2019-ATM"]),
    Claim("ombudsman-fee", [r"ombudsman.*(fee|charge|cost|pay|lawyer)", r"(lawyer|advocate).*(ombudsman|rbi complaint)"], "wrong",
          "The RBI Ombudsman is free and you don't need a lawyer. File online at cms.rbi.org.in, by email or by calling 14448, after the bank has had 30 days.",
          "RBI Ombudsman free; lawyer தேவையில்ல. cms.rbi.org.in, email, அல்லது 14448 — bank-க்கு 30 நாள் கொடுத்த பிறகு.", ["RBI-OMBUDSMAN-2026-CLOCK"]),
    Claim("card-closure-charge", [r"(charge|fee).*(close|closing|closure).*(credit )?card", r"card.*(close|closure).*(charge|fee|penalty)"], "partly",
          "A bank may not charge you for closing a credit card with no dues, and it must close it within 7 working days of your request — otherwise it owes you ₹500 for every day of delay.",
          "Due இல்லாத credit card-ஐ close பண்ண charge கூடாது; 7 working days-க்குள்ள close பண்ணணும், இல்லைன்னா ₹500/நாள் உங்களுக்கு.", ["RBI-CARD-2022-CLOSURE"]),
    Claim("zero-liability-always", [r"(zero|no) liability.*(always|any time|whenever|even if)", r"bank (has to|must) refund.*(fraud|scam).*(always|any)"], "partly",
          "Zero liability applies when you report within 3 working days and the loss was due to the bank's fault or a third-party breach. Report between 4 and 7 working days and your liability is limited (₹5,000–₹25,000 depending on the account). Later than that, the bank's board policy decides. If you shared the OTP/PIN yourself, the bank can hold you liable until you report it.",
          "3 working days-க்குள்ள report பண்ணி, bank தப்பு / third-party breach-ன்னா zero liability. 4–7 நாள்ல limited liability. அதுக்கு அப்புறம் bank policy. OTP/PIN நீங்களே கொடுத்திருந்தா report பண்ற வரை உங்க பொறுப்பு.", ["RBI-LIAB-2017-ZERO"]),
    Claim("downtime-compensation", [r"(compensation|money|refund).*(server|app|site).*(down|outage)", r"(server|app).*(down|outage).*(compensation|pay me|owe)"], "wrong",
          "There is no RBI rule paying compensation for downtime itself. What you can claim: ₹100/day for any transaction that failed during the outage and wasn't reversed on time, and a 'deficiency in service' complaint to the Ombudsman if the outage caused you a loss.",
          "Downtime-க்கு மட்டும் compensation-ன்னு RBI rule இல்ல. அப்போ fail ஆன transaction திரும்ப வரலைன்னா ₹100/நாள்; நஷ்டம் வந்தா Ombudsman-ல 'deficiency in service'.", ["RBI-TAT-2019-UPI"]),
    Claim("basic-account-refuse", [r"bank (can|may) (refuse|deny|reject).*(basic|bsbda|zero balance)", r"(basic|bsbda).*(only for|only poor|jan dhan only)"], "wrong",
          "Any customer can ask for a Basic Savings Bank Deposit Account — it is not only for Jan Dhan or low-income customers — and since 1 April 2026 the bank must convert within 7 working days. The one condition: you may hold only one BSBDA.",
          "யார் வேணா Basic Savings account கேக்கலாம் — Jan Dhan-க்கு மட்டும் இல்ல — 2026 Apr 1-ல இருந்து 7 working days-க்குள்ள bank பண்ணணும். ஒரே ஒரு BSBDA தான்.", ["RBI-BSBDA-2026-ZEROCHARGE"]),
    Claim("kfs-optional", [r"(kfs|key fact).*(optional|not (needed|required|compulsory))", r"loan charge.*(not|no).*(kfs|key fact).*(allowed|fine|ok)"], "wrong",
          "Since 1 October 2024 the Key Fact Statement is mandatory for retail and MSME loans, and a lender may not levy any charge that is not in it without your explicit consent.",
          "2024 Oct 1-ல இருந்து KFS கட்டாயம்; அதுல இல்லாத charge உங்க ஒப்புதல் இல்லாம போட முடியாது.", ["RBI-KFS-2024-NOEXTRA"]),
]

ASSERTION_HINTS = re.compile(r"\b(is it true|true that|i heard|they said|bank (said|says|told)|someone (said|told)|correct\??|right\??|can (the )?bank|is (it|this) (legal|allowed|ok|correct)|allowed\??|legal\??|illegal|myth)\b", re.I)


# ----- matching -------------------------------------------------------------- #
def _tokens(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9₹]+|[஀-௿]+", s.lower()) if w not in STOP]


def _concepts_in(q: str) -> set[str]:
    ql = " " + q.lower() + " "
    found = set()
    for key, words in SYN.items():
        for w in words:
            if f" {w} " in ql or (len(w) > 3 and w in ql):
                found.add(key)
                break
    return found


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


@dataclass
class Hit:
    entry: Entry
    score: float


def search(question: str, limit: int = 3) -> list[Hit]:
    qc = _concepts_in(question)
    qt = set(_tokens(question))
    hits: list[Hit] = []
    for e in KB:
        score = 0.0
        if e.concepts:
            overlap = len(qc & set(e.concepts))
            score += 0.45 * overlap / len(e.concepts) + 0.15 * overlap
        fuzzy = max((_sim(question, ex) for ex in e.questions), default=0.0)
        score += 0.6 * fuzzy
        tok = 0.0
        for ex in e.questions:
            et = set(_tokens(ex))
            if et:
                tok = max(tok, len(qt & et) / len(et))
        score += 0.35 * tok
        if score >= 0.42:
            hits.append(Hit(e, round(score, 3)))
    hits.sort(key=lambda h: -h.score)
    return hits[:limit]


def check_claim(question: str) -> Optional[Claim]:
    ql = question.lower()
    for c in CLAIMS:
        for p in c.patterns:
            if re.search(p, ql):
                return c
    return None


def looks_like_assertion(question: str) -> bool:
    return bool(ASSERTION_HINTS.search(question))


def is_banking_question(question: str) -> bool:
    return bool(_concepts_in(question)) or bool(re.search(r"\b(account|money|rupee|₹|rs\.?|bank|payment|transaction|deposit|withdraw|charge|loan|card|upi|atm|rbi)\b", question, re.I))
