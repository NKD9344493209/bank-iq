"""Bank IQ – ML intelligence endpoints (mounted into api.main).

GET  /api/ml/status                      – are the trained models present? which ones?
GET  /api/ml/results                     – experiment results (results/*.json) for the dashboard
GET  /api/ml/figures/{name}.png          – experiment figures
POST /api/ml/analyze  (multipart file)   – parse a statement (CSV/PDF/image) and return the ML analysis
POST /api/ml/analyze-json {rows:[...]}   – same, for already-parsed rows
GET  /api/accounts/{id}/intelligence     – analysis of an account's stored transaction history
      (this one is account-scoped, so it sits behind the session middleware like the rest of /api/accounts)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import service

router = APIRouter(prefix="/api/ml", tags=["intelligence"])
account_router = APIRouter(prefix="/api/accounts", tags=["intelligence"])

FIG_DIR = service.RESULTS_DIR / "figures"
ALLOWED = {".pdf", ".csv", ".tsv", ".txt", ".xlsx", ".xls", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


class RowsIn(BaseModel):
    rows: list[dict[str, Any]]
    customer_id: str = "upload"


def _run(rows: list[dict[str, Any]], cid: str = "upload") -> dict[str, Any]:
    try:
        return service.analyze(rows, cid)
    except service.ModelsMissing as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/status")
def status():
    return {"available": service.models_available(), "models": sorted(p.name for p in service.MODEL_DIR.glob("*.joblib")) if service.MODEL_DIR.exists() else []}


@router.get("/results")
def results():
    return service.results_summary()


@router.get("/figures/{name}")
def figure(name: str):
    p = FIG_DIR / Path(name).name
    if p.suffix != ".png" or not p.exists():
        raise HTTPException(404, "figure not found")
    return FileResponse(str(p), media_type="image/png")


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    from vasool.parsers import parse_bytes
    data = await file.read()
    if Path(file.filename or "").suffix.lower() not in ALLOWED:
        raise HTTPException(415, "upload a PDF, CSV/TSV, XLSX or an image of a statement")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "file too large (15 MB limit)")
    try:
        parsed = parse_bytes(data, file.filename or "statement.csv")
    except Exception as e:
        raise HTTPException(422, f"could not read {file.filename}: {e}")
    rows = [{"date": r["date"], "narration": r["narration"], "debit": r.get("debit", 0.0), "credit": r.get("credit", 0.0), "balance": r.get("balance"), "bank": parsed.bank} for r in parsed.rows]
    if not rows:
        raise HTTPException(422, "no transaction lines found in the file")
    out = _run(rows, Path(file.filename or "upload").stem)
    out["source"] = {"filename": file.filename, "bank": parsed.bank, "kind": parsed.source_kind, "warnings": parsed.warnings}
    return out


@router.post("/analyze-json")
def analyze_json(body: RowsIn):
    return _run(body.rows, body.customer_id)


def make_account_endpoint(load_account: Callable[[str], dict[str, Any]]):
    """Bind the account endpoint to api.main's `_load` (which enforces ownership)."""
    @account_router.get("/{account_id}/intelligence")
    def account_intelligence(account_id: str):
        acct = load_account(account_id)
        txns = acct.get("transactions") or []
        rows = [{"date": t.date.isoformat(), "narration": t.narration, "debit": t.debit, "credit": t.credit, "balance": t.balance, "bank": acct["profile"].bank or ""} for t in txns]
        if not rows:
            raise HTTPException(422, "this account has no transactions yet")
        return _run(rows, account_id)
    return account_intelligence
