"""Load and query the open rulebook (rulebook/rules.json).

Rules are versioned by effective date. `rules_in_force(on)` returns only the
rules that applied on a given day, so the same ATM charge is judged by the
₹21 cap in April 2025 and the ₹23 cap in May 2025.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

RULEBOOK_PATH = Path(__file__).resolve().parent.parent / "rulebook" / "rules.json"


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    category: str
    status: str
    right_en: str
    right_ta: str
    source: dict[str, Any]
    effective_from: date
    effective_to: Optional[date]
    evaluable_from: tuple[str, ...]
    parameters: dict[str, Any]
    formula: str
    evidence_required: tuple[str, ...]
    questions: tuple[dict[str, Any], ...]
    compensation_type: str
    document_help: Optional[dict[str, Any]] = None

    def in_force(self, on: date) -> bool:
        if on < self.effective_from:
            return False
        if self.effective_to and on > self.effective_to:
            return False
        return True

    @property
    def can_claim(self) -> bool:
        """Only 'active' rules may generate a recoverable claim."""
        return self.status == "active"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "category": self.category, "status": self.status,
            "right_en": self.right_en, "right_ta": self.right_ta, "source": self.source,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "evaluable_from": list(self.evaluable_from), "parameters": self.parameters,
            "formula": self.formula, "evidence_required": list(self.evidence_required),
            "questions": list(self.questions), "compensation_type": self.compensation_type,
            "document_help": self.document_help,
        }


class Rulebook:
    def __init__(self, data: dict[str, Any]):
        self.version: str = data.get("version", "unknown")
        self.rules: dict[str, Rule] = {}
        for r in data["rules"]:
            rule = Rule(
                id=r["id"], title=r["title"], category=r["category"], status=r["status"],
                right_en=r["right_en"], right_ta=r.get("right_ta", ""), source=r["source"],
                effective_from=date.fromisoformat(r["effective_from"]),
                effective_to=date.fromisoformat(r["effective_to"]) if r.get("effective_to") else None,
                evaluable_from=tuple(r.get("evaluable_from", [])), parameters=r.get("parameters", {}),
                formula=r["formula"], evidence_required=tuple(r.get("evidence_required", [])),
                questions=tuple(r.get("questions", [])), compensation_type=r["compensation_type"],
                document_help=r.get("document_help"),
            )
            self.rules[rule.id] = rule

    def get(self, rule_id: str) -> Rule:
        return self.rules[rule_id]

    def rules_in_force(self, on: date) -> list[Rule]:
        return [r for r in self.rules.values() if r.in_force(on)]

    def by_category(self, category: str) -> list[Rule]:
        return [r for r in self.rules.values() if r.category == category]

    def all(self) -> list[Rule]:
        return list(self.rules.values())


@lru_cache(maxsize=1)
def load(path: Optional[str] = None) -> Rulebook:
    p = Path(path) if path else RULEBOOK_PATH
    with open(p, encoding="utf-8") as fh:
        return Rulebook(json.load(fh))
