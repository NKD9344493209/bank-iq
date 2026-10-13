"""Bank IQ HTTP API (FastAPI).

Run:  uvicorn api.main:app --reload
Docs: http://localhost:8000/docs

Design notes
* Every endpoint that changes state writes an audit row.
* Nothing is ever "sent" without an explicit human action (approve/send).
* Statements are parsed in memory; only normalised transactions are stored.
  Set VASOOL_DB to choose the SQLite path (default data/vasool.db).
"""
from __future__ import annotations

import contextvars
import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from vasool import __version__, alerts, cases as case_mod, complaint, crypto, explain, guardian as guardian_mod, merge, notify, printable, rulebook as rb_mod, scan, twin as twin_mod, voice
from vasool.assistant import Assistant
from vasool.models import AccountProfile, AccountType, Case, CaseState, CityTier, Finding, Guardian, Label, Transaction
from vasool.rules.user_claims import card_closure_claim, gold_release_claim, unauthorised_txn_claim
from vasool.store import Store

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "static"

app = FastAPI(title="Bank IQ API", version=__version__, description="A Regulatory Digital Twin for Indian bank customers. The rule engine decides; AI only explains.")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("VASOOL_CORS", "*").split(","), allow_methods=["*"], allow_headers=["*"])

ALLOWED_UPLOAD_EXT = {".pdf", ".csv", ".tsv", ".txt", ".xlsx", ".xls", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


CURRENT_USER: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("vasool_user", default=None)
AUTH_ON = os.getenv("VASOOL_AUTH", "on").lower() not in ("off", "0", "false", "no")
PUBLIC_PREFIXES = ("/api/health", "/api/rules", "/api/scope", "/api/validation", "/api/samples", "/api/auth/", "/api/approvals/", "/api/ask", "/api/claims/", "/api/ml/")
SESSION_COOKIE = "vr_session"


def _user_from_request(request: Request) -> Optional[dict]:
    if not AUTH_ON:
        return {"id": "local", "login": "local", "name": "Local user"}
    return store().user_for_session(request.cookies.get(SESSION_COOKIE, ""))


@app.middleware("http")
async def require_session(request: Request, call_next):
    """Every account-scoped API needs a logged-in user. Public: health, rules, scope, samples, auth, approval links."""
    path = request.url.path
    user = _user_from_request(request)
    token = CURRENT_USER.set(user)
    try:
        if path.startswith("/api/") and not path.startswith(PUBLIC_PREFIXES) and user is None:
            return JSONResponse({"detail": "login required"}, status_code=401)
        return await call_next(request)
    finally:
        CURRENT_USER.reset(token)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Defensive defaults for a fintech surface: no sniffing, no framing, no referrer leakage, no caching of API JSON."""
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
    if request.url.path.startswith("/api/"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp

_store: Optional[Store] = None
_channel = guardian_mod.ConsoleChannel()
_email = notify.EmailChannel()
_voice = voice.TwilioChannel()
_telegram = alerts.TelegramChannel()


def _public_url(request: Request) -> str:
    return _email.cfg.public_url or str(request.base_url).rstrip("/")


def _send_complaint_copy(c: Case, acct: dict[str, Any], request: Request) -> dict[str, Any]:
    """Email the complaint to a person (guardian/holder) — never to the bank. Logged either way."""
    prof: AccountProfile = acct["profile"]
    g = store().get_guardian(c.account_id)
    to = (g.email if g and g.email else "") or _email.cfg.demo_to
    amount = f"₹{c.amount:,.2f}"
    subject, text, html = notify.complaint_copy_email(prof.holder_name or "the account holder", prof.bank or "the bank",
                                                      complaint.BANK_GRIEVANCE_EMAIL.get((prof.bank or "").upper(), ""), amount, c.id, c.complaint_text,
                                                      f"{_public_url(request)}/api/cases/{c.id}/complaint.html?lang={prof.language}", prof.language)
    r = _email.send(to, subject, text, html, kind="email_complaint_copy")
    store().log_notification(c.account_id, r | {"case_id": c.id})
    return r


def store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def rb():
    return rb_mod.load()


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class ProfileIn(BaseModel):
    bank: str = ""
    account_type: str = "SAVINGS"
    city_tier: str = "NON_METRO"
    min_balance_required: Optional[float] = None
    language: str = "ta"
    holder_name: str = ""
    account_last4: str = ""
    holder_phone: str = ""

    def to_model(self) -> AccountProfile:
        return AccountProfile(bank=self.bank.upper(), account_type=AccountType(self.account_type), city_tier=CityTier(self.city_tier),
                              min_balance_required=self.min_balance_required, language=self.language, holder_name=self.holder_name, account_last4=self.account_last4,
                              holder_phone=self.holder_phone.replace(" ", ""))


class AnswersIn(BaseModel):
    answers: dict[str, Any]


class CaseIn(BaseModel):
    finding_ids: Optional[list[str]] = None   # default: all RECOVERABLE findings with priority RECOVER_NOW/COMBINE


class EventIn(BaseModel):
    state: str
    note: str = ""
    actor: str = "user"


class GuardianIn(BaseModel):
    name: str
    relation: str
    phone: str
    language: str = "ta"
    consent_transcript: str = ""
    email: str = ""


class TestMailIn(BaseModel):
    to: str = ""


class TestCallIn(BaseModel):
    to: str = ""
    lang: str = "ta"


class AsOfIn(BaseModel):
    as_of: date


class AskIn(BaseModel):
    question: str
    lang: Optional[str] = None


class CardClosureIn(BaseModel):
    request_date: date
    closure_date: Optional[date] = None
    dues_cleared: bool = True
    as_of: Optional[date] = None


class UnauthorisedIn(BaseModel):
    txn_date: date
    amount: float
    reported_on: date
    credited_on: Optional[date] = None
    as_of: Optional[date] = None


class GoldIn(BaseModel):
    repaid_on: date
    released_on: Optional[date] = None
    as_of: Optional[date] = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _uid() -> Optional[str]:
    u = CURRENT_USER.get()
    return u["id"] if u else None


def _case(case_id: str):
    c = store().get_case(case_id)
    if not c:
        raise HTTPException(404, "case not found")
    _load(c.account_id)     # ownership check
    return c


def _load(account_id: str, check_owner: bool = True) -> dict[str, Any]:
    acct = store().get_account(account_id)
    if not acct:
        raise HTTPException(404, "account not found")
    if check_owner and AUTH_ON and acct.get("user_id") not in (None, _uid()):
        raise HTTPException(404, "account not found")   # never confirm another user's account exists
    return acct


def _result_payload(account_id: str, res: scan.ScanResult) -> dict[str, Any]:
    d = res.to_dict()
    d["account_id"] = account_id
    d["cases"] = [c.to_dict() | {"status_text": case_mod.user_status(c, res.profile.language), "days_left": case_mod.days_left(c)} for c in store().list_cases(account_id)]
    g = store().get_guardian(account_id)
    d["guardian"] = g.to_dict() if g else None
    stmts = store().list_statements(account_id)
    cov = merge.coverage([(date.fromisoformat(x["period_from"]) if x["period_from"] else None, date.fromisoformat(x["period_to"]) if x["period_to"] else None) for x in stmts])
    d["statements"] = [{k: v for k, v in x.items() if k != "txn_ids"} for x in stmts]
    d["coverage"] = cov.to_dict()
    acct = store().get_account(account_id)
    d["account_answers"] = acct["answers"] if acct else {}
    d["as_of"] = acct["as_of"].isoformat() if acct else None
    d["alerts"] = alerts.send_alerts(_telegram, store(), account_id, res.findings, res.profile.holder_name, res.profile.bank or "", res.profile.language,
                                     txns=res.transactions, rulebook=rb(), last4=res.profile.account_last4, as_of=res.as_of)
    d["alert_days"] = __import__("vasool.priority", fromlist=["ALERT_DAYS"]).ALERT_DAYS
    if cov.gaps:
        d["summary"]["warnings"] = list(d["summary"].get("warnings", [])) + [
            f"No statement covers {a.isoformat()} → {b.isoformat()}. Rules that count by month (ATM, minimum balance) are judged only on the months we can see." for a, b in cov.gaps]
    return d


def _ingest(account_id: Optional[str], data: bytes, filename: str, prof: AccountProfile, as_of_d: Optional[date]) -> tuple[str, scan.ScanResult, dict[str, Any]]:
    """Parse one file and either create an account or merge into an existing one.
    Returns (account_id, result over the merged history, per-file upload report)."""
    acct = store().get_account(account_id) if account_id else None
    if account_id and not acct:
        raise HTTPException(404, "account not found")
    try:
        res = scan.scan_bytes(data, filename, prof if not acct else AccountProfile(bank=acct["profile"].bank), as_of=as_of_d or (acct["as_of"] if acct else None))
    except ValueError as e:
        raise HTTPException(422, {"message": str(e), "warnings": []})
    except Exception as e:  # a parser crash must never reach the user as "Internal Server Error"
        import traceback
        traceback.print_exc()
        raise HTTPException(422, {"message": f"We couldn't read {filename} ({type(e).__name__}). Your data has not been used. Try a clearer photo (flat page, good light) or upload PDF/CSV.", "warnings": [str(e)[:200]]})
    if not res.transactions:
        raise HTTPException(422, {"message": f"We couldn't find any transaction lines in {filename}. Try a clearer photo (flat page, good light, whole table in frame) or upload PDF/CSV.", "warnings": res.parse.warnings})
    period = (res.parse.period_from, res.parse.period_to)
    if not acct:
        as_of_d = as_of_d or date.today()
        meta = {"source_kind": res.parse.source_kind, "filename": filename, "warnings": res.parse.warnings,
                "period_from": period[0].isoformat() if period[0] else None, "period_to": period[1].isoformat() if period[1] else None}
        account_id = store().save_account(None, res.profile, res.transactions, {}, meta, as_of_d, user_id=_uid())
        store().replace_findings(account_id, res.findings)
        store().add_statement(account_id, filename, res.parse.source_kind, period[0], period[1], len(res.transactions), len(res.transactions), 0, [t.id for t in res.transactions], res.parse.warnings)
        store().audit(account_id, "scan", f"{filename} · {len(res.transactions)} txns · {len(res.findings)} findings")
        return account_id, res, {"filename": filename, "new": len(res.transactions), "duplicates": 0, "period_from": meta["period_from"], "period_to": meta["period_to"], "warnings": res.parse.warnings, "created": True}
    # ---- append to an existing account: refuse an obviously different account
    prof0: AccountProfile = acct["profile"]
    same_last4 = bool(res.parse.account_last4 and prof0.account_last4 and res.parse.account_last4 == prof0.account_last4)
    if res.parse.account_last4 and prof0.account_last4 and not same_last4:
        raise HTTPException(409, {"message": f"{filename} is for an account ending {res.parse.account_last4}; this one ends {prof0.account_last4}. Start a new scan for it instead.", "code": "account_mismatch"})
    if not same_last4 and res.parse.detected_bank and prof0.bank and res.parse.detected_bank.upper() != prof0.bank.upper():
        raise HTTPException(409, {"message": f"{filename} looks like a {res.parse.detected_bank} statement but this account is {prof0.bank}. Start a new scan for it instead.", "code": "bank_mismatch"})
    m = merge.merge_transactions(acct["transactions"], res.transactions)
    if not prof0.account_last4 and res.parse.account_last4:
        prof0.account_last4 = res.parse.account_last4
        store().update_profile(account_id, prof0)
    new_as_of = as_of_d or acct["as_of"]
    store().update_transactions(account_id, m.transactions, as_of=new_as_of)
    store().add_statement(account_id, filename, res.parse.source_kind, period[0], period[1], len(res.transactions), len(m.added), m.duplicates, [t.id for t in m.added], res.parse.warnings + m.warnings)
    full = scan.rescan(m.transactions, prof0, new_as_of, acct["answers"])
    store().replace_findings(account_id, full.findings)
    store().audit(account_id, "scan.append", f"{filename} · +{len(m.added)} new · {m.duplicates} duplicate · {len(full.findings)} findings")
    return account_id, full, {"filename": filename, "new": len(m.added), "duplicates": m.duplicates, "period_from": period[0].isoformat() if period[0] else None, "period_to": period[1].isoformat() if period[1] else None, "warnings": res.parse.warnings + m.warnings, "created": False}


def _rescan_and_save(account_id: str, acct: dict[str, Any]) -> scan.ScanResult:
    res = scan.rescan(acct["transactions"], acct["profile"], acct["as_of"], acct["answers"])
    store().replace_findings(account_id, res.findings)
    return res


# --------------------------------------------------------------------------- #
# Health / rules
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"ok": True, "version": __version__, "rulebook": rb().version, "rules": len(rb().all()), "notify": _email.cfg.status() | _voice.cfg.status() | _telegram.cfg.status()}


def _sample_alert() -> tuple[Finding, list[Transaction], AccountProfile, date, str]:
    """The finding a test alert should show: the most urgent one from this user's own accounts;
    otherwise the open UPI failure in the bundled demo statement (always urgent — ₹100/day)."""
    best = None
    for a in store().list_accounts(_uid() if AUTH_ON else None):
        acct = store().get_account(a["id"])
        if not acct:
            continue
        for f in store().get_findings(a["id"]):
            if f.amount <= 0 and not f.alert:
                continue
            key = (f.alert, f.days_left is not None and f.days_left < 0, f.amount)
            if best is None or key > best[0]:
                best = (key, f, acct["transactions"], acct["profile"], acct["as_of"], "your account")
    if best:
        return best[1:]
    prof = AccountProfile(bank="CANARA", min_balance_required=500, holder_name="Selvi R", language="en")
    res = scan.scan_file(str(ROOT / "data" / "samples" / "canara_amma_pension_2026.csv"), prof, as_of=date.today())
    f = next((x for x in res.findings if x.alert), None) or max(res.findings, key=lambda x: x.amount)
    return f, res.transactions, res.profile, res.as_of, "demonstration data"


@app.post("/api/notify/test-alert")
def notify_test_alert():
    """Send a real-looking red alert to the configured Telegram chat, built from a real finding."""
    f, txns, prof, as_of, src = _sample_alert()
    body = alerts.alert_text(prof.holder_name, prof.bank or "", f, prof.language or "en", txns=txns, rule=rb().get(f.rule_id), last4=prof.account_last4, as_of=as_of)
    text = f"🧪 TEST ALERT — this is exactly what a red alert looks like ({src}).\n\n{body}"
    return _telegram.send(text, kind="alert_test") | {"finding_id": f.id, "source": src}


@app.post("/api/notify/test-call")
def notify_test_call(body: TestCallIn):
    """Place a real test call so the team can check Twilio before the demo."""
    text = ("வணக்கம். Bank IQ பேசுறோம். இது ஒரு test call. எல்லாம் சரியா வேலை செய்யுது." if body.lang == "ta"
            else "Hello. This is Bank IQ. This is a test call. Everything is working.")
    return _voice.call(body.to or _voice.cfg.demo_phone, text, body.lang, kind="voice_test")


@app.post("/api/notify/test")
def notify_test(body: TestMailIn):
    """Send a test mail so the team can check the SMTP setup before the demo."""
    r = _email.send(body.to or _email.cfg.demo_to or _email.cfg.user, "Bank IQ — test mail", "If you can read this, real delivery works. Nothing was sent to any bank.",
                    "<p><b>Bank IQ</b> — test mail. If you can read this, real delivery works. Nothing was sent to any bank.</p>", kind="email_test")
    return r


@app.get("/api/rules")
def rules(category: Optional[str] = None, on: Optional[date] = None):
    out = rb().all()
    if category:
        out = [r for r in out if r.category == category]
    if on:
        out = [r for r in out if r.in_force(on)]
    return [r.to_dict() for r in out]


@app.get("/api/scope")
def scope():
    """Exactly what this prototype checks — never 'all RBI regulations'."""
    rules = rb().all()
    active = [r for r in rules if r.status == "active"]
    cats: dict[str, int] = {}
    for r in active:
        cats[r.category] = cats.get(r.category, 0) + 1
    return {"implemented": len(active), "listed": len(rules), "mapped": 40, "categories": cats, "rulebook_version": rb().version,
            "statement": "This prototype implements a curated set of RBI customer-protection rules, each linked to its circular and effective window. It is not complete RBI coverage, and a finding is a potential claim until the bank or the Ombudsman decides."}


@app.get("/api/validation")
def validation():
    """Real test results, as written by `python scripts/validate.py` (never typed by hand)."""
    p = ROOT / "data" / "validation.json"
    if not p.exists():
        return {"available": False, "hint": "run: python scripts/validate.py"}
    return {"available": True} | json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/accounts/{account_id}/twin")
def account_twin(account_id: str):
    """The digital twin as data: counts, balance path, reversal pairs, charges — all derived from the uploaded lines."""
    acct = _load(account_id)
    ctx = twin_mod.build_twin(acct["transactions"], acct["profile"], rb(), acct["as_of"], acct["answers"])
    return explain.twin_summary(ctx, store().get_findings(account_id))


@app.get("/api/accounts/{account_id}/transactions/{txn_id}/why-not")
def why_not(account_id: str, txn_id: str):
    """'Why wasn't this flagged?' — the deterministic checklist for one line."""
    acct = _load(account_id)
    txn = next((t for t in acct["transactions"] if t.id == txn_id), None)
    if not txn:
        raise HTTPException(404, "transaction not found")
    ctx = twin_mod.build_twin(acct["transactions"], acct["profile"], rb(), acct["as_of"], acct["answers"])
    return explain.why_not_flagged(ctx, txn, store().get_findings(account_id))


@app.get("/api/rules/{rule_id}")
def rule(rule_id: str):
    try:
        return rb().get(rule_id).to_dict()
    except KeyError:
        raise HTTPException(404, "rule not found")


# --------------------------------------------------------------------------- #
# Scan
# --------------------------------------------------------------------------- #
@app.post("/api/scan")
async def api_scan(file: Optional[UploadFile] = File(None), files: list[UploadFile] = File(default=[]), profile: str = Form("{}"), as_of: Optional[str] = Form(None), account_id: Optional[str] = Form(None)):
    """Scan one or more statements. With `account_id`, the files are added to that account's
    history (duplicates dropped, rules re-run over the whole history). Without it, the first
    file creates the account and the rest are merged into it."""
    try:
        prof = ProfileIn(**json.loads(profile or "{}")).to_model()
    except Exception as e:
        raise HTTPException(400, f"bad profile: {e}")
    uploads = ([file] if file else []) + list(files or [])
    if not uploads:
        raise HTTPException(400, "no file uploaded")
    as_of_d = date.fromisoformat(as_of) if as_of else None
    reports, res = [], None
    for up in uploads:
        data = await up.read()
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(413, f"{up.filename}: file too large (15 MB limit)")
        if Path(up.filename or "").suffix.lower() not in ALLOWED_UPLOAD_EXT:
            raise HTTPException(415, f"{up.filename}: only PDF, CSV/TSV, XLSX or an image (JPG/PNG) of a statement can be uploaded")
        account_id, res, rep = _ingest(account_id, data, up.filename or "statement.csv", prof, as_of_d)
        reports.append(rep)
    return _result_payload(account_id, res) | {"upload": reports}


@app.post("/api/accounts/{account_id}/statements")
async def add_statements(account_id: str, file: Optional[UploadFile] = File(None), files: list[UploadFile] = File(default=[]), as_of: Optional[str] = Form(None)):
    """Add more statements to an existing account (older quarter, next month, a passbook page)."""
    acct = _load(account_id)
    uploads = ([file] if file else []) + list(files or [])
    if not uploads:
        raise HTTPException(400, "no file uploaded")
    as_of_d = date.fromisoformat(as_of) if as_of else None
    reports, res = [], None
    for up in uploads:
        data = await up.read()
        account_id, res, rep = _ingest(account_id, data, up.filename or "statement.csv", acct["profile"], as_of_d)
        reports.append(rep)
    return _result_payload(account_id, res) | {"upload": reports}


@app.get("/api/accounts/{account_id}/statements")
def list_statements(account_id: str):
    _load(account_id)
    stmts = store().list_statements(account_id)
    cov = merge.coverage([(date.fromisoformat(x["period_from"]) if x["period_from"] else None, date.fromisoformat(x["period_to"]) if x["period_to"] else None) for x in stmts])
    return {"statements": [{k: v for k, v in x.items() if k != "txn_ids"} for x in stmts], "coverage": cov.to_dict()}


@app.delete("/api/accounts/{account_id}/statements/{statement_id}")
def delete_statement(account_id: str, statement_id: str):
    """Remove one uploaded statement (its lines only) and re-run the rules on what remains."""
    acct = _load(account_id)
    st = store().get_statement(statement_id)
    if not st or st["account_id"] != account_id:
        raise HTTPException(404, "statement not found")
    drop = set(st["txn_ids"])
    remaining = [t for t in acct["transactions"] if t.id not in drop]
    store().delete_statement(statement_id)
    store().update_transactions(account_id, remaining)
    store().audit(account_id, "statement.delete", f"{st['filename']} · -{len(drop)} lines")
    if not remaining:
        store().replace_findings(account_id, [])
        return {"deleted": statement_id, "remaining_transactions": 0}
    acct["transactions"] = remaining
    res = _rescan_and_save(account_id, acct)
    return _result_payload(account_id, res)


@app.get("/api/accounts")
def list_accounts():
    return store().list_accounts(_uid() if AUTH_ON else None)


# --------------------------------------------------------------------------- #
# Auth — signup / login / logout. Passwords are PBKDF2-hashed, sessions are HttpOnly cookies.
# --------------------------------------------------------------------------- #
class SignupIn(BaseModel):
    login: str = Field(min_length=3, max_length=120)      # phone or email
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=6, max_length=200)


