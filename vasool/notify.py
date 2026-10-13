"""Real outbound email — for the guardian message and the complaint copy.

Off unless configured. Configure with a `.env` file in the repo root (or
environment variables):

    VASOOL_SMTP_USER=you@gmail.com
    VASOOL_SMTP_PASS=xxxx xxxx xxxx xxxx      # Gmail "App password", not the login password
    VASOOL_SMTP_HOST=smtp.gmail.com           # optional (default)
    VASOOL_SMTP_PORT=465                      # optional (default, SSL)
    VASOOL_DEMO_TO=teammate@gmail.com         # SAFETY: when set, EVERY mail goes here, whatever the recipient
    VASOOL_PUBLIC_URL=http://192.168.43.12:8000   # optional: lets the Approve link in the mail open the app from a phone

Safety rules, deliberately hard-coded:
* A bank grievance address is never a recipient. The complaint copy goes to
  the guardian / holder only, with a line saying where it *would* go.
* When VASOOL_DEMO_TO is set, it overrides every recipient — the demo can
  never mail a stranger.
* Every send (or skip) is returned as a plain dict so the API can log it.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny .env loader (no dependency). Forgiving on purpose: later lines override earlier
    ones (so a leftover example line above your real one does no harm), and anything after
    a `#` or `←` on the line is treated as a note. Real environment variables still win."""
    if not path.exists():
        return
    found: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        for mark in ("#", "←", "<-"):
            if mark in v:
                v = v.split(mark, 1)[0]
        k, v = k.strip().upper(), v.strip().strip('"').strip("'")
        if k.startswith("VASOOL_") or k == "ANTHROPIC_API_KEY":
            found[k] = v
    for k, v in found.items():
        if v and k not in os.environ:
            os.environ[k] = v


load_dotenv()


@dataclass
class EmailConfig:
    user: str = ""
    password: str = ""
    host: str = "smtp.gmail.com"
    port: int = 465
    sender: str = ""
    demo_to: str = ""
    public_url: str = ""

    @classmethod
    def from_env(cls) -> "EmailConfig":
        return cls(
            user=os.getenv("VASOOL_SMTP_USER", ""), password=os.getenv("VASOOL_SMTP_PASS", "").replace(" ", ""),
            host=os.getenv("VASOOL_SMTP_HOST", "smtp.gmail.com"), port=int(os.getenv("VASOOL_SMTP_PORT", "465")),
            sender=os.getenv("VASOOL_SMTP_FROM", "") or os.getenv("VASOOL_SMTP_USER", ""),
            demo_to=os.getenv("VASOOL_DEMO_TO", ""), public_url=os.getenv("VASOOL_PUBLIC_URL", "").rstrip("/"),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.user and self.password)

    def status(self) -> dict:
        return {"email": self.enabled, "from": self.sender if self.enabled else "", "demo_to": self.demo_to, "public_url": self.public_url}


