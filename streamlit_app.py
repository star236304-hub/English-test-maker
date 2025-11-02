import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import cm
import tempfile
import random

# -----------------------------
# 기본 설정
# -----------------------------
st.title("📘 영어 단어 시험지 생성기 (iPad 한글 지원)")
st.write("Numbers나 Excel로 만든 파일을 CSV 또는 XLSX로 저장 후 업로드하세요.")
st.write("➡️ 절반은 영어 비우기, 절반은 뜻 비우기 형태로 자동 구성됩니다.")

uploaded_files = st.file_uploader(
    "단어 스프레드시트 파일을 업로드하세요 (여러 개 선택 가능)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

# -----------------------------
# 파일 읽기 (chardet 없이 처리)
# -----------------------------
def load_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        # Bytes를 읽고 인코딩 자동 추정
        raw = uploaded_file.read()
        # utf-8 실패 시 cp949 (한글 윈도우용)로 재시도
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(raw), encoding="cp949")
        return df
    elif name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)
    else:
        return None

# -----------------------------
# PDF 생성 (한글 폰트 적용)
# -----------------------------
def make_pdf(word_pairs):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(tmp.name, pagesize=A4)
    width, height = A4

    # ✅ 한글 폰트 등록 (iPad에서도 내장 지원)
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
    c.setFont("HYSMyeongJo-Medium", 14)

    x_margin, y_margin = 2 * cm, 2 * cm
    y = height - y_margin

    c.drawString(x_margin, y, "영어 단어 시험지")
    y -= 1.5 * cm

    c.setFont("HYSMyeongJo-Medium", 11)

    for i, (eng, kor) in enumerate(word_pairs, 1):
        line = f"{i}. {eng or ''}   -   {kor or ''}"
        c.drawString(x_margin, y, line)
        y -= 0.8 * cm
        if y < 2 * cm:
            c.showPage()
            c.setFont("HYSMyeongJo-Medium", 11)
            y = height - y_margin

    c.save()
    return tmp.name

# -----------------------------
# 메인 로직
# -----------------------------
if uploaded_files:
    dfs = []
    for uploaded_file in uploaded_files:
        try:
            df = load_file(uploaded_file)
            if df is not None and len(df.columns) >= 2:
                dfs.append(df)
        except Exception as e:
            st.error(f"{uploaded_file.name} 읽기 오류: {e}")

    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.iloc[:, :2]
        combined.columns = ["영어", "뜻"]

        # 중복 및 결측 제거
        combined = combined.dropna().drop_duplicates(subset=["영어"])
        combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

        # 절반씩 비우기
        half = len(combined) // 2
        test_df = combined.copy()
        test_df.loc[:half, "뜻"] = ""
        test_df.loc[half:, "영어"] = ""

        # PDF 생성
        pdf_path = make_pdf(test_df.values.tolist())

        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📄 시험지 PDF 다운로드",
                data=f,
                file_name="영어단어시험지.pdf",
                mime="application/pdf"
            )

        st.success("✅ 시험지 생성 완료!")
        st.dataframe(test_df.head(10))
    else:
        st.warning("유효한 데이터를 가진 파일이 없습니다.")
