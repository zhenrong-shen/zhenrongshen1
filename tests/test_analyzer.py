import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from risk_checker.analyzer import analyze_text
from risk_checker.rules import Rule, load_rules, save_rules


class AnalyzeTextTests(unittest.TestCase):
    def setUp(self):
        self.rules = [
            Rule(
                id="R001",
                category="출퇴근 통제",
                risk_level="상",
                keywords=["출근시간"],
                reason="지휘감독 근거",
                suggestion="자율 스케줄 표현으로 수정",
            )
        ]

    def test_exact_match(self):
        text = "매일 출근시간을 준수해야 합니다."
        matches = analyze_text(text, self.rules)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].rule_id, "R001")
        self.assertIn("출근시간", matches[0].current_wording)

    def test_ocr_whitespace_noise_is_still_matched(self):
        # OCR이 글자 사이에 공백을 잘못 인식한 경우에도 매칭되어야 한다.
        text = "매일 출 근 시 간을 준수해야 합니다."
        matches = analyze_text(text, self.rules)
        self.assertEqual(len(matches), 1)

    def test_no_match_returns_empty_list(self):
        text = "자유롭게 원하는 시간에 활동 가능합니다."
        matches = analyze_text(text, self.rules)
        self.assertEqual(matches, [])

    def test_empty_text_returns_empty_list(self):
        self.assertEqual(analyze_text("", self.rules), [])
        self.assertEqual(analyze_text("   ", self.rules), [])

    def test_duplicate_span_not_double_counted(self):
        rules = [
            Rule(
                id="R002",
                category="테스트",
                risk_level="중",
                keywords=["복장 규정", "복장규정"],
                reason="중복 표현 테스트",
                suggestion="삭제",
            )
        ]
        text = "복장규정을 반드시 준수하세요."
        matches = analyze_text(text, rules)
        # 정규화하면 두 키워드가 동일한 위치를 가리키므로 1건만 잡혀야 한다.
        self.assertEqual(len(matches), 1)

    def test_results_sorted_by_risk_level(self):
        rules = [
            Rule(id="R_low", category="c", risk_level="하", keywords=["낮음"], reason="", suggestion=""),
            Rule(id="R_high", category="c", risk_level="상", keywords=["높음"], reason="", suggestion=""),
        ]
        text = "낮음 그리고 높음"
        matches = analyze_text(text, rules)
        self.assertEqual([m.rule_id for m in matches], ["R_high", "R_low"])


class RulesIOTests(unittest.TestCase):
    def test_default_dictionary_loads_and_is_well_formed(self):
        rules = load_rules()
        self.assertGreater(len(rules), 0)
        for r in rules:
            self.assertIn(r.risk_level, {"상", "중", "하"})
            self.assertTrue(r.keywords)

    def test_save_and_reload_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "test_rules.json"
            rules = [
                Rule(id="R001", category="c", risk_level="상", keywords=["a", "b"], reason="r", suggestion="s"),
            ]
            save_rules(rules, tmp_path)
            loaded = load_rules(tmp_path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].keywords, ["a", "b"])


if __name__ == "__main__":
    unittest.main()
