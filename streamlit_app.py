import streamlit as st
import pandas as pd
import random
import io
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import black, red
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# -------------------------------
# 📘 폰트 등록 (한글 깨짐 방지)
# -------------------------------
pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

# -------------------------------
# 📘 파일명에서 Day 라벨 추출
# -------------------------------
def extract_day_label(filename):
    match = re.search(r'(Day\s*\d+)', filename, re.IGNORECASE)
    return match.group(1) if match else os.path.splitext(filename)[0]

# -------------------------------
# ✅ Day 인식 유틸 추가
# -------------------------------
def extract_day_number(filename):
    """파일명에서 Day 뒤 숫자만 추출"""
    m = re.search(r"Day\s*(\d+)", filename, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None

def get_day_range_label(uploaded_files):
    """여러 파일명에서 Day 숫자 범위를 찾아 'Day n - Day m' 형태로 반환"""
    days = []
    for f in uploaded_files:
        n = extract_day_number(f.name)
        if n is not None:
            days.append(n)
    if not days:
        return extract_day_label(uploaded_files[0].name)
    days = sorted(days)
    if len(days) == 1:
        return f"Day {days[0]}"
    return f"Day {days[0]} - Day {days[-1]}"

# -------------------------------
# 📘 시험지 PDF 생성 함수
# -------------------------------
def generate_exam_pdf(data, num_questions, file_label):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 기본 여백 설정
    left_margin = 24 * mm
    right_margin = 24 * mm
    top_margin = 62 * mm
    bottom_margin = 24 * mm

    # 문항당 높이 및 구역 설정
    line_height = 4 * mm
    col_gap = 49 * mm  # 111mm - 62mm = 49mm
    underline_length = 37 * mm

    # 한 페이지당 최대 문항수
    max_per_column = 30
    max_per_page = 60

    # ---------------------------
    # 헤더
    # ---------------------------
    def draw_header(page_num):
        c.setFont("HYSMyeongJo-Medium", 10)
        header_y = height - 30 * mm
        header_title = f"{file_label} 영어 단어 시험지"
        c.drawCentredString(width / 2, header_y, header_title)

        # 점수란
        c.setFont("HYSMyeongJo-Medium", 8)
        c.drawString(left_margin, header_y - 8 * mm, "이름: ____________________")
        c.drawString(left_margin + 60 * mm, header_y - 8 * mm, "반: ________")
        c.drawString(left_margin + 90 * mm, header_y - 8 * mm, "점수: ________")
        c.drawString(left_margin + 120 * mm, header_y - 8 * mm, "시험일: ____________")

    # ---------------------------
    # 페이지 번호
    # ---------------------------
    def draw_page_number(page_num):
        c.setFont("HYSMyeongJo-Medium", 6)
        c.drawCentredString(width / 2, bottom_margin / 2, f"- {page_num} -")

    # ---------------------------
    # 본문 출력
    # ---------------------------
    y = height - top_margin
    col_x_positions = [62 * mm, 152 * mm]
    col_label_x = [24 * mm, 111 * mm]
    page_num = 1
    question_count = 0

    draw_header(page_num)

    for i, (eng, kor, blank_eng) in enumerate(data):
        if question_count == max_per_page:
            draw_page_number(page_num)
            c.showPage()
            page_num += 1
            draw_header(page_num)
            y = height - top_margin
            question_count = 0

        col = (question_count // max_per_column)
        if col > 1:
            draw_page_number(page_num)
            c.showPage()
            page_num += 1
            draw_header(page_num)
            y = height - top_margin
            question_count = 0
            col = 0

        label_x = col_label_x[col]
        text_x = col_x_positions[col]
        underline_x_start = text_x
        underline_x_end = text_x + underline_length

        c.setFont("HYSMyeongJo-Medium", 8)
        question_num = i + 1
        c.drawString(label_x, y, f"{question_num}.")

        # 빈칸 여부 처리
        if blank_eng:
            # 영어 비워짐 → 영어 밑줄
            c.line(underline_x_start, y - 1, underline_x_end, y - 1)
            text = kor
            c.drawString(text_x, y, text)
        else:
            # 한글 비워짐 → 한글 밑줄
            c.line(underline_x_start, y - 1, underline_x_end, y - 1)
            text = eng
            c.drawString(text_x, y, text)

        y -= line_height
        question_count += 1

    draw_page_number(page_num)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# -------------------------------
# 📘 정답지 PDF 생성 함수
# -------------------------------
def generate_answer_pdf(data, file_label):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left_margin = 24 * mm
    bottom_margin = 24 * mm
    line_height = 4 * mm
    col_gap = 49 * mm
    underline_length = 37 * mm
    max_per_column = 30
    max_per_page = 60
    y = height - 62 * mm
    col_x_positions = [62 * mm, 152 * mm]
    col_label_x = [24 * mm, 111 * mm]
    page_num = 1
    question_count = 0

    c.setFont("HYSMyeongJo-Medium", 10)
    c.drawCentredString(width / 2, height - 30 * mm, f"{file_label} 영어 단어 시험지 - 정답지")

    for i, (eng, kor, blank_eng) in enumerate(data):
        if question_count == max_per_page:
            c.showPage()
            page_num += 1
            c.setFont("HYSMyeongJo-Medium", 10)
            c.drawCentredString(width / 2, height - 30 * mm, f"{file_label} 영어 단어 시험지 - 정답지")
            y = height - 62 * mm
            question_count = 0

        col = (question_count // max_per_column)
        if col > 1:
            c.showPage()
            page_num += 1
            c.setFont("HYSMyeongJo-Medium", 10)
            c.drawCentredString(width / 2, height - 30 * mm, f"{file_label} 영어 단어 시험지 - 정답지")
            y = height - 62 * mm
            question_count = 0
            col = 0

        label_x = col_label_x[col]
        text_x = col_x_positions[col]
        question_num = i + 1
        c.setFont("HYSMyeongJo-Medium", 8)
        c.setFillColor(red)
        c.drawString(label_x, y, f"{question_num}.")
        if blank_eng:
            c.drawString(text_x, y, f"{kor} → {eng}")
        else:
            c.drawString(text_x, y, f"{eng} → {kor}")
        c.setFillColor(black)
        y -= line_height
        question_count += 1

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# -------------------------------
# 📘 Streamlit UI
# -------------------------------
st.title("📘 영어 단어 시험지 생성기")

uploaded_files = st.file_uploader("엑셀(.xlsx) 또는 Numbers 변환 파일 업로드", type=["xlsx"], accept_multiple_files=True)
num_questions = st.number_input("출제할 문항 수", min_value=10, max_value=200, value=60, step=10)

if uploaded_files:
    file_label = get_day_range_label(uploaded_files)
    all_words = []

    for file in uploaded_files:
        try:
            df = pd.read_excel(file)
            df = df.dropna()
            for i, row in df.iterrows():
                if len(row) >= 2:
                    all_words.append((str(row[0]).strip(), str(row[1]).strip()))
        except Exception as e:
            st.error(f"{file.name} 읽는 중 오류: {e}")

    if len(all_words) == 0:
        st.warning("단어 데이터를 찾을 수 없습니다.")
    else:
        num_questions = min(num_questions, len(all_words))
        sampled_words = random.sample(all_words, num_questions)
        half = num_questions // 2
        data = [(eng, kor, i >= half) for i, (eng, kor) in enumerate(sampled_words)]

        exam_pdf = generate_exam_pdf(data, num_questions, file_label)
        answer_pdf = generate_answer_pdf(data, file_label)

        st.download_button("📄 시험지 다운로드", data=exam_pdf, file_name=f"{file_label}_시험지.pdf", mime="application/pdf")
        st.download_button("🧾 정답지 다운로드", data=answer_pdf, file_name=f"{file_label}_정답지.pdf", mime="application/pdf")
