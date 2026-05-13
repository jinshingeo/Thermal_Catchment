"""
TAVI 학회 발표 PPT 생성
스타일: Traffic-IT_발제_신진.pptx 동일
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from PIL import Image
import os, copy
from lxml import etree

# ── 색상 ─────────────────────────────────────────────────────────────────
C_RED     = RGBColor(0xB2, 0x22, 0x34)
C_DARKRED = RGBColor(0x8B, 0x00, 0x00)
C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK   = RGBColor(0x1A, 0x1A, 0x1A)
C_GRAY    = RGBColor(0x55, 0x55, 0x55)
FONT      = '맑은 고딕'

FIG_DIR  = '/Users/jin/석사논문/TAVI/Thermal_Catchment/03_결과물/figures'
PROF_DIR = os.path.join(FIG_DIR, '교수님논의')
OUT_PATH = '/Users/jin/석사논문/TAVI/writing/지도학회발표/2026-05-13_TAVI_학회발표.pptx'

# ── 헬퍼 ─────────────────────────────────────────────────────────────────
def add_textbox(slide, text, left, top, width, height,
                size=12, bold=False, color=C_BLACK, align=PP_ALIGN.LEFT, italic=False):
    txb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txb

def add_multiline_textbox(slide, lines, left, top, width, height, size=12, color=C_BLACK):
    """lines: list of (text, bold)"""
    txb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txb.text_frame
    tf.word_wrap = True
    first = True
    for text, bold in lines:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        run = p.add_run()
        run.text = text
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
    return txb

def add_rect(slide, left, top, width, height, fill_color, text=None,
             text_size=12, text_bold=True, text_color=C_WHITE):
    shape = slide.shapes.add_shape(
        1, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    if text:
        tf = shape.text_frame
        tf.word_wrap = False
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = text
        run.font.name = FONT
        run.font.size = Pt(text_size)
        run.font.bold = text_bold
        run.font.color.rgb = text_color
    return shape

def add_divider(slide, top=1.18):
    add_rect(slide, 0.40, top, 12.53, 0.02, C_RED)

def add_chapter_header(slide, chapter_num, chapter_title, section_label=None):
    add_textbox(slide, f'Chapter {chapter_num}.', 0.40, 0.18, 4.0, 0.40,
                size=11, color=C_RED)
    add_textbox(slide, chapter_title, 0.40, 0.52, 12.50, 0.55,
                size=24, color=C_BLACK)
    add_divider(slide, top=1.18)
    if section_label:
        add_rect(slide, 0.40, 1.35, len(section_label)*0.18+0.4, 0.36,
                 C_DARKRED, text=section_label, text_size=12)

def add_image_fit(slide, img_path, left, top, max_w, max_h, caption=None, caption_size=10):
    """비율 유지하며 max_w × max_h 안에 맞춤 (자르기 없음)"""
    img = Image.open(img_path)
    iw, ih = img.size
    ratio_w = max_w / iw
    ratio_h = max_h / ih
    ratio = min(ratio_w, ratio_h)
    w = iw * ratio
    h = ih * ratio
    # 중앙 정렬
    offset_x = (max_w - w) / 2
    offset_y = 0
    pic = slide.shapes.add_picture(
        img_path,
        Inches(left + offset_x), Inches(top + offset_y),
        Inches(w), Inches(h)
    )
    if caption:
        add_textbox(slide, caption,
                    left, top + h + 0.05, max_w, 0.35,
                    size=caption_size, color=C_GRAY, align=PP_ALIGN.CENTER)
    return pic, w, h


# ── PPT 초기화 ────────────────────────────────────────────────────────────
prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.50)
blank_layout = prs.slide_layouts[6]  # Blank

def new_slide():
    return prs.slides.add_slide(blank_layout)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 1: 표지
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()

add_textbox(s, '한국지도학회 학술대회 발표', 0.40, 0.20, 8.0, 0.40,
            size=11, color=C_GRAY)

add_textbox(s,
    'Thermal Catchment Area:\nMRT 기반 확률적 임계값과\nMonte Carlo 접근',
    0.80, 1.00, 8.50, 2.60, size=28, bold=True, color=C_BLACK)

add_textbox(s,
    '폭염을 반영한 보행 대중교통 접근성 공간 단위 제안\n— 서울 성동구 사례 —',
    0.80, 3.50, 8.50, 0.90, size=14, color=C_GRAY)

add_textbox(s, '신진', 9.50, 5.10, 3.50, 0.40, size=15, bold=True, color=C_BLACK)
add_textbox(s, '경희대학교 기후사회과학융합학과 석사과정', 9.50, 5.55, 3.50, 0.35,
            size=10, color=C_BLACK)
add_textbox(s, '2026. 05. 30', 9.50, 5.95, 3.50, 0.35, size=11, color=C_BLACK)

add_rect(s, 0.40, 6.85, 12.53, 0.02, C_RED)

# 우측 장식 이미지 (TARR 공간지도)
img_path = os.path.join(FIG_DIR, 'tarr_spatial_map.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 9.20, 0.60, 3.90, 4.30)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 2: 목차
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_textbox(s, '목차', 0.40, 0.18, 4.0, 0.55, size=24, color=C_BLACK)
add_divider(s, top=0.82)

chapters = [
    ('Chapter 1.', '연구 배경 및 목적'),
    ('Chapter 2.', '연구 지역 및 데이터'),
    ('Chapter 3.', '방법론'),
    ('Chapter 4.', '분석 결과'),
    ('Chapter 5.', '한계점 및 향후 연구'),
    ('Chapter 6.', '결론'),
]
for i, (ch, title) in enumerate(chapters):
    row_top = 1.10 + i * 0.95
    add_rect(s, 0.40, row_top, 0.08, 0.36, C_RED)
    add_textbox(s, ch,   0.60, row_top, 2.20, 0.36, size=12, bold=True, color=C_RED)
    add_textbox(s, title, 2.80, row_top, 9.0, 0.36, size=14, bold=False, color=C_BLACK)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 3: Chapter 1 — 연구 배경 (1)
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 1, '연구 배경', '기존 접근성 분석의 한계')

bullets = [
    ('● 역세권 Catchment Area = 물리적 거리·시간만을 기준으로 정의', True),
    ('   → 보행자가 균질한 환경에서 이동한다는 암묵적 가정에 기반', False),
    ('   → 현실의 보행 환경은 공간적으로 이질적이며, 기상 조건에 따라 크게 달라짐', False),
    ('● 기후변화로 도시 폭염의 빈도·강도 증가 → 여름철 보행 열 스트레스 심화', True),
    ('   → UTCI ≥ 38°C: "Very Strong Heat Stress" — 신체 활동에 심각한 위험', False),
    ('   → 그럼에도 기존 접근성 연구에서 열환경을 체계적으로 반영한 공간 단위 없음', False),
]
add_multiline_textbox(s, bullets, 0.45, 1.88, 12.40, 3.20, size=13)

add_rect(s, 0.40, 5.30, 2.0, 0.36, C_DARKRED, text='연구 공백', text_size=12)
gaps = [
    ('● 열환경 임계값을 초과할 때 접근 가능 범위 자체가 변하는 공간 단위 개념 없음', True),
    ('● 임계값의 불확실성을 확률적으로 다루는 연구 없음', True),
]
add_multiline_textbox(s, gaps, 0.45, 5.80, 12.40, 1.20, size=13)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 4: Chapter 1 — 연구 목적 & 질문
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 1, '연구 목적 및 질문', '연구 목적')

obj = [
    ('● Thermal Catchment Area 개념 제안', True),
    ('   → 폭염 시 MRT 기반 Hard Cut을 적용하여 실제 보행 가능 범위를 공간 단위로 정식화', False),
    ('● 서울 성동구 집계구 기점 대중교통 접근성 분석에 적용 → 실증적 유효성 검증', True),
    ('● Monte Carlo로 임계값 불확실성을 정량화 → 확률적 TARR 분포 제시', True),
]
add_multiline_textbox(s, obj, 0.45, 1.88, 12.40, 2.00, size=13)

add_rect(s, 0.40, 4.00, 1.80, 0.36, C_DARKRED, text='연구 질문', text_size=12)
qs = [
    ('Q1. MRT Hard Cut 적용 시, 폭염 조건에서 기존 Catchment 대비 접근 가능 정류장은 얼마나 감소하는가?', True),
    ('Q2. MRT 임계값의 불확실성을 Monte Carlo로 전파했을 때, TARR의 확률 분포는 어떠한가?', True),
    ('Q3. 접근성 손실 패턴이 집계구의 공간 환경 변수(SVF, 캐노피, 건물 형태)와 어떠한 관계를 갖는가?', True),
]
add_multiline_textbox(s, qs, 0.45, 4.55, 12.40, 2.20, size=13)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 5: Chapter 2 — 연구 지역 & 데이터
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 2, '연구 지역 및 데이터', '연구 지역: 서울특별시 성동구')

area = [
    ('● 면적 16.86 km², 지하철역 7개소 (왕십리·행당·응봉·뚝섬·성수·서울숲·옥수)', True),
    ('● 한강·중랑천 수변, 서울숲 녹지, 왕십리·성수 업무지구, 아파트 단지 혼재', False),
    ('   → 열환경 공간 변이가 크고 보행 접근성 연구의 적절한 대상 지역', False),
]
add_multiline_textbox(s, area, 0.45, 1.88, 7.50, 1.50, size=13)

add_rect(s, 0.40, 3.55, 1.80, 0.36, C_DARKRED, text='분석 데이터', text_size=12)
data_rows = [
    ('● 보행 네트워크: OpenStreetMap (osmnx) — 링크 15,608개', False),
    ('● 기상 데이터: 성동구 S-DoT 센서 57개소, 10분 간격', False),
    ('● 일사량: Open-Meteo archive (성동구 중심 단일 지점)', False),
    ('● 집계구 경계: 통계청 2016 기준 — 570개 집계구', False),
    ('● 대중교통 정류장: 지하철 7개 + 버스 482개 = 489개 (네트워크 노드 385개)', False),
    ('● 분석 기간: 2025.07.28–08.03 폭염일 7일 평균 | 분석 시간대: 13시', True),
]
add_multiline_textbox(s, data_rows, 0.45, 4.05, 7.50, 2.60, size=12)

# S-DoT 센서 위치 그림 (우측)
img_path = os.path.join(PROF_DIR, '00_SDot센서위치.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 8.20, 1.30, 4.90, 5.80,
                  caption='그림 1. S-DoT 기상 센서 위치 (n=57개)')


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 6: Chapter 3 — MRT 산출 방법론
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 3, '방법론', 'MRT 산출: SOLWEIG 약식 구현')

mrt_lines = [
    ('● Lindberg & Grimmond (2011) SOLWEIG 모형 기반 — Python 직접 구현', True),
    ('', False),
    ('  Tmrt = [ (Ksw + Llw) / σ ]^0.25  − 273.15', True),
    ('', False),
    ('    Ksw (단파복사): αp × [ (1-SVF)·Kdif + shadow·Kdir·cosθ + SVF·Kdif ]', False),
    ('    Llw (장파복사): εp × [ SVF·Lsky + (1-SVF)·Lwall ]', False),
    ('', False),
    ('● 주요 입력 변수', True),
    ('   SVF (Sky View Factor): 0=완전차폐, 1=완전개방 — 건물 차폐 반영', False),
    ('   GHI → DNI/DHI 분리: Erbs 모델 (Open-Meteo archive)', False),
    ('   Shadow: 13시 태양 천정각 기반 그림자 마스크', False),
    ('   Tair, RH, va: S-DoT 57개소 평균값 (폭염일 13시)', False),
]
add_multiline_textbox(s, mrt_lines, 0.45, 1.88, 7.80, 5.00, size=12)

# MRT 분포 그림 (우측)
img_path = os.path.join(PROF_DIR, '06_MRT.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 8.50, 1.50, 4.60, 5.60,
                  caption='그림 2. 링크별 MRT 분포 (13시, 폭염일 평균)')


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 7: Chapter 3 — Thermal Catchment & TARR 개념
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 3, '방법론', 'Thermal Catchment Area & TARR')

concept = [
    ('● Classic Catchment: 집계구 도심에서 15분 보행 내 도달 가능 정류장 수 (열환경 무시)', True),
    ('', False),
    ('● Thermal Catchment: MRT ≥ 임계값(°C) 링크를 제거한 네트워크에서 15분 이내 도달 정류장 수', True),
    ('   → Hard Cut 가정: 보행자가 고온 링크를 완전히 회피', False),
    ('   → Dijkstra 최단경로 → 정류장 도달 가능 여부 판단', False),
    ('', False),
    ('● TARR (Thermal Accessibility Reduction Rate, 열환경 접근성 감소율)', True),
    ('', False),
    ('   TARR = (Classic_cnt − Thermal_cnt) / Classic_cnt × 100  (%)', True),
    ('', False),
    ('   → TARR = 0%: 열환경 제약 없음 (폭염에도 정류장 접근 가능)', False),
    ('   → TARR = 100%: 모든 정류장 접근 불가 (완전 차단)', False),
]
add_multiline_textbox(s, concept, 0.45, 1.88, 12.40, 5.00, size=13)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 8: Chapter 3 — Monte Carlo 설계
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 3, '방법론', 'Monte Carlo 임계값 불확실성 분석')

mc_lines = [
    ('● 왜 Monte Carlo? — MRT 임계값(55°C)의 물리적 불확실성', True),
    ('   → 기상 조건(기온·습도·풍속) 변동에 따라 "위험 MRT"는 ±수°C 변동', False),
    ('   → 단일값으로 고정하는 것은 불확실성 무시', False),
    ('', False),
    ('● 설계 (N=2,000 샘플)', True),
    ('   Step 1. MRT 임계값 그리드 [45, 49, 51, 53, 55, 57, 59, 61, 65°C] × 집계구별 TARR 사전 계산', False),
    ('   Step 2. threshold ~ N(μ=55, σ²=4²) 에서 2,000개 샘플링', False),
    ('   Step 3. 집계구별 TARR(threshold) 선형 보간 → 샘플별 TARR 획득', False),
    ('   Step 4. 집계구별 TARR 중앙값·95% CI 산출', False),
    ('', False),
    ('● 핵심 발견: S-curve (임계값 민감도 곡선)', True),
    ('   → 53~57°C 구간에서 TARR이 88% → 39%로 급변 (변곡점 = 55°C)', False),
    ('   → CI 폭이 넓은 것은 "불안정"이 아니라 이 민감 구간의 존재를 보여주는 것', False),
]
add_multiline_textbox(s, mc_lines, 0.45, 1.88, 12.40, 5.00, size=12)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 9: Chapter 4 — S-curve (핵심 그림)
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 4, '분석 결과', 'MRT 임계값 민감도: S-curve')

img_path = os.path.join(FIG_DIR, 'mc_threshold_sensitivity.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 0.50, 1.55, 8.50, 5.60,
                  caption='그림 3. MRT 임계값 민감도 곡선 (집계구 평균 TARR, n=506)')

key_findings = [
    ('핵심 발견', True),
    ('', False),
    ('● 45°C → TARR ≈ 95%', False),
    ('   (거의 모든 링크 차단)', False),
    ('● 55°C → TARR ≈ 73%', True),
    ('   (기준 임계값)', False),
    ('● 65°C → TARR ≈ 5%', False),
    ('   (거의 차단 없음)', False),
    ('', False),
    ('● 53~57°C 구간에서', True),
    ('  TARR 88%→39%로 급변', True),
    ('  → S-curve 변곡점', True),
    ('', False),
    ('● 55°C = 변곡점 중심값', False),
    ('  → 보수적 기준값', False),
]
add_multiline_textbox(s, key_findings, 9.30, 1.55, 3.70, 5.60, size=11)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 10: Chapter 4 — TARR 공간 분포
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 4, '분석 결과', 'TARR 공간 분포 (집계구별)')

img_path = os.path.join(FIG_DIR, 'tarr_spatial_map.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 0.40, 1.50, 12.50, 5.65,
                  caption='그림 4. 집계구별 TARR 공간 분포 (MRT 55°C 기준, 13시, 폭염일 평균, n=506)')


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 11: Chapter 4 — Monte Carlo 결과
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 4, '분석 결과', 'Monte Carlo TARR 분포 (N=2,000)')

img_path = os.path.join(FIG_DIR, 'mc_tarr_distribution.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 0.40, 1.50, 12.50, 4.80,
                  caption='그림 5. 집계구별 TARR 중앙값 분포 (좌) 및 95% CI 폭 분포 (우) — threshold~N(55, 4²)')

summary = [
    ('● TARR 중앙값 평균: 70.2%  |  95% CI 폭 평균: 39.0%p', True),
    ('● CI 폭이 넓은 이유 = S-curve 민감 구간(53~57°C)이 샘플링 범위 안에 포함되기 때문', False),
]
add_multiline_textbox(s, summary, 0.45, 6.50, 12.40, 0.80, size=11)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 12: Chapter 4 — Monte Carlo CI 공간지도
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 4, '분석 결과', 'Monte Carlo 집계구별 공간 분포')

img_path = os.path.join(FIG_DIR, 'mc_tarr_ci_map.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 0.40, 1.50, 12.50, 5.65,
                  caption='그림 6. 집계구별 TARR 중앙값(좌) 및 95% CI 폭(우) 공간 분포')


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 13: Chapter 4 — 3시간대 비교
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 4, '분석 결과', '시간대별 비교 (9시·13시·18시)')

img_path = os.path.join(FIG_DIR, 'tarr_3hour_comparison.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 0.40, 1.50, 12.50, 5.30,
                  caption='그림 7. 시간대별 MRT 최댓값, 고온링크 비율, TARR 비교 (9시·13시·18시)')

note = [('● 13시에 MRT·TARR 모두 최대 → 폭염 피크 시간대의 접근성 제약이 가장 심각', False)]
add_multiline_textbox(s, note, 0.45, 6.95, 12.40, 0.35, size=11)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 14: Chapter 4 — 역별 정류장 손실
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 4, '분석 결과', '지하철역별 접근 가능 정류장 손실율')

img_path = os.path.join(FIG_DIR, 'station_stop_loss_table.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 0.40, 1.50, 12.50, 5.65,
                  caption='그림 8. 지하철역별 Classic vs Thermal Catchment 접근 가능 정류장 수 및 손실율 (MRT 55°C, 13시)')


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 15: Chapter 4 — OLS 회귀분석
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 4, '분석 결과', '공간 환경 변수 × TARR 회귀분석')

img_path = os.path.join(FIG_DIR, 'regression_scatter.png')
if os.path.exists(img_path):
    add_image_fit(s, img_path, 0.40, 1.50, 12.50, 4.80,
                  caption='그림 9. 공간 환경 변수 × TARR OLS 회귀 산점도 (n=506)')

reg = [
    ('● OLS R²=0.174 — hot_link_ratio (r=0.332***), SVF (r=0.295***), H/W (r=-0.208***)', False),
    ('● 해석: MRT로 정량화된 열환경이 공간 환경과 관계 — 보조적 탐색 분석', False),
]
add_multiline_textbox(s, reg, 0.45, 6.50, 12.40, 0.80, size=11)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 16: Chapter 5 — 한계점 및 향후 연구
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 5, '한계점 및 향후 연구', '한계점')

limits = [
    ('● 바람 속도 균일 가정: va=2.37 m/s 전 구간 동일 → 도시 협곡 내 풍속 변이 미반영', False),
    ('● GHI 단일 지점: 성동구 전체에 동일 GHI 적용 → 미세 공간 일사량 차이 무시', False),
    ('● MRT 실측 검증 없음: SOLWEIG 약식 추정값 — 복사계 실측 비교 미수행', False),
    ('● Hard Cut 행동 가정: 보행자가 고온 링크를 완전 회피한다는 가정의 실증 근거 부재', False),
    ('   → "물리적 열스트레스 임계값"으로 재해석하여 행동적 의미와 구분', False),
    ('● 집계구 도심 가정: 실제 거주민은 집계구 전역에 분포 → 도심 출발 가정은 근사치', False),
    ('● 분석 기간 일반화: 2025.07.28–08.03 단일 폭염 이벤트 (7일) — 사례 연구 수준', False),
    ('● OSM 네트워크 완전성: 지하도·실내 공조 구간 등 열환경 양호 경로 미포함', False),
]
add_multiline_textbox(s, limits, 0.45, 1.88, 12.40, 3.60, size=12)

add_rect(s, 0.40, 5.60, 2.20, 0.36, C_DARKRED, text='향후 연구 방향', text_size=12)
futures = [
    ('● 노인 보행 속도(3.0 km/h) 분리 적용 → 고령 취약계층 접근성 분석', False),
    ('● QWEN 멀티모달 LLM 활용 거리뷰 영상 기반 MRT 추정 → SVF·그림자 자동 추출', False),
    ('● CFD 또는 다점 S-DoT 풍속 데이터 연계 → 바람 공간 변이 반영', False),
]
add_multiline_textbox(s, futures, 0.45, 6.10, 12.40, 1.20, size=12)


# ═══════════════════════════════════════════════════════════════════════════
# 슬라이드 17: Chapter 6 — 결론
# ═══════════════════════════════════════════════════════════════════════════
s = new_slide()
add_chapter_header(s, 6, '결론', '요약')

conclusions = [
    ('● 개념 제안: Thermal Catchment Area — 폭염 시 MRT Hard Cut을 적용한 새로운 보행 접근성 공간 단위', True),
    ('   → 기존 Catchment가 무시해온 열환경 제약을 공간 단위 자체에 내재화', False),
    ('', False),
    ('● 실증 결과 (성동구, MRT 55°C 기준, 13시)', True),
    ('   → 집계구 평균 TARR 73.3% — 폭염 시 약 73%의 정류장 접근 기회가 상실됨', False),
    ('   → 서울숲역 80.0%, 행당역 77.6% 등 역별 손실율 차이 확인', False),
    ('', False),
    ('● 핵심 방법론적 기여: S-curve 발견 + Monte Carlo 불확실성 정량화', True),
    ('   → 53~57°C 구간에서 TARR 88%→39% 급변 — 임계값 선택이 결과에 결정적', False),
    ('   → Monte Carlo (N=2,000)로 임계값 불확실성을 확률적으로 전파', False),
    ('', False),
    ('● 정책적 함의', True),
    ('   → 폭염 취약 집계구(TARR 고지역)를 우선 쿨링 인프라 정비 대상으로 식별 가능', False),
    ('   → Thermal Catchment는 기후 적응형 도시 접근성 계획의 공간 기준 단위로 활용 가능', False),
]
add_multiline_textbox(s, conclusions, 0.45, 1.88, 12.40, 5.20, size=12)

add_rect(s, 0.40, 7.10, 12.53, 0.02, C_RED)


# ── 저장 ──────────────────────────────────────────────────────────────────
prs.save(OUT_PATH)
print(f"저장 완료: {OUT_PATH}")
print(f"슬라이드 수: {len(prs.slides)}")