class LoginIn(BaseModel):
    login: str
    password: str


def _set_session(resp: JSONResponse, user: dict) -> JSONResponse:
    tok = store().new_session(user["id"])
    resp.set_cookie(SESSION_COOKIE, tok, httponly=True, samesite="lax", max_age=7 * 24 * 3600, path="/")
    return resp


@app.post("/api/auth/signup")
def signup(body: SignupIn):
    try:
        user = store().create_user(body.login, body.name, body.password)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return _set_session(JSONResponse({"user": user}), user)


@app.post("/api/auth/login")
def login(body: LoginIn):
    user = store().authenticate(body.login, body.password)
    if not user:
        raise HTTPException(401, "Wrong phone/email or password")
    return _set_session(JSONResponse({"user": user}), user)


@app.post("/api/auth/logout")
def logout(request: Request):
    store().end_session(request.cookies.get(SESSION_COOKIE, ""))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@app.get("/api/auth/me")
def me(request: Request):
    u = _user_from_request(request)
    return {"user": u, "auth": AUTH_ON, "encryption": "AES-256-GCM at rest", "password_hash": f"PBKDF2-HMAC-SHA256 × {crypto.PBKDF2_ITERATIONS:,}"}


@app.get("/api/accounts/{account_id}")
def get_account(account_id: str):
    acct = _load(account_id)
    res = scan.rescan(acct["transactions"], acct["profile"], acct["as_of"], acct["answers"])
    for c in store().list_cases(account_id):
        before = c.state
        case_mod.tick(c)
        if c.state != before:
            store().save_case(c)
    return _result_payload(account_id, res)


