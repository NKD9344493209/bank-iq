"""Red alerts — when a claim is about to run out of time, the app does not wait for it to be "worth it".

Delivery: a Telegram bot (one HTTPS POST, no SDK). Off unless configured in `.env`:

    VASOOL_TELEGRAM_TOKEN=123456:ABC...      # from @BotFather
    VASOOL_TELEGRAM_CHAT=987654321           # the chat id the alert goes to (your own chat with the bot)

The message is a complete, actionable notice: the statement line, what the bank did, what the RBI rule
requires (circular + date), the arithmetic, the potential claim, the act-by date, and the three steps to
take. Never the balance, never unrelated lines.  Every send (or skip) is returned as a plain dict and
logged; it never raises.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Optional

from . import notify  # noqa: F401  (loads .env)
from .models import Finding, Transaction

TELEGRAM_MAX = 4000   # Telegram hard limit is 4096 chars per message


@dataclass
class TelegramConfig:
    token: str = ""
    chat: str = ""

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        return cls(token=os.getenv("VASOOL_TELEGRAM_TOKEN", "").strip(), chat=os.getenv("VASOOL_TELEGRAM_CHAT", "").strip())

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat)

    def status(self) -> dict:
        return {"telegram": self.enabled, "telegram_chat": self.chat if self.enabled else ""}


# ----- message text ------------------------------------------------------------------------ #
def _d(d: Optional[date]) -> str:
    return d.strftime("%d %b %Y") if d else "—"


def _inr(x: float) -> str:
    return f"₹{x:,.2f}"


def _evidence_lines(f: Finding, txns: Optional[list[Transaction]], limit: int = 3) -> list[str]:
    """The statement lines behind the finding — date, narration, amount. Only those lines, nothing else."""
    if not txns:
        return []
    by_id = {t.id: t for t in txns}
    out = []
    for tid in f.evidence[:limit]:
        t = by_id.get(tid)
        if not t:
            continue
        narr = " ".join(t.narration.split())
        if len(narr) > 70:
            narr = narr[:67] + "…"
        amt = f"−{_inr(t.debit)}" if t.debit else f"+{_inr(t.credit)}"
        out.append(f"• {_d(t.date)} · {narr} · {amt}")
    if len(f.evidence) > limit:
        out.append(f"• … and {len(f.evidence) - limit} more line(s) in the evidence pack")
    return out


def alert_text(holder: str, bank: str, f: Finding, lang: str = "en", txns: Optional[list[Transaction]] = None,
               rule=None, last4: str = "", as_of: Optional[date] = None) -> str:
    """A red alert a bank customer (or their guardian) can act on without opening the app."""
    as_of = as_of or date.today()
    acct = f"{holder or 'Account holder'} · {bank or 'Bank'}" + (f" · a/c ••{last4}" if last4 else "")
    lines = _evidence_lines(f, txns)
    src = getattr(rule, "source", {}) or {}
    rule_title = getattr(rule, "title", "") or f.rule_id
    circ = src.get("circular", "")
    cdate = src.get("date", "")
    cite = " · ".join(x for x in (circ, cdate) if x)
    right = getattr(rule, "right_ta" if lang == "ta" else "right_en", "") or ""
    calc = " ".join(f.calculation.split())
    if len(calc) > 300:
        calc = calc[:297] + "…"
    open_failure = f.twin.get("kind") == "tat" and f.twin.get("reversed") is False
    per_day = f.twin.get("per_day", 100)
    claim = _inr(f.amount) if f.amount > 0 else ("needs one answer from you" if lang == "en" else "உங்க ஒரு பதில் தேவை")
    over = f.days_left is not None and f.days_left < 0

    if lang == "ta":
        head = ["🔴 VASOOL RAJA — RED ALERT", acct, ""]
        what = ["📄 என்ன நடந்தது", *lines, f.actual, ""]
        rulep = ["📜 RBI விதி என்ன சொல்லுது", f"{f.rule_id} — {rule_title}" + (f" ({cite})" if cite else ""), right or f.expected, ""]
        money = ["💰 உங்க potential claim", claim]
        if open_failure:
            money.append(f"ஒவ்வொரு நாளும் ₹{per_day:.0f} சேருது — {_d(as_of)} வரை கணக்கு.")
        if calc:
            money.append(f"கணக்கு: {calc}")
        money.append("")
        when = ["⏰ கடைசி தேதி"]
        when.append((f"{_d(f.act_by)} தாண்டிடுச்சு ({-f.days_left} நாள் முன்) — இப்பவே file பண்ணுங்க; Ombudsman இன்னும் எடுத்துக்கலாம்." if over
                     else f"{_d(f.act_by)}-க்குள்ள action வேணும் — {f.days_left} நாள் இருக்கு.") if f.act_by else "—")
        when += [f.alert_reason, ""]
        todo = ["✅ இப்ப என்ன பண்ணணும்",
                "1. Bank IQ → Findings → 'Get it back' → evidence pack print பண்ணுங்க.",
                "2. Branch-ல / bank grievance portal-ல கொடுங்க. Complaint number, தேதி எழுதி வைங்க.",
                "3. 30 நாள்ல பதில் இல்லனா / reject பண்ணா → RBI Ombudsman: cms.rbi.org.in (இலவசம்), மேல இருக்கற circular-ஐ சொல்லுங்க.", ""]
        foot = ["தொகை சின்னதுன்னு காத்திருக்க முடியாது. Potential claim — உறுதியான பணம் இல்ல; bank / Ombudsman முடிவு பண்ணுவாங்க.",
                "இந்த app எந்த bank-க்கும் எதுவும் அனுப்பல. Balance / மத்த transactions இதுல இல்ல."]
    else:
        head = ["🔴 VASOOL RAJA — RED ALERT", acct, ""]
        what = ["📄 WHAT HAPPENED", *lines, f.actual, ""]
        rulep = ["📜 WHAT THE RBI RULE SAYS", f"{f.rule_id} — {rule_title}" + (f" ({cite})" if cite else ""), right or f.expected, ""]
        money = ["💰 YOUR POTENTIAL CLAIM", claim]
        if open_failure:
            money.append(f"Grows ₹{per_day:.0f} every day the bank waits — priced as of {_d(as_of)}.")
        if calc:
            money.append(f"Calculation: {calc}")
        money.append("")
        when = ["⏰ DEADLINE"]
        when.append((f"Act-by {_d(f.act_by)} has passed ({-f.days_left} days ago) — file immediately; the Ombudsman may still admit it." if over
                     else f"Act by {_d(f.act_by)} — {f.days_left} days left.") if f.act_by else "—")
        when += [f.alert_reason, ""]
        todo = ["✅ WHAT TO DO NOW",
                "1. Open Bank IQ → Findings → 'Get it back' → print the evidence pack.",
                "2. Hand it in at the branch or the bank's grievance portal. Note the complaint number and date.",
                "3. No reply in 30 days, or rejected → RBI Ombudsman at cms.rbi.org.in (free), quoting the circular above.", ""]
        foot = ["Too small to bundle is not a reason to wait. Potential claim, not guaranteed money — the bank or the Ombudsman decides.",
                "Nothing has been sent to any bank by this app. No balance or other transactions are in this message."]
    text = "\n".join(x for x in head + what + rulep + money + when + todo + foot if x is not None)
    if len(text) > TELEGRAM_MAX:
        text = text[:TELEGRAM_MAX - 1] + "…"
    return text


# ----- delivery ---------------------------------------------------------------------------- #
class TelegramChannel:
    def __init__(self, cfg: Optional[TelegramConfig] = None):
        self.cfg = cfg or TelegramConfig.from_env()

    def send(self, text: str, kind: str = "alert_telegram") -> dict:
        cfg = self.cfg
        base = {"kind": kind, "to": cfg.chat, "text": text}
        if not cfg.enabled:
            return base | {"sent": False, "simulated": True, "reason": "telegram not configured (set VASOOL_TELEGRAM_TOKEN / VASOOL_TELEGRAM_CHAT in .env)"}
        data = urllib.parse.urlencode({"chat_id": cfg.chat, "text": text, "disable_web_page_preview": "true"}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{cfg.token}/sendMessage", data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                j = json.loads(r.read().decode())
            return base | {"sent": bool(j.get("ok")), "simulated": not j.get("ok"), "message_id": (j.get("result") or {}).get("message_id")}
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode()).get("description", str(e))
            except Exception:
                msg = str(e)
            return base | {"sent": False, "simulated": True, "reason": f"Telegram {e.code}: {msg}"}
        except Exception as e:
            return base | {"sent": False, "simulated": True, "reason": f"{type(e).__name__}: {e}"}


def send_alerts(channel: TelegramChannel, store, account_id: str, findings: list[Finding], holder: str, bank: str, lang: str = "en",
                force: bool = False, txns: Optional[list[Transaction]] = None, rulebook=None, last4: str = "", as_of: Optional[date] = None) -> list[dict]:
    """One alert per finding that has entered the red window, never twice for the same finding (unless force)."""
    already = {n.get("finding_id") for n in store.notifications(account_id) if n.get("kind") == "alert_telegram"}
    out = []
    for f in findings:
        if not f.alert or (f.id in already and not force):
            continue
        rule = None
        if rulebook is not None:
            try:
                rule = rulebook.get(f.rule_id)
            except Exception:
                rule = None
        text = alert_text(holder, bank, f, lang, txns=txns, rule=rule, last4=last4, as_of=as_of)
        r = channel.send(text) | {"finding_id": f.id, "amount": f.amount, "act_by": f.act_by.isoformat() if f.act_by else None}
        store.log_notification(account_id, r)
        out.append(r)
    return out
