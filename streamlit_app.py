import streamlit as st
import pandas as pd
import io
import random
import tempfile
from math import floor, ceil
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import mm
from reportlab.lib import colors

# -----------------------
# 상수 (mm 단위 좌표를 정확히 사용)
# -----------------------
# 좌표(사용자 요구 대로 mm단위)
NUM_X1_MM = 24     # 왼쪽 열 번호 위치 (24mm)
UNDER_X1_MM = 62   # 왼쪽 밑줄 시작 위치 (62mm)
UNDER_LEN_MM = 37  # 밑줄 길이 (37mm)

NUM_X2_MM = 111    # 오른쪽 열 번호 위치 (111mm)
UNDER_X2_MM = 152  # 오른쪽 밑줄 시작 위치 (152mm)

TOP_OFFSET_MM = 62   # 위에서 62mm 지점부터 문항 시작
BOTTOM_RESERVED_MM = 24  # 아래 24mm 비우기(페이지 번호 영역)
LINE_HEIGHT_MM = 4  # 밑줄간 상하 간격 0.4cm = 4mm
CHAR_SIZE_MM = 2     # 한 글자당 2mm

# -----------------------
# 폰트 등록
# -----------------------
# HYSMyeongJo-Medium 사용 (ReportLab의 CJK CID 폰트)
pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

# -----------------------
# 유틸: 텍스트를 max_width(포인트) 기준으로 단어 단위 줄바꿈
# -----------------------
def wrap_text_for_width(text, font_name, font_size_pt, max_width_pt):
    """문자 단위가 아니라 단어 단위로 라인 분리(한국어도 공백 기준으로 처리하나,
       공백이 적은 한국어 경우 한글 문자 단위로 잘라 넣음).
       반환: 리스트(라인들)"""
    if not text or str(text).strip() == "":
        return []
    text = str(text)
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip() if cur else w
        if pdfmetrics.stringWidth(candidate, font_name, font_size_pt) <= max_width_pt:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            # 단어(w)가 너무 길면 문자단위로 자르기
            if pdfmetrics.stringWidth(w, font_name, font_size_pt) <= max_width_pt:
                cur = w
            else:
                # 문자 단위 분할
                sub = ""
                for ch in w:
                    if pdfmetrics.stringWidth(sub + ch, font_name, font_size_pt) <= max_width_pt:
                        sub += ch
                    else:
                        if sub:
                            lines.append(sub)
                        sub = ch
                if sub:
                    cur = sub
                else:
                    cur = ""
    if cur:
        lines.append(cur)
    return lines