@app.post("/api/accounts/{account_id}/answers")
def post_answers(account_id: str, body: AnswersIn):
    acct = _load(account_id)
    acct["answers"].update(body.answers)
    store().update_answers(account_id, acct["answers"])
    store().audit(account_id, "answers", json.dumps(body.answers))
    res = _rescan_and_save(account_id, acct)
    return _result_payload(account_id, res)


@app.post("/api/accounts/{account_id}/as-of")
def set_as_of(account_id: str, body: AsOfIn):
    """Move the 'as of' date: every ₹/day claim is recomputed for that day (the time slider)."""
    acct = _load(account_id)
    store().update_transactions(account_id, acct["transactions"], as_of=body.as_of)
    acct["as_of"] = body.as_of
    res = _rescan_and_save(account_id, acct)
    return _result_payload(account_id, res)


@app.patch("/api/accounts/{account_id}/profile")
def patch_profile(account_id: str, body: ProfileIn):
    acct = _load(account_id)
    prof = body.to_model()
    store().update_profile(account_id, prof)
    acct["profile"] = prof
    res = _rescan_and_save(account_id, acct)
    return _result_payload(account_id, res)


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: str):
    _load(account_id)
    store().delete_account(account_id)
    return {"deleted": account_id}


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #
@app.post("/api/accounts/{account_id}/cases")
def create_case(account_id: str, body: CaseIn):
    acct = _load(account_id)
    findings = store().get_findings(account_id)
    if body.finding_ids:
        chosen = [f for f in findings if f.id in body.finding_ids and f.label == Label.RECOVERABLE]
    else:
        chosen = [f for f in findings if f.label == Label.RECOVERABLE and f.priority.value in ("RECOVER_NOW", "COMBINE")]
    if not chosen:
        raise HTTPException(400, "no recoverable findings selected")
    case = case_mod.new_case(account_id, chosen)
    by_id = {t.id: t for t in acct["transactions"]}
    pack = complaint.build_pack(chosen, by_id, acct["profile"], rb(), sent_on=acct["as_of"], case_id=case.id)
    case.complaint_text = pack.bank_letter + "\n\nEVIDENCE\n" + pack.evidence_table
    case.ombudsman_text = pack.ombudsman_text
    case_mod.transition(case, CaseState.PREPARED, "Complaint pack generated", actor="system")
    store().save_case(case)
    store().audit(account_id, "case.create", case.id)
    return case.to_dict() | {"status_text": case_mod.user_status(case, acct["profile"].language), "bank_email_to": pack.bank_email_to, "subject": pack.subject}


