"""채용 사이트 URL에서 공고 본문 텍스트를 가져오는 모듈.

알바몬·잡코리아 등 채용 사이트는 로그인/JS 렌더링 등으로 본문을 가져오지
못하는 경우가 있다. 이런 경우 사용자에게 원인을 알리고, 앱에서는 화면 캡쳐
이미지 업로드(OCR)로 대체하도록 안내한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# 채용 사이트가 봇으로 인식해 차단하는 것을 줄이기 위한 일반 브라우저 UA.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 15
MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5MB 초과 응답은 차단

# 본문과 무관한 영역(내비게이션, 광고, 스크립트 등)으로 보고 제거할 태그.
_NOISE_TAGS = ["script", "style", "noscript", "header", "footer", "nav", "aside", "svg", "form"]


class FetchError(Exception):
    """URL에서 텍스트를 가져오지 못했을 때 발생하는 예외."""


@dataclass
class FetchResult:
    text: str
    final_url: str


def _validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise FetchError("URL을 입력해 주세요.")
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise FetchError("올바른 URL 형식이 아닙니다.")
    return url


def fetch_html(url: str) -> tuple[str, str]:
    """URL을 요청해 (HTML, 최종 URL)을 반환한다. 실패 시 FetchError를 던진다."""
    url = _validate_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
    try:
        resp = requests.get(
            url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=True
        )
    except requests.exceptions.RequestException as e:
        raise FetchError(f"페이지를 가져오지 못했습니다: {e}") from e

    content_length = resp.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_CONTENT_BYTES:
        resp.close()
        raise FetchError("응답 크기가 너무 커서 처리할 수 없습니다.")

    raw = resp.content[:MAX_CONTENT_BYTES]
    if resp.status_code >= 400:
        raise FetchError(f"페이지를 가져오지 못했습니다 (HTTP {resp.status_code}).")

    resp.encoding = resp.encoding or resp.apparent_encoding
    html = raw.decode(resp.encoding or "utf-8", errors="replace")
    return html, resp.url


def html_to_text(html: str) -> str:
    """HTML에서 내비게이션/스크립트 등을 제외한 본문 텍스트를 추출한다."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    # 블록 요소 사이에는 줄바꿈을 넣어 문단 구분을 살린다.
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def fetch_url_text(url: str) -> FetchResult:
    """채용공고 URL에서 본문으로 추정되는 텍스트를 가져온다.

    JS로 본문을 렌더링하는 사이트는 빈 결과나 극히 짧은 텍스트만 나올 수
    있으므로, 호출부에서 결과 길이를 확인해 사용자에게 캡쳐 업로드를
    안내하는 것을 권장한다.
    """
    html, final_url = fetch_html(url)
    text = html_to_text(html)
    if not text.strip():
        raise FetchError(
            "페이지에서 텍스트를 추출하지 못했습니다. "
            "로그인이 필요하거나 자바스크립트로 내용을 표시하는 사이트일 수 있습니다. "
            "화면 캡쳐 이미지 업로드 기능을 이용해 주세요."
        )
    return FetchResult(text=text, final_url=final_url)
