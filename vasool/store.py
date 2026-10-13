"""SQLite persistence. Documents are stored as JSON per row; the schema stays
stable while the domain model evolves. Swap for Postgres by replacing this
module — the API only talks to `Store`."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import timedelta, date, datetime
from pathlib import Path
from typing import Any, Optional

from . import crypto
from .models import AccountProfile, Case, CaseEvent, CaseState, Confidence, Finding, Guardian, Label, Priority, Question, Transaction, Channel, Kind

DEFAULT_DB = os.getenv("VASOOL_DB", str(Path(__file__).resolve().parent.parent / "data" / "vasool.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, profile TEXT, transactions TEXT, answers TEXT, parse_meta TEXT, as_of TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, login TEXT UNIQUE, name TEXT, salt TEXT, pw_hash TEXT, created_at TEXT, last_login TEXT);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id TEXT, created_at TEXT, expires_at TEXT);
CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, account_id TEXT, doc TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, account_id TEXT, doc TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS guardians (account_id TEXT PRIMARY KEY, doc TEXT);
CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT, doc TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS approvals (token TEXT PRIMARY KEY, case_id TEXT, account_id TEXT, used INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT, action TEXT, detail TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS statements (id TEXT PRIMARY KEY, account_id TEXT, filename TEXT, source_kind TEXT, period_from TEXT, period_to TEXT, txn_count INTEGER, new_count INTEGER, dup_count INTEGER, txn_ids TEXT, warnings TEXT, uploaded_at TEXT);
CREATE INDEX IF NOT EXISTS idx_statements_acct ON statements(account_id);
CREATE INDEX IF NOT EXISTS idx_findings_acct ON findings(account_id);
CREATE INDEX IF NOT EXISTS idx_cases_acct ON cases(account_id);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = DEFAULT_DB):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(SCHEMA)
            cols = {r[1] for r in self._conn.execute("PRAGMA table_info(accounts)").fetchall()}
            if "user_id" not in cols:
                self._conn.execute("ALTER TABLE accounts ADD COLUMN user_id TEXT")

    # ----- accounts --------------------------------------------------------- #
    def save_account(self, account_id: Optional[str], profile: AccountProfile, txns: list[Transaction], answers: dict[str, Any], parse_meta: dict[str, Any], as_of: date, user_id: Optional[str] = None) -> str:
        account_id = account_id or "acct_" + uuid.uuid4().hex[:8]
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO accounts (id, profile, transactions, answers, parse_meta, as_of, created_at, updated_at, user_id) VALUES (?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET profile=excluded.profile, transactions=excluded.transactions, answers=excluded.answers, parse_meta=excluded.parse_meta, as_of=excluded.as_of, updated_at=excluded.updated_at, user_id=COALESCE(excluded.user_id, accounts.user_id)",
                (account_id, crypto.seal(profile.to_dict()), crypto.seal([t.to_dict() for t in txns]), crypto.seal(answers), crypto.seal(parse_meta), as_of.isoformat(), _now(), _now(), user_id),
            )
        return account_id

    def get_account(self, account_id: str) -> Optional[dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"], "user_id": row["user_id"], "profile": AccountProfile.from_dict(crypto.open_(row["profile"])),
            "transactions": [_txn_from(d) for d in crypto.open_(row["transactions"])],
            "answers": crypto.open_(row["answers"], {}), "parse_meta": crypto.open_(row["parse_meta"], {}),
            "as_of": date.fromisoformat(row["as_of"]), "created_at": row["created_at"],
        }

    def list_accounts(self, user_id: Optional[str] = None) -> list[dict[str, Any]]:
        """History view: one row per account with what a returning user needs to pick it out. Scoped to one user."""
        if user_id is None:
            rows = self._conn.execute("SELECT id, profile, transactions, as_of, created_at, updated_at FROM accounts ORDER BY updated_at DESC").fetchall()
        else:
            rows = self._conn.execute("SELECT id, profile, transactions, as_of, created_at, updated_at FROM accounts WHERE user_id=? ORDER BY updated_at DESC", (user_id,)).fetchall()
        out = []
        for r in rows:
            txns = crypto.open_(r["transactions"], [])
            dates = sorted(t["date"] for t in txns)
            findings = [crypto.open_(f["doc"]) for f in self._conn.execute("SELECT doc FROM findings WHERE account_id=?", (r["id"],)).fetchall()]
            cases = [crypto.open_(c["doc"]) for c in self._conn.execute("SELECT doc FROM cases WHERE account_id=?", (r["id"],)).fetchall()]
            n_stmts = self._conn.execute("SELECT COUNT(*) FROM statements WHERE account_id=?", (r["id"],)).fetchone()[0]
            out.append({
                "id": r["id"], "profile": crypto.open_(r["profile"]), "as_of": r["as_of"],
                "created_at": r["created_at"], "updated_at": r["updated_at"],
                "transactions": len(txns), "statements": n_stmts or (1 if txns else 0),
                "period": {"from": dates[0] if dates else None, "to": dates[-1] if dates else None},
                "total_recoverable": round(sum(f["amount"] for f in findings if f["label"] == "RECOVERABLE"), 2),
                "total_unclear": round(sum(f["amount"] for f in findings if f["label"] == "UNCLEAR"), 2),
                "findings": len(findings),
                "cases": len(cases),
                "open_cases": sum(1 for c in cases if c["state"] not in ("RECOVERED", "CLOSED_BANK_RIGHT", "CLOSED_BY_USER")),
                "recovered": round(sum(c["amount"] for c in cases if c["state"] == "RECOVERED"), 2),
            })
        return out

    def update_transactions(self, account_id: str, txns: list[Transaction], parse_meta: Optional[dict[str, Any]] = None, as_of: Optional[date] = None) -> None:
        """Replace the transaction list (after a merge) without touching answers."""
        with self._lock, self._conn:
            self._conn.execute("UPDATE accounts SET transactions=?, updated_at=? WHERE id=?", (crypto.seal([t.to_dict() for t in txns]), _now(), account_id))
            if parse_meta is not None:
                self._conn.execute("UPDATE accounts SET parse_meta=? WHERE id=?", (crypto.seal(parse_meta), account_id))
            if as_of is not None:
                self._conn.execute("UPDATE accounts SET as_of=? WHERE id=?", (as_of.isoformat(), account_id))

    # ----- statements (one row per uploaded file) --------------------------- #
    def add_statement(self, account_id: str, filename: str, source_kind: str, period_from: Optional[date], period_to: Optional[date],
                      txn_count: int, new_count: int, dup_count: int, txn_ids: list[str], warnings: list[str]) -> str:
        sid = "stmt_" + uuid.uuid4().hex[:8]
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO statements (id, account_id, filename, source_kind, period_from, period_to, txn_count, new_count, dup_count, txn_ids, warnings, uploaded_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, account_id, filename, source_kind, period_from.isoformat() if period_from else None, period_to.isoformat() if period_to else None,
                 txn_count, new_count, dup_count, crypto.seal(txn_ids), crypto.seal(warnings), _now()))
        return sid

    def list_statements(self, account_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM statements WHERE account_id=? ORDER BY period_from, uploaded_at", (account_id,)).fetchall()
        return [{"id": r["id"], "filename": r["filename"], "source_kind": r["source_kind"], "period_from": r["period_from"], "period_to": r["period_to"],
                 "txn_count": r["txn_count"], "new_count": r["new_count"], "dup_count": r["dup_count"],
                 "txn_ids": crypto.open_(r["txn_ids"], []), "warnings": crypto.open_(r["warnings"], []), "uploaded_at": r["uploaded_at"]} for r in rows]

    def get_statement(self, statement_id: str) -> Optional[dict[str, Any]]:
        r = self._conn.execute("SELECT * FROM statements WHERE id=?", (statement_id,)).fetchone()
        if not r:
            return None
        return {"id": r["id"], "account_id": r["account_id"], "filename": r["filename"], "period_from": r["period_from"], "period_to": r["period_to"],
                "txn_ids": crypto.open_(r["txn_ids"], [])}

    def delete_statement(self, statement_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM statements WHERE id=?", (statement_id,))

    def update_answers(self, account_id: str, answers: dict[str, Any]) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE accounts SET answers=?, updated_at=? WHERE id=?", (crypto.seal(answers), _now(), account_id))

    def update_profile(self, account_id: str, profile: AccountProfile) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE accounts SET profile=?, updated_at=? WHERE id=?", (crypto.seal(profile.to_dict()), _now(), account_id))

    # ----- findings --------------------------------------------------------- #
    def replace_findings(self, account_id: str, findings: list[Finding]) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM findings WHERE account_id=?", (account_id,))
            self._conn.executemany("INSERT INTO findings (id, account_id, doc, updated_at) VALUES (?,?,?,?)",
                                   [(f.id, account_id, crypto.seal(f.to_dict()), _now()) for f in findings])

    def get_findings(self, account_id: str) -> list[Finding]:
        rows = self._conn.execute("SELECT doc FROM findings WHERE account_id=?", (account_id,)).fetchall()
        return [_finding_from(crypto.open_(r["doc"])) for r in rows]

    # ----- cases ------------------------------------------------------------ #
    def save_case(self, case: Case) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO cases (id, account_id, doc, updated_at) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET doc=excluded.doc, updated_at=excluded.updated_at",
                               (case.id, case.account_id, crypto.seal(case.to_dict()), _now()))

    def get_case(self, case_id: str) -> Optional[Case]:
        row = self._conn.execute("SELECT doc FROM cases WHERE id=?", (case_id,)).fetchone()
        return _case_from(crypto.open_(row["doc"])) if row else None

    def list_cases(self, account_id: str) -> list[Case]:
        rows = self._conn.execute("SELECT doc FROM cases WHERE account_id=? ORDER BY updated_at DESC", (account_id,)).fetchall()
        return [_case_from(crypto.open_(r["doc"])) for r in rows]

    def all_cases(self) -> list[Case]:
        rows = self._conn.execute("SELECT doc FROM cases").fetchall()
        return [_case_from(crypto.open_(r["doc"])) for r in rows]

    # ----- guardian / approvals / notifications ----------------------------- #
    def save_guardian(self, account_id: str, g: Guardian) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO guardians (account_id, doc) VALUES (?,?) ON CONFLICT(account_id) DO UPDATE SET doc=excluded.doc", (account_id, crypto.seal(g.to_dict())))

    def delete_guardian(self, account_id: str) -> bool:
        with self._lock, self._conn:
            return self._conn.execute("DELETE FROM guardians WHERE account_id=?", (account_id,)).rowcount > 0

    def get_guardian(self, account_id: str) -> Optional[Guardian]:
        row = self._conn.execute("SELECT doc FROM guardians WHERE account_id=?", (account_id,)).fetchone()
        if not row:
            return None
        d = crypto.open_(row["doc"])
        return Guardian(name=d["name"], relation=d["relation"], phone=d["phone"], language=d.get("language", "ta"),
                        consent_recorded_at=datetime.fromisoformat(d["consent_recorded_at"]) if d.get("consent_recorded_at") else None,
                        consent_note=d.get("consent_note", ""), email=d.get("email", ""))

    def new_approval(self, case_id: str, account_id: str) -> str:
        token = uuid.uuid4().hex[:6].upper()
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO approvals (token, case_id, account_id, created_at) VALUES (?,?,?,?)", (token, case_id, account_id, _now()))
        return token

    def use_approval(self, token: str) -> Optional[str]:
        row = self._conn.execute("SELECT case_id, used FROM approvals WHERE token=?", (token.upper(),)).fetchone()
        if not row or row["used"]:
            return None
        with self._lock, self._conn:
            self._conn.execute("UPDATE approvals SET used=1 WHERE token=?", (token.upper(),))
        return row["case_id"]

    # ----- users & sessions -------------------------------------------------- #
    def create_user(self, login: str, name: str, password: str) -> dict[str, Any]:
        login = login.strip().lower()
        if self._conn.execute("SELECT 1 FROM users WHERE login=?", (login,)).fetchone():
            raise ValueError("An account with this phone/email already exists")
        salt, pw = crypto.hash_password(password)
        uid = "usr_" + uuid.uuid4().hex[:10]
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO users (id, login, name, salt, pw_hash, created_at) VALUES (?,?,?,?,?,?)", (uid, login, crypto.seal(name), salt, pw, _now()))
        return {"id": uid, "login": login, "name": name}

    def authenticate(self, login: str, password: str) -> Optional[dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM users WHERE login=?", (login.strip().lower(),)).fetchone()
        if not row or not crypto.verify_password(password, row["salt"], row["pw_hash"]):
            return None
        with self._lock, self._conn:
            self._conn.execute("UPDATE users SET last_login=? WHERE id=?", (_now(), row["id"]))
        return {"id": row["id"], "login": row["login"], "name": crypto.open_(row["name"], "")}

    def new_session(self, user_id: str, days: int = 7) -> str:
        tok = crypto.new_token()
        exp = (datetime.now() + timedelta(days=days)).isoformat(timespec="seconds")
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)", (tok, user_id, _now(), exp))
        return tok

    def user_for_session(self, token: str) -> Optional[dict[str, Any]]:
        if not token:
            return None
        row = self._conn.execute("SELECT u.id, u.login, u.name, s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?", (token,)).fetchone()
        if not row or row["expires_at"] < _now():
            return None
        return {"id": row["id"], "login": row["login"], "name": crypto.open_(row["name"], "")}

    def end_session(self, token: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM sessions WHERE token=?", (token,))

    def log_notification(self, account_id: str, doc: dict[str, Any]) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO notifications (account_id, doc, at) VALUES (?,?,?)", (account_id, crypto.seal(doc), _now()))

    def notifications(self, account_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT doc, at FROM notifications WHERE account_id=? ORDER BY id DESC LIMIT 50", (account_id,)).fetchall()
        return [dict(crypto.open_(r["doc"]), at=r["at"]) for r in rows]

    def audit(self, account_id: str, action: str, detail: str = "") -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO audit (account_id, action, detail, at) VALUES (?,?,?,?)", (account_id, action, detail, _now()))

    def delete_account(self, account_id: str) -> None:
        """DPDP: erase everything about an account on request."""
        with self._lock, self._conn:
            for table in ("accounts", "findings", "cases", "guardians", "notifications", "approvals", "audit", "statements"):
                col = "id" if table == "accounts" else "account_id"
                self._conn.execute(f"DELETE FROM {table} WHERE {col}=?", (account_id,))


# ----- (de)serialisers ------------------------------------------------------ #
def _txn_from(d: dict[str, Any]) -> Transaction:
    t = Transaction(date=date.fromisoformat(d["date"]), narration=d["narration"], debit=d["debit"], credit=d["credit"], balance=d.get("balance"), ref=d.get("ref", ""), id=d["id"], seq=d.get("seq", 0))
    t.channel = Channel(d.get("channel", "OTHER"))
    t.kind = Kind(d.get("kind", "UNKNOWN"))
    t.merchant = d.get("merchant", "")
    t.own_bank_atm = d.get("own_bank_atm")
    t.failed_hint = d.get("failed_hint", False)
    return t


def _finding_from(d: dict[str, Any]) -> Finding:
    return Finding(
        rule_id=d["rule_id"], label=Label(d["label"]), confidence=Confidence(d["confidence"]), amount=d["amount"],
        evidence=d["evidence"], calculation=d["calculation"], expected=d["expected"], actual=d["actual"],
        summary_en=d["summary_en"], summary_ta=d["summary_ta"],
        questions=[Question(q["id"], q["en"], q["ta"], q.get("options", []), q.get("type", "choice")) for q in d.get("questions", [])],
        prevention_en=d.get("prevention_en", ""), prevention_ta=d.get("prevention_ta", ""),
        priority=Priority(d.get("priority", "COMBINE")), priority_score=d.get("priority_score", 0.0),
        priority_reasons=d.get("priority_reasons", []), id=d["id"], group_key=d.get("group_key", ""),
        occurred_on=date.fromisoformat(d["occurred_on"]) if d.get("occurred_on") else None,
        twin=d.get("twin") or {},
        act_by=date.fromisoformat(d["act_by"]) if d.get("act_by") else None, days_left=d.get("days_left"), alert=bool(d.get("alert")), alert_reason=d.get("alert_reason", ""),
    )


def _case_from(d: dict[str, Any]) -> Case:
    c = Case(account_id=d["account_id"], finding_ids=d["finding_ids"], amount=d["amount"], rule_ids=d["rule_ids"], state=CaseState(d["state"]), id=d["id"])
    c.events = [CaseEvent(datetime.fromisoformat(e["at"]), CaseState(e["state"]), e.get("note", ""), e.get("actor", "system")) for e in d.get("events", [])]
    c.sent_on = date.fromisoformat(d["sent_on"]) if d.get("sent_on") else None
    c.bank_reply_due = date.fromisoformat(d["bank_reply_due"]) if d.get("bank_reply_due") else None
    c.ombudsman_deadline = date.fromisoformat(d["ombudsman_deadline"]) if d.get("ombudsman_deadline") else None
    c.complaint_text = d.get("complaint_text", "")
    c.ombudsman_text = d.get("ombudsman_text", "")
    c.guardian_approved_by = d.get("guardian_approved_by", "")
    return c