@app.get("/api/accounts/{account_id}/cases")
def list_cases(account_id: str):
    acct = _load(account_id)
    out = []
    for c in store().list_cases(account_id):
        case_mod.tick(c)
        store().save_case(c)
        out.append(c.to_dict() | {"status_text": case_mod.user_status(c, acct["profile"].language), "days_left": case_mod.days_left(c)})
    return out


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    c = _case(case_id)
    case_mod.tick(c)
    store().save_case(c)
    acct = _load(c.account_id)
    return c.to_dict() | {"status_text": case_mod.user_status(c, acct["profile"].language), "days_left": case_mod.days_left(c)}


@app.post("/api/cases/{case_id}/request-approval")
def request_approval(case_id: str, request: Request, lang: Optional[str] = None):
    """Step 1 of the human layer: call the holder, message the guardian, wait."""
    c = _case(case_id)
    acct = _load(c.account_id)
    prof: AccountProfile = acct["profile"]
    lang = lang or prof.language
    g = store().get_guardian(c.account_id)
    findings = store().get_findings(c.account_id)
    script = guardian_mod.holder_voice_script(c.amount, g, lang, holder_name=prof.holder_name, bank=prof.bank or "", case=c, findings=findings)
    call_ref = _channel.call("holder", script)
    token = store().new_approval(c.id, c.account_id)
    store().log_notification(c.account_id, {"kind": "voice_call", "to": "holder", "lang": lang, "text": script.text, "options": script.ivr_options, "case_id": c.id, "token": token})
    # the real one: Twilio dials the holder's phone and speaks the same script
    real_call = _voice.call(prof.holder_phone or (g.phone if g else ""), script.text, lang)
    store().log_notification(c.account_id, real_call | {"case_id": c.id})
    msg = None
    mail = None
    if g:
        msg = guardian_mod.guardian_message(c, findings, g, prof.holder_name, token, g.language or lang)
        _channel.message(msg)
        store().log_notification(c.account_id, {"kind": "guardian_message", "to": g.phone, "text": msg.text, "case_id": c.id, "token": token})
        # the real one: an email with one button (WhatsApp/SMS adapters plug in here)
        approve_url = f"{_public_url(request)}/#/approve/{token}"
        subject, text, html = notify.guardian_email(prof.holder_name or "the account holder", g.name, f"₹{c.amount:,.2f}", msg.text, token, approve_url, g.language or lang)
        mail = _email.send(g.email or _email.cfg.demo_to, subject, text, html, kind="email_guardian")
        store().log_notification(c.account_id, mail | {"case_id": c.id, "token": token})
    if c.state == CaseState.PREPARED:
        case_mod.transition(c, CaseState.AWAITING_APPROVAL, "Holder called; " + ("guardian messaged" if g else "no guardian on file — holder may approve directly"), actor="system")
        store().save_case(c)
    store().audit(c.account_id, "case.request_approval", f"{c.id} token={token}")
    return {"case": c.to_dict(), "approve_token": token, "holder_call": {"text": script.text, "options": script.ivr_options, "lang": lang},
            "guardian_message": msg.text if msg else None, "email": mail, "call": real_call, "status_text": case_mod.user_status(c, prof.language)}


