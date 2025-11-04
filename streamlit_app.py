import streamlit as st
import pandas as pd
import io
import random
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import cm
from reportlab.lib.colors import black, blue

# -----------------------------
# Streamlit 기본 설정
# -----------------------------
st.title("📘 영어 단어 시험지 생성기 (2단 정렬 + 정답지 색 강조 + 밑줄 개선)")
st.write("CSV 또는 XLSX 파일을 업로드하세요. Numbers 파일도 변환 후 사용 가능합니다.")

uploaded_files = st.file_uploader(
    "📂 단어 스프레드시트 파일 업로드 (여러 개 가능)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

num_questions = st.number_input("출력할 문항 수", min_value=10, max_value=200, value=60, step=10)

# -----------------------------
# 파일 로드 함수
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
def make_pdf(word_pairs, is_answer_sheet=False):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(tmp.name, pagesize=A4)
    width, height = A4

    # ✅ 한글 폰트 등록
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
    c.setFont("HYSMyeongJo-Medium", 12)

    # 기본 여백 및 구조 설정
    left_margin = 2 * cm
    top_margin = 2 * cm
    bottom_margin = 2 * cm
    col_gap = 1.0 * cm
    col_width = (width - (left_margin * 2) - col_gap) / 2

    # 1페이지당 문항수
    per_col = 30
    per_page = per_col * 2
    line_height = 1.0 * cm

    total_pages = (len(word_pairs) - 1) // per_page + 1
    page_num = 1

    for page in range(total_pages):
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, len(word_pairs))
        page_data = word_pairs[start_idx:end_idx]

        for i, (eng, kor) in enumerate(page_data):
            col = 0 if i < per_col else 1
            row = i if i < per_col else i - per_col
            x = left_margin + col * (col_width + col_gap)
            y = height - top_margin - (row * line_height)

            num = start_idx + i + 1
            text = eng if eng else kor

            if is_answer_sheet:
                # 정답지: 색상 강조 (영어=검정, 한글=파랑)
                c.setFillColor(black)
                c.drawString(x, y, f"{num}. {eng}")
                if kor:
                    c.setFillColor(blue)
                    # 긴 뜻 자동 줄바꿈
                    max_width = col_width - 1.2 * cm
                    lines = []
                    cur_line = ""
                    for word in kor.split():
                        if pdfmetrics.stringWidth(cur_line + " " + word, "HYSMyeongJo-Medium", 12) < max_width:
                            cur_line += " " + word
                        else:
                            lines.append(cur_line.strip())
                            cur_line = word
                    lines.append(cur_line.strip())
                    y2 = y - 0.4 * cm
                    for line in lines:
                        c.drawString(x + 1.2 * cm, y2, line)
                        y2 -= 0.45 * cm
                    c.setFillColor(black)
            else:
                # 시험지: 단어 옆에 밑줄
                c.drawString(x, y, f"{num}. {text}")
                # 밑줄 시작점 = 단어 끝부분 + 여백
                if not eng or not kor:
                    word_width = pdfmetrics.stringWidth(f"{num}. {text}", "HYSMyeongJo-Medium", 12)
                    underline_start = x + word_width + 0.2 * cm
                    underline_end = underline_start + 3.5 * cm
                    underline_y = y - 0.2 * cm
                    c.line(underline_start, underline_y, underline_end, underline_y)

        # 페이지 번호
        c.setFont("HYSMyeongJo-Medium", 10)
        c.drawCentredString(width / 2, bottom_margin / 2, f"Page {page_num} / {total_pages}")
        if page < total_pages - 1:
            c.showPage()
            c.setFont("HYSMyeongJo-Medium", 12)
        page_num += 1

    c.save()
    return tmp.name

# -----------------------------
# 메인 로직
# -----------------------------
if uploaded_files:
    dfs = []
    for f in uploaded_files:
        df = load_file(f)
        if df is not None and len(df.columns) >= 2:
            dfs.append(df)

    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.iloc[:, :2]
        combined.columns = ["영어", "뜻"]
        combined = combined.dropna().drop_duplicates(subset=["영어"])
        combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

        # 문항 수 제한
        combined = combined.head(num_questions)

        # 절반 비우기
        half = len(combined) // 2
        test_df = combined.copy()
        test_df.loc[:half, "뜻"] = ""
        test_df.loc[half:, "영어"] = ""

        # PDF 생성
        pdf_path_test = make_pdf(test_df.values.tolist(), is_answer_sheet=False)
        pdf_path_answer = make_pdf(combined.values.tolist(), is_answer_sheet=True)

        # 다운로드 버튼
        with open(pdf_path_test, "rb") as f1, open(pdf_path_answer, "rb") as f2:
            st.download_button("📝 시험지 다운로드", data=f1, file_name="시험지.pdf", mime="application/pdf")
            st.download_button("✅ 정답지 다운로드", data=f2, file_name="정답지.pdf", mime="application/pdf")

        st.success("✅ 시험지와 정답지가 모두 정상적으로 생성되었습니다!")
        st.dataframe(test_df.head(10))
