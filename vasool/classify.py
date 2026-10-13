"""Transaction understanding: narration → channel, kind, merchant.

This is deliberately a rule/regex layer, not a model. Bank narrations are
cryptic but finite; every pattern here is testable. A language model may be
plugged in later for the long tail via `ExternalClassifier`, but it can only
*suggest* a kind that this module then validates against the amount/direction
of the line — it can never invent a charge.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from .models import Channel, Kind, Transaction

# ---- pattern tables ------------------------------------------------------- #
P = lambda *pats: re.compile("|".join(pats), re.I)

ATM_WDL = P(r"\bATM\b.*\b(WDL|WITHDRAWAL|CASH|CW|WD)\b", r"\bNWD\b", r"\bAWB\b", r"\bCWDR\b", r"\bATW\b", r"\bATM[- ]?CASH\b", r"\bCASH WDL\b", r"\bNFS[/ -]")
ATM_ENQ = P(r"\bATM\b.*\b(BAL(ANCE)? ?ENQ|MINI ?STMT|MINI STATEMENT|PIN CHANGE)\b", r"\bBALENQ\b")
UPI = P(r"\bUPI\b")
IMPS = P(r"\bIMPS\b")
NEFT = P(r"\bNEFT\b")
RTGS = P(r"\bRTGS\b")
POS = P(r"\bPOS\b", r"\bPCD\b", r"\bVPS\b", r"\bPUR(CHASE)?\b.*\bCARD\b", r"\bDEBIT CARD\b.*\bPUR")
ECOM = P(r"\bECOM\b", r"\bE-?COMM?\b", r"\bONLINE PUR")
CHEQUE = P(r"\bCHQ\b(?!.*(BOOK|CHRG|CHARGE))", r"\bCHEQUE\b(?!.*(BOOK|CHRG|CHARGE))", r"\bCLG\b")

MIN_BAL = P(r"\bMIN(IMUM)?\.? ?BAL", r"\b(MAB|AMB|SMAB|AQB|QAB|MQB)\b", r"NON[- ]?MAINT", r"\bBAL(ANCE)? ?SHORTFALL", r"\bMONTHLY AVG BAL", r"\bBELOW MIN")
SMS_CHG = P(r"\bSMS\b", r"SMS[_ -]?CH(R)?GS?", r"\bALERT(S)? ?(CHRG|CHG|CHARGE|FEE)")
ATM_CHG = P(r"\bATM\b.*\b(CHRG|CHGS?|CHARGES?|FEES?|DECLINE)", r"\b(CHRG|CHGS?|CHARGES?|FEES?)\b.*\bATM\b", r"\bATW\b.*\bCHG", r"\bNFS\b.*\b(CHRG|CHG|CHARGE)\b", r"\bEXCESS ATM")
CARD_AMC = P(r"\b(DEBIT|ATM) ?CARD\b.*\b(AMC|ANNUAL|FEE|CHARGE|ISSU)", r"\bDC ANNUAL", r"\bCARD (AMC|ANNUAL FEE|ISSUANCE)")
CHQ_CHG = P(r"\bCHQ\b.*\b(BOOK|CHRG|CHARGE|RETURN|BOUNCE)", r"\bCHEQUE\b.*\b(BOOK|CHRG|CHARGE|RETURN|BOUNCE)", r"\bECS RET(URN)? CHG")
REACTIVATION = P(r"\bREACTIVAT", r"\bDORMAN", r"\bINOPERATIVE")
GST = P(r"\b(CGST|SGST|IGST|GST)\b")
GENERIC_CHG = P(r"\b(CHRG|CHG|CHARGE|CHARGES|FEE|FEES|PENALTY|SERVICE CHARGE|SC)\b", r"\bFOLIO\b", r"\bLEDGER FEE")
REVERSAL = P(r"\bREV(ERSAL|ERSED)?\b", r"\bREFUND\b", r"\bCHARGEBACK\b", r"\bRETURN(ED)?\b(?!.*CHG)", r"\bRET\b", r"\bFAILED?\b.*\bCR\b", r"\bCREDIT ADJ", r"\bTXN REV")
FAILED = P(r"\bFAIL(ED|URE)?\b", r"\bDECLIN(E|ED)\b", r"\bTIME ?OUT\b", r"\bUNSUCCESS", r"\bNOT DISPENSED", r"\bTECH(NICAL)? DECLINE")
INTEREST = P(r"\bINT(ERES)?T?\.? ?(PD|PAID|CR|CREDIT)\b", r"\bCREDIT INTEREST", r"\bSB INT", r"\bINTEREST\b(?!.*(PENAL|OVERDUE|DEBIT))")
LOAN_EMI = P(r"\bEMI\b", r"\bLOAN\b.*\b(INST|INSTAL|REPAY|EMI)", r"\bGOLD LOAN\b.*\b(INT|INTEREST|REPAY)")
LOAN_PENAL = P(r"\bPENAL\b", r"\bOVERDUE (INT|CHARGE|CHG)", r"\bLATE (PAYMENT|FEE)", r"\bBOUNCE CHARGE")
LOAN_CHG = P(r"\bLOAN\b.*\b(PROCESS|CHRG|CHG|CHARGE|FEE|DOC)", r"\bFORECLOS", r"\bPREPAY(MENT)? (CHG|CHARGE)")
COMPENSATION = P(r"\bCOMPENSAT", r"\bTAT COMP", r"\bDELAY COMP")
CREDIT_HINTS = P(r"\bSALARY\b", r"\bPENSION\b", r"\bDIVIDEND\b", r"\bCASH DEP", r"\bBY TRANSFER", r"\bCR\b")

METRO_CITIES = ("MUMBAI", "DELHI", "NEW DELHI", "CHENNAI", "KOLKATA", "BENGALURU", "BANGALORE", "HYDERABAD")
BANK_TOKENS = ["SBI", "HDFC", "ICICI", "AXIS", "CANARA", "PNB", "BOB", "UNION", "KOTAK", "INDIAN BANK", "IOB", "BOI", "TMB", "CUB", "KVB", "FEDERAL", "IDBI", "YES", "INDUSIND", "CENTRAL BANK", "UCO", "IDFC"]


def _merchant(narration: str) -> str:
    n = narration.upper()
    # UPI: "UPI/DR/1234567890/NETFLIX/HDFC/..." or "UPI-NETFLIX-..."
    m = re.search(r"UPI[/-](?:DR|CR|P2M|P2A)?[/-]?\d*[/-]([A-Z0-9 .&*@_-]{3,40}?)(?:[/-]|$)", n)
    if m:
        return _clean_merchant(m.group(1))
    m = re.search(r"(?:POS|PCD|VPS|ECOM)[/ -]+\d*[/ -]*([A-Z0-9 .&*@_-]{3,40}?)(?:[/-]|$)", n)
    if m:
        return _clean_merchant(m.group(1))
    return ""


def _clean_merchant(s: str) -> str:
    s = re.sub(r"[*@_].*$", "", s)         # NETFLIX*IN → NETFLIX ; name@okaxis → name
    s = re.sub(r"\b(PVT|LTD|LIMITED|INDIA|IN|COM|PAYMENTS?|TECHNOLOGIES|SERVICES|ONLINE)\b", "", s)
    s = re.sub(r"\d{4,}", "", s)
    s = re.sub(r"\s+", " ", s).strip(" .-/")
    return s[:32]


def classify(txn: Transaction, own_bank: str = "") -> Transaction:
    n = txn.narration.upper()
    txn.failed_hint = bool(FAILED.search(n))
    txn.merchant = _merchant(txn.narration)

    # --- bank-initiated lines first (charges, interest, compensation) ------ #
    if txn.is_debit:
        if MIN_BAL.search(n):
            txn.kind, txn.channel = Kind.CHARGE_MIN_BAL, Channel.BANK
        elif ATM_CHG.search(n):
            txn.kind, txn.channel = Kind.CHARGE_ATM, Channel.BANK
        elif SMS_CHG.search(n):
            txn.kind, txn.channel = Kind.CHARGE_SMS, Channel.BANK
        elif CARD_AMC.search(n):
            txn.kind, txn.channel = Kind.CHARGE_CARD_AMC, Channel.BANK
        elif CHQ_CHG.search(n):
            txn.kind, txn.channel = Kind.CHARGE_CHEQUE, Channel.BANK
        elif REACTIVATION.search(n):
            txn.kind, txn.channel = Kind.CHARGE_REACTIVATION, Channel.BANK
        elif LOAN_PENAL.search(n):
            txn.kind, txn.channel = Kind.LOAN_PENAL, Channel.LOAN
        elif LOAN_CHG.search(n):
            txn.kind, txn.channel = Kind.LOAN_CHARGE, Channel.LOAN
        elif LOAN_EMI.search(n):
            txn.kind, txn.channel = Kind.LOAN_EMI, Channel.LOAN
        elif GST.search(n) and txn.debit < 200:
            txn.kind, txn.channel = Kind.GST_ON_CHARGE, Channel.BANK
        elif GENERIC_CHG.search(n) and not (UPI.search(n) or IMPS.search(n) or POS.search(n)):
            txn.kind, txn.channel = Kind.CHARGE_OTHER, Channel.BANK
        elif ATM_ENQ.search(n):
            txn.kind, txn.channel = Kind.ATM_ENQUIRY, Channel.ATM
        elif ATM_WDL.search(n):
            txn.kind, txn.channel = Kind.ATM_WITHDRAWAL, Channel.ATM
        elif UPI.search(n):
            txn.kind, txn.channel = Kind.DEBIT, Channel.UPI
        elif IMPS.search(n):
            txn.kind, txn.channel = Kind.DEBIT, Channel.IMPS
        elif NEFT.search(n):
            txn.kind, txn.channel = Kind.DEBIT, Channel.NEFT
        elif RTGS.search(n):
            txn.kind, txn.channel = Kind.DEBIT, Channel.RTGS
        elif ECOM.search(n):
            txn.kind, txn.channel = Kind.DEBIT, Channel.ECOM
        elif POS.search(n):
            txn.kind, txn.channel = Kind.DEBIT, Channel.POS
        elif CHEQUE.search(n):
            txn.kind, txn.channel = Kind.DEBIT, Channel.CHEQUE
        else:
            txn.kind, txn.channel = Kind.DEBIT, Channel.OTHER
    else:
        if COMPENSATION.search(n):
            txn.kind, txn.channel = Kind.COMPENSATION, Channel.BANK
        elif REVERSAL.search(n) or txn.failed_hint:
            txn.kind = Kind.REVERSAL
            txn.channel = _channel_of(n)
        elif INTEREST.search(n):
            txn.kind, txn.channel = Kind.INTEREST_CREDIT, Channel.BANK
        else:
            txn.kind = Kind.CREDIT
            txn.channel = _channel_of(n)

    # ATM: own bank vs other bank -------------------------------------------- #
    if txn.channel == Channel.ATM:
        txn.own_bank_atm = _own_bank_atm(n, own_bank)
        txn.meta["metro"] = any(c in n for c in METRO_CITIES)
    # ATM enquiries sometimes appear as zero-amount lines
    if ATM_ENQ.search(n) and txn.amount == 0:
        txn.kind, txn.channel = Kind.ATM_ENQUIRY, Channel.ATM
        txn.own_bank_atm = _own_bank_atm(n, own_bank)
    return txn


def _channel_of(n: str) -> Channel:
    if UPI.search(n):
        return Channel.UPI
    if IMPS.search(n):
        return Channel.IMPS
    if NEFT.search(n):
        return Channel.NEFT
    if ATM_WDL.search(n) or re.search(r"\bATM\b", n):
        return Channel.ATM
    if POS.search(n):
        return Channel.POS
    if ECOM.search(n):
        return Channel.ECOM
    return Channel.OTHER


def _own_bank_atm(n: str, own_bank: str) -> Optional[bool]:
    if re.search(r"\bNFS\b", n):          # National Financial Switch = another bank's ATM
        return False
    own = (own_bank or "").upper()
    mentioned = [b for b in BANK_TOKENS if re.search(rf"\b{re.escape(b)}\b", n)]
    if not mentioned:
        return None                       # unknown — the twin will ask or assume conservatively
    if own and own in mentioned:
        return True
    return False if own else None


def classify_all(txns: Iterable[Transaction], own_bank: str = "") -> list[Transaction]:
    return [classify(t, own_bank) for t in txns]
