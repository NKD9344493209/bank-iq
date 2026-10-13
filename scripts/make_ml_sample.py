"""Writes data/samples/axis_kavya_longtail_2026.csv — a SYNTHETIC salaried account whose narrations are the
*long-tail* formats (merchant-only lines, bank codes, abbreviations) that the regex engine was never written for.
Used on the Intelligence screen to show where the learned classifier and the rules disagree.
Run:  python scripts/make_ml_sample.py
"""
from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "samples" / "axis_kavya_longtail_2026.csv"

# (date, narration, debit, credit)  – amounts chosen so the running balance stays plausible
LINES = [
    ("01/01/26", "PAYROLL JAN26", 0, 58000), ("03/01/26", "TPT-RAMESH K-RENT", 14000, 0), ("04/01/26", "BAJAJ FIN 40221187", 6200, 0),
    ("06/01/26", "SWIGGY CHENNAI", 410, 0), ("08/01/26", "PAYTM*JIO RECHARGE", 299, 0), ("10/01/26", "CSH WDL ANNA NAGAR", 3000, 0),
    ("12/01/26", "BIL/ONL/904411238/TNEB", 1240, 0), ("15/01/26", "AMAZON*7731KQ", 2150, 0), ("18/01/26", "GPAY DMART", 1860, 0),
    ("20/01/26", "CONSOLIDATED CHARGES", 118, 0), ("22/01/26", "CASHBACK AMAZON", 0, 150), ("25/01/26", "ravi@okaxis 551203", 500, 0),
    ("28/01/26", "ZOMATO.COM", 380, 0), ("31/01/26", "INT", 0, 92),
    ("01/02/26", "PAYROLL FEB26", 0, 58000), ("03/02/26", "TPT-RAMESH K-RENT", 14000, 0), ("04/02/26", "BAJAJ FIN 40221188", 6200, 0),
    ("05/02/26", "CARD WDL CBE 3312", 2000, 0), ("07/02/26", "KMCH HOSPITAL CBE", 18500, 0), ("09/02/26", "FROM LAKSHMI", 0, 10000),
    ("11/02/26", "MYNTRA INDIA PVT LTD", 1699, 0), ("14/02/26", "PHONEPE SURESH BABU", 1200, 0), ("16/02/26", "AMB SHORTFALL", 295, 0),
    ("16/02/26", "GST", 53.1, 0), ("19/02/26", "UBER 03/26 IN", 240, 0), ("21/02/26", "RVSL 88213405", 0, 240), ("24/02/26", "SELF CBE CASH", 2500, 0),
    ("27/02/26", "LIC PREMIUM 90112", 4800, 0),
    ("01/03/26", "PAYROLL MAR26", 0, 58000), ("03/03/26", "TPT-RAMESH K-RENT", 14000, 0), ("04/03/26", "BAJAJ FIN 40221189", 6200, 0),
    ("06/03/26", "ATM-CASH 772910", 5000, 0), ("09/03/26", "BIGBASKET STORE CBE", 2340, 0), ("12/03/26", "DC ISSUANCE", 236, 0),
    ("15/03/26", "SPOTIFY*119", 119, 0), ("18/03/26", "IB FUNDS TRANSFER PRIYA S", 7000, 0), ("20/03/26", "AMAZON REFUND", 0, 2150),
    ("23/03/26", "PSG COLLEGE FEES", 25000, 0), ("26/03/26", "INDIAN OIL CBE IN", 2100, 0), ("28/03/26", "ALERT CHRGS", 15, 0), ("31/03/26", "QTRLY INT", 0, 118),
]


def main():
    bal = 42000.0
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["SYNTHETIC SAMPLE — Axis Bank format — for demo only (long-tail narrations)"])
        w.writerow(["Account No : 9170XXXXXX2201", "Salary Account", "Coimbatore"])
        w.writerow([])
        w.writerow(["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"])
        for d, n, dr, cr in LINES:
            bal = round(bal - dr + cr, 2)
            w.writerow([d, n, "", d, f"{dr:.2f}" if dr else "", f"{cr:.2f}" if cr else "", f"{bal:.2f}"])
    print("wrote", OUT, len(LINES), "lines")


if __name__ == "__main__":
    main()
