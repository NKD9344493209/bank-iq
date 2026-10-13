"""Print-ready complaint pages.

A complaint is often handed over at a branch counter, by the account holder or
the guardian, on paper. So every case can be printed as an A4 letter:

* the bank complaint (To / From / Date / Subject, numbered claims with the RBI
  reference and the arithmetic, the request, signature block, Annexure A with
  the statement lines);
* the RBI Ombudsman draft, laid out as the cms.rbi.org.in form asks for it.

The page is self-contained HTML with print CSS; the browser's "Save as PDF"
gives the PDF. A screen-only strip on top carries the print button and a short
Tamil/English checklist for the person carrying the paper. Nothing on the
printed page mentions balances or spending beyond the lines in evidence.
"""
from __future__ import annotations

from datetime import date, timedelta
from html import escape as e
from typing import Iterable, Optional

from .models import AccountProfile, Case, Finding, Guardian, Transaction
from .rulebook import Rulebook
from .rules.base import dmy, inr
from .complaint import BANK_GRIEVANCE_EMAIL

CSS = """
:root{--ink:#111;--muted:#555;--line:#bbb;--green:#1E6A44;--gold:#B7891C}
*{box-sizing:border-box}
html,body{margin:0;background:#e9ebe7;color:var(--ink);font-family:Cambria,Georgia,'Noto Serif','Times New Roman',serif;font-size:11.5pt;line-height:1.45}
.toolbar{position:sticky;top:0;background:#144C31;color:#fff;padding:10px 16px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;font-family:system-ui,sans-serif;font-size:14px;z-index:5}
.toolbar b{font-size:15px}
.toolbar .sp{flex:1}
.toolbar a,.toolbar button{font:inherit;background:#C9961A;color:#144C31;border:0;border-radius:8px;padding:8px 14px;font-weight:600;cursor:pointer;text-decoration:none}
.toolbar a.ghost{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.4)}
.check{background:#F6EDD3;color:#3a2e12;padding:12px 16px;font-family:system-ui,sans-serif;font-size:14px;line-height:1.5;border-bottom:1px solid #e0c98a}
.check ul{margin:6px 0 0 18px;padding:0}
.page{background:#fff;width:210mm;min-height:297mm;margin:18px auto;padding:22mm 20mm 20mm;box-shadow:0 6px 30px rgba(0,0,0,.15);position:relative}
.page + .page{page-break-before:always}
h1{font-size:15pt;margin:0 0 4mm;letter-spacing:.02em;text-transform:uppercase}
h2{font-size:12.5pt;margin:7mm 0 2mm}
.head{display:grid;grid-template-columns:22mm 1fr;gap:1.5mm 4mm;margin-bottom:6mm}
.head b{font-weight:600;color:var(--muted)}
.sub{font-weight:700}
p{margin:0 0 3.2mm;text-align:justify}
ol.claims{padding-left:5mm;margin:0 0 4mm}
ol.claims li{margin-bottom:3.5mm}
ol.claims .title{font-weight:700}
table{border-collapse:collapse;width:100%;font-size:9.6pt;margin:2mm 0 4mm}
th,td{border:1px solid var(--line);padding:1.6mm 2mm;vertical-align:top;text-align:left}
th{background:#f0f2ee;font-weight:600}
td.r,th.r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.kv td:first-child{width:34mm;color:var(--muted)}
.total{font-size:12.5pt;font-weight:700;margin:3mm 0 5mm}
.sign{display:grid;grid-template-columns:1fr 1fr;gap:8mm;margin-top:12mm}
.sign .box{border-top:1px solid #000;padding-top:2mm;font-size:10pt;color:var(--muted)}
.ack{border:1px dashed var(--line);padding:4mm;margin-top:10mm;font-size:10pt;color:var(--muted)}
.foot{position:absolute;left:20mm;right:20mm;bottom:10mm;font-size:8.5pt;color:var(--muted);display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:2mm;font-family:system-ui,sans-serif}
.fill{display:inline-block;min-width:38mm;border-bottom:1px dotted #000}
.small{font-size:9.5pt;color:var(--muted)}
.ta{font-family:'Noto Sans Tamil','Anek Tamil','Latha',system-ui,sans-serif}
@page{size:A4;margin:0}
@media print{
  html,body{background:#fff}
  .noprint{display:none!important}
  .page{width:auto;min-height:auto;margin:0;padding:16mm 16mm 14mm;box-shadow:none}
  .foot{position:static;margin-top:10mm}
  ol.claims li,tr,.sign,.ack{break-inside:avoid;page-break-inside:avoid}
  a{color:inherit;text-decoration:none}
}
@media screen and (max-width:820px){.page{width:auto;margin:0;padding:16px;min-height:auto}.foot{position:static;margin-top:16px}.sign{grid-template-columns:1fr}}
"""