@app.get("/api/approvals/{token}")
def approval_info(token: str):
    """What the guardian sees when they open the link from the message: amount, holder, the message — nothing else."""
    row = store()._conn.execute("SELECT case_id, account_id, used FROM approvals WHERE token=?", (token.upper(),)).fetchone()
    if not row:
        raise HTTPException(404, "invalid token")
    c = store().get_case(row["case_id"])
    acct = _load(row["account_id"], check_owner=False)
    g = store().get_guardian(row["account_id"])
    notes = [n for n in store().notifications(row["account_id"]) if n.get("token") == token.upper() and n.get("kind") == "guardian_message"]
    return {"token": token.upper(), "used": bool(row["used"]), "case_id": c.id, "amount": c.amount, "state": c.state.value,
            "holder": acct["profile"].holder_name, "bank": acct["profile"].bank, "guardian": g.to_dict() if g else None,
            "message": notes[0]["text"] if notes else "", "lang": (g.language if g else acct["profile"].language)}


@app.post("/api/approvals/{token}")
def approve(token: str, request: Request, approver: str = "guardian"):
    """Step 2: a human taps approve → the complaint is marked sent and the 30-day clock starts."""
    case_id = store().use_approval(token)
    if not case_id:
        raise HTTPException(404, "invalid or used token")
    c = store().get_case(case_id)
    acct = _load(c.account_id, check_owner=False)
    c.guardian_approved_by = approver
    case_mod.transition(c, CaseState.SENT_TO_BANK, f"Approved by {approver}; complaint marked sent to bank grievance cell (demo: copy emailed to the family, not the bank)", actor=approver, rb=rb(), on=acct["as_of"])
    store().save_case(c)
    store().audit(c.account_id, "case.sent", f"{c.id} via approval {token}")
    mail = _send_complaint_copy(c, acct, request)
    return c.to_dict() | {"status_text": case_mod.user_status(c, acct["profile"].language), "days_left": case_mod.days_left(c), "email": mail}


