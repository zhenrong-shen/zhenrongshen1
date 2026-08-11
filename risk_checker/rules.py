"""위험 워딩 사전(rule dictionary)을 읽고 쓰는 모듈."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DICT_PATH = Path(__file__).parent / "risk_dictionary.json"


@dataclass
class Rule:
    id: str
    category: str
    risk_level: str
    keywords: list[str]
    reason: str
    suggestion: str

    @staticmethod
    def from_dict(d: dict) -> "Rule":
        return Rule(
            id=d["id"],
            category=d["category"],
            risk_level=d["risk_level"],
            keywords=list(d.get("keywords", [])),
            reason=d.get("reason", ""),
            suggestion=d.get("suggestion", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "risk_level": self.risk_level,
            "keywords": self.keywords,
            "reason": self.reason,
            "suggestion": self.suggestion,
        }


def load_rules(path: Path | str = DEFAULT_DICT_PATH) -> list[Rule]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [Rule.from_dict(r) for r in data.get("rules", [])]


def save_rules(rules: list[Rule], path: Path | str = DEFAULT_DICT_PATH) -> None:
    payload = {"version": 1, "rules": [r.to_dict() for r in rules]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def next_rule_id(rules: list[Rule]) -> str:
    nums = []
    for r in rules:
        if r.id.startswith("R") and r.id[1:].isdigit():
            nums.append(int(r.id[1:]))
    n = (max(nums) + 1) if nums else 1
    return f"R{n:03d}"
