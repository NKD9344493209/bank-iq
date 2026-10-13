"""Ask Bank IQ — the human interface to the twin.

Answer order (first match wins):
  1. greetings / thanks / "what can you do"
  2. your account: "why ₹295?", "how much?", "status?", "what should I do?"
  3. claim check: "is it true that…", "bank says…" → corrected against the rulebook
  4. banking knowledge base: "how do I download my statement?", "what is a KFS?" …
  5. optional language model (VASOOL_LLM=on) for open-ended questions, with the
     rulebook + findings as context and a prompt that forbids inventing claims
  6. honest fallback: "I don't have that one — here's what I can help with"

Grounded by construction: the assistant never decides that a bank owes money;
it explains what the rule engine decided, corrects wrong beliefs using the
rulebook, and gives general guidance from a curated knowledge base.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from . import cases as case_mod
from . import knowledge as kb
from .models import Case, Finding, Label
from .rulebook import Rulebook
from .rules.base import inr

INTENTS = {
    "greet": [r"^\s*(hi|hello|hey|vanakkam|வணக்கம்|good (morning|evening|afternoon))\b"],
    "thanks": [r"\b(thanks|thank you|nandri|நன்றி)\b"],
    "why_charge": [r"\bwhy\b.*\b(charge|charged|cut|deduct|deducted|take|took|taken|gone|missing|debit|debited)", r"ஏன்.*(cut|charge|பிடி|எடுத்|போச்சு)", r"yen.*(cut|charge|edu|po)", r"\bwhat happened\b", r"என்ன ஆச்சு", r"enna aachu"],
    "how_much": [r"\bhow much\b", r"\btotal\b", r"எவ்வளவு", r"\bevlo\b", r"\bevvalavu\b", r"\bamount\b.*\b(owe|owed|get|recover)"],
    "status": [r"\bstatus\b", r"what('s| is) happening", r"\b(my )?(complaint|case)\b.*\b(status|where|reply|replied|update)\b", r"\bdid (the )?bank reply\b", r"நிலை", r"case.*(எப்போ|eppo)"],
    "next_step": [r"what (should|do|can) i do", r"\bnext step\b", r"நான் என்ன", r"naan enna", r"பண்ணணும்", r"pannanum", r"\bwhat now\b"],
    "do_i_complain": [r"(do|should) i (have to )?complain", r"\bworth (it|complaining)\b", r"complaint பண்ணணுமா", r"complaint pannanuma", r"\bbother\b"],
    "is_it_wrong": [r"(is|was) (it|this|that|the charge) (wrong|right|correct|legal|illegal|allowed|ok)", r"சரியா", r"\bthappa\b", r"\bsariya\b"],
}


@dataclass
class Answer:
    text: str
    lang: str
    kind: str = "general"                       # account | claim_check | knowledge | llm | fallback | chat
    grounded_on: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)   # [{id, title, url}]
    steps: list[str] = field(default_factory=list)


def detect_intent(q: str) -> str:
    ql = q.lower()
    for intent, pats in INTENTS.items():
        for p in pats:
            if re.search(p, ql, re.I):
                return intent
    return "general"


def _amount_in(q: str) -> Optional[float]:
    m = re.search(r"(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)", q, re.I)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _find_by_amount(findings: list[Finding], amount: Optional[float]) -> list[Finding]:
    if amount is None:
        return []
    out = []
    for f in findings:
        if abs(f.amount - amount) < 1.0:
            out.append(f)
            continue
        calc = f.calculation.replace(",", "")
        if re.search(rf"₹{int(amount)}(?:\.\d+)?\b", calc) or f"{amount:.2f}" in calc:
            out.append(f)
    return out


def _has_tamil(s: str) -> bool:
    return bool(re.search(r"[஀-௿]", s))


class Assistant:
    def __init__(self, rb: Rulebook, lang: str = "ta"):
        self.rb = rb
        self.lang = lang
        self.llm = LLMAnswerer.from_env()

    # ------------------------------------------------------------------ #
    def answer(self, question: str, findings: list[Finding], cases: list[Case], lang: Optional[str] = None) -> Answer:
        lang = lang or self.lang
        if _has_tamil(question):
            lang = "ta"
        q = question.strip()
        if not q:
            return self._fallback(q, lang, findings)
        intent = detect_intent(q)
        amount = _amount_in(q)

        # 1. chat
        if intent == "greet":
            return Answer("வணக்கம்! உங்க account பத்தியோ, bank rules பத்தியோ எதுவும் கேளுங்க." if lang == "ta" else "Hello! Ask me about your account, a charge, a case, or any banking rule.", lang, "chat")
        if intent == "thanks":
            return Answer("நாங்க பாத்துக்கறோம். நீங்க கவலைப்பட வேண்டாம்." if lang == "ta" else "We watch. You don't have to.", lang, "chat")

        # 2. account-specific
        acct = self._account_answer(q, intent, amount, findings, cases, lang)
        if acct:
            return acct

        # 3. claim check
        claim = kb.check_claim(q)
        if claim:
            return self._claim_answer(claim, lang)

        # 4. knowledge base
        hits = kb.search(q)
        if hits and hits[0].score >= 0.55:
            return self._kb_answer(hits, lang)

        # 5. language model, if enabled
        if self.llm.enabled and kb.is_banking_question(q):
            text = self.llm.answer(q, lang, findings, cases, hits, self.rb)
            if text:
                return Answer(text, lang, "llm", suggestions=[h.entry.title for h in hits[:2]])

        # 4b. weaker KB hit — offer it as a maybe
        if hits:
            a = self._kb_answer(hits, lang)
            a.text = ("இதைத்தான் கேட்டீங்களா? " if lang == "ta" else "I think you mean this — ") + a.text
            return a

        # 6. honest fallback
        return self._fallback(q, lang, findings)

    # ------------------------------------------------------------------ #
    def _account_answer(self, q: str, intent: str, amount: Optional[float], findings: list[Finding], cases: list[Case], lang: str) -> Optional[Answer]:
        rec = [f for f in findings if f.label == Label.RECOVERABLE]
        unclear = [f for f in findings if f.label == Label.UNCLEAR]
        total = sum(f.amount for f in rec)

        if intent in ("why_charge", "is_it_wrong") and amount is not None:
            hits = _find_by_amount(findings, amount)
            if hits:
                f = hits[0]
                rule = self.rb.get(f.rule_id)
                text = (f"{f.summary_ta} RBI rule: {rule.right_ta} " + self._label_line_ta(f)) if lang == "ta" else (f"{f.summary_en} The rule: {rule.right_en} " + self._label_line_en(f))
                return Answer(text, lang, "account", [f.id, rule.id], self._suggest(f, lang), [self._src(rule.id)])
            if findings:  # amount asked about isn't a finding
                text = (f"₹{amount:,.0f}-ஐ உங்க statement-ல bank charge-ஆ நாங்க பாக்கல — அது ஒரு சாதாரண payment-ஆ இருக்கலாம். அது fail ஆனதுன்னா 'Found' page-ல அந்த line-க்கு 'fail ஆச்சா?' கேள்விக்கு பதில் சொல்லுங்க, check பண்றோம்."
                        if lang == "ta" else
                        f"We don't see ₹{amount:,.0f} as a bank charge in your statement — it looks like an ordinary payment, which we never flag. If that payment failed, answer 'yes' to the 'did it fail?' question on the Found page and we'll check it under the failed-transaction rule.")
                return Answer(text, lang, "account")
            return None

        if intent == "why_charge" and findings and amount is None:
            # "what happened?" → summary of findings
            return self._summary(findings, lang)

        if intent == "how_much":
            if not findings:
                return None
            text = (f"இப்போ {inr(total)} திரும்ப வாங்கக்கூடியதா இருக்கு ({len(rec)} items)." + (f" இன்னும் {len(unclear)}-க்கு உங்க பதில் வேணும் — சேர்ந்தா {inr(total + sum(f.amount for f in unclear))} வரை." if unclear else "")
                    if lang == "ta" else
                    f"{inr(total)} is recoverable right now across {len(rec)} item(s)." + (f" {len(unclear)} more need one answer from you — with them it could reach {inr(total + sum(f.amount for f in unclear))}." if unclear else ""))
            return Answer(text, lang, "account", [f.id for f in rec])

        if intent == "status":
            if not cases:
                if not findings:
                    return None
                return Answer("இன்னும் எந்த complaint-ம் அனுப்பல. 'திரும்ப வாங்கு' அழுத்தினா தயார் பண்றோம்." if lang == "ta" else "No complaint has been sent yet. Tap 'Get it back' and we'll prepare it.", lang, "account")
            parts = []
            for c in cases:
                left = case_mod.days_left(c)
                s = case_mod.user_status(c, lang)
                if left is not None:
                    s += (f" ({left} நாள் மீதம்)" if lang == "ta" else f" ({left} days left)")
                parts.append(f"{c.id}: {inr(c.amount)} — {s}")
            return Answer("\n".join(parts), lang, "account", [c.id for c in cases])

        if intent in ("next_step", "do_i_complain"):
            if not findings:
                return None
            now = [f for f in rec if f.priority.value == "RECOVER_NOW"]
            combine = [f for f in rec if f.priority.value == "COMBINE"]
            skip = [f for f in rec if f.priority.value == "NOT_WORTH_IT"]
            if lang == "ta":
                text = ""
                if now: text += f"{len(now)} item(s), மொத்தம் {inr(sum(f.amount for f in now))} — இப்பவே கேக்கலாம். உங்க வேலை 2 நிமிஷம்: 'திரும்ப வாங்கு' அழுத்துங்க. "
                if combine: text += f"{len(combine)} சின்ன items ({inr(sum(f.amount for f in combine))}) ஒரே complaint-ல சேர்க்கிறோம். "
                if skip: text += f"{len(skip)} items ரொம்ப சின்னது — நாங்க பாத்துக்கறோம். "
                if unclear: text += f"{len(unclear)} கேள்விக்கு பதில் சொன்னா இன்னும் தெளிவா சொல்லுவோம்."
                if not text: text = "இப்போ எதுவும் பண்ண வேண்டாம். எல்லாம் சரியா இருக்கு. நாங்க பாத்துட்டே இருப்போம்."
            else:
                text = ""
                if now: text += f"{len(now)} item(s) worth {inr(sum(f.amount for f in now))} are worth acting on now. Your effort: about 2 minutes — tap 'Get it back'. "
                if combine: text += f"{len(combine)} small items ({inr(sum(f.amount for f in combine))}) will be bundled into the same complaint. "
                if skip: text += f"{len(skip)} items are too small to bother you with alone — we'll keep watching. "
                if unclear: text += f"Answer {len(unclear)} short question(s) and we can be more definite."
                if not text: text = "Nothing to do right now. Everything looks okay. We'll keep watching."
            return Answer(text, lang, "account", [f.id for f in rec + unclear])
        return None

    def _summary(self, findings: list[Finding], lang: str) -> Answer:
        rec = [f for f in findings if f.label == Label.RECOVERABLE]
        unclear = [f for f in findings if f.label == Label.UNCLEAR]
        avoid = [f for f in findings if f.label == Label.AVOIDABLE]
        total = sum(f.amount for f in rec)
        lines = [f"• {inr(f.amount)} — {(f.summary_ta if lang == 'ta' else f.summary_en)}" for f in sorted(rec, key=lambda f: -f.amount)[:4]]
        head = (f"உங்க statement-ல {len(rec)} items திரும்ப வாங்கலாம் ({inr(total)}), {len(unclear)}-க்கு ஒரு பதில் வேணும், {len(avoid)}-ஐ தடுக்கலாம்.\n" if lang == "ta"
                else f"From your statement: {len(rec)} recoverable item(s) worth {inr(total)}, {len(unclear)} that need one answer, {len(avoid)} you can prevent next time.\n")
        return Answer(head + "\n".join(lines), lang, "account", [f.id for f in findings])

    # ------------------------------------------------------------------ #
    def _claim_answer(self, claim: kb.Claim, lang: str) -> Answer:
        # truth texts already open with their own verdict word ("No.", "Not yet.", "Partly…")
        text = (claim.truth_ta or claim.truth_en) if lang == "ta" else claim.truth_en
        srcs = [self._src(r) for r in claim.rule_ids]
        return Answer(text, lang, "claim_check", list(claim.rule_ids), [], srcs)

    def _kb_answer(self, hits: list[kb.Hit], lang: str) -> Answer:
        e = hits[0].entry
        text = (e.answer_ta or e.answer_en) if lang == "ta" else e.answer_en
        steps = (e.steps_ta or e.steps_en) if lang == "ta" else e.steps_en
        if steps:
            text += "\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        srcs = [self._src(r) for r in e.rule_ids]
        also = [h.entry.title for h in hits[1:3] if h.score >= 0.62]
        return Answer(text, lang, "knowledge", [e.id] + list(e.rule_ids), also, srcs, steps)

    def _fallback(self, q: str, lang: str, findings: list[Finding]) -> Answer:
        if not findings and detect_intent(q) in ("next_step", "how_much", "status", "why_charge", "do_i_complain", "is_it_wrong"):
            text = ("அதுக்கு முதல்ல உங்க statement-ஐ scan பண்ணணும். Scan page-ல ஒரு statement அல்லது passbook photo கொடுங்க — அப்புறம் என்ன ஆச்சு, என்ன பண்ணணும்-னு சொல்றேன்."
                    if lang == "ta" else
                    "To answer that I need your statement first. Go to Scan and give me a statement or a passbook photo — then I can tell you what happened and what to do.")
            return Answer(text, lang, "fallback", [], ["how do I download my statement?"] if lang == "en" else ["statement எப்படி download பண்றது?"])
        banking = kb.is_banking_question(q)
        ideas_en = ["how do I download my statement?", "what is the ₹100 a day rule?", "can the bank charge for SMS?", "how do I complain to the RBI Ombudsman?"] + (["what happened?", "what should I do?"] if findings else [])
        ideas_ta = ["statement எப்படி download பண்றது?", "₹100/நாள் rule என்ன?", "SMS-க்கு charge பண்ணலாமா?", "RBI Ombudsman-ல எப்படி complaint பண்றது?"] + (["என்ன ஆச்சு?", "நான் என்ன பண்ணணும்?"] if findings else [])
        if lang == "ta":
            text = ("அந்த கேள்விக்கு என்கிட்ட நம்பகமான பதில் இல்ல — யூகிச்சு சொல்ல மாட்டேன். " if banking else "நான் bank, பணம், உங்க account பத்தி மட்டும் தான் பேசுவேன். ") + "இப்படி கேட்டு பாருங்க:"
        else:
            text = ("I don't have a reliable answer for that one, and I won't guess. " if banking else "I only know banking, money and your account. ") + "Try one of these:"
        return Answer(text, lang, "fallback", [], ideas_ta if lang == "ta" else ideas_en)

    # ------------------------------------------------------------------ #
    def _src(self, rule_id: str) -> dict[str, str]:
        r = self.rb.get(rule_id)
        return {"id": r.id, "title": r.source.get("circular", r.id), "url": r.source.get("url", "")}

    def _label_line_en(self, f: Finding) -> str:
        return {Label.RECOVERABLE: "This is recoverable — we can prepare the complaint.",
                Label.AVOIDABLE: "This charge is allowed, so no complaint is needed — but you can avoid the next one: " + (f.prevention_en or ""),
                Label.UNCLEAR: "Whether it's recoverable depends on one thing we need from you."}[f.label]

    def _label_line_ta(self, f: Finding) -> str:
        return {Label.RECOVERABLE: "இது திரும்ப வாங்கலாம் — complaint தயார் பண்றோம்.",
                Label.AVOIDABLE: "இந்த charge சரி, complaint வேண்டாம் — ஆனா அடுத்ததை தடுக்கலாம்: " + (f.prevention_ta or ""),
                Label.UNCLEAR: "திரும்ப வாங்கலாமா-ங்கறது உங்க ஒரு பதிலை பொறுத்தது."}[f.label]

    def _suggest(self, f: Finding, lang: str) -> list[str]:
        return [q.text_ta if lang == "ta" else q.text_en for q in f.questions]


# ---------------------------------------------------------------------- #
class LLMAnswerer:
    """Optional open-ended answering. Off unless VASOOL_LLM=on and ANTHROPIC_API_KEY is set.

    The model receives the rulebook rights, the customer's findings and the KB hits as
    context, and is told: explain, don't decide; never state an amount the bank owes
    that isn't in the findings; say 'I don't know' outside banking."""

    def __init__(self, enabled: bool):
        self.enabled = enabled

    @classmethod
    def from_env(cls) -> "LLMAnswerer":
        return cls(enabled=os.getenv("VASOOL_LLM", "off").lower() == "on" and bool(os.getenv("ANTHROPIC_API_KEY")))

    def answer(self, q: str, lang: str, findings: list[Finding], cases: list[Case], hits: list[kb.Hit], rb: Rulebook) -> str:
        try:  # pragma: no cover — network
            import anthropic  # type: ignore
            rights = "\n".join(f"- {r.id}: {r.right_en} (source: {r.source.get('circular')}, {r.source.get('date')})" for r in rb.all())
            fx = "\n".join(f"- {f.id} {f.rule_id} {f.label.value} {inr(f.amount)}: {f.summary_en}" for f in findings[:12]) or "(no statement scanned yet)"
            kbx = "\n".join(f"- {h.entry.title}: {h.entry.answer_en}" for h in hits[:3])
            system = (
                "You are Bank IQ's assistant for Indian bank customers, many with low literacy. Answer in "
                + ("Tamil (colloquial, simple; English words for banking terms are fine)" if lang == "ta" else "simple English")
                + ". Rules: (1) Explain and guide; you never decide whether a bank owes money — only the findings below do. "
                "(2) Never state an amount the customer is owed unless it appears in the findings. (3) Prefer the RBI rules and knowledge notes given; if the question is outside Indian banking/personal finance, say you only know banking. "
                "(4) Be concrete: steps, timelines, where to go. (5) Keep answers under 120 words unless steps are needed. (6) If unsure, say so.\n\n"
                f"RBI RULES:\n{rights}\n\nCUSTOMER FINDINGS:\n{fx}\n\nKNOWLEDGE NOTES:\n{kbx}"
            )
            client = anthropic.Anthropic()
            msg = client.messages.create(model=os.getenv("VASOOL_LLM_MODEL", "claude-3-5-haiku-latest"), max_tokens=500, system=system, messages=[{"role": "user", "content": q}])
            return (msg.content[0].text or "").strip()
        except Exception:
            return ""
