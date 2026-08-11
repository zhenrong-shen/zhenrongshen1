"""추출된 공고 텍스트에서 위험 워딩을 찾아 수정 제안을 만드는 매칭 엔진.

OCR 결과는 띄어쓰기가 원문과 다르게 인식되는 경우가 많으므로, 공백을 무시한
정규화 텍스트에서 키워드를 찾은 뒤 원문 위치로 되돌려 문맥 스니펫을 뽑는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .rules import Rule

CONTEXT_CHARS = 20


@dataclass
class Match:
    rule_id: str
    category: str
    risk_level: str
    matched_keyword: str
    current_wording: str
    suggestion: str
    reason: str


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    """공백을 제거한 정규화 텍스트와, 정규화 텍스트의 각 글자가 원문의
    몇 번째 인덱스였는지를 담은 매핑 리스트를 함께 반환한다."""
    norm_chars = []
    index_map = []
    for i, ch in enumerate(text):
        if ch.isspace():
            continue
        norm_chars.append(ch)
        index_map.append(i)
    return "".join(norm_chars), index_map


def _find_all(haystack: str, needle: str) -> list[int]:
    if not needle:
        return []
    positions = []
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1
    return positions


def analyze_text(text: str, rules: list[Rule]) -> list[Match]:
    if not text or not text.strip():
        return []

    norm_text, index_map = _normalize_with_map(text)
    matches: list[Match] = []
    seen_spans: set[tuple[str, int]] = set()

    for rule in rules:
        for keyword in rule.keywords:
            norm_keyword = re.sub(r"\s+", "", keyword)
            if not norm_keyword:
                continue
            for norm_pos in _find_all(norm_text, norm_keyword):
                key = (rule.id, norm_pos)
                if key in seen_spans:
                    continue
                seen_spans.add(key)

                start_orig = index_map[norm_pos]
                end_orig = index_map[norm_pos + len(norm_keyword) - 1] + 1

                ctx_start = max(0, start_orig - CONTEXT_CHARS)
                ctx_end = min(len(text), end_orig + CONTEXT_CHARS)
                snippet = text[ctx_start:ctx_end]
                snippet = re.sub(r"\s+", " ", snippet).strip()
                if ctx_start > 0:
                    snippet = "…" + snippet
                if ctx_end < len(text):
                    snippet = snippet + "…"

                matches.append(
                    Match(
                        rule_id=rule.id,
                        category=rule.category,
                        risk_level=rule.risk_level,
                        matched_keyword=keyword,
                        current_wording=snippet,
                        suggestion=rule.suggestion,
                        reason=rule.reason,
                    )
                )

    risk_order = {"상": 0, "중": 1, "하": 2}
    matches.sort(key=lambda m: (risk_order.get(m.risk_level, 99), m.category))
    return matches