def _evidence(findings: Iterable[Finding], txns_by_id: dict[str, Transaction]) -> list[Transaction]:
    seen: dict[str, Transaction] = {}
    for f in findings:
        for tid in f.evidence:
            t = txns_by_id.get(tid)
            if t and tid not in seen:
                seen[tid] = t
    return sorted(seen.values(), key=lambda t: (t.date, t.seq))


def _evidence_table(rows: list[Transaction]) -> str:
    body = "".join(
        f"<tr><td>{e(t.date.isoformat())}</td><td>{e(t.narration)}</td><td class=r>{e(inr(t.debit)) if t.debit else ''}</td>"
        f"<td class=r>{e(inr(t.credit)) if t.credit else ''}</td><td class=r>{e(inr(t.balance)) if t.balance is not None else ''}</td><td>{e(t.ref or '')}</td></tr>"
        for t in rows)
    return ("<table><thead><tr><th>Date</th><th>Narration (as printed in statement)</th><th class=r>Debit</th><th class=r>Credit</th><th class=r>Balance</th><th>Ref / UTR</th></tr></thead>"
            f"<tbody>{body}</tbody></table>")


def _claims(findings: list[Finding], rb: Rulebook) -> str:
    items = []
    for f in findings:
        r = rb.get(f.rule_id)
        items.append(
            f"<li><div class=title>{e(r.title)} <span class=small>({e(f.rule_id)})</span></div>"
            f"<table class=kv><tbody>"
            f"<tr><td>RBI reference</td><td>{e(r.source['circular'])} dated {e(r.source['date'])}<br><span class=small>{e(r.source['url'])}</span></td></tr>"
            f"<tr><td>What the rule requires</td><td>{e(f.expected)}</td></tr>"
            f"<tr><td>What the statement shows</td><td>{e(f.actual)}</td></tr>"
            f"<tr><td>Calculation</td><td>{e(f.calculation)}</td></tr>"
            f"<tr><td>Amount claimed</td><td><b>{e(inr(f.amount))}</b></td></tr>"
            f"</tbody></table></li>")
    return "<ol class=claims>" + "".join(items) + "</ol>"


def _toolbar(case: Case, kind: str, lang: str) -> str:
    other = "ombudsman" if kind == "bank" else "complaint"
    other_label = "RBI Ombudsman draft" if kind == "bank" else "Bank complaint"
    ta = lang == "ta"
    check = ("<div class='check noprint'><b>" + ("பிரிண்ட் எடுத்து branch-க்கு போறதுக்கு முன்னாடி" if ta else "Before you take this to the branch") + "</b><ul>"
             + ("<li>2 copies எடுங்க. ஒண்ணு bank-க்கு, ஒண்ணுல 'Received' seal + தேதி + complaint number வாங்கி நீங்க வெச்சுக்கோங்க.</li>"
                "<li>Statement page-களோட copy-ஐ சேர்த்து குடுங்க (கடைசி பக்கத்துல list இருக்கு).</li>"
                "<li>Account holder கையெழுத்து போடணும். காப்பாளர் கூட வரலாம்; கையெழுத்து holder-ஓடது.</li>"
                "<li>30 நாள்ல பதில் இல்லைன்னா cms.rbi.org.in-ல complaint பண்ணலாம் — அந்த draft-ம் இங்க இருக்கு.</li>"
                if ta else
                "<li>Print 2 copies. Hand one in; on the other get a <i>Received</i> stamp, the date and a complaint number, and keep it.</li>"
                "<li>Attach a copy of the statement pages that contain the lines listed in Annexure A.</li>"
                "<li>The account holder signs. A guardian may accompany them; the signature is the holder's.</li>"
                "<li>No satisfactory reply in 30 days → file at cms.rbi.org.in. The Ombudsman draft is the next page.</li>")
             + "</ul></div>")
    return (f"<div class='toolbar noprint'><b>Bank IQ · {e(case.id)}</b><span class=sp></span>"
            f"<a class=ghost href='/api/cases/{e(case.id)}/{other}.html'>{other_label}</a>"
            f"<a class=ghost href='/api/cases/{e(case.id)}/complaint.txt'>Plain text</a>"
            f"<button onclick='window.print()'>🖨 {'Print / PDF-ஆ சேமி' if ta else 'Print / Save as PDF'}</button></div>" + check)


