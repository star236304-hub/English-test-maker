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
import math

# -----------------------------
# 기본 설정
# -----------------------------
st.title("📘 영어 단어 시험지 & 정답지 자동 생성기 (iPad 한글 지원)")
st.write("CSV 또는 XLSX 파일을 업로드하면 자동으로 시험지와 정답지를 만들어줍니다.")
st.write("➡️ 절반은 영어, 절반은 뜻을 비운 형태로 구성됩니다.")

uploaded_files = st.file_uploader(
    "단어 스프레드시트 파일을 업로드하세요 (여러 개 선택 가능)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

# -----------------------------
# 파일 읽기 (인코딩 자동)
# -----------------------------
def load_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        raw = uploaded_file.read()
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
# PDF 생성 함수
# -----------------------------
def make_pdf(word_pairs, show_answer=False):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(tmp.name, pagesize=A4)
    width, height = A4

    # ✅ 한글 폰트 등록
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
    c.setFont("HYSMyeongJo-Medium", 12)

    # 여백 및 위치 설정
    margin_x = 2 * cm
    margin_y = 2 * cm
    column_gap = 9 * cm  # 두 번째 열 x 위치
    line_height = 0.8 * cm
    max_per_column = 30
    max_per_page = 60

    total = len(word_pairs)
    total_pages = math.ceil(total / max_per_page)

    index = 0
    for page in range(total_pages):
        c.setFont("HYSMyeongJo-Medium", 14)
        c.drawString(margin_x, height - margin_y, "영어 단어 시험지" if not show_answer else "정답지")
        c.setFont("HYSMyeongJo-Medium", 11)
        y_positions = [height - margin_y - 1.2 * cm, height - margin_y - 1.2 * cm]  # 왼쪽, 오른쪽 시작 Y
        x_positions = [margin_x, margin_x + column_gap]

        for col in range(2):  # 왼쪽, 오른쪽 열
            for i in range(max_per_column):
                if index >= total:
                    break

                eng, kor = word_pairs[index]
                index += 1

                # 문제 번호
                num = i + 1 + (col * max_per_column) + (page * max_per_page)
                text = ""
                if show_answer:
                    # 정답지 → 둘 다 표시
                    text = f"{num}. {eng} ({kor})"
                else:
                    # 시험지 → 절반씩 비우기 + 밑줄
                    if eng and not kor:
                        text = f"{num}. {eng}"
                    elif kor and not eng:
                        text = f"{num}. {kor}"
                    else:
                        text = f"{num}. "

                # 왼쪽 정렬로 텍스트 출력
                y = y_positions[col]
                c.drawString(x_positions[col], y, text)

                # 빈칸 밑줄
                if not show_answer:
                    if (not kor and eng) or (not eng and kor):
                        underline_start = x_positions[col] + 4.5 * cm
                        underline_end = underline_start + 5 * cm
                        c.line(underline_start, y - 0.1 * cm, underline_end, y - 0.1 * cm)

                y_positions[col] -= line_height

            # 다음 열로 넘어가기 전에 y위치 초기화
            y_positions[col] = height - margin_y - 1.2 * cm

        c.showPage()

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

        # 중복, 결측 제거
        combined = combined.dropna().drop_duplicates(subset=["영어"])
        combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

        # 절반씩 비우기
        half = len(combined) // 2
        test_df = combined.copy()
        test_df.loc[:half, "뜻"] = ""
        test_df.loc[half:, "영어"] = ""

        # PDF 생성
        test_pdf = make_pdf(test_df.values.tolist(), show_answer=False)
        answer_pdf = make_pdf(combined.values.tolist(), show_answer=True)

        with open(test_pdf, "rb") as f:
            st.download_button(
                label="📄 시험지 PDF 다운로드",
                data=f,
                file_name="영어단어시험지.pdf",
                mime="application/pdf"
            )

        with open(answer_pdf, "rb") as f:
            st.download_button(
                label="✅ 정답지 PDF 다운로드",
                data=f,
                file_name="영어단어정답지.pdf",
                mime="application/pdf"
            )

        st.success("✅ 시험지 및 정답지 생성 완료!")
        st.dataframe(test_df.head(10))
    else:
        st.warning("유효한 데이터를 가진 파일이 없습니다.")