@app.post("/api/cases/{case_id}/send")
def send_direct(case_id: str, request: Request):
    """Holder sends without a guardian (literate user path)."""
    c = _case(case_id)
    acct = _load(c.account_id)
    if c.state == CaseState.FOUND:
        case_mod.transition(c, CaseState.PREPARED, "prepared", actor="user")
    case_mod.transition(c, CaseState.SENT_TO_BANK, "Sent by account holder (demo: copy emailed to the holder, not the bank)", actor="user", rb=rb(), on=acct["as_of"])
    store().save_case(c)
    store().audit(c.account_id, "case.sent", c.id)
    mail = _send_complaint_copy(c, acct, request)
    return c.to_dict() | {"status_text": case_mod.user_status(c, acct["profile"].language), "days_left": case_mod.days_left(c), "email": mail}


@app.post("/api/cases/{case_id}/event")
def case_event(case_id: str, body: EventIn):
    c = _case(case_id)
    acct = _load(c.account_id)
    try:
        case_mod.transition(c, CaseState(body.state), body.note, actor=body.actor, rb=rb(), on=acct["as_of"])
    except ValueError as e:
        raise HTTPException(409, str(e))
    store().save_case(c)
    store().audit(c.account_id, "case.event", f"{c.id} → {body.state}")
    return c.to_dict() | {"status_text": case_mod.user_status(c, acct["profile"].language), "days_left": case_mod.days_left(c)}