def _accompanied(guardian: Optional[Guardian]) -> str:
    if not guardian:
        return ""
    return f'<p class=small style="margin-top:6mm">Accompanied by: {e(guardian.name)} ({e(guardian.relation)}), with the account holder&#39;s recorded consent.</p>'


def _foot(case: Case, rb: Rulebook, label: str) -> str:
    return (f"<div class=foot><span>{e(label)} · Case {e(case.id)}</span>"
            f"<span>Prepared with Bank IQ · rulebook {e(rb.version)} · every claim cites the RBI direction in force on the transaction date</span></div>")


def render_bank_letter(case: Case, findings: list[Finding], txns_by_id: dict[str, Transaction], profile: AccountProfile, rb: Rulebook,
                       guardian: Optional[Guardian] = None, lang: str = "en", autoprint: bool = False) -> str:
    findings = [f for f in findings if f.id in set(case.finding_ids)] or findings
    total = round(sum(f.amount for f in findings), 2) or case.amount
    bank = profile.bank or "the Bank"
    acct = f"account ending {profile.account_last4}" if profile.account_last4 else "my savings account"
    holder = profile.holder_name or "the account holder"
    sent_on = case.sent_on or date.today()
    clock = rb.get("RBI-OMBUDSMAN-2026-CLOCK").parameters
    reply_due = case.bank_reply_due or (sent_on + timedelta(days=int(clock["bank_reply_days"])))
    email = BANK_GRIEVANCE_EMAIL.get((profile.bank or "").upper(), "")
    subject = f"Grievance — {acct} — request for credit of {inr(total)} under RBI directions [Ref {case.id}]"
    rows = _evidence(findings, txns_by_id)

    body = f"""
<div class=page>
  <h1>Complaint to the Bank</h1>
  <div class=head>
    <b>To</b><span>The Grievance Redressal Officer / Branch Manager, {e(bank)}{(' · ' + e(email)) if email else ''}</span>
    <b>From</b><span>{e(holder)}, {e(acct)}</span>
    <b>Date</b><span>{e(dmy(sent_on))}</span>
    <b>Subject</b><span class=sub>{e(subject)}</span>
  </div>
  <p>Dear Sir/Madam,</p>
  <p>I am writing under the Bank's Board-approved grievance redressal policy and the Reserve Bank of India's customer-protection directions regarding the following entries in my account statement. For each entry I state the RBI direction that applied on that date, what the direction requires, what my statement shows, and the amount involved.</p>
  {_claims(findings, rb)}
  <div class=total>Total amount requested to be credited: {e(inr(total))}</div>
  <p>I request that the Bank, within 30 days of receiving this complaint:</p>
  <p style="padding-left:6mm">(a) credit the above amount to my account; or<br>
  (b) where the Bank believes a charge was correctly levied, provide me the specific evidence relied upon — the date and mode of the prior notice, the disclosure document, or the reversal reference — together with the RBI provision that permits the charge.</p>
  <p>Please treat this as a formal complaint, acknowledge it with a complaint reference number, and reply in writing. Under the Reserve Bank – Integrated Ombudsman Scheme, if I do not receive a satisfactory reply within 30 days (by <b>{e(dmy(reply_due))}</b>), I intend to approach the RBI Ombudsman through cms.rbi.org.in.</p>
  <p>The relevant statement entries are listed in Annexure A and copies of the statement pages are attached.</p>
  <p>Yours faithfully,</p>
  <div class=sign>
    <div><div style="height:16mm"></div><div class=box>Signature of account holder<br><b style="color:#111">{e(holder)}</b> · {e(acct)}</div></div>
    <div><div style="height:16mm"></div><div class=box>Mobile: <span class=fill></span><br>Date: <span class=fill></span></div></div>
  </div>
  {_accompanied(guardian)}
  <div class=ack><b>For bank use — acknowledgement</b><br>Received on <span class=fill></span> &nbsp; Complaint / SR number <span class=fill></span> &nbsp; Officer <span class=fill></span> &nbsp; Seal</div>
  {_foot(case, rb, 'Complaint to the Bank')}
</div>
<div class=page>
  <h1>Annexure A — statement entries referred to</h1>
  <p class=small>{e(bank)} · {e(acct)} · {len(rows)} line(s). Copied exactly as printed in the statement; nothing else from the statement is disclosed.</p>
  {_evidence_table(rows)}
  <h2>Enclosures</h2>
  <p>1. Copy of statement page(s) containing the lines above.<br>2. Copy of identity proof (if the branch asks).<br>3. This complaint, in duplicate.</p>
  {_foot(case, rb, 'Annexure A')}
</div>"""
    return _doc(f"Complaint {case.id} — {holder}", _toolbar(case, "bank", lang) + body, autoprint)


