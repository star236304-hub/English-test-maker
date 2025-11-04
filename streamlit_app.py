import streamlit as st
import pandas as pd
import random
import io
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import cm
from reportlab.lib import colors

# --------------------------------------------------------
# ⚙️ PDF 생성 함수 (시험지 & 정답지 공용)
# --------------------------------------------------------
def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, line_spacing):
    """한글 줄바꿈 기능 (폭 초과 시 자동 줄바꿈)"""
    words = list(text)
    lines = []
    current_line = ""

    for ch in words:
        if pdfmetrics.stringWidth(current_line + ch, font_name, font_size) < max_width:
            current_line += ch
        else:
            lines.append(current_line)
            current_line = ch
    lines.append(current_line)

    for i, line in enumerate(lines):
        c.drawString(x, y - (i * line_spacing), line)
    return len(lines)


def generate_pdf(words, num_questions, header_title, is_answer=False):
    """시험지 또는 정답지 PDF 생성"""
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ------------------ 기본 좌표 설정 ------------------
    left_margin = 2.4 * cm     # 왼쪽 여백 24mm
    right_col_x = 11.1 * cm    # 오른쪽 열 시작점 111mm
    underline_len = 3.7 * cm   # 밑줄 길이 37mm
    y_top_start = height - 6.2 * cm   # 상단 62mm 비움
    bottom_margin = 2.4 * cm   # 하단 24mm 비움
    line_gap = 0.4 * cm        # 행간 4mm
    font_size = 6              # 2mm 크기
    underline_offset = 0.2 * cm

    c.setFont("HYSMyeongJo-Medium", font_size)

    # ------------------ 헤더 ------------------
    header_y = height - 2.5 * cm
    c.setLineWidth(0.3)
    c.line(left_margin, header_y + 0.3 * cm, width - left_margin, header_y + 0.3 * cm)

    c.setFont("HYSMyeongJo-Medium", 10)
    c.drawCentredString(width / 2, header_y, f"{header_title} 영어 단어 시험지")

    c.setFont("HYSMyeongJo-Medium", 7)
    info_text = "이름: ___________________   반: ________   점수: ________   시험일: __________"
    c.drawCentredString(width / 2, header_y - 0.5 * cm, info_text)

    c.line(left_margin, header_y - 0.8 * cm, width - left_margin, header_y - 0.8 * cm)

    # ------------------ 문항 배치 ------------------
    x_positions = [left_margin, right_col_x]
    current_y = y_top_start
    col = 0
    item_in_col = 0

    for i, (eng, kor, is_eng_blank) in enumerate(words[:num_questions]):
        x_num = x_positions[col]
        underline_x = (x_num + 6.2 * cm) if col == 0 else (x_num + 4.1 * cm)

        # 문항 번호
        c.setFont("HYSMyeongJo-Medium", font_size)
        c.drawString(x_num, current_y, f"{i+1}.")

        # 내용 출력
        display_text = kor if is_eng_blank else eng
        blank_part = eng if is_eng_blank else kor

        # 한글 줄바꿈 고려
        lines_used = draw_wrapped_text(c, display_text, x_num + 0.6 * cm, current_y, 4.5 * cm,
                                       "HYSMyeongJo-Medium", font_size, line_gap)

        # 밑줄
        underline_y = current_y - (lines_used - 1) * line_gap
        c.line(underline_x, underline_y - underline_offset, underline_x + underline_len, underline_y - underline_offset)

        # 정답지 빨간색 표시
        if is_answer:
            c.setFillColor(colors.red)
            c.drawString(underline_x + 0.2 * cm, underline_y, blank_part)
            c.setFillColor(colors.black)

        # 다음 문항 y 좌표
        current_y -= (lines_used * line_gap + line_gap)
        item_in_col += 1

        # 30문항 초과 → 오른쪽 열로 이동
        if item_in_col == 30:
            col = 1
            item_in_col = 0
            current_y = y_top_start

        # 60문항 초과 → 새 페이지
        if (i + 1) % 60 == 0 and (i + 1) < num_questions:
            c.setFont("HYSMyeongJo-Medium", 6)
            c.drawCentredString(width / 2, bottom_margin / 2, f"- Page {c.getPageNumber()} -")
            c.showPage()
            c.setFont("HYSMyeongJo-Medium", font_size)
            current_y = y_top_start
            col = 0
            item_in_col = 0

    # 페이지 번호
    c.setFont("HYSMyeongJo-Medium", 6)
    c.drawCentredString(width / 2, bottom_margin / 2, f"- Page {c.getPageNumber()} -")

    c.save()
    buffer.seek(0)
    return buffer


# --------------------------------------------------------
# 🧩 Streamlit 인터페이스
# --------------------------------------------------------
st.title("📘 영어 단어 시험지 생성기 (Day 자동 인식 + 한글 줄바꿈 지원)")
st.write("Numbers/Excel 파일을 업로드하면 Day 번호를 인식해 자동으로 헤더를 구성합니다.")

uploaded_files = st.file_uploader("📂 파일 업로드 (여러 개 가능)", type=["xlsx", "csv"], accept_multiple_files=True)
num_questions = st.number_input("출제할 문항 수", min_value=10, max_value=200, value=60, step=10)

if uploaded_files:
    # ------------------ 파일명에서 Day 번호 추출 ------------------
    day_numbers = []
    for file in uploaded_files:
        match = re.search(r"Day\s*(\d+)", file.name, re.IGNORECASE)
        if match:
            day_numbers.append(int(match.group(1)))

    # 💡 아래 부분을 수정하면 '단어 1', '복습 2' 같은 다른 패턴도 인식 가능
    # 예시: match = re.search(r"(단어|복습)\s*(\d+)", file.name)

    if day_numbers:
        header_title = f"Day {min(day_numbers)} - Day {max(day_numbers)}"
    else:
        header_title = "영어 단어 시험"

    all_words = pd.DataFrame()

    for file in uploaded_files:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_csv(file, encoding="utf-8")

        df.columns = [c.strip().lower() for c in df.columns]

        if "english" in df.columns and "korean" in df.columns:
            subset = df[["english", "korean"]]
        elif "단어" in df.columns and "뜻" in df.columns:
            subset = df[["단어", "뜻"]]
            subset.columns = ["english", "korean"]
        else:
            st.warning(f"{file.name} 파일의 컬럼명을 확인해주세요.")
            continue

        all_words = pd.concat([all_words, subset], ignore_index=True)

    all_words.drop_duplicates(inplace=True)

    selected = all_words.sample(min(num_questions, len(all_words)), random_state=42)
    half = len(selected) // 2
    word_pairs = []

    for i, row in enumerate(selected.itertuples(index=False)):
        is_eng_blank = i < half
        word_pairs.append((row.english, row.korean, is_eng_blank))

    test_pdf = generate_pdf(word_pairs, num_questions, header_title, is_answer=False)
    answer_pdf = generate_pdf(word_pairs, num_questions, header_title, is_answer=True)

    st.download_button("📄 시험지 다운로드", data=test_pdf, file_name=f"{header_title}_시험지.pdf")
    st.download_button("✅ 정답지 다운로드", data=answer_pdf, file_name=f"{header_title}_정답지.pdf")

else:
    st.info("📥 Day 1.xlsx 같은 파일을 업로드해주세요.")
