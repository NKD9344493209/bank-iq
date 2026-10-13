"""Synthetic, labelled bank-transaction dataset for the Bank IQ ML layer.

Why synthetic: real statements are private.  The generator reproduces the *shape* of Indian
bank statements (the same narration conventions the Vasool Raja parsers already handle —
UPI/DR/..., NFS/ATM WDL, CHRG MIN BAL, NEFT CR-SALARY, REV/UPI ...) for many customers and
months, with a ground-truth category per line that the narration alone does not reveal
cleanly (abbreviation variants, merchant names, bank-specific formats, noise).

Output (data/ml/):
  transactions.csv  customer_id, date, narration, debit, credit, balance, bank, category, archetype
  customers.csv     customer_id, bank, archetype, monthly_income, opening_balance

Categories (10):
  UPI_PAYMENT · CARD_POS · ATM_WITHDRAWAL · TRANSFER_OUT · LOAN_EMI · BANK_CHARGE ·
  INCOME_CREDIT · TRANSFER_IN · REFUND_REVERSAL · INTEREST_CREDIT
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "ml"
CATEGORIES = ["UPI_PAYMENT", "CARD_POS", "ATM_WITHDRAWAL", "TRANSFER_OUT", "LOAN_EMI", "BANK_CHARGE", "INCOME_CREDIT", "TRANSFER_IN", "REFUND_REVERSAL", "INTEREST_CREDIT"]
BANKS = ["CANARA", "SBI", "HDFC", "ICICI", "AXIS"]

MERCHANTS = ["SWIGGY", "ZOMATO", "AMAZON", "FLIPKART", "BIGBASKET", "ANNAPOORNA STORES", "RELIANCE FRESH", "DMART", "NETFLIX", "SPOTIFY", "JIO RECHARGE", "AIRTEL",
             "UBER", "OLA", "REDBUS", "IRCTC", "BPCL PETROL", "INDIAN OIL", "APOLLO PHARMACY", "MEDPLUS", "DECATHLON", "MYNTRA", "PVR CINEMAS", "BOOKMYSHOW",
             "SARAVANA BHAVAN", "DOMINOS", "KFC", "CAFE COFFEE DAY", "TNEB", "GAS AGENCY", "TATA POWER", "CHENNAI METRO", "PAYTM", "PHONEPE", "GPAY"]
PEOPLE = ["RAVI KUMAR", "PRIYA S", "MURUGAN", "LAKSHMI", "ARUN K", "SELVI R", "KARTHIK", "DIVYA", "SURESH BABU", "MEENA", "VIJAY", "ANITHA", "RAJESH", "KAVITHA"]
EMPLOYERS = ["ACME TECH PVT LTD", "INFOSYS LTD", "TATA CONSULTANCY", "CIT COIMBATORE", "SUNRISE TEXTILES", "LAKSHMI MILLS", "TN TREASURY", "ZOHO CORP"]
LENDERS = ["BAJAJ FIN", "HDFC LTD", "SBI HOME LOAN", "TVS CREDIT", "MUTHOOT GOLD", "AXIS CAR LOAN"]
CITIES = ["CBE", "CHENNAI", "MADURAI", "SALEM", "TRICHY", "ERODE", "TIRUPUR", "BANGALORE"]
UPI_HANDLES = ["okaxis", "oksbi", "okhdfcbank", "okicici", "ybl", "paytm", "ibl", "axl"]

rng = random.Random(42)
nrng = np.random.default_rng(42)


def _ref(n=10):
    return "".join(rng.choice("0123456789") for _ in range(n))


def _noise(s: str) -> str:
    """Realistic mess: random spacing, truncation, dropped vowels in long words, extra ref codes."""
    r = rng.random()
    if r < 0.12:
        s = s.replace("/", "-")
    elif r < 0.2:
        s = s.replace(" ", "  ", 1)
    if rng.random() < 0.1:
        s = s[: max(18, int(len(s) * rng.uniform(0.6, 0.95)))]
    if rng.random() < 0.08:
        s = s + " " + _ref(6)
    return s


# ---------------------------------------------------------------------------- narration templates
def narr(cat: str, bank: str, amt: float, d: date, ctx: dict) -> str:
    m = rng.choice(MERCHANTS); p = rng.choice(PEOPLE); h = rng.choice(UPI_HANDLES); c = rng.choice(CITIES)
    T = {
        "UPI_PAYMENT": [f"UPI/DR/{_ref()}/{m}/{bank}/{m.split()[0].lower()}@{h}", f"UPI/DR/{_ref()}/{rng.choice(['PSG COLLEGE FEES', 'CIT FEES', 'KMCH HOSPITAL', 'APARTMENT RENT', 'LIC PREMIUM'])}/{bank}/{h}", f"UPI-{m}-{_ref(12)}", f"UPI/P2M/{_ref()}/{m}", f"UPI/DR/{_ref()}/{p}/{rng.choice(BANKS)}/{p.split()[0].lower()}@{h}", f"UPI-DR-{m}-{_ref(8)}", f"BY UPI/{m}/{_ref(9)}", f"UPI/{_ref()}/{m} {c}"],
        "CARD_POS": [f"POS {_ref(6)} {m} {c}", f"PCD/{_ref(8)}/{m}", f"ECOM PUR/{m}*IN/{_ref(6)}", f"VPS/{m}/{_ref(8)}", f"DEBIT CARD PUR {m} {c}", f"POS/{m} {c}/{_ref(5)}", f"E-COMM {m} ONLINE PUR"],
        "ATM_WITHDRAWAL": [f"ATM WDL {bank} {c}", f"NFS/ATM WDL/{rng.choice(BANKS)} {c}/{_ref(6)}", f"ATW {_ref(6)} {c}", f"ATM CASH WDL {c} {_ref(5)}", f"CWDR {bank} ATM {c}", f"NWD {rng.choice(BANKS)} ATM {c} {_ref(4)}"],
        "TRANSFER_OUT": [f"NEFT DR-{p}-{_ref(10)}", f"IMPS/P2A/{_ref()}/{p}/{rng.choice(BANKS)}", f"RTGS DR {p} {_ref(8)}", f"IMPS-{_ref(12)}-{p}", f"NEFT/{_ref(10)}/{p}/RENT", f"TO TRANSFER-{p}", f"CHQ {_ref(6)} {p}"],
        "LOAN_EMI": [f"ACH D- {rng.choice(LENDERS)} EMI {d.strftime('%b%y').upper()}", f"NACH/{rng.choice(LENDERS)}/EMI/{_ref(8)}", f"LOAN INST {rng.choice(LENDERS)} {d.strftime('%m%y')}", f"EMI {rng.choice(LENDERS)} {_ref(6)}", f"ECS DR {rng.choice(LENDERS)} LOAN REPAY", f"GOLD LOAN INT {rng.choice(LENDERS)}"],
        "BANK_CHARGE": [f"CHRG MIN BAL NON MAINT {d.strftime('%b%y').upper()}", f"MIN BAL CHRG INCL GST {d.strftime('%b%y').upper()}", f"DEBIT CARD ANNUAL FEE {_ref(4)}XXXXXXXX{_ref(4)}", "ATM CASH WDL CHRG", "ATM CASH WDL CHARGES", "DORMANT ACCT REACTIVATION CHRG", "MIN BAL NON MAINT CHRG", "GST", "SMS ALERT CHRG " + rng.choice(["Q1", "Q2", "Q3", "Q4"]) + " 26-27", "GST ON CHARGES", f"ATM CHGS EXCESS TXN {_ref(4)}", "DEBIT CARD AMC " + str(d.year), "CHQ BOOK CHRG", "MAB NON MAINTENANCE CHARGES", "SMS CHGS", "NFS ATM DECLINE CHG", "SERVICE CHARGE FOLIO", "REACTIVATION CHARGES DORMANT A/C", "ECS RETURN CHG", "LATE PAYMENT FEE", "CGST ON CHGS", "AMB CHRG " + d.strftime("%b").upper()],
        "INCOME_CREDIT": [f"SALARY-{d.strftime('%b%y').upper()}-{ctx.get('employer', rng.choice(EMPLOYERS))}", f"NEFT CR-PENSION-TN TREASURY-{d.strftime('%b').upper()}", f"SAL {ctx.get('employer', rng.choice(EMPLOYERS))} {_ref(6)}", f"NEFT CR-{ctx.get('employer', rng.choice(EMPLOYERS))}-SALARY", f"BY TRANSFER-PENSION {d.strftime('%m/%Y')}", f"ACH C- {ctx.get('employer', rng.choice(EMPLOYERS))} SAL", f"CR-SALARY {d.strftime('%b').upper()} {_ref(6)}"],
        "TRANSFER_IN": [f"UPI/CR/{_ref()}/{p}/{rng.choice(BANKS)}/{p.split()[0].lower()}@{h}", f"IMPS/P2A/{_ref()}/{p}/CR", f"NEFT CR-{p}-{_ref(10)}", f"BY TRANSFER-{p}", f"CASH DEP {c} BRANCH", f"RTGS CR {p} {_ref(8)}", f"UPI-CR-{p}-{_ref(8)}"],
        "REFUND_REVERSAL": [f"REV/UPI/{_ref()}/{m}", f"REFUND {m} {_ref(8)}", f"UPI/REV/{_ref()}/{m}/FAILED", f"ATM WDL REV {c} {_ref(5)}", f"CHARGEBACK {m}", f"TXN REV {_ref(8)}", f"REVERSAL OF POS {m}", f"CREDIT ADJ {m} RETURN", f"FAILED TXN CR {_ref(8)}"],
        "INTEREST_CREDIT": ["SB INT CREDIT", f"INT.PD:{d.strftime('%d-%m-%Y')}", "CREDIT INTEREST", f"INTEREST PAID {d.strftime('%b%y').upper()}", "SB INTEREST CR", "INT CR SAVINGS"],
    }
    H = {   # long tail: merchant-only lines, bank-specific codes, unusual wording — the regex layer misses many of these
        "UPI_PAYMENT": [f"{m} {c}", f"PAYTM*{m}", f"{m.split()[0]}@{h}", f"BIL/ONL/{_ref(9)}/{m}", f"{p.split()[0].lower()}@{h} {_ref(6)}", f"{m} PAYMENT {_ref(5)}", f"GPAY {m}", f"PHONEPE {p}"],
        "CARD_POS": [f"{m} {c} IN", f"{m}*{_ref(6)}", f"VIN/{m}/{_ref(8)}", f"{m} INDIA PVT LTD", f"CARD {_ref(4)} {m}", f"{m}.COM", f"{m} STORE {c}"],
        "ATM_WITHDRAWAL": [f"CSH WDL {c}", f"CASH WD {_ref(5)}", f"{bank}ATM {c}", f"ATM-CASH {_ref(6)}", f"CARD WDL {c} {_ref(4)}", f"WDL {c} {_ref(6)}", f"SELF {c} CASH"],
        "TRANSFER_OUT": [f"TPT-{p}", f"FT-{p}-{_ref(8)}", f"MMT/{_ref(10)}/{p}", f"IB FUNDS TRANSFER {p}", f"INB {p} {_ref(6)}", f"TO {p} A/C {_ref(6)}", f"BY CHEQUE {_ref(6)}", f"RENT {p}", f"MAINT {p} SOCIETY"],
        "LOAN_EMI": [f"{rng.choice(LENDERS)} {_ref(8)}", f"ACH/{rng.choice(LENDERS)}/{_ref(6)}", f"NACH DR {rng.choice(LENDERS)}", f"{rng.choice(LENDERS)} INST {d.strftime('%m')}", f"ECS {rng.choice(LENDERS)} {_ref(5)}", f"BAJAJ FIN {_ref(7)}"],
        "BANK_CHARGE": ["CONSOLIDATED CHARGES", f"FOLIO CHGS {d.strftime('%b').upper()}", "DEBIT CARD ANNUAL FEE", "ANNUAL MAINT", "AMC DC", "SMS ALRT", "ALERT CHRGS", "BAL NON-MAINTENANCE", "A/C MAINT FEE", "DC ISSUANCE", "NON MAINT PENALTY", "CASH HANDLING CHGS", "DUPLICATE STMT CHG", "STOP PAYMENT CHG", "ATM TXN BEYOND FREE LIMIT", "AMB SHORTFALL"],
        "INCOME_CREDIT": [f"NEFT CR-{ctx.get('employer', rng.choice(EMPLOYERS))}-{d.strftime('%b').upper()}", f"CREDIT BY {ctx.get('employer', rng.choice(EMPLOYERS))}", f"{ctx.get('employer', rng.choice(EMPLOYERS))} {_ref(6)}", "MONTHLY STIPEND", f"PENSION CR {d.strftime('%m%y')}", f"IMPS/{_ref(10)}/{ctx.get('employer', rng.choice(EMPLOYERS))}", f"PAYROLL {d.strftime('%b%y').upper()}", f"ACH C-{ctx.get('employer', rng.choice(EMPLOYERS))}"],
        "TRANSFER_IN": [f"{p} {_ref(8)}", f"MMT/{_ref(10)}/{p}/CR", f"FROM {p}", f"TPT-{p}-CR", f"INB {p}", f"{p.split()[0].lower()}@{h}", f"CR {p} {_ref(6)}", f"DEPOSIT {c}"],
        "REFUND_REVERSAL": [f"{m} REFUND", f"CASHBACK {m}", f"RVSL {_ref(8)}", f"UPI RRN {_ref(12)} RETURN", f"{m} CR {_ref(6)}", f"REFUND ORD {_ref(10)}", f"RVRSL ATM {c}", f"{m} REV"],
        "INTEREST_CREDIT": ["INT", f"INT:{d.strftime('%d%m%y')}", "QTRLY INT", "SB A/C INT", "INTT CR", f"INT CAPITALISED {d.strftime('%b').upper()}"],
    }
    if cat == "UPI_PAYMENT" and amt >= 5000:
        big = rng.choice(["PSG COLLEGE FEES", "CIT FEES", "KMCH HOSPITAL", "APARTMENT RENT", "LIC PREMIUM", "SCHOOL FEES", "GANGA HOSPITAL", "JEWELLERS", "TRAVEL AGENCY"])
        return _noise(rng.choice([f"UPI/DR/{_ref()}/{big}/{bank}/{big.split()[0].lower()}@{h}", f"UPI-{big}-{_ref(12)}", f"UPI/P2M/{_ref()}/{big}", f"{big} {c}", f"GPAY {big}"]))
    pool = H[cat] if rng.random() < 0.35 else T[cat]
    return _noise(rng.choice(pool))


# ---------------------------------------------------------------------------- customer archetypes
ARCHETYPES = {
    #            income     upi  card  atm  tr_out emi  charges refund   p_income
    "salaried":   ((35000, 95000), 14, 4, 2, 2, 0.6, 0.25, 0.25, 1.0),
    "pensioner":  ((3000, 25000), 3, 0.5, 2, 1, 0.1, 0.35, 0.1, 1.0),
    "student":    ((4000, 12000), 18, 2, 1, 1, 0.0, 0.3, 0.3, 0.9),
    "business":   ((60000, 200000), 25, 6, 4, 8, 0.4, 0.3, 0.3, 0.7),
    "low_activity": ((0, 6000), 1, 0.2, 0.6, 0.3, 0.0, 0.5, 0.05, 0.4),
}


SEASON = {1: 0.9, 2: 0.9, 3: 1.05, 4: 1.0, 5: 1.0, 6: 1.15, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.25, 11: 1.2, 12: 1.1}


def generate(n_customers: int = 500, months: int = 12, start: date = date(2025, 1, 1), seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    global rng, nrng
    rng = random.Random(seed); nrng = np.random.default_rng(seed)
    rows, custs = [], []
    arche_names = list(ARCHETYPES)
    arche_p = [0.38, 0.2, 0.15, 0.12, 0.15]
    for ci in range(n_customers):
        a = rng.choices(arche_names, arche_p)[0]
        inc_rng, upi, card, atm, trout, emi_p, chg_p, ref_p, p_inc = ARCHETYPES[a]
        bank = rng.choice(BANKS)
        income = round(rng.uniform(*inc_rng), -2)
        has_emi = rng.random() < emi_p
        emi_amt = round(rng.uniform(0.08, 0.3) * max(income, 5000), -2) if has_emi else 0
        bal = round(rng.uniform(0.2, 2.5) * max(income, 3000), -2)
        ctx = {"employer": rng.choice(EMPLOYERS)}
        cid = f"C{ci + 1:04d}"
        custs.append({"customer_id": cid, "bank": bank, "archetype": a, "monthly_income": income, "opening_balance": bal, "has_emi": int(has_emi)})
        spend_scale = rng.uniform(0.55, 0.95)
        for mi in range(months):
            m0 = date(start.year + (start.month - 1 + mi) // 12, (start.month - 1 + mi) % 12 + 1, 1)
            days = ((date(m0.year + m0.month // 12, m0.month % 12 + 1, 1)) - m0).days
            month_rows = []
            # income
            if income > 0 and rng.random() < p_inc:
                month_rows.append((m0 + timedelta(days=rng.randint(0, 3)), "INCOME_CREDIT", 0.0, round(income * rng.uniform(0.97, 1.03), 2)))
            # EMI
            if has_emi:
                month_rows.append((m0 + timedelta(days=rng.randint(4, 9)), "LOAN_EMI", emi_amt, 0.0))
            # seasonality (festival season Oct-Nov, school fees Jun, year-end) + occasional one-off big-ticket month
            budget = max(income, 4000) * spend_scale * rng.uniform(0.8, 1.0) * SEASON[m0.month] * (1.6 if rng.random() < 0.08 else 1.0)
            def add(cat, n, lo, hi):
                for _ in range(nrng.poisson(n)):
                    month_rows.append((m0 + timedelta(days=rng.randint(0, days - 1)), cat, round(float(np.clip(nrng.lognormal(np.log((lo + hi) / 2), 0.6), lo, hi)), 0), 0.0))
            add("UPI_PAYMENT", upi, 40, max(300, budget * 0.08))
            add("CARD_POS", card, 200, max(800, budget * 0.15))
            add("ATM_WITHDRAWAL", atm, 500, max(2000, budget * 0.25))
            add("TRANSFER_OUT", trout, 500, max(2000, budget * 0.4))
            for _ in range(nrng.poisson(1.2 if a != "low_activity" else 0.3)):
                month_rows.append((m0 + timedelta(days=rng.randint(0, days - 1)), "TRANSFER_IN", 0.0, round(float(np.clip(nrng.lognormal(np.log(2500), 0.8), 100, 60000)), 0)))
            # charges (more likely when balance low / dormant)
            if rng.random() < chg_p:
                month_rows.append((date(m0.year, m0.month, min(days, 28 + rng.randint(0, 2))), "BANK_CHARGE", round(rng.choice([15, 17.7, 23, 29.5, 59, 100, 118, 150, 236, 295, 354, 500, 590, 708, 826, 885, 1180, 1475]), 2), 0.0))
                if rng.random() < 0.5:
                    month_rows.append((date(m0.year, m0.month, min(days, 29)), "BANK_CHARGE", round(rng.choice([2.7, 4.14, 5.4, 9, 18, 27, 53.1]), 2), 0.0))
            # refunds / reversals
            if rng.random() < ref_p:
                month_rows.append((m0 + timedelta(days=rng.randint(5, days - 1)), "REFUND_REVERSAL", 0.0, round(float(rng.choice([99, 149, 199, 250, 299, 450, 500, 640, 999, 1200, 1500, 2000])), 0)))
            # quarterly interest
            if m0.month in (3, 6, 9, 12):
                month_rows.append((date(m0.year, m0.month, min(days, 30)), "INTEREST_CREDIT", 0.0, round(max(1.0, bal * 0.0275 / 4 * rng.uniform(0.6, 1.2)), 2)))
            # scale discretionary debits so the month's spend ≈ budget (keeps balances plausible)
            disc = [i for i, r in enumerate(month_rows) if r[2] > 0 and r[1] not in ("LOAN_EMI", "BANK_CHARGE")]
            tot = sum(month_rows[i][2] for i in disc)
            target = max(1500.0, budget * rng.uniform(0.85, 1.15) - emi_amt)
            if tot > 0:
                k = target / tot
                for i in disc:
                    r = month_rows[i]; month_rows[i] = (r[0], r[1], round(max(10.0, r[2] * k), 0), r[3])
            if bal < 2000 and rng.random() < 0.5:                     # family top-up when running low
                month_rows.append((m0 + timedelta(days=rng.randint(1, 10)), "TRANSFER_IN", 0.0, round(rng.uniform(2000, 15000), -2)))
            if rng.random() < 0.05 and income > 0:   # big-ticket UPI/transfer: fees, hospital, rent, insurance (unscaled, realistic amounts)
                big_cat = rng.choice(["UPI_PAYMENT", "UPI_PAYMENT", "TRANSFER_OUT"])
                month_rows.append((m0 + timedelta(days=rng.randint(0, days - 1)), big_cat, float(round(min(60000, max(5000, income * rng.uniform(0.15, 0.6))), -2)), 0.0))
            month_rows.sort(key=lambda r: r[0])
            for d, cat, dr, cr in month_rows:
                bal = round(bal - dr + cr, 2)
                rows.append({"customer_id": cid, "date": d.isoformat(), "narration": narr(cat, bank, dr or cr, d, ctx), "debit": dr, "credit": cr, "balance": bal, "bank": bank, "category": cat, "archetype": a})
    return pd.DataFrame(rows), pd.DataFrame(custs)


def load(regenerate: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    tp, cp = OUT / "transactions.csv", OUT / "customers.csv"
    if regenerate or not tp.exists():
        t, c = generate()
        t.to_csv(tp, index=False); c.to_csv(cp, index=False)
    return pd.read_csv(tp, parse_dates=["date"]), pd.read_csv(cp)


if __name__ == "__main__":
    t, c = load(regenerate=True)
    print(t.shape, c.shape); print(t["category"].value_counts()); print(t.sample(8, random_state=1)[["narration", "debit", "credit", "category"]].to_string())