def render_ombudsman(case: Case, findings: list[Finding], txns_by_id: dict[str, Transaction], profile: AccountProfile, rb: Rulebook,
                     lang: str = "en", autoprint: bool = False) -> str:
    findings = [f for f in findings if f.id in set(case.finding_ids)] or findings
    total = round(sum(f.amount for f in findings), 2) or case.amount
    bank = profile.bank or "the Bank"
    acct = f"account ending {profile.account_last4}" if profile.account_last4 else "savings account"
    holder = profile.holder_name or "the account holder"
    sent_on = case.sent_on or date.today()
    clock = rb.get("RBI-OMBUDSMAN-2026-CLOCK").parameters
    reply_due = case.bank_reply_due or (sent_on + timedelta(days=int(clock["bank_reply_days"])))
    omb_end = case.ombudsman_deadline or (reply_due + timedelta(days=int(clock["ombudsman_window_days"])))
    rows = _evidence(findings, txns_by_id)
    body = f"""
<div class=page>
  <h1>RBI Complaint Management System — draft</h1>
  <p class=small>File online at <b>cms.rbi.org.in</b> (no fee, no lawyer needed) after <b>{e(dmy(reply_due))}</b> if the Bank has not replied, or earlier if the reply is unsatisfactory. Window closes <b>{e(dmy(omb_end))}</b>. Copy each field below into the form.</p>
  <table class=kv><tbody>
    <tr><td>Complainant</td><td>{e(holder)}</td></tr>
    <tr><td>Regulated entity</td><td>{e(bank)}</td></tr>
    <tr><td>Account</td><td>{e(acct)}</td></tr>
    <tr><td>Nature of complaint</td><td>Deficiency in service — non-adherence to RBI directions on customer charges / failed-transaction compensation</td></tr>
    <tr><td>Amount involved</td><td><b>{e(inr(total))}</b></td></tr>
    <tr><td>Complaint lodged with Bank on</td><td>{e(dmy(sent_on))}</td></tr>
    <tr><td>Bank reference no.</td><td><span class=fill></span></td></tr>
    <tr><td>Bank's reply</td><td>☐ No reply within 30 days &nbsp; ☐ Reply received on <span class=fill></span>, unsatisfactory because <span class=fill style="min-width:60mm"></span></td></tr>
  </tbody></table>
  <h2>Facts of the case</h2>
  {_claims(findings, rb)}
  <h2>Relief sought</h2>
  <p>Credit of {e(inr(total))} to my account, together with any compensation the Ombudsman considers appropriate for the delay and deficiency in service.</p>
  <h2>Documents to upload</h2>
  <p>1. Statement extract (Annexure A).&nbsp; 2. Copy of complaint to the Bank dated {e(dmy(sent_on))} with acknowledgement.&nbsp; 3. Bank's reply, if any.</p>
  {_foot(case, rb, 'RBI Ombudsman draft')}
</div>
<div class=page>
  <h1>Annexure A — statement entries referred to</h1>
  {_evidence_table(rows)}
  {_foot(case, rb, 'Annexure A')}
</div>"""
    return _doc(f"Ombudsman draft {case.id} — {holder}", _toolbar(case, "ombudsman", lang) + body, autoprint)


def render_plain(case: Case, text: str, rb: Rulebook, lang: str = "en", autoprint: bool = False) -> str:
    """Fallback when the findings behind a case are no longer available: print the stored text."""
    body = f"<div class=page><pre style='white-space:pre-wrap;font:inherit'>{e(text)}</pre>{_foot(case, rb, 'Complaint')}</div>"
    return _doc(f"Complaint {case.id}", _toolbar(case, "bank", lang) + body, autoprint)


def _doc(title: str, body: str, autoprint: bool) -> str:
    script = "<script>window.addEventListener('load',()=>setTimeout(()=>window.print(),300))</script>" if autoprint else ""
    return f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{e(title)}</title><style>{CSS}</style></head><body>{body}{script}</body></html>"
