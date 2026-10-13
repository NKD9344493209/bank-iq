"""Real outbound voice call (Twilio) — the Tamil call that reaches the account holder first.

Off unless configured in `.env`:

    VASOOL_TWILIO_SID=ACxxxxxxxx
    VASOOL_TWILIO_TOKEN=xxxxxxxx
    VASOOL_TWILIO_FROM=+1xxxxxxxxxx      # the Twilio number the call comes from
    VASOOL_DEMO_PHONE=+91xxxxxxxxxx     # SAFETY: when set, EVERY call goes to this number
    VASOOL_TWILIO_TWIML_URL=            # optional: your own TwiML Bin URL with a {{text}} placeholder

Trial accounts: Twilio's free trial rejects the inline `Twiml` parameter ("trial accounts have
limited parameter access"). We then retry with a `Url` — the Twilio-hosted echo twimlet, which
simply returns the TwiML we put in the query string — so the demo works on a trial account
with zero extra setup. A paid account uses inline TwiML directly.

Safety rules
* A Twilio trial can only dial verified numbers, and VASOOL_DEMO_PHONE overrides every recipient
  anyway — the demo cannot ring a stranger.
* No dependency: the REST API is one HTTPS POST with Basic auth, so nothing new to install.
* Every call (or skip) is returned as a plain dict for the notification log; never raises.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional
from xml.sax.saxutils import escape

from . import notify  # ensures .env is loaded

VOICES = {"ta": ("Google.ta-IN-Standard-A", "ta-IN"), "en": ("Google.en-IN-Standard-A", "en-IN")}


@dataclass
class VoiceConfig:
    sid: str = ""
    token: str = ""
    sender: str = ""
    demo_phone: str = ""
    twiml_url: str = ""

    @classmethod
    def from_env(cls) -> "VoiceConfig":
        return cls(sid=os.getenv("VASOOL_TWILIO_SID", "").strip(), token=os.getenv("VASOOL_TWILIO_TOKEN", "").strip(),
                   sender=os.getenv("VASOOL_TWILIO_FROM", "").replace(" ", ""), demo_phone=os.getenv("VASOOL_DEMO_PHONE", "").replace(" ", ""),
                   twiml_url=os.getenv("VASOOL_TWILIO_TWIML_URL", "").strip())

    @property
    def enabled(self) -> bool:
        return bool(self.sid and self.token and self.sender)

    def status(self) -> dict:
        return {"voice": self.enabled, "from": self.sender if self.enabled else "", "demo_phone": self.demo_phone}


ECHO = "https://twimlets.com/echo"   # Twilio-hosted: returns whatever TwiML is in ?Twiml=


def twiml(text: str, lang: str = "ta", repeat: int = 2) -> str:
    """The call: a short pause (so the trial preamble finishes), the script, repeated."""
    voice, language = VOICES.get(lang, VOICES["ta"])
    say = f'<Say voice="{voice}" language="{language}">{escape(text)}</Say>'
    return "<Response>" + '<Pause length="1"/>'.join([say] * max(1, repeat)) + "</Response>"


def twiml_url(text: str, lang: str = "ta", custom: str = "") -> str:
    """A URL Twilio can fetch for the call's TwiML — a user's TwiML Bin ({{text}} template) or the echo twimlet."""
    if custom:
        voice, language = VOICES.get(lang, VOICES["ta"])
        sep = "&" if "?" in custom else "?"
        return custom + sep + urllib.parse.urlencode({"text": text, "voice": voice, "language": language})
    return ECHO + "?" + urllib.parse.urlencode({"Twiml": twiml(text, lang, repeat=1)})


class TwilioChannel:
    def __init__(self, cfg: Optional[VoiceConfig] = None):
        self.cfg = cfg or VoiceConfig.from_env()

    def call(self, to: str, text: str, lang: str = "ta", kind: str = "voice_real") -> dict:
        cfg = self.cfg
        actual_to = cfg.demo_phone or (to or "").replace(" ", "")
        base = {"kind": kind, "requested_to": to, "to": actual_to, "lang": lang, "text": text}
        if not cfg.enabled:
            return base | {"placed": False, "simulated": True, "reason": "voice not configured (set VASOOL_TWILIO_SID / TOKEN / FROM in .env)"}
        if not actual_to.startswith("+"):
            return base | {"placed": False, "simulated": True, "reason": "phone number must be in +91xxxxxxxxxx form"}
        # A TwiML Bin, when given, is used first; otherwise inline TwiML, falling back to the hosted
        # echo URL when Twilio says the account is a trial.
        attempts = ([{"Url": twiml_url(text, lang, cfg.twiml_url)}] if cfg.twiml_url else
                    [{"Twiml": twiml(text, lang)}, {"Url": twiml_url(text, lang)}])
        last = ""
        for i, extra in enumerate(attempts):
            ok, result = self._post(cfg, {"To": actual_to, "From": cfg.sender} | extra)
            if ok:
                return base | {"placed": True, "simulated": False, "call_sid": result.get("sid"), "status": result.get("status"),
                               "via": "url" if "Url" in extra else "twiml"}
            last = result
            if "trial" not in last.lower() and i == 0 and len(attempts) > 1:
                break  # a real error (bad number, auth…) — no point retrying another way
        return base | {"placed": False, "simulated": True, "reason": last}

    def _post(self, cfg: VoiceConfig, params: dict) -> tuple[bool, object]:
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{cfg.sid}/Calls.json", data=data, method="POST")
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{cfg.sid}:{cfg.token}".encode()).decode())
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return True, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode()).get("message", str(e))
            except Exception:
                msg = str(e)
            return False, f"Twilio {e.code}: {msg}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
