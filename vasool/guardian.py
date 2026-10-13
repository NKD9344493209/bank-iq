"""Guardian (காப்பாளர்) — the human layer.

Two messages, in this order, always:
  1. a short voice call to the account holder, in their language
  2. a minimum-information message to the guardian with one action

Nothing is filed until a human taps. The guardian never sees balances,
salary, or other transactions — only: an issue exists, the amount, the rule,
approve or not.

Channel adapters are pluggable. The default `ConsoleChannel` prints; a
`TwilioChannel` would implement the same two methods with real calls/WhatsApp.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .models import Case, Finding, Guardian
from .rules.base import inr


@dataclass
class VoiceScript:
    language: str
    text: str
    ivr_options: dict[str, str]


@dataclass
class GuardianMessage:
    to: str
    text: str
    approve_token: str


def _case_findings(case: Case, findings: list[Finding] | None) -> list[Finding]:
    fs = [f for f in (findings or []) if f.id in set(case.finding_ids)] if case else []
    return sorted(fs, key=lambda f: -f.amount)


def _rule(rule_id: str):
    try:
        from . import rulebook as rb
        return rb.load().get(rule_id)
    except Exception:
        return None


def _spoken_items(fs: list[Finding], lang: str, limit: int = 2) -> list[str]:
    """One spoken sentence per finding — what happened, on which date, how much (kept short: a phone call)."""
    out = [(f.summary_ta if lang == "ta" else f.summary_en).strip() for f in fs[:limit]]
    if len(fs) > limit:
        out.append(f"இன்னும் {len(fs) - limit} item இருக்கு." if lang == "ta" else f"And {len(fs) - limit} more item(s).")
    return out


def holder_voice_script(amount: float, guardian: Guardian | None, lang: str = "ta", holder_name: str = "", bank: str = "",
                        case: Case | None = None, findings: list[Finding] | None = None) -> VoiceScript:
    """The Tamil call to the account holder: what happened, how much, which rule, what happens next.

    Spoken by a real phone call (no key-press menu — Twilio's <Say> cannot listen), so every
    sentence carries information: date, amount, the RBI rule in plain words, and the one fact
    that matters most — nothing is sent to the bank until the guardian (or the holder) says OK."""
    gname = guardian.name if guardian else None
    fs = _case_findings(case, findings)
    items = _spoken_items(fs, lang)
    bank_word = f"{bank} " if bank else ""
    name = holder_name.split()[0] if holder_name else ""
    if lang == "ta":
        hello = f"வணக்கம் {name}." if name else "வணக்கம்."
        opening = (f"{hello} Bank IQ பேசுறோம். உங்க {bank_word}bank statement-ஐ RBI rules வெச்சு check பண்ணோம். "
                   f"மொத்தம் {inr(amount)} bank உங்களுக்கு திரும்ப தரணும்-னு தெரியுது.")
        details = " ".join(items) if items else ""
        if gname:
            nxt = (f"இதை திரும்ப வாங்க complaint தயாரா இருக்கு. {gname}-க்கு ஒரு message போகும். {gname} OK சொன்னா மட்டும் bank-க்கு போகும். "
                   f"நீங்க எதுவும் பண்ண வேண்டாம். நாங்க பாத்துக்கறோம்.")
            opts = {"1": f"call_guardian:{guardian.phone}", "2": "dismiss"}
        else:
            nxt = "இதை திரும்ப வாங்க complaint தயாரா இருக்கு. நீங்க OK சொன்னா மட்டும் bank-க்கு போகும். நாங்க பாத்துக்கறோம்."
            opts = {"2": "nearest_help_centre", "3": "repeat"}
        text = f"{opening} {details} {nxt}".replace("  ", " ").strip()
    else:
        hello = f"Hello {name}." if name else "Hello."
        opening = (f"{hello} This is Bank IQ. We checked your {bank_word}bank statement against the RBI rules. "
                   f"It looks like the bank owes you {inr(amount)} in total.")
        details = " ".join(items) if items else ""
        if gname:
            nxt = (f"A complaint is ready to get it back. {gname} will get one message with one button. Nothing goes to the bank until {gname} says OK. "
                   f"You don't have to do anything. We are watching this for you.")
            opts = {"1": f"call_guardian:{guardian.phone}", "2": "dismiss"}
        else:
            nxt = "A complaint is ready to get it back. Nothing goes to the bank until you say OK. We are watching this for you."
            opts = {"2": "nearest_help_centre", "3": "repeat"}
        text = f"{opening} {details} {nxt}".replace("  ", " ").strip()
    return VoiceScript(language=lang, text=text, ivr_options=opts)


def guardian_message(case: Case, findings: list[Finding], guardian: Guardian, holder_name: str, approve_token: str, lang: str = "ta") -> GuardianMessage:
    """The one message to the guardian: each item on its own line (date · what · amount · rule), the total,
    what the complaint asks for, and the one action. Still minimum-information: only the evidence lines —
    never the balance, never the rest of the spending."""
    fs = _case_findings(case, findings)
    who = holder_name or ("account holder" if lang != "ta" else "account holder")
    lines = []
    for i, f in enumerate(fs, 1):
        r = _rule(f.rule_id)
        cite = r.source.get("circular", f.rule_id).split(" ")[0] if r and r.source else f.rule_id
        summary = f.summary_ta if lang == "ta" else f.summary_en
        lines.append(f"{i}. {summary} ({cite}) — {inr(f.amount)}")
    body = "\n".join(lines)
    if lang == "ta":
        text = (f"Bank IQ: {who}-ஓட bank account-ல {len(fs)} பிரச்சனை கண்டுபிடிச்சோம். மொத்தம் {inr(case.amount)} bank திரும்ப தரணும்.\n\n"
                f"{body}\n\n"
                f"Complaint தயார் — ஒவ்வொரு item-க்கும் RBI rule, கணக்கு, statement line attach ஆயிருக்கு. Bank 30 நாளுக்குள்ள பதில் சொல்லணும்; இல்லைன்னா RBI Ombudsman.\n"
                f"நீங்க OK சொன்னா மட்டும் bank-க்கு போகும். OK code: {approve_token}\n\n"
                f"({who}-க்கு முதல்ல phone பண்ணி சொல்லிட்டோம். Balance, மத்த செலவு விவரம் எதுவும் இதுல இல்ல.)")
    else:
        text = (f"Bank IQ: we found {len(fs)} issue(s) on {who}'s bank account. The bank owes {inr(case.amount)} in total.\n\n"
                f"{body}\n\n"
                f"A complaint is ready — each item carries the RBI rule, the arithmetic and the statement line. The bank must reply within 30 days, else RBI Ombudsman.\n"
                f"Nothing goes to the bank until you say OK. OK code: {approve_token}\n\n"
                f"({who} was called first. No balance or other spending details are in this message.)")
    return GuardianMessage(to=guardian.phone, text=text, approve_token=approve_token)


class Channel(Protocol):
    def call(self, to: str, script: VoiceScript) -> str: ...
    def message(self, msg: GuardianMessage) -> str: ...


class ConsoleChannel:
    """Default adapter: logs instead of dialling. Swap for Twilio/Exotel in production."""

    def __init__(self):
        self.log: list[dict] = []

    def call(self, to: str, script: VoiceScript) -> str:
        entry = {"kind": "voice", "to": to, "lang": script.language, "text": script.text, "options": script.ivr_options, "at": datetime.now().isoformat(timespec="seconds")}
        self.log.append(entry)
        return f"voice:{len(self.log)}"

    def message(self, msg: GuardianMessage) -> str:
        entry = {"kind": "whatsapp", "to": msg.to, "text": msg.text, "at": datetime.now().isoformat(timespec="seconds")}
        self.log.append(entry)
        return f"msg:{len(self.log)}"


def record_consent(guardian: Guardian, transcript: str) -> Guardian:
    guardian.consent_recorded_at = datetime.now()
    guardian.consent_note = transcript
    return guardian
