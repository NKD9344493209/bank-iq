"""Generate synthetic sample statements (clearly labelled synthetic) in real bank export shapes.

Run:  python scripts/make_samples.py
Writes to data/samples/. Every file carries a SYNTHETIC marker in its header rows.
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "samples"
OUT.mkdir(parents=True, exist_ok=True)


def write_canara(rows, path, opening):
    """Canara-style: Txn Date, Value Date, Description, Ref No./Cheque No., Branch Code, Debit, Credit, Balance"""
    bal = opening
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["SYNTHETIC SAMPLE — Canara Bank format — for demo only"])
        w.writerow(["Account Name", "SELVI R"])
        w.writerow(["Account Number", "XXXXXXXX4417"])
        w.writerow(["Account Type", "SB PENSION"])
        w.writerow([])
        w.writerow(["Txn Date", "Value Date", "Description", "Ref No./Cheque No.", "Branch Code", "Debit", "Credit", "Balance"])
        for d, desc, ref, dr, cr in rows:
            bal = round(bal - dr + cr, 2)
            w.writerow([d.strftime("%d-%m-%Y"), d.strftime("%d-%m-%Y"), desc, ref, "0421", f"{dr:.2f}" if dr else "", f"{cr:.2f}" if cr else "", f"{bal:.2f}"])


def write_sbi(rows, path, opening):
    """SBI-style: Txn Date, Value Date, Description, Ref No./Cheque No., Debit, Credit, Balance (tab separated export)"""
    bal = opening
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["SYNTHETIC SAMPLE — State Bank of India format — for demo only"])
        w.writerow(["Account Name :", "ARUN K"])
        w.writerow(["Account Number :", "_00000039281105"])
        w.writerow(["Address :", "Coimbatore"])
        w.writerow([])
        w.writerow(["Txn Date", "Value Date", "Description", "Ref No./Cheque No.", "        Debit", "Credit", "Balance"])
        for d, desc, ref, dr, cr in rows:
            bal = round(bal - dr + cr, 2)
            w.writerow([d.strftime("%d %b %Y"), d.strftime("%d %b %Y"), desc, ref, f"{dr:,.2f}" if dr else "", f"{cr:,.2f}" if cr else "", f"{bal:,.2f}"])


def write_hdfc(rows, path, opening):
    """HDFC-style: Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance"""
    bal = opening
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["SYNTHETIC SAMPLE — HDFC Bank format — for demo only"])
        w.writerow(["Account No : 50100XXXXX8823", "Salary Account", "Chennai"])
        w.writerow([])
        w.writerow(["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"])
        for d, desc, ref, dr, cr in rows:
            bal = round(bal - dr + cr, 2)
            w.writerow([d.strftime("%d/%m/%y"), desc, ref, d.strftime("%d/%m/%y"), f"{dr:.2f}" if dr else "", f"{cr:.2f}" if cr else "", f"{bal:.2f}"])


D = date

# --------------------------------------------------------------------------- #
# 1. Amma — Canara pension account, Coimbatore (non-metro). The demo statement.
#    Expect: failed ATM reversed 12 days late (₹1,200) · unreversed failed UPI ₹500 (+₹100/day)
#            · min-bal penalty ₹295+GST with unknown notice (question) · SMS ₹17.70 (question)
#            · ATM charge inside free allowance (₹23+GST recoverable) · ₹50,000 college fee NOT flagged
# --------------------------------------------------------------------------- #
amma = [
    (D(2026, 6, 2), "NEFT CR-PENSION-TN TREASURY-JUN", "N152260041", 0, 6500),
    (D(2026, 6, 4), "ATM WDL CANARA RS PURAM CBE", "ATM402117", 3000, 0),
    (D(2026, 6, 11), "NFS/ATM WDL/SBI GANDHIPURAM/CBE", "NFS611022", 2000, 0),
    (D(2026, 6, 18), "UPI/DR/616812345/ANNAPOORNA STORES/CNRB/an***@okaxis", "616812345", 640, 0),
    (D(2026, 6, 30), "CHRG MIN BAL NON MAINT MAY26", "", 295, 0),
    (D(2026, 6, 30), "GST ON CHARGES", "", 53.10, 0),
    (D(2026, 6, 30), "SMS ALERT CHRG Q1 26-27", "", 15, 0),
    (D(2026, 6, 30), "GST ON CHARGES", "", 2.70, 0),
    (D(2026, 7, 2), "NEFT CR-PENSION-TN TREASURY-JUL", "N152270041", 0, 6500),
    (D(2026, 7, 6), "ATM WDL CANARA RS PURAM CBE", "ATM402331", 2000, 0),
    (D(2026, 7, 9), "ATM WDL CANARA TOWNHALL CBE", "ATM402398", 1500, 0),
    (D(2026, 7, 9), "ATM CASH WDL CHRG", "", 23, 0),
    (D(2026, 7, 9), "GST ON CHARGES", "", 4.14, 0),
    (D(2026, 7, 15), "UPI/DR/619977001/TNEB BILL/CNRB/tneb@sbi", "619977001", 812, 0),
    (D(2026, 7, 19), "BY TRANSFER FROM KUMAR S", "TFR7720", 0, 52000),
    (D(2026, 7, 21), "UPI/DR/620311902/PSG COLLEGE FEES/CNRB/psg@icici", "620311902", 50000, 0),
    (D(2026, 8, 2), "NEFT CR-PENSION-TN TREASURY-AUG", "N152280041", 0, 6500),
    (D(2026, 8, 3), "NFS/ATM WDL/IOB PEELAMEDU/CBE", "NFS803110", 1200, 0),           # failed; reversed 20 Aug
    (D(2026, 8, 5), "ATM WDL CANARA RS PURAM CBE", "ATM402510", 1200, 0),            # retry — succeeded
    (D(2026, 8, 10), "UPI/DR/622100455/RAJ MEDICALS/CNRB/raj@ybl/FAILED", "622100455", 500, 0),  # never reversed
    (D(2026, 8, 20), "ATM REVERSAL NFS803110 03/08 IOB PEELAMEDU", "NFS803110", 0, 1200),
    (D(2026, 8, 28), "UPI/DR/624455001/ANNAPOORNA STORES/CNRB/an***@okaxis", "624455001", 710, 0),
    (D(2026, 8, 31), "SB INT CR", "", 0, 84),
]
write_canara(amma, OUT / "canara_amma_pension_2026.csv", 8000)

# --------------------------------------------------------------------------- #
# 1b. Amma — the PREVIOUS quarter of the same account (Mar – 4 Jun 2026), to demo
#     multiple statements. Overlaps the main statement by two lines (2 Jun, 4 Jun)
#     which must be de-duplicated. With this slice merged, the June "MIN BAL MAY26"
#     penalty is judged on May's real balances (never below ₹500) → CONFIRMED, no
#     question needed. Also: 3rd own-bank ATM withdrawal charged in April → recoverable.
# --------------------------------------------------------------------------- #
amma_prev = [
    (D(2026, 3, 2), "NEFT CR-PENSION-TN TREASURY-MAR", "N152230041", 0, 6500),
    (D(2026, 3, 5), "ATM WDL CANARA RS PURAM CBE", "ATM401552", 2500, 0),
    (D(2026, 3, 12), "UPI/DR/607112233/ANNAPOORNA STORES/CNRB/an***@okaxis", "607112233", 560, 0),
    (D(2026, 3, 18), "NFS/ATM WDL/SBI GANDHIPURAM/CBE", "NFS318041", 1000, 0),          # failed; reversed in 2 days → no claim
    (D(2026, 3, 20), "ATM REVERSAL NFS318041 18/03 SBI GANDHIPURAM", "NFS318041", 0, 1000),
    (D(2026, 3, 31), "SMS ALERT CHRG Q4 25-26", "", 15, 0),
    (D(2026, 3, 31), "GST ON CHARGES", "", 2.70, 0),
    (D(2026, 4, 2), "NEFT CR-PENSION-TN TREASURY-APR", "N152240041", 0, 6500),
    (D(2026, 4, 4), "ATM WDL CANARA RS PURAM CBE", "ATM401790", 2000, 0),
    (D(2026, 4, 9), "ATM WDL CANARA TOWNHALL CBE", "ATM401844", 1500, 0),
    (D(2026, 4, 14), "ATM WDL CANARA RS PURAM CBE", "ATM401901", 1000, 0),               # 3rd own-bank → still free
    (D(2026, 4, 14), "ATM CASH WDL CHRG", "", 23, 0),                                    # charged anyway → recoverable
    (D(2026, 4, 14), "GST ON CHARGES", "", 4.14, 0),
    (D(2026, 4, 20), "UPI/DR/611022001/TNEB BILL/CNRB/tneb@sbi", "611022001", 760, 0),
    (D(2026, 5, 2), "NEFT CR-PENSION-TN TREASURY-MAY", "N152250041", 0, 6500),
    (D(2026, 5, 6), "ATM WDL CANARA RS PURAM CBE", "ATM402004", 3000, 0),
    (D(2026, 5, 15), "UPI/DR/613511002/RAJ MEDICALS/CNRB/raj@ybl", "613511002", 430, 0),
    (D(2026, 5, 24), "UPI/DR/614412003/ANNAPOORNA STORES/CNRB/an***@okaxis", "614412003", 690, 0),
    (D(2026, 6, 2), "NEFT CR-PENSION-TN TREASURY-JUN", "N152260041", 0, 6500),          # overlap with main statement
    (D(2026, 6, 4), "ATM WDL CANARA RS PURAM CBE", "ATM402117", 3000, 0),               # overlap with main statement
]
# opening chosen so the running balance meets the main statement exactly (8,000 before 2 Jun)
_net = sum(cr - dr for _, _, _, dr, cr in amma_prev[:-2])
write_canara(amma_prev, OUT / "canara_amma_pension_2026_mar_may.csv", round(8000 - _net, 2))

# --------------------------------------------------------------------------- #
# 2. Arun — SBI student account, Coimbatore. The TRAP statement.
#    Expect: partial reversal (2 × ₹1,000 within T+5) → NO claim
#            ₹25 ATM charge in Apr 2025 → over the ₹21 cap then (excess) · ₹23 in May 2025 → legal
#            6th ATM withdrawal charge → AVOIDABLE · same-amount retry within 2 days → ASK, never claim
# --------------------------------------------------------------------------- #
arun = [
    (D(2025, 4, 1), "BY TRANSFER-UPI/CR/509123001/APPA/SBIN", "509123001", 0, 5000),
    (D(2025, 4, 3), "ATM WDL-SBI ATM RS PURAM", "509303001", 1000, 0),
    (D(2025, 4, 8), "ATM WDL-SBI ATM GANDHIPURAM", "509803011", 500, 0),
    (D(2025, 4, 12), "ATM WDL-SBI ATM PEELAMEDU", "510201101", 500, 0),
    (D(2025, 4, 16), "ATM WDL-SBI ATM RS PURAM", "510601001", 500, 0),
    (D(2025, 4, 20), "ATM WDL-SBI ATM RS PURAM", "511001001", 500, 0),
    (D(2025, 4, 24), "ATM WDL-SBI ATM RS PURAM", "511401001", 500, 0),            # 6th → charge allowed
    (D(2025, 4, 24), "ATM CASH WDL CHARGES", "", 25, 0),                          # but ₹25 > ₹21 cap (Apr 2025)
    (D(2025, 4, 24), "GST ON CHARGES", "", 4.50, 0),
    (D(2025, 5, 1), "BY TRANSFER-UPI/CR/512123001/APPA/SBIN", "512123001", 0, 5000),
    (D(2025, 5, 2), "ATM WDL-SBI ATM RS PURAM", "512201001", 500, 0),
    (D(2025, 5, 6), "ATM WDL-SBI ATM RS PURAM", "512601001", 500, 0),
    (D(2025, 5, 10), "ATM WDL-SBI ATM RS PURAM", "513001001", 500, 0),
    (D(2025, 5, 14), "ATM WDL-SBI ATM RS PURAM", "513401001", 500, 0),
    (D(2025, 5, 18), "ATM WDL-SBI ATM RS PURAM", "513801001", 500, 0),
    (D(2025, 5, 22), "ATM WDL-SBI ATM RS PURAM", "514201001", 500, 0),            # 6th
    (D(2025, 5, 22), "ATM CASH WDL CHARGES", "", 23, 0),                          # ₹23 = cap (May 2025) → legal, avoidable
    (D(2025, 5, 22), "GST ON CHARGES", "", 4.14, 0),
    (D(2025, 6, 1), "BY TRANSFER-UPI/CR/515123001/APPA/SBIN", "515123001", 0, 5000),
    (D(2025, 6, 4), "NWD-ATM CASH-HDFC BANK ATM AVINASHI RD", "515401001", 2000, 0),     # failed
    (D(2025, 6, 4), "NWD-ATM CASH-HDFC BANK ATM AVINASHI RD", "515401002", 2000, 0),     # retry same day → ask
    (D(2025, 6, 7), "ATM REV-PARTIAL-515401001", "515401001", 0, 1000),                  # partial 1
    (D(2025, 6, 8), "ATM REV-PARTIAL-515401001", "515401001", 0, 1000),                  # partial 2 → within T+5
    (D(2025, 6, 15), "UPI/DR/516501001/ZOMATO/SBIN/zomato@ptybl", "516501001", 349, 0),
    (D(2025, 6, 15), "UPI/DR/516501002/ZOMATO/SBIN/zomato@ptybl", "516501002", 349, 0),  # same amount, same merchant → ask
    (D(2025, 6, 30), "CREDIT INTEREST", "", 0, 31),
]
write_sbi(arun, OUT / "sbi_arun_student_2025.tsv", 1200)

# --------------------------------------------------------------------------- #
# 3. Priya — HDFC salary account, Chennai (metro). Requires profile min_balance_required=10000.
#    Expect: min-bal penalty although balance never dipped below 10,000 → CONFIRMED recoverable
#            IMPS failed & reversed next day → no claim · charge increase (card AMC ₹590→₹708) → ask
# --------------------------------------------------------------------------- #
priya = [
    (D(2026, 1, 1), "SALARY-JAN26-ACME TECH PVT LTD", "SAL0126", 0, 62000),
    (D(2026, 1, 5), "UPI-SWIGGY-swiggy@icici-UPI/601500011", "601500011", 480, 0),
    (D(2026, 1, 9), "IMPS-P2A-601900022-RENT-JAN", "601900022", 15000, 0),
    (D(2026, 1, 15), "POS 4123XXXXXXXX7710 NETFLIX.COM", "", 499, 0),
    (D(2026, 1, 20), "DEBIT CARD ANNUAL FEE 4123XXXXXXXX7710", "", 590, 0),
    (D(2026, 1, 27), "IMPS-P2A-602700045-SIS", "602700045", 5000, 0),              # failed
    (D(2026, 1, 28), "IMPS RETURN 602700045-BENEFICIARY NOT FOUND", "602700045", 0, 5000),   # reversed T+1 → fine
    (D(2026, 2, 1), "SALARY-FEB26-ACME TECH PVT LTD", "SAL0226", 0, 62000),
    (D(2026, 2, 3), "MIN BAL CHRG INCL GST JAN26", "", 708, 0),                    # balance never below 10k → recoverable
    (D(2026, 2, 9), "IMPS-P2A-604900022-RENT-FEB", "604900022", 15000, 0),
    (D(2026, 2, 15), "POS 4123XXXXXXXX7710 NETFLIX.COM", "", 649, 0),             # price creep 499→649 (info only)
    (D(2026, 2, 20), "ATM WDL HDFC ANNA NAGAR", "", 5000, 0),
    (D(2026, 3, 1), "SALARY-MAR26-ACME TECH PVT LTD", "SAL0326", 0, 62000),
    (D(2026, 3, 9), "IMPS-P2A-606900022-RENT-MAR", "606900022", 15000, 0),
    (D(2026, 3, 15), "POS 4123XXXXXXXX7710 NETFLIX.COM", "", 649, 0),
]
write_hdfc(priya, OUT / "hdfc_priya_salary_2026.csv", 24000)

# --------------------------------------------------------------------------- #
# 4. Murugan — Indian Bank account, dormant for 2+ years, then penalised. Also BSBDA when profile says so.
# --------------------------------------------------------------------------- #
murugan = [
    (D(2024, 1, 10), "CASH DEP BY SELF", "", 0, 3000),
    (D(2024, 2, 5), "ATM WDL INDIAN BANK POLLACHI", "", 1000, 0),
    (D(2024, 6, 30), "SB INT CR", "", 0, 22),
    (D(2024, 12, 31), "SB INT CR", "", 0, 24),
    (D(2025, 6, 30), "SB INT CR", "", 0, 25),
    (D(2025, 12, 31), "SB INT CR", "", 0, 26),
    (D(2026, 3, 31), "MIN BAL NON MAINT CHRG", "", 200, 0),     # 785 days after last customer txn → inoperative → recoverable
    (D(2026, 3, 31), "GST", "", 36, 0),
    (D(2026, 6, 30), "SB INT CR", "", 0, 21),
    (D(2026, 8, 12), "DORMANT ACCT REACTIVATION CHRG", "", 100, 0),
]
write_canara(murugan, OUT / "indianbank_murugan_dormant_2026.csv", 2500)

print("wrote", sorted(p.name for p in OUT.iterdir()))
