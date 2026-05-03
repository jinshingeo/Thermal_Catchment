"""
Task 5 — 시각화
================
Classic / Thermal 접근성 비교, TARR, AAL, 분류 지도 생성

출력 (→ 03_결과물/figures/):
  fig1_accessibility_comparison.png   — Classic vs Thermal A_i 비교
  fig2_tarr_map.png                   — TARR (%) 공간 분포
  fig3_aal_map.png                    — AAL 공간 분포
  fig4_category_map.png               — Thermal-robust / moderate / prone 분류
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import contextily as ctx
from matplotlib.colors import Normalize
from matplotlib.colorbar import ColorbarBase

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
os.makedirs(FIG_DIR, exist_ok=True)

BOUNDARY_SHP   = os.path.join(DATA_DIR, '행정경계',
                              '통계지역경계(2016년+기준)', '집계구.shp')
RESULTS_PATH   = os.path.join(RES_DIR, 'gravity_results_30min.csv')
SEONGDONG_PREFIX = '1104'

# ── 한국어 폰트 설정 ──────────────────────────────────────────────────────
def set_korean_font():
    candidates = [
        '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
        '/Library/Fonts/NanumGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            prop = fm.FontProperties(fname=path)
            plt.rcParams['font.family'] = prop.get_name()
            break
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()


# ── 1. 데이터 로드 ────────────────────────────────────────────────────────
print("데이터 로드 중...")
results_df = pd.read_csv(RESULTS_PATH, encoding='utf-8-sig')
results_df['집계구코드'] = results_df['집계구코드'].astype(float).astype(int).astype(str)

jibgaegu = gpd.read_file(BOUNDARY_SHP, encoding='cp949')
code_col = None
for c in jibgaegu.columns:
    sample = str(jibgaegu[c].iloc[0])
    if sample.startswith('11') and len(sample) >= 10:
        code_col = c
        break
if code_col is None:
    for candidate in ['집계구코드', 'TOT_REG_CD']:
        if candidate in jibgaegu.columns:
            code_col = candidate
            break

jibgaegu[code_col] = jibgaegu[code_col].astype(str)
seongdong_gdf = jibgaegu[jibgaegu[code_col].str.startswith(SEONGDONG_PREFIX)].copy()
if seongdong_gdf.crs is None:
    seongdong_gdf = seongdong_gdf.set_crs(epsg=5179)
seongdong_gdf = seongdong_gdf.to_crs(epsg=3857)

gdf = seongdong_gdf.merge(results_df, left_on=code_col, right_on='집계구코드', how='left')
print(f"  병합 완료: {len(gdf)}개 집계구")


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────
def add_basemap(ax):
    try:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=13)
    except Exception:
        pass

def save_fig(fig, fname):
    path = os.path.join(FIG_DIR, fname)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  저장: {path}")


# ── Fig 1: Classic vs Thermal 접근성 비교 ────────────────────────────────
print("\nFig 1: Classic vs Thermal 접근성 비교...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

vmin = gdf[['a_classic', 'a_thermal']].min().min()
vmax = gdf['a_classic'].max()

for ax, col, title in zip(axes,
                           ['a_classic', 'a_thermal'],
                           ['Classic Catchment\n접근성 (A_i)', 'Thermal Catchment\n접근성 (A_i)']):
    gdf.plot(column=col, ax=ax, cmap='YlOrRd', vmin=vmin, vmax=vmax,
             linewidth=0.2, edgecolor='grey')
    add_basemap(ax)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
    ax.axis('off')

sm = plt.cm.ScalarMappable(cmap='YlOrRd', norm=Normalize(vmin=vmin, vmax=vmax))
sm.set_array([])
cbar = fig.colorbar(sm, ax=axes, shrink=0.6, pad=0.02)
cbar.set_label('접근성 지수 (A_i)', fontsize=11)

fig.suptitle('폭염 전후 대중교통 보행 접근성 비교 — 성동구 (13시, UTCI ≥ 38°C)',
             fontsize=14, fontweight='bold', y=1.01)
save_fig(fig, 'fig1_accessibility_comparison.png')


# ── Fig 2: TARR 분포 지도 ────────────────────────────────────────────────
print("Fig 2: TARR 분포...")
fig, ax = plt.subplots(figsize=(9, 8))

gdf_valid = gdf[gdf['a_classic'] > 0]
gdf_noac  = gdf[gdf['a_classic'] == 0]

gdf_valid.plot(column='tarr', ax=ax, cmap='RdYlGn_r',
               vmin=0, vmax=100, linewidth=0.2, edgecolor='grey')
if len(gdf_noac) > 0:
    gdf_noac.plot(ax=ax, color='#cccccc', linewidth=0.2, edgecolor='grey')

add_basemap(ax)
ax.set_title('Thermal Accessibility Reduction Rate (TARR)\n성동구 집계구별 접근성 감소율 (%)',
             fontsize=12, fontweight='bold', pad=10)
ax.axis('off')

sm = plt.cm.ScalarMappable(cmap='RdYlGn_r', norm=Normalize(vmin=0, vmax=100))
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
cbar.set_label('TARR (%)', fontsize=11)
if len(gdf_noac) > 0:
    patch = mpatches.Patch(color='#cccccc', label='Classic 접근 불가')
    ax.legend(handles=[patch], loc='lower right', fontsize=9)

save_fig(fig, 'fig2_tarr_map.png')


# ── Fig 3: AAL 분포 지도 ─────────────────────────────────────────────────
print("Fig 3: AAL 분포...")
fig, ax = plt.subplots(figsize=(9, 8))

gdf.plot(column='aal', ax=ax, cmap='Purples',
         vmin=0, vmax=gdf['aal'].quantile(0.95),
         linewidth=0.2, edgecolor='grey')
add_basemap(ax)
ax.set_title('Absolute Accessibility Loss (AAL)\n성동구 집계구별 접근성 절대 손실량',
             fontsize=12, fontweight='bold', pad=10)
ax.axis('off')

sm = plt.cm.ScalarMappable(cmap='Purples',
                            norm=Normalize(vmin=0, vmax=gdf['aal'].quantile(0.95)))
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
cbar.set_label('AAL (A_i 단위)', fontsize=11)

save_fig(fig, 'fig3_aal_map.png')


# ── Fig 4: 분류 지도 ─────────────────────────────────────────────────────
print("Fig 4: Thermal-robust / moderate / prone 분류...")
fig, ax = plt.subplots(figsize=(9, 8))

color_map = {
    'thermal_robust': '#2166ac',
    'moderate':       '#f7f7f7',
    'thermal_prone':  '#d6604d',
    'no_access':      '#969696',
}
label_map = {
    'thermal_robust': 'Thermal-robust (TARR 낮음)',
    'moderate':       'Moderate',
    'thermal_prone':  'Thermal-prone (TARR 높음)',
    'no_access':      'Classic 접근 불가',
}

for cat, color in color_map.items():
    sub = gdf[gdf['category'] == cat]
    if len(sub) > 0:
        sub.plot(ax=ax, color=color, linewidth=0.2, edgecolor='grey')

add_basemap(ax)
ax.set_title('Thermal-robust / Thermal-prone 분류\n성동구 집계구 (TARR 3분위 기준)',
             fontsize=12, fontweight='bold', pad=10)
ax.axis('off')

patches = [mpatches.Patch(color=c, label=label_map[k])
           for k, c in color_map.items() if k in gdf['category'].values]
ax.legend(handles=patches, loc='lower right', fontsize=9, framealpha=0.9)

save_fig(fig, 'fig4_category_map.png')


# ── 완료 ─────────────────────────────────────────────────────────────────
print("\n=== Task 5 완료 ===")
print(f"  저장 위치: {FIG_DIR}")
print("다음 단계: Task 6 문서화 & 커밋")