class EmailChannel:
    def __init__(self, cfg: Optional[EmailConfig] = None):
        self.cfg = cfg or EmailConfig.from_env()

    def send(self, to: str, subject: str, text: str, html: Optional[str] = None, kind: str = "email") -> dict:
        cfg = self.cfg
        actual_to = cfg.demo_to or to
        base = {"kind": kind, "requested_to": to, "to": actual_to, "subject": subject}
        if not cfg.enabled:
            return base | {"sent": False, "simulated": True, "reason": "email not configured (set VASOOL_SMTP_USER / VASOOL_SMTP_PASS in .env)"}
        if not actual_to or "@" not in actual_to:
            return base | {"sent": False, "simulated": True, "reason": "no email address for the recipient"}
        msg = EmailMessage()
        msg["From"] = f"Bank IQ <{cfg.sender}>"
        msg["To"] = actual_to
        msg["Subject"] = subject
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")
        try:
            if cfg.port == 465:
                with smtplib.SMTP_SSL(cfg.host, cfg.port, context=ssl.create_default_context(), timeout=20) as s:
                    s.login(cfg.user, cfg.password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(cfg.host, cfg.port, timeout=20) as s:
                    s.starttls(context=ssl.create_default_context())
                    s.login(cfg.user, cfg.password)
                    s.send_message(msg)
            return base | {"sent": True, "simulated": False}
        except Exception as e:  # network blocked, wrong app password, etc. — never crash the flow
            return base | {"sent": False, "simulated": True, "reason": f"{type(e).__name__}: {e}"}


# --------------------------------------------------------------------------- #
# Message bodies
# --------------------------------------------------------------------------- #
def guardian_email(holder: str, guardian_name: str, amount_text: str, message_text: str, token: str, approve_url: str, lang: str) -> tuple[str, str, str]:
    """(subject, text, html) for the one-button guardian mail."""
    ta = lang == "ta"
    subject = (f"Bank IQ: {holder}-ஓட account — {amount_text} திரும்ப வாங்க உங்க OK வேணும்" if ta
               else f"Bank IQ: {holder}'s account — your OK needed to recover {amount_text}")
    btn = "✓ சரி, அனுப்பு" if ta else "✓ Yes, send the complaint"
    note = ("Balance, செலவு விவரம் எதுவும் இதுல இல்ல. Complaint bank-க்கு மட்டும் போகும்." if ta
            else "No balance or spending details are in this message. The complaint goes only to the bank.")
    text = f"{message_text}\n\n{btn}: {approve_url}\nApproval code: {token}\n\n{note}"
    html = f"""<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto;color:#18261F">
  <div style="background:#144C31;color:#fff;padding:14px 18px;border-radius:12px 12px 0 0"><b style="font-size:18px">₹ Bank IQ</b><div style="color:#9DB8A8;font-size:13px">{'நாங்க பாத்துக்கறோம்.' if ta else 'We watch. You don&#39;t have to.'}</div></div>
  <div style="border:1px solid #D7DDD6;border-top:0;padding:18px;border-radius:0 0 12px 12px">
    <p style="font-size:16px;line-height:1.5;white-space:pre-line">{_esc(message_text)}</p>
    <p style="text-align:center;margin:22px 0"><a href="{approve_url}" style="background:#C9961A;color:#144C31;text-decoration:none;font-weight:700;font-size:17px;padding:14px 26px;border-radius:10px;display:inline-block">{btn}</a></p>
    <p style="font-size:13px;color:#4E5D55">{'Approval code' if not ta else 'OK code'}: <b style="font-family:monospace;font-size:15px">{token}</b></p>
    <p style="font-size:12px;color:#4E5D55">{note}</p>
  </div></div>"""
    return subject, text, html


def complaint_copy_email(holder: str, bank: str, bank_email: str, amount_text: str, case_id: str, complaint_text: str, print_url: str, lang: str) -> tuple[str, str, str]:
    """(subject, text, html) — the complaint, as it would go to the bank, sent to a person."""
    ta = lang == "ta"
    subject = f"[Bank IQ · {case_id}] Complaint to {bank} — {amount_text}"
    where = (f"இந்த complaint bank-க்கு போகும் address: {bank_email or '(bank grievance cell)'}. Demo-ல நேரடியா bank-க்கு அனுப்பல; இது உங்க copy." if ta
             else f"This complaint is addressed to {bank} ({bank_email or 'grievance cell'}). In this demo it is NOT sent to the bank — this is your copy.")
    text = f"{where}\n\nPrint / PDF: {print_url}\n\n{complaint_text}"
    html = f"""<div style="font-family:system-ui,sans-serif;max-width:640px;margin:auto;color:#18261F">
  <div style="background:#144C31;color:#fff;padding:14px 18px;border-radius:12px 12px 0 0"><b style="font-size:18px">₹ Bank IQ</b> · {case_id}</div>
  <div style="border:1px solid #D7DDD6;border-top:0;padding:18px;border-radius:0 0 12px 12px">
    <p style="background:#F6EDD3;padding:10px 12px;border-radius:8px;font-size:14px">{where}</p>
    <p><a href="{print_url}" style="background:#1E6A44;color:#fff;text-decoration:none;font-weight:600;padding:10px 16px;border-radius:8px;display:inline-block">🖨 {'Print / PDF' if not ta else 'Print / PDF எடு'}</a></p>
    <pre style="white-space:pre-wrap;font-family:Cambria,Georgia,serif;font-size:14px;line-height:1.5;background:#F5F7F2;padding:14px;border-radius:8px">{_esc(complaint_text)}</pre>
  </div></div>"""
    return subject, text, html


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