@app.post("/api/cases/{case_id}/check-recovery")
async def check_recovery(case_id: str, file: UploadFile = File(...)):
    """Closed loop: upload the next statement; if the refund credit is there, close the case."""
    c = _case(case_id)
    acct = _load(c.account_id)
    data = await file.read()
    res = scan.scan_bytes(data, file.filename or "statement.csv", acct["profile"], as_of=date.today())
    hit = case_mod.detect_recovery(c, res.transactions)
    if hit:
        case_mod.transition(c, CaseState.RECOVERED, f"Credit {hit.credit:.2f} on {hit.date.isoformat()}: {hit.narration}", actor="system")
        store().save_case(c)
        store().audit(c.account_id, "case.recovered", c.id)
        return {"recovered": True, "credit": hit.to_dict(), "case": c.to_dict(), "status_text": case_mod.user_status(c, acct["profile"].language)}
    return {"recovered": False, "case": c.to_dict(), "status_text": case_mod.user_status(c, acct["profile"].language), "days_left": case_mod.days_left(c)}


@app.get("/api/cases/{case_id}/complaint.txt", response_class=PlainTextResponse)
def complaint_txt(case_id: str):
    c = _case(case_id)
    return c.complaint_text


@app.get("/api/cases/{case_id}/ombudsman.txt", response_class=PlainTextResponse)
def ombudsman_txt(case_id: str):
    c = _case(case_id)
    return c.ombudsman_text


def _printable(case_id: str, kind: str, lang: Optional[str], autoprint: bool) -> str:
    c = _case(case_id)
    acct = _load(c.account_id)
    prof: AccountProfile = acct["profile"]
    lang = lang or prof.language
    wanted = set(c.finding_ids)
    findings = [f for f in store().get_findings(c.account_id) if f.id in wanted]
    by_id = {t.id: t for t in acct["transactions"]}
    store().audit(c.account_id, "case.print", f"{c.id} {kind}")
    if not findings:
        return printable.render_plain(c, c.complaint_text if kind == "bank" else c.ombudsman_text, rb(), lang, autoprint)
    if kind == "bank":
        return printable.render_bank_letter(c, findings, by_id, prof, rb(), guardian=store().get_guardian(c.account_id), lang=lang, autoprint=autoprint)
    return printable.render_ombudsman(c, findings, by_id, prof, rb(), lang=lang, autoprint=autoprint)


