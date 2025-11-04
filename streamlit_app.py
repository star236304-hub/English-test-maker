import streamlit as st
import pandas as pd
import random
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import cm
from reportlab.lib import colors

# --------------------------------------------------
# PDF 생성 함수
# --------------------------------------------------
def generate_test_pdf(words, num_questions, filename="vocab_test.pdf"):
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))  # 한글 폰트
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 여백 및 기본 설정
    margin_x = 2 * cm
    margin_y = 2 * cm
    column_gap = 1.5 * cm
    column_width = (width - 2 * margin_x - column_gap) / 2
    line_height = 0.8 * cm  # 줄 간격
    font_size = 6  # 2mm 폰트
    underline_length = 3.5 * cm

    c.setFont("HYSMyeongJo-Medium", font_size)

    items_per_col = 30
    total_items = min(num_questions, len(words))

    for i in range(total_items):
        col = (i // items_per_col) % 2
        row = i % items_per_col
        x = margin_x + col * (column_width + column_gap)
        y = height - margin_y - (row + 1) * line_height

        eng, kor, is_eng_blank = words[i]
        display_text = f"{i+1}. {kor}" if is_eng_blank else f"{i+1}. {eng}"
        c.drawString(x, y, display_text)

        text_width = pdfmetrics.stringWidth(display_text, "HYSMyeongJo-Medium", font_size)
        underline_start = x + text_width + 0.4 * cm
        underline_end = underline_start + underline_length

        c.line(underline_start, y - 0.05 * cm, underline_end, y - 0.05 * cm)

        if (i + 1) % 60 == 0 and i + 1 < total_items:
            c.drawCentredString(width / 2, 1 * cm, f"- Page {c.getPageNumber()} -")
            c.showPage()
            c.setFont("HYSMyeongJo-Medium", font_size)

    c.drawCentredString(width / 2, 1 * cm, f"- Page {c.getPageNumber()} -")
    c.save()
    buffer.seek(0)
    return buffer


# --------------------------------------------------
# 정답지 생성 함수
# --------------------------------------------------
def generate_answer_pdf(words, num_questions, filename="answer_sheet.pdf"):
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 2 * cm
    margin_y = 2 * cm
    column_gap = 1.5 * cm
    column_width = (width - 2 * margin_x - column_gap) / 2
    line_height = 0.8 * cm
    font_size = 6
    underline_length = 3.5 * cm

    c.setFont("HYSMyeongJo-Medium", font_size)
    items_per_col = 30
    total_items = min(num_questions, len(words))

    for i in range(total_items):
        col = (i // items_per_col) % 2
        row = i % items_per_col
        x = margin_x + col * (column_width + column_gap)
        y = height - margin_y - (row + 1) * line_height

        eng, kor, is_eng_blank = words[i]
        display_text = f"{i+1}. {kor}" if is_eng_blank else f"{i+1}. {eng}"
        c.drawString(x, y, display_text)

        text_width = pdfmetrics.stringWidth(display_text, "HYSMyeongJo-Medium", font_size)
        underline_start = x + text_width + 0.4 * cm

        c.setFillColor(colors.red)
        answer_text = eng if is_eng_blank else kor
        c.drawString(underline_start + 0.2 * cm, y, answer_text)
        c.setFillColor(colors.black)

        if (i + 1) % 60 == 0 and i + 1 < total_items:
            c.drawCentredString(width / 2, 1 * cm, f"- Page {c.getPageNumber()} -")
            c.showPage()
            c.setFont("HYSMyeongJo-Medium", font_size)

    c.drawCentredString(width / 2, 1 * cm, f"- Page {c.getPageNumber()} -")
    c.save()
    buffer.seek(0)
    return buffer


# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------
st.title("📘 영어 단어 시험지 생성기 (iPad 한글 완벽 지원)")
st.write("엑셀 또는 Numbers에서 내보낸 파일을 업로드하면 자동으로 시험지와 정답지를 만들어드립니다.")

uploaded_files = st.file_uploader("📂 파일 업로드 (여러 개 가능)", type=["xlsx", "csv"], accept_multiple_files=True)

num_questions = st.number_input("출제할 문항 수 선택", min_value=10, max_value=200, value=60, step=10)

if uploaded_files:
    all_words = pd.DataFrame()

    for uploaded_file in uploaded_files:
        try:
            df = pd.read_excel(uploaded_file)
        except:
            df = pd.read_csv(uploaded_file, encoding="utf-8")

        df.columns = [col.strip().lower() for col in df.columns]

        # 예상되는 컬럼명 처리
        if "english" in df.columns and "korean" in df.columns:
            subset = df[["english", "korean"]]
        elif "단어" in df.columns and "뜻" in df.columns:
            subset = df[["단어", "뜻"]]
            subset.columns = ["english", "korean"]
        else:
            st.warning(f"{uploaded_file.name} 파일의 컬럼명을 확인해주세요.")
            continue

        all_words = pd.concat([all_words, subset], ignore_index=True)

    # 중복 제거
    all_words.drop_duplicates(inplace=True)

    # 무작위 선택
    selected = all_words.sample(min(num_questions, len(all_words)), random_state=42)
    half = len(selected) // 2
    word_pairs = []

    for i, row in enumerate(selected.itertuples(index=False)):
        is_eng_blank = i < half
        word_pairs.append((row.english, row.korean, is_eng_blank))

    # PDF 생성
    test_pdf = generate_test_pdf(word_pairs, num_questions)
    answer_pdf = generate_answer_pdf(word_pairs, num_questions)

    st.download_button("📄 시험지 다운로드", data=test_pdf, file_name="vocab_test.pdf")
    st.download_button("✅ 정답지 다운로드", data=answer_pdf, file_name="answer_sheet.pdf")

else:
    st.info("엑셀(.xlsx) 또는 CSV 파일을 업로드해주세요.")
