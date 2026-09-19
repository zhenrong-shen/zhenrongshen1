"""동화세상에듀코 채용공고 근로자성 리스크 워딩 점검 도구 (Streamlit 앱).

사용 방법:
    streamlit run app.py

기능:
  1) 채용공고 텍스트를 직접 붙여넣거나, 화면 캡쳐 이미지를 업로드하면 OCR로
     텍스트를 추출한다. 공고 내용이 길어 여러 장으로 나눠 캡쳐한 경우에도
     업로드 순서대로 이어붙여 한 건으로 분석할 수 있다.
  2) 추출된 텍스트를 위험 워딩 사전과 대조하여 "현재워딩 => 수정/삭제 제안"
     형태로 결과를 보여준다.
  3) 위험 워딩 사전은 앱 안에서 직접 추가·수정·삭제할 수 있다.
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st
from PIL import Image

from risk_checker.analyzer import analyze_text
from risk_checker.ocr import extract_text
from risk_checker.rules import Rule, load_rules, next_rule_id, save_rules

st.set_page_config(page_title="채용공고 근로자성 리스크 점검", layout="wide")

RISK_EMOJI = {"상": "🔴 상", "중": "🟠 중", "하": "🟡 하"}


def _init_state():
    st.session_state.setdefault("ocr_text", "")
    st.session_state.setdefault("uploaded_texts", {})


def analyze_tab():
    st.header("1. 공고 내용 입력")
    input_mode = st.radio(
        "입력 방식을 선택하세요",
        ["텍스트 붙여넣기", "화면 캡쳐 이미지 업로드"],
        horizontal=True,
    )

    combined_text = ""

    if input_mode == "텍스트 붙여넣기":
        combined_text = st.text_area(
            "채용공고 텍스트를 붙여넣으세요", height=280, key="pasted_text"
        )
    else:
        st.caption(
            "공고 내용이 길어 한 화면에 다 안 잡히면, 이어지는 부분을 나눠서 "
            "여러 장으로 캡쳐한 뒤 한 번에 업로드하세요. **선택(업로드)한 순서대로 "
            "이어붙여** 한 건으로 분석합니다."
        )
        files = st.file_uploader(
            "캡쳐 이미지 업로드 (여러 장 선택 가능, 업로드 순서 = 이어붙이는 순서)",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            accept_multiple_files=True,
        )

        if files:
            cols = st.columns(min(4, len(files)))
            for i, f in enumerate(files):
                with cols[i % len(cols)]:
                    st.image(f, caption=f"{i+1}. {f.name}", use_container_width=True)

            if st.button("🔎 OCR로 텍스트 추출", type="primary"):
                texts = []
                progress = st.progress(0.0, text="OCR 처리 중...")
                for i, f in enumerate(files):
                    image = Image.open(io.BytesIO(f.getvalue()))
                    result = extract_text(image)
                    texts.append(result.text)
                    progress.progress((i + 1) / len(files), text=f"OCR 처리 중... ({i+1}/{len(files)})")
                progress.empty()
                st.session_state["ocr_text"] = "\n".join(t for t in texts if t)
                st.success(f"{len(files)}장의 이미지에서 텍스트를 추출했습니다. 아래에서 오탈자를 확인·수정하세요.")

        combined_text = st.text_area(
            "추출된 텍스트 (OCR 오류가 있으면 직접 수정한 뒤 분석하세요)",
            value=st.session_state.get("ocr_text", ""),
            height=280,
            key="ocr_text_area",
        )
        st.session_state["ocr_text"] = combined_text

    st.divider()
    st.header("2. 위험 워딩 분석")

    rules = load_rules()

    if st.button("⚠️ 위험 워딩 분석 실행", type="primary", disabled=not combined_text.strip()):
        matches = analyze_text(combined_text, rules)
        st.session_state["last_matches"] = matches

    matches = st.session_state.get("last_matches")
    if matches is None:
        st.info("텍스트를 입력한 뒤 분석 버튼을 눌러주세요.")
        return

    if not matches:
        st.success("사전에 등록된 위험 워딩이 발견되지 않았습니다. (사전에 없는 새로운 표현은 놓칠 수 있으니 참고용으로만 활용하세요.)")
        return

    df = pd.DataFrame(
        [
            {
                "위험도": RISK_EMOJI.get(m.risk_level, m.risk_level),
                "분류": m.category,
                "현재워딩": m.current_wording,
                "수정/삭제 제안": m.suggestion,
                "판단 근거": m.reason,
                "규칙 ID": m.rule_id,
            }
            for m in matches
        ]
    )
    st.warning(f"총 {len(matches)}건의 위험 워딩이 발견되었습니다.")
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("결과 CSV 다운로드", csv, file_name="risk_wording_result.csv", mime="text/csv")


def dictionary_tab():
    st.header("위험 워딩 사전 관리")
    st.caption(
        "여기서 위험 워딩 판단 기준(사전)을 추가·수정·삭제할 수 있습니다. "
        "키워드 열에는 쉼표(,)로 구분해 여러 표현을 등록하세요."
    )

    rules = load_rules()
    df = pd.DataFrame(
        [
            {
                "id": r.id,
                "category": r.category,
                "risk_level": r.risk_level,
                "keywords": ", ".join(r.keywords),
                "reason": r.reason,
                "suggestion": r.suggestion,
            }
            for r in rules
        ]
    )

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "risk_level": st.column_config.SelectboxColumn(options=["상", "중", "하"]),
        },
        key="rules_editor",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("💾 사전 저장", type="primary"):
            new_rules = []
            existing_ids = set()
            for _, row in edited_df.iterrows():
                rid = str(row.get("id") or "").strip()
                if not rid or rid in existing_ids:
                    rid = next_rule_id(new_rules)
                existing_ids.add(rid)
                keywords = [k.strip() for k in str(row.get("keywords") or "").split(",") if k.strip()]
                new_rules.append(
                    Rule(
                        id=rid,
                        category=str(row.get("category") or "").strip(),
                        risk_level=str(row.get("risk_level") or "중").strip(),
                        keywords=keywords,
                        reason=str(row.get("reason") or "").strip(),
                        suggestion=str(row.get("suggestion") or "").strip(),
                    )
                )
            save_rules(new_rules)
            st.success("사전을 저장했습니다.")
            st.rerun()


def main():
    _init_state()
    st.title("📋 동화세상에듀코 채용공고 근로자성 리스크 점검")
    st.caption(
        "알바몬·잡코리아 등에 게재된 채용공고 텍스트/캡쳐 이미지에서 근로자성 인정 "
        "위험이 있는 표현을 찾아 '현재워딩 → 수정·삭제 제안'을 안내합니다. "
        "본 도구의 결과는 참고용이며, 최종 판단은 노무 전문가 검토를 받으시기 바랍니다."
    )

    tab1, tab2 = st.tabs(["공고 분석", "위험 워딩 사전 관리"])
    with tab1:
        analyze_tab()
    with tab2:
        dictionary_tab()


if __name__ == "__main__":
    main()