@app.get("/api/cases/{case_id}/complaint.html", response_class=HTMLResponse)
def complaint_html(case_id: str, lang: Optional[str] = None, print: int = 0):
    """Print-ready A4 complaint: letter + Annexure A (statement lines). Use the browser's Save as PDF."""
    return _printable(case_id, "bank", lang, bool(print))


@app.get("/api/cases/{case_id}/ombudsman.html", response_class=HTMLResponse)
def ombudsman_html(case_id: str, lang: Optional[str] = None, print: int = 0):
    return _printable(case_id, "ombudsman", lang, bool(print))


# --------------------------------------------------------------------------- #
# Guardian, notifications, assistant, letters
# --------------------------------------------------------------------------- #
@app.post("/api/accounts/{account_id}/guardian")
def set_guardian(account_id: str, body: GuardianIn):
    _load(account_id)
    g = Guardian(name=body.name, relation=body.relation, phone=body.phone, language=body.language, email=body.email.strip())
    if body.consent_transcript:
        guardian_mod.record_consent(g, body.consent_transcript)
    store().save_guardian(account_id, g)
    store().audit(account_id, "guardian.set", f"{g.relation}")
    return g.to_dict()


@app.delete("/api/accounts/{account_id}/guardian")
def revoke_guardian(account_id: str):
    """Revoke: the guardian is removed and every unused approval link for this account stops working."""
    _load(account_id)
    removed = store().delete_guardian(account_id)
    store().audit(account_id, "guardian.revoked", "guardian removed by the account holder")
    return {"revoked": removed}


@app.get("/api/accounts/{account_id}/notifications")
def notifications(account_id: str):
    _load(account_id)
    return store().notifications(account_id)


@app.post("/api/ask")
def ask_general(body: AskIn):
    """Ask without an account — general banking questions only."""
    a = Assistant(rb(), body.lang or "ta").answer(body.question, [], [], body.lang)
    return {"text": a.text, "lang": a.lang, "kind": a.kind, "grounded_on": a.grounded_on, "suggestions": a.suggestions, "sources": a.sources, "steps": a.steps}


@app.post("/api/accounts/{account_id}/ask")
def ask(account_id: str, body: AskIn):
    acct = _load(account_id)
    findings = store().get_findings(account_id)
    cases = store().list_cases(account_id)
    a = Assistant(rb(), acct["profile"].language).answer(body.question, findings, cases, body.lang)
    store().audit(account_id, "ask", body.question[:120])
    return {"text": a.text, "lang": a.lang, "kind": a.kind, "grounded_on": a.grounded_on, "suggestions": a.suggestions, "sources": a.sources, "steps": a.steps}


@app.get("/api/accounts/{account_id}/basic-account-letter", response_class=PlainTextResponse)
def basic_letter(account_id: str):
    acct = _load(account_id)
    return complaint.basic_account_request(acct["profile"])


@app.get("/api/accounts/{account_id}/audit")
def audit(account_id: str):
    _load(account_id)
    rows = store()._conn.execute("SELECT action, detail, at FROM audit WHERE account_id=? ORDER BY id DESC LIMIT 100", (account_id,)).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# User-initiated claims (no statement needed)
# --------------------------------------------------------------------------- #
@app.post("/api/claims/card-closure")
def claim_card(body: CardClosureIn):
    return card_closure_claim(rb(), body.request_date, body.closure_date, body.as_of or date.today(), body.dues_cleared).to_dict()


@app.post("/api/claims/unauthorised")
def claim_unauth(body: UnauthorisedIn):
    return unauthorised_txn_claim(rb(), body.txn_date, body.amount, body.reported_on, body.credited_on, body.as_of or date.today()).to_dict()


@app.post("/api/claims/gold-release")
def claim_gold(body: GoldIn):
    return gold_release_claim(rb(), body.repaid_on, body.released_on, body.as_of or date.today()).to_dict()


# --------------------------------------------------------------------------- #
# Demo helpers + static web app
# --------------------------------------------------------------------------- #
@app.get("/api/samples")
def samples():
    d = ROOT / "data" / "samples"
    return [{"name": p.name, "size": p.stat().st_size} for p in sorted(d.iterdir()) if p.is_file()]


@app.get("/api/samples/{name}")
def sample(name: str):
    p = (ROOT / "data" / "samples" / name).resolve()
    if not str(p).startswith(str((ROOT / "data" / "samples").resolve())) or not p.exists():
        raise HTTPException(404, "sample not found")
    return FileResponse(p)


# --------------------------------------------------------------------------- #
# Bank IQ intelligence layer (classical ML on top of the rule engine)
# --------------------------------------------------------------------------- #
from bankiq.api import ml as ml_api  # noqa: E402

ml_api.make_account_endpoint(_load)
app.include_router(ml_api.router)
app.include_router(ml_api.account_router)


if WEB.exists():
    app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