# -----------------------
# PDF 생성: 시험지 (빈칸 + 밑줄)
# -----------------------
def create_test_pdf(word_pairs, num_questions):
    """
    word_pairs: list of tuples (eng, kor, is_korean_blank)  
      - is_korean_blank True -> korean is blank (show English), else True for english blank
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width_pt, height_pt = A4  # 단위: points

    # konsts in points
    num_x1 = NUM_X1_MM * mm
    under_x1 = UNDER_X1_MM * mm
    under_len = UNDER_LEN_MM * mm
    num_x2 = NUM_X2_MM * mm
    under_x2 = UNDER_X2_MM * mm

    top_offset = TOP_OFFSET_MM * mm
    bottom_reserved = BOTTOM_RESERVED_MM * mm
    line_height = LINE_HEIGHT_MM * mm
    font_size = CHAR_SIZE_MM * mm  # 포인트 단위로 설정 (mm->pt)
    small_gap = 1.5 * mm  # 텍스트와 밑줄 사이 약간 여유

    font_name = "HYSMyeongJo-Medium"
    c.setFont(font_name, font_size)

    # 가로 텍스트 영역 (텍스트 시작 x 위치)
    text_x1 = num_x1 + 6 * mm   # 번호 뒤에서 6mm 띄우고 글자 시작
    text_x2 = num_x2 + 6 * mm

    # 텍스트 최대 너비 (밑줄 시작 - 텍스트 시작 - padding)
    text_max_w1 = (under_x1 - small_gap) - text_x1
    text_max_w2 = (under_x2 - small_gap) - text_x2

    # 실제 가능한 행 수 계산 (열당)
    available_height = height_pt - top_offset - bottom_reserved
    rows_per_col = int(available_height // line_height)
    if rows_per_col < 1:
        rows_per_col = 1
    per_page = rows_per_col * 2

    total = min(num_questions, len(word_pairs))
    total_pages = ceil(total / per_page)

    idx = 0
    page_no = 1
    for p in range(total_pages):
        # 페이지별 아이템
        start = p * per_page
        end = min(start + per_page, total)
        page_items = word_pairs[start:end]

        # 페이지 타이틀 영역은 비우기(요구: 위쪽 62mm 공백을 확보했으므로 바로 사용)
        # 각 항목을 순서대로 배치
        for i, (eng, kor, is_kor_blank) in enumerate(page_items):
            # 컬럼, 행 계산
            col = 0 if i < rows_per_col else 1
            row = i if i < rows_per_col else i - rows_per_col

            # y 좌표: 위에서 내려옴
            y = height_pt - top_offset - row * line_height

            # 번호, 텍스트, 밑줄 위치 설정 (각 열 고정 x)
            if col == 0:
                num_x = num_x1
                text_x = text_x1
                under_x = under_x1
                text_max_w = text_max_w1
            else:
                num_x = num_x2
                text_x = text_x2
                under_x = under_x2
                text_max_w = text_max_w2

            # 번호 출력
            c.setFillColor(colors.black)
            c.drawString(num_x, y, f"{start + i + 1}.")  # 번호만 좌측 고정

            # 표시할 텍스트(시험지): 한글이 비워진 항목은 영어가 보이고 밑줄은 한글 적는 곳.
            # 사용자가 요구: "한글을 비운 부분이 시험지의 앞쪽에 나오게" -> caller should have arranged order already.
            shown_text = eng if is_kor_blank else kor

            # 줄바꿈 처리 (wrap)
            # font_size pt value:
            font_size_pt = font_size
            lines = wrap_text_for_width(shown_text, font_name, font_size_pt, text_max_w)

            # vertical offset for multi-line: we draw first line at y, next lines go downward
            line_gap = font_size * 1.2  # 약간 여유
            for li, line in enumerate(lines if lines else [""]):
                line_y = y - li * line_gap
                c.drawString(text_x, line_y, line)

            # 밑줄 그리기 (시험지에서는 '답을 적는 공간'으로 실선)
            # 사용자 요구: 밑줄은 번호/단어 옆에 위치하고 길이는 37mm.
            underline_y = y - 0.2 * mm  # baseline보다 살짝 아래
            c.setStrokeColor(colors.black)
            # Only show underline as blank area to write answer: if the answer cell is blank in the test sheet.
            # For our marking: if is_kor_blank -> kor is blank (student writes Korean), so we draw underline at under_x
            # else -> eng is blank -> underline drawn at under_x
            # We always draw the underline at the fixed under_x for that column.
            c.line(under_x, underline_y, under_x + under_len, underline_y)

        # 페이지 하단: 페이지 번호 (요구: 아래 24mm 영역을 비우고 그곳에 페이지수, 글자당 2mm)
        page_count_text = f"Page {page_no} / {total_pages}"
        # set font size for page num equal to CHAR_SIZE_MM (2mm)
        c.setFont(font_name, font_size)
        # 중앙 정렬
        c.drawCentredString(width_pt / 2, bottom_reserved / 2, page_count_text)

        if p < total_pages - 1:
            c.showPage()
            c.setFont(font_name, font_size)
        page_no += 1

    c.save()
    buffer.seek(0)
    return buffer

# -----------------------
# PDF 생성: 정답지 (밑줄 영역에 정답 표시, 색 강조)
# -----------------------
def create_answer_pdf(word_pairs, num_questions):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width_pt, height_pt = A4

    num_x1 = NUM_X1_MM * mm
    under_x1 = UNDER_X1_MM * mm
    under_len = UNDER_LEN_MM * mm
    num_x2 = NUM_X2_MM * mm
    under_x2 = UNDER_X2_MM * mm

    top_offset = TOP_OFFSET_MM * mm
    bottom_reserved = BOTTOM_RESERVED_MM * mm
    line_height = LINE_HEIGHT_MM * mm
    font_size = CHAR_SIZE_MM * mm
    font_name = "HYSMyeongJo-Medium"

    text_x1 = num_x1 + 6 * mm
    text_x2 = num_x2 + 6 * mm
    text_max_w1 = (under_x1 - 1.5 * mm) - text_x1
    text_max_w2 = (under_x2 - 1.5 * mm) - text_x2

    available_height = height_pt - top_offset - bottom_reserved
    rows_per_col = int(available_height // line_height)
    if rows_per_col < 1:
        rows_per_col = 1
    per_page = rows_per_col * 2

    total = min(num_questions, len(word_pairs))
    total_pages = ceil(total / per_page)

    idx = 0
    page_no = 1
    for p in range(total_pages):
        start = p * per_page
        end = min(start + per_page, total)
        page_items = word_pairs[start:end]

        for i, (eng, kor, is_kor_blank) in enumerate(page_items):
            col = 0 if i < rows_per_col else 1
            row = i if i < rows_per_col else i - rows_per_col
            y = height_pt - top_offset - row * line_height

            if col == 0:
                num_x = num_x1
                text_x = text_x1
                under_x = under_x1
                text_max_w = text_max_w1
            else:
                num_x = num_x2
                text_x = text_x2
                under_x = under_x2
                text_max_w = text_max_w2

            # 번호 출력
            c.setFillColor(colors.black)
            c.drawString(num_x, y, f"{start + i + 1}.")

            # 시험지와 달리 정답지에서는 밑줄 영역에 정답(색상) 출력
            if is_kor_blank:
                # korean blank originally -> we showed English in test, now show Korean answer on underline area (blue)
                shown_text = eng
                # show shown_text at text_x (may wrap)
                lines = wrap_text_for_width(shown_text, font_name, font_size, text_max_w)
                for li, line in enumerate(lines if lines else [""]):
                    line_y = y - li * (font_size * 1.2)
                    c.drawString(text_x, line_y, line)

                # print Korean answer next to underline in blue (kor)
                answer_text = kor
                # wrap kor if needed in underline area width
                under_area_width = under_len - 2 * mm
                kor_lines = wrap_text_for_width(answer_text, font_name, font_size, under_area_width)
                c.setFillColor(colors.blue)
                for li, kline in enumerate(kor_lines if kor_lines else [""]):
                    # place starting slightly right of underline start
                    kline_y = y - li * (font_size * 1.2)
                    c.drawString(under_x + 1 * mm, kline_y, kline)
                c.setFillColor(colors.black)
            else:
                # english blank originally -> show Korean in text area, English (answer) in underline area
                shown_text = kor
                lines = wrap_text_for_width(shown_text, font_name, font_size, text_max_w)
                for li, line in enumerate(lines if lines else [""]):
                    line_y = y - li * (font_size * 1.2)
                    c.drawString(text_x, line_y, line)

                answer_text = eng
                under_area_width = under_len - 2 * mm
                eng_lines = wrap_text_for_width(answer_text, font_name, font_size, under_area_width)
                c.setFillColor(colors.blue)
                for li, kline in enumerate(eng_lines if eng_lines else [""]):
                    kline_y = y - li * (font_size * 1.2)
                    c.drawString(under_x + 1 * mm, kline_y, kline)
                c.setFillColor(colors.black)

        # page number
        page_count_text = f"Page {page_no} / {total_pages}"
        c.setFont(font_name, font_size)
        c.drawCentredString(width_pt / 2, bottom_reserved / 2, page_count_text)

        if p < total_pages - 1:
            c.showPage()
            c.setFont(font_name, font_size)
        page_no += 1

    c.save()
    buffer.seek(0)
    return buffer

# -----------------------
# Streamlit 인터페이스
# -----------------------
st.title("📘 정밀 레이아웃 영어 단어 시험지 생성기")
st.write(
    "요구한 서식(정밀 mm 위치, 밑줄, 줄바꿈, 글자크기 2mm 등)을 반영한 시험지 + 정답지 생성기입니다.\n\n"
    "- 업로드 가능한 파일: .xlsx, .csv\n"
    "- 전체 문제 수를 지정하면 무작위로 선택합니다. (중복 제거)\n"
    "- 시험지 앞쪽(먼저 나오는 항목)은 한글이 비워진(=영어 보이는) 항목들입니다."
)

uploaded_files = st.file_uploader("파일 업로드 (.xlsx 또는 .csv, 여러 개 가능)", type=["xlsx", "csv"], accept_multiple_files=True)
num_questions = st.number_input("출력할 전체 문항 수", min_value=2, max_value=500, value=60, step=2)

if uploaded_files:
    dfs = []
    for f in uploaded_files:
        try:
            if str(f.name).lower().endswith(".xlsx"):
                df = pd.read_excel(f)
            else:
                raw = f.read()
                try:
                    df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
                except Exception:
                    df = pd.read_csv(io.BytesIO(raw), encoding="cp949")
            # normalize column names
            cols = [c.strip().lower() for c in df.columns]
            df.columns = cols
            # try common names
            if "english" in df.columns and "korean" in df.columns:
                df_sub = df[["english", "korean"]].copy()
                df_sub.columns = ["english", "korean"]
            elif "단어" in df.columns and "뜻" in df.columns:
                df_sub = df[["단어", "뜻"]].copy()
                df_sub.columns = ["english", "korean"]
            else:
                # fallback to first two columns
                df_sub = df.iloc[:, :2].copy()
                df_sub.columns = ["english", "korean"]
            dfs.append(df_sub)
        except Exception as e:
            st.error(f"{f.name} 처리중 오류: {e}")

    if not dfs:
        st.warning("유효한 데이터가 없습니다.")
    else:
        combined = pd.concat(dfs, ignore_index=True)
        # drop rows missing either key
        combined = combined.dropna(subset=["english", "korean"])
        # remove duplicates by english lower
        combined = combined.drop_duplicates(subset=[combined.columns[0]])
        available = len(combined)
        if available == 0:
            st.warning("단어가 없습니다.")
        else:
            pick_n = min(int(num_questions), available)
            sampled = combined.sample(frac=1, random_state=42).reset_index(drop=True).iloc[:pick_n]

            # Build word_pairs such that first half have Korean blank (show English),
            # and second half have English blank (show Korean). "한글을 비운 부분이 시험지의 앞쪽에 나오게"
            half = pick_n // 2
            word_pairs = []
            # first half: kor blank (show english)
            for i in range(half):
                eng = str(sampled.iloc[i]["english"])
                kor = str(sampled.iloc[i]["korean"])
                word_pairs.append((eng, kor, True))  # True => kor blank (korean to be written by student)
            # second half: eng blank (show korean)
            for i in range(half, pick_n):
                eng = str(sampled.iloc[i]["english"])
                kor = str(sampled.iloc[i]["korean"])
                word_pairs.append((eng, kor, False))

            # create PDFs
            test_buf = create_test_pdf(word_pairs, pick_n)
            answer_buf = create_answer_pdf(word_pairs, pick_n)

            st.download_button("📄 시험지 다운로드 (PDF)", data=test_buf, file_name="시험지.pdf", mime="application/pdf")
            st.download_button("✅ 정답지 다운로드 (PDF)", data=answer_buf, file_name="정답지.pdf", mime="application/pdf")

            st.success(f"총 {pick_n}문항으로 시험지 및 정답지 생성 완료 (원본 단어 수: {available}).")
