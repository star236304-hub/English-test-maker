# streamlit_app.py
import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import random
import io

st.set_page_config(page_title="영어 단어 시험지 생성기", layout="centered")
st.title("📘 영어 단어 시험지 생성기")

uploaded_files = st.file_uploader(
    "엑셀 또는 CSV 파일 업로드 (여러 개 가능)", 
    type=["xlsx", "csv"], 
    accept_multiple_files=True
)

num_words = st.number_input("출제할 단어 수 (짝수 권장)", min_value=2, value=10, step=1)

# 옵션: 헤더 명 지정(선택)
eng_header = st.text_input("영어 단어 컬럼 이름 예시 (비워두면 자동탐지)", value="")
kor_header = st.text_input("한국어 뜻 컬럼 이름 예시 (비워두면 자동탐지)", value="")

if st.button("시험지 PDF 만들기"):
    all_words = []

    # 1) 업로드 파일에서 단어 수집
    for f in uploaded_files:
        try:
            if f.name.lower().endswith(".xlsx"):
                df = pd.read_excel(f)
            else:
                df = pd.read_csv(f)
        except Exception as e:
            st.warning(f"{f.name} 읽는 중 오류: {e}")
            continue

        # 컬럼명 정리
        cols = [c.strip() for c in df.columns]
        df.columns = cols

        # 영어/한글 컬럼 자동 인식 (사용자가 입력하면 우선)
        def find_col(preferred, keywords):
            if preferred and preferred in df.columns:
                return preferred
            for k in df.columns:
                kl = k.lower()
                if any(word in kl for word in keywords):
                    return k
            return None

        eng_col = find_col(eng_header, ["eng", "word", "english", "단어"])
        kor_col = find_col(kor_header, ["kor", "mean", "korean", "뜻", "의미"])

        if not (eng_col and kor_col):
            st.info(f"{f.name}: 영어/한국어 컬럼을 자동으로 찾지 못했습니다. 파일을 확인하세요.")
            continue

        for _, row in df.iterrows():
            e = str(row.get(eng_col, "")).strip()
            k = str(row.get(kor_col, "")).strip()
            if e and k and e.lower() != "nan" and k.lower() != "nan":
                all_words.append((e.strip(), k.strip()))

    # 2) 중복 제거(영어 소문자 기준)
    seen = set()
    unique_words = []
    for e, k in all_words:
        key = e.lower()
        if key not in seen:
            seen.add(key)
            unique_words.append((e, k))

    if len(unique_words) == 0:
        st.warning("단어가 감지되지 않았습니다. 파일과 컬럼을 확인해주세요.")
    else:
        # 3) 샘플링 및 섞기
        random.shuffle(unique_words)
        n = min(int(num_words), len(unique_words))
        selected = unique_words[:n]

        # 4) 절반 나누기 (만약 홀수면 앞 절반이 더 적게/많게 될 수 있음)
        half = n // 2
        english_only = selected[:half]   # 뜻 빈칸
        korean_only = selected[half:]    # 영어 빈칸

        # 5) 시험지 PDF 생성
        buffer_test = io.BytesIO()
        doc_test = SimpleDocTemplate(buffer_test, pagesize=A4)
        styles = getSampleStyleSheet()
        story_test = [Paragraph("📘 영어 단어 시험지", styles["Title"]), Spacer(1, 20)]

        idx = 1
        for e, k in english_only:
            story_test.append(Paragraph(f"{idx}. {e}  -  __________", styles["Normal"]))
            story_test.append(Spacer(1, 8))
            idx += 1

        for e, k in korean_only:
            story_test.append(Paragraph(f"{idx}. __________  -  {k}", styles["Normal"]))
            story_test.append(Spacer(1, 8))
            idx += 1

        doc_test.build(story_test)

        # 6) 정답지 생성
        buffer_ans = io.BytesIO()
        doc_ans = SimpleDocTemplate(buffer_ans, pagesize=A4)
        story_ans = [Paragraph("📖 영어 단어 정답지", styles["Title"]), Spacer(1, 20)]

        idx = 1
        for e, k in selected:
            story_ans.append(Paragraph(f"{idx}. {e} - {k}", styles["Normal"]))
            story_ans.append(Spacer(1, 6))
            idx += 1

        doc_ans.build(story_ans)

        # 7) 다운로드 버튼 (Streamlit)
        st.download_button(
            "📄 시험지 PDF 다운로드", 
            data=buffer_test.getvalue(), 
            file_name="word_test.pdf",
            mime="application/pdf"
        )
        st.download_button(
            "📝 정답지 PDF 다운로드", 
            data=buffer_ans.getvalue(), 
            file_name="word_answers.pdf",
            mime="application/pdf"
        )

        st.success(f"총 {n}개 단어로 시험지를 생성했습니다. (중복 제거 후)")
