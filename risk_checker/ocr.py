"""이미지에서 텍스트를 추출하는 OCR 모듈.

기본 엔진은 오프라인/무료인 Tesseract(한국어+영어)이며, 캡쳐 이미지가 작아
글자가 뭉개지는 문제를 줄이기 위해 업스케일/이진화 전처리를 거친다.
추후 상용 OCR(Naver Clova, Claude API 등)로 교체할 수 있도록 인터페이스를
함수 단위로 분리해 두었다.
"""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageOps

# 캡쳐 이미지의 짧은 변이 이 값보다 작으면 업스케일한다.
MIN_SHORT_SIDE = 1200


@dataclass
class OcrResult:
    text: str
    engine: str


def _preprocess(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")  # 그레이스케일

    short_side = min(image.size)
    if short_side < MIN_SHORT_SIDE and short_side > 0:
        scale = MIN_SHORT_SIDE / short_side
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.LANCZOS)

    image = ImageOps.autocontrast(image)
    return image


def extract_text(image: Image.Image, lang: str = "kor+eng") -> OcrResult:
    """단일 이미지에서 텍스트를 추출한다."""
    import pytesseract

    processed = _preprocess(image)
    # --psm 6: 채용공고 캡쳐처럼 문단이 밀집된 균일한 텍스트 블록에 적합.
    # 기본 psm(자동 레이아웃 분석)은 줄 순서가 뒤섞이는 문제가 있었다.
    text = pytesseract.image_to_string(processed, lang=lang, config="--psm 6")
    return OcrResult(text=text.strip(), engine=f"tesseract:{lang}")


def extract_text_from_images(images: list[Image.Image], lang: str = "kor+eng") -> str:
    """여러 장으로 나눠 캡쳐한 이미지를 업로드 순서대로 이어 붙여 하나의
    공고 텍스트로 합친다 (한 건이 여러 장일 때 사용)."""
    parts = [extract_text(img, lang=lang).text for img in images]
    return "\n".join(p for p in parts if p)
