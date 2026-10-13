"""Domain model for the Regulatory Twin.

Everything the rule engine reasons about is defined here, with no framework
dependencies, so the same objects flow through the parser, the twin, the
rules, the complaint generator and the API.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Transactions
# --------------------------------------------------------------------------- #
class Channel(str, Enum):
    ATM = "ATM"
    UPI = "UPI"
    IMPS = "IMPS"
    NEFT = "NEFT"
    RTGS = "RTGS"
    POS = "POS"
    ECOM = "ECOM"
    CARD = "CARD"
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    BANK = "BANK"          # bank-initiated (charges, interest, penalties)
    LOAN = "LOAN"
    OTHER = "OTHER"


class Kind(str, Enum):
    """What a statement line *is*. Charges are the interesting ones."""
    DEBIT = "DEBIT"                     # ordinary customer payment / withdrawal
    CREDIT = "CREDIT"                   # ordinary inflow (salary, pension, transfer in)
    REVERSAL = "REVERSAL"               # credit that reverses an earlier debit
    ATM_WITHDRAWAL = "ATM_WITHDRAWAL"
    ATM_ENQUIRY = "ATM_ENQUIRY"         # non-financial ATM transaction
    CHARGE_ATM = "CHARGE_ATM"
    CHARGE_MIN_BAL = "CHARGE_MIN_BAL"
    CHARGE_SMS = "CHARGE_SMS"
    CHARGE_CARD_AMC = "CHARGE_CARD_AMC"
    CHARGE_CHEQUE = "CHARGE_CHEQUE"
    CHARGE_REACTIVATION = "CHARGE_REACTIVATION"
    CHARGE_OTHER = "CHARGE_OTHER"
    GST_ON_CHARGE = "GST_ON_CHARGE"
    INTEREST_CREDIT = "INTEREST_CREDIT"
    LOAN_EMI = "LOAN_EMI"
    LOAN_PENAL = "LOAN_PENAL"
    LOAN_CHARGE = "LOAN_CHARGE"
    COMPENSATION = "COMPENSATION"       # bank paid TAT compensation
    UNKNOWN = "UNKNOWN"


CHARGE_KINDS = {
    Kind.CHARGE_ATM, Kind.CHARGE_MIN_BAL, Kind.CHARGE_SMS, Kind.CHARGE_CARD_AMC,
    Kind.CHARGE_CHEQUE, Kind.CHARGE_REACTIVATION, Kind.CHARGE_OTHER, Kind.LOAN_PENAL,
    Kind.LOAN_CHARGE,
}

CUSTOMER_INITIATED_KINDS = {
    Kind.DEBIT, Kind.CREDIT, Kind.ATM_WITHDRAWAL, Kind.ATM_ENQUIRY, Kind.LOAN_EMI,
}


@dataclass
class Transaction:
    date: date
    narration: str
    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None
    ref: str = ""                      # UTR / RRN / cheque number if present
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    seq: int = 0                       # original order within the statement (stable sort key for same-day lines)
    # derived by the classifier
    channel: Channel = Channel.OTHER
    kind: Kind = Kind.UNKNOWN
    merchant: str = ""                 # normalised counterparty
    own_bank_atm: Optional[bool] = None
    failed_hint: bool = False          # narration says FAILED / DECLINED / TIMEOUT
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def amount(self) -> float:
        return self.debit if self.debit else self.credit

    @property
    def is_debit(self) -> bool:
        return self.debit > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "seq": self.seq, "date": self.date.isoformat(), "narration": self.narration,
            "debit": self.debit, "credit": self.credit, "balance": self.balance, "ref": self.ref,
            "channel": self.channel.value, "kind": self.kind.value, "merchant": self.merchant,
            "own_bank_atm": self.own_bank_atm, "failed_hint": self.failed_hint,
        }


# --------------------------------------------------------------------------- #
# Account profile — the facts a statement cannot tell us
# --------------------------------------------------------------------------- #
class AccountType(str, Enum):
    SAVINGS = "SAVINGS"
    SALARY = "SALARY"
    BSBDA = "BSBDA"          # Basic Savings Bank Deposit Account
    PENSION = "PENSION"
    CURRENT = "CURRENT"


class CityTier(str, Enum):
    METRO = "METRO"          # Mumbai, Delhi, Chennai, Kolkata, Bengaluru, Hyderabad
    NON_METRO = "NON_METRO"


@dataclass
class AccountProfile:
    bank: str = ""
    account_type: AccountType = AccountType.SAVINGS
    city_tier: CityTier = CityTier.NON_METRO
    min_balance_required: Optional[float] = None
    language: str = "ta"
    holder_name: str = ""
    account_last4: str = ""
    holder_phone: str = ""     # E.164 (+91...) — where the Tamil voice call goes

    def to_dict(self) -> dict[str, Any]:
        return {
            "bank": self.bank, "account_type": self.account_type.value, "city_tier": self.city_tier.value,
            "min_balance_required": self.min_balance_required, "language": self.language,
            "holder_name": self.holder_name, "account_last4": self.account_last4, "holder_phone": self.holder_phone,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AccountProfile":
        return cls(
            bank=d.get("bank", ""),
            account_type=AccountType(d.get("account_type", "SAVINGS")),
            city_tier=CityTier(d.get("city_tier", "NON_METRO")),
            min_balance_required=d.get("min_balance_required"),
            language=d.get("language", "ta"),
            holder_name=d.get("holder_name", ""),
            account_last4=d.get("account_last4", ""),
            holder_phone=d.get("holder_phone", ""),
        )


# --------------------------------------------------------------------------- #
# Findings — the output of the twin
# --------------------------------------------------------------------------- #
class Label(str, Enum):
    RECOVERABLE = "RECOVERABLE"   # 🔴 rule broken, money claimable
    AVOIDABLE = "AVOIDABLE"       # 🟡 legal but preventable
    UNCLEAR = "UNCLEAR"           # ⚪ needs a fact we don't have


class Confidence(str, Enum):
    CONFIRMED = "CONFIRMED"
    NEEDS_CHECKING = "NEEDS_CHECKING"
    INFO = "INFO"


class Priority(str, Enum):
    RECOVER_NOW = "RECOVER_NOW"
    COMBINE = "COMBINE"
    NOT_WORTH_IT = "NOT_WORTH_IT"
    PREVENT = "PREVENT"


@dataclass
class Question:
    id: str
    text_en: str
    text_ta: str
    options: list[str] = field(default_factory=list)
    qtype: str = "choice"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "en": self.text_en, "ta": self.text_ta, "options": self.options, "type": self.qtype}


@dataclass
class Finding:
    rule_id: str
    label: Label
    confidence: Confidence
    amount: float                          # rupees potentially recoverable (0 for prevent/info)
    evidence: list[str]                    # transaction ids
    calculation: str                       # human-readable arithmetic
    expected: str                          # what should have happened
    actual: str                            # what did happen
    summary_en: str
    summary_ta: str
    questions: list[Question] = field(default_factory=list)
    prevention_en: str = ""
    prevention_ta: str = ""
    priority: Priority = Priority.COMBINE
    priority_score: float = 0.0
    priority_reasons: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: "f_" + uuid.uuid4().hex[:8])
    group_key: str = ""                    # findings with the same key can be combined
    occurred_on: Optional[date] = None
    twin: dict[str, Any] = field(default_factory=dict)   # structured actual-vs-expected data for the Twin View
    act_by: Optional[date] = None          # last sensible day to raise this with the bank (limitation clock)
    days_left: Optional[int] = None        # act_by - as_of
    alert: bool = False                    # inside the red-alert window → promoted whatever the amount
    alert_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "rule_id": self.rule_id, "label": self.label.value, "twin": self.twin,
            "confidence": self.confidence.value, "amount": round(self.amount, 2),
            "evidence": self.evidence, "calculation": self.calculation,
            "expected": self.expected, "actual": self.actual,
            "summary_en": self.summary_en, "summary_ta": self.summary_ta,
            "questions": [q.to_dict() for q in self.questions],
            "prevention_en": self.prevention_en, "prevention_ta": self.prevention_ta,
            "priority": self.priority.value, "priority_score": round(self.priority_score, 3),
            "priority_reasons": self.priority_reasons, "group_key": self.group_key,
            "occurred_on": self.occurred_on.isoformat() if self.occurred_on else None,
            "act_by": self.act_by.isoformat() if self.act_by else None, "days_left": self.days_left, "alert": self.alert, "alert_reason": self.alert_reason,
        }


# --------------------------------------------------------------------------- #
# Cases — the recovery state machine
# --------------------------------------------------------------------------- #
class CaseState(str, Enum):
    FOUND = "FOUND"
    PREPARED = "PREPARED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SENT_TO_BANK = "SENT_TO_BANK"
    BANK_REPLIED = "BANK_REPLIED"
    DEADLINE_PASSED = "DEADLINE_PASSED"
    ESCALATED_OMBUDSMAN = "ESCALATED_OMBUDSMAN"
    RECOVERED = "RECOVERED"
    CLOSED_BANK_RIGHT = "CLOSED_BANK_RIGHT"
    CLOSED_BY_USER = "CLOSED_BY_USER"


@dataclass
class CaseEvent:
    at: datetime
    state: CaseState
    note: str = ""
    actor: str = "system"

    def to_dict(self) -> dict[str, Any]:
        return {"at": self.at.isoformat(timespec="seconds"), "state": self.state.value, "note": self.note, "actor": self.actor}


@dataclass
class Case:
    account_id: str
    finding_ids: list[str]
    amount: float
    rule_ids: list[str]
    state: CaseState = CaseState.FOUND
    events: list[CaseEvent] = field(default_factory=list)
    sent_on: Optional[date] = None
    bank_reply_due: Optional[date] = None
    ombudsman_deadline: Optional[date] = None
    complaint_text: str = ""
    ombudsman_text: str = ""
    guardian_approved_by: str = ""
    id: str = field(default_factory=lambda: "VR-" + uuid.uuid4().hex[:6].upper())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "account_id": self.account_id, "finding_ids": self.finding_ids,
            "amount": round(self.amount, 2), "rule_ids": self.rule_ids, "state": self.state.value,
            "events": [e.to_dict() for e in self.events],
            "sent_on": self.sent_on.isoformat() if self.sent_on else None,
            "bank_reply_due": self.bank_reply_due.isoformat() if self.bank_reply_due else None,
            "ombudsman_deadline": self.ombudsman_deadline.isoformat() if self.ombudsman_deadline else None,
            "complaint_text": self.complaint_text, "ombudsman_text": self.ombudsman_text,
            "guardian_approved_by": self.guardian_approved_by,
        }


# --------------------------------------------------------------------------- #
# Guardian
# --------------------------------------------------------------------------- #
@dataclass
class Guardian:
    name: str
    relation: str          # son / daughter / spouse / trusted
    phone: str
    language: str = "ta"
    consent_recorded_at: Optional[datetime] = None
    consent_note: str = ""  # e.g. transcript / file ref of the holder's voice consent
    email: str = ""         # where the real one-button message goes (WhatsApp/SMS adapters come later)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "relation": self.relation, "phone": self.phone, "language": self.language, "email": self.email,
            "consent_recorded_at": self.consent_recorded_at.isoformat(timespec="seconds") if self.consent_recorded_at else None,
            "consent_note": self.consent_note,
        }
