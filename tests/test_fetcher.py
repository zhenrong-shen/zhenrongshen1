import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from risk_checker.fetcher import FetchError, fetch_url_text, html_to_text


class HtmlToTextTests(unittest.TestCase):
    def test_strips_script_style_and_nav(self):
        html = """
        <html>
          <head><style>.a{color:red}</style></head>
          <body>
            <nav>메뉴</nav>
            <script>var x = 1;</script>
            <main>
              <h1>파트너 모집 공고</h1>
              <p>출근시간을 반드시 준수해야 합니다.</p>
            </main>
            <footer>회사 정보</footer>
          </body>
        </html>
        """
        text = html_to_text(html)
        self.assertIn("파트너 모집 공고", text)
        self.assertIn("출근시간을 반드시 준수해야 합니다.", text)
        self.assertNotIn("메뉴", text)
        self.assertNotIn("var x", text)
        self.assertNotIn("회사 정보", text)


class FetchUrlTextTests(unittest.TestCase):
    def _mock_response(self, html: str, status_code: int = 200, url: str = "https://example.com/job/1"):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = {}
        resp.content = html.encode("utf-8")
        resp.encoding = "utf-8"
        resp.apparent_encoding = "utf-8"
        resp.url = url
        return resp

    def test_missing_url_raises(self):
        with self.assertRaises(FetchError):
            fetch_url_text("")

    def test_invalid_url_raises(self):
        with self.assertRaises(FetchError):
            fetch_url_text("not a url")

    @patch("risk_checker.fetcher.requests.get")
    def test_successful_fetch_returns_text(self, mock_get):
        mock_get.return_value = self._mock_response(
            "<html><body><p>매일 실적 보고 필수</p></body></html>"
        )
        result = fetch_url_text("example.com/job/1")
        self.assertIn("매일 실적 보고 필수", result.text)
        self.assertEqual(result.final_url, "https://example.com/job/1")

    @patch("risk_checker.fetcher.requests.get")
    def test_http_error_raises_fetch_error(self, mock_get):
        mock_get.return_value = self._mock_response("<html></html>", status_code=404)
        with self.assertRaises(FetchError):
            fetch_url_text("https://example.com/missing")

    @patch("risk_checker.fetcher.requests.get")
    def test_empty_body_raises_fetch_error(self, mock_get):
        mock_get.return_value = self._mock_response("<html><body><script>1</script></body></html>")
        with self.assertRaises(FetchError):
            fetch_url_text("https://example.com/empty")

    @patch("risk_checker.fetcher.requests.get")
    def test_network_error_raises_fetch_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        with self.assertRaises(FetchError):
            fetch_url_text("https://example.com/down")


if __name__ == "__main__":
    unittest.main()
