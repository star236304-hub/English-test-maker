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
# 페이지 기본 설정
# -----------------------------
st.title("📘 영어 단어 시험지 생성기 (2단 정렬 + 정답지 색 강조)")
st.write("CSV 또는 XLSX 파일을 업로드하세요. Numbers에서도 변환 가능해요!")

uploaded_files = st.file_uploader(
    "📂 단어 스프레드시트 파일 업로드 (여러 개 가능)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

num_questions = st.number_input("출력할 문항 수", min_value=10, max_value=200, value=60, step=10)

# -----------------------------
# 파일 읽기 함수
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

    # 기본 여백 설정
    left_margin = 2 * cm
    top_margin = 2 * cm
    bottom_margin = 2 * cm

    # 열 배치 (2단)
    col_width = (width - 4 * cm) / 2
    line_height = 0.8 * cm
    max_per_col = 30

    total_pages = (len(word_pairs) - 1) // 60 + 1
    page_num = 1
    y_positions = [height - top_margin - i * line_height for i in range(max_per_col)]

    # 텍스트 출력
    for idx, (eng, kor) in enumerate(word_pairs):
        col = (idx // max_per_col) % 2  # 왼쪽(0) / 오른쪽(1)
        row = idx % max_per_col
        x = left_margin + col * (col_width + 1 * cm)
        y = y_positions[row]

        if is_answer_sheet:
            # 정답지는 색상 강조
            if eng and kor:
                c.setFillColor(black)
                c.drawString(x, y, f"{idx+1}. {eng}")
                c.setFillColor(blue)
                text_y = y - 0.3 * cm
                # 긴 뜻 자동 줄바꿈
                max_width = col_width - 1 * cm
                words = []
                cur_line = ""
                for word in kor.split():
                    if pdfmetrics.stringWidth(cur_line + " " + word, "HYSMyeongJo-Medium", 12) < max_width:
                        cur_line += " " + word
                    else:
                        words.append(cur_line.strip())
                        cur_line = word
                words.append(cur_line.strip())
                for line in words:
                    text_y -= 0.5 * cm
                    c.drawString(x + 1 * cm, text_y, line)
                c.setFillColor(black)
            else:
                text = eng if eng else kor
                c.drawString(x, y, f"{idx+1}. {text}")
        else:
            # 시험지: 빈칸 밑줄
            shown = eng if eng else kor
            c.drawString(x, y, f"{idx+1}. {shown}")
            # 밑줄 (빈칸만)
            if not eng or not kor:
                underline_y = y - 0.2 * cm
                c.line(x + 1 * cm, underline_y, x + col_width - 0.5 * cm, underline_y)

        # 페이지 넘김
        if (idx + 1) % 60 == 0 and idx < len(word_pairs) - 1:
            c.setFont("HYSMyeongJo-Medium", 10)
            c.drawCentredString(width / 2, bottom_margin / 2, f"Page {page_num} / {total_pages}")
            c.showPage()
            c.setFont("HYSMyeongJo-Medium", 12)
            page_num += 1

    # 마지막 페이지 번호 출력
    c.setFont("HYSMyeongJo-Medium", 10)
    c.drawCentredString(width / 2, bottom_margin / 2, f"Page {page_num} / {total_pages}")

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

        # 사용자 지정 문항 수만큼 추출
        combined = combined.head(num_questions)

        # 절반 비우기
        half = len(combined) // 2
        test_df = combined.copy()
        test_df.loc[:half, "뜻"] = ""
        test_df.loc[half:, "영어"] = ""

        # 시험지 PDF 생성
        pdf_path_test = make_pdf(test_df.values.tolist(), is_answer_sheet=False)
        pdf_path_answer = make_pdf(combined.values.tolist(), is_answer_sheet=True)

        # 다운로드 버튼
        with open(pdf_path_test, "rb") as f1, open(pdf_path_answer, "rb") as f2:
            st.download_button("📝 시험지 다운로드", data=f1, file_name="시험지.pdf", mime="application/pdf")
            st.download_button("✅ 정답지 다운로드", data=f2, file_name="정답지.pdf", mime="application/pdf")

        st.success("✅ 시험지와 정답지가 모두 생성되었습니다!")
        st.dataframe(test_df.head(10))
