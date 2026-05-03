"""
Task 5 — 시각화 (3개 시간대: 폭염 전·중간·피크)
=================================================
출력 (→ 03_결과물/figures/):
  fig1_accessibility_comparison.png   — Classic + Thermal 3시간대 A_i 비교 (1×4)
  fig2_tarr_multihour.png             — TARR 3시간대 비교 (1×3)
  fig3_aal_multihour.png              — AAL 3시간대 비교 (1×3)
  fig4_category_map.png               — Thermal-robust/prone 분류 (14시 피크 기준)
  fig9_catchment_summary_bar.png      — 시간대별 평균 도달 정류장·완전차단 집계구 요약
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

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
os.makedirs(FIG_DIR, exist_ok=True)

BOUNDARY_SHP     = os.path.join(DATA_DIR, '행정경계',
                                '통계지역경계(2016년+기준)', '집계구.shp')
RESULTS_PATH     = os.path.join(RES_DIR, 'gravity_results_multihour.csv')
SUMMARY_PATH     = os.path.join(RES_DIR, 'catchment_summary_multihour.csv')
SEONGDONG_PREFIX = '1104'

TARGET_HOURS = {10: '폭염 전\n(10시)', 13: '폭염 중간\n(13시)', 14: '폭염 피크\n(14시)'}


# ── 한국어 폰트 ───────────────────────────────────────────────────────────
def set_korean_font():
    for path in ['/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                 '/Library/Fonts/NanumGothic.ttf']:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            plt.rcParams['font.family'] = fm.FontProperties(fname=path).get_name()
            break
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()


# ── 1. 데이터 로드 & 공간 조인 ────────────────────────────────────────────
print("데이터 로드 중...")
results_df = pd.read_csv(RESULTS_PATH, encoding='utf-8-sig')
results_df['집계구코드'] = results_df['집계구코드'].astype(float).astype(int).astype(str)

jibgaegu = gpd.read_file(BOUNDARY_SHP, encoding='cp949')
code_col  = next(c for c in jibgaegu.columns
                 if str(jibgaegu[c].iloc[0]).startswith('11') and len(str(jibgaegu[c].iloc[0])) >= 10)
jibgaegu[code_col] = jibgaegu[code_col].astype(str)
seongdong = jibgaegu[jibgaegu[code_col].str.startswith(SEONGDONG_PREFIX)].copy()
if seongdong.crs is None:
    seongdong = seongdong.set_crs(epsg=5179)
seongdong = seongdong.to_crs(epsg=3857)

gdf = seongdong.merge(results_df, left_on=code_col, right_on='집계구코드', how='left')
print(f"  병합 완료: {len(gdf)}개 집계구")


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


# ── Fig 1: Classic + Thermal 3시간대 A_i 비교 (1×4) ─────────────────────
print("\nFig 1: 접근성 비교 (1×4)...")
fig, axes = plt.subplots(1, 4, figsize=(22, 7))

cols   = ['a_classic'] + [f'a_thermal_h{h}' for h in TARGET_HOURS]
titles = ['Classic\n(기준)'] + list(TARGET_HOURS.values())
vmax   = gdf['a_classic'].quantile(0.98)

for ax, col, title in zip(axes, cols, titles):
    gdf.plot(column=col, ax=ax, cmap='YlOrRd', vmin=0, vmax=vmax,
             linewidth=0.15, edgecolor='#aaaaaa', missing_kwds={'color': '#eeeeee'})
    add_basemap(ax)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=8)
    ax.axis('off')

sm = plt.cm.ScalarMappable(cmap='YlOrRd', norm=Normalize(vmin=0, vmax=vmax))
sm.set_array([])
fig.colorbar(sm, ax=axes, shrink=0.55, pad=0.01, label='접근성 지수 (A_i)')
fig.suptitle('폭염 진행에 따른 대중교통 보행 접근성 변화 — 성동구',
             fontsize=14, fontweight='bold', y=1.01)
save_fig(fig, 'fig1_accessibility_comparison.png')


# ── Fig 2: TARR 3시간대 비교 ─────────────────────────────────────────────
print("Fig 2: TARR 비교...")
fig, axes = plt.subplots(1, 3, figsize=(18, 7))

for ax, (hour, label) in zip(axes, TARGET_HOURS.items()):
    col   = f'tarr_h{hour}'
    valid = gdf[gdf['a_classic'] > 0]
    noac  = gdf[gdf['a_classic'] == 0]
    valid.plot(column=col, ax=ax, cmap='RdYlGn_r', vmin=0, vmax=100,
               linewidth=0.15, edgecolor='#aaaaaa')
    if len(noac) > 0:
        noac.plot(ax=ax, color='#cccccc', linewidth=0.15, edgecolor='#aaaaaa')
    add_basemap(ax)
    mean_tarr = valid[col].mean()
    ax.set_title(f'{label}\n평균 TARR {mean_tarr:.1f}%', fontsize=11, fontweight='bold', pad=8)
    ax.axis('off')

sm = plt.cm.ScalarMappable(cmap='RdYlGn_r', norm=Normalize(vmin=0, vmax=100))
sm.set_array([])
fig.colorbar(sm, ax=axes, shrink=0.6, pad=0.01, label='TARR (%)')
fig.suptitle('Thermal Accessibility Reduction Rate (TARR) — 시간대별 비교',
             fontsize=13, fontweight='bold', y=1.01)
save_fig(fig, 'fig2_tarr_multihour.png')


# ── Fig 3: AAL 3시간대 비교 ──────────────────────────────────────────────
print("Fig 3: AAL 비교...")
fig, axes = plt.subplots(1, 3, figsize=(18, 7))

vmax_aal = gdf[[f'aal_h{h}' for h in TARGET_HOURS]].quantile(0.97).max()

for ax, (hour, label) in zip(axes, TARGET_HOURS.items()):
    col = f'aal_h{hour}'
    gdf.plot(column=col, ax=ax, cmap='Purples', vmin=0, vmax=vmax_aal,
             linewidth=0.15, edgecolor='#aaaaaa', missing_kwds={'color': '#eeeeee'})
    add_basemap(ax)
    mean_aal = gdf[col].mean()
    ax.set_title(f'{label}\n평균 AAL {mean_aal:.1f}', fontsize=11, fontweight='bold', pad=8)
    ax.axis('off')

sm = plt.cm.ScalarMappable(cmap='Purples', norm=Normalize(vmin=0, vmax=vmax_aal))
sm.set_array([])
fig.colorbar(sm, ax=axes, shrink=0.6, pad=0.01, label='AAL (A_i 단위)')
fig.suptitle('Absolute Accessibility Loss (AAL) — 시간대별 비교',
             fontsize=13, fontweight='bold', y=1.01)
save_fig(fig, 'fig3_aal_multihour.png')


# ── Fig 4: 분류 지도 (14시 피크 기준) ────────────────────────────────────
print("Fig 4: 분류 지도 (폭염 피크 14시)...")
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

fig, ax = plt.subplots(figsize=(9, 8))
for cat, color in color_map.items():
    sub = gdf[gdf['category'] == cat]
    if len(sub) > 0:
        sub.plot(ax=ax, color=color, linewidth=0.2, edgecolor='grey')
add_basemap(ax)
ax.set_title('Thermal-robust / Thermal-prone 분류\n(폭염 피크 14시 TARR 기준, 3분위)',
             fontsize=12, fontweight='bold', pad=10)
ax.axis('off')
patches = [mpatches.Patch(color=c, label=label_map[k])
           for k, c in color_map.items() if k in gdf['category'].values]
ax.legend(handles=patches, loc='lower right', fontsize=9, framealpha=0.9)
save_fig(fig, 'fig4_category_map.png')


# ── Fig 9: 시간대별 요약 막대 그래프 ─────────────────────────────────────
print("Fig 9: 시간대별 요약 막대 그래프...")
summary_df = pd.read_csv(SUMMARY_PATH, encoding='utf-8-sig')

labels      = ['Classic', '폭염 전\n(10시)', '폭염 중간\n(13시)', '폭염 피크\n(14시)']
mean_stops  = [
    summary_df['n_classic_stops'].mean(),
    summary_df['n_thermal_h10'].mean(),
    summary_df['n_thermal_h13'].mean(),
    summary_df['n_thermal_h14'].mean(),
]
blocked_cnt = [
    (summary_df['n_classic_stops'] == 0).sum(),
    (summary_df['n_thermal_h10'] == 0).sum(),
    (summary_df['n_thermal_h13'] == 0).sum(),
    (summary_df['n_thermal_h14'] == 0).sum(),
]
colors = ['#4393c3', '#74c476', '#fd8d3c', '#d73027']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

bars = ax1.bar(labels, mean_stops, color=colors, edgecolor='white', linewidth=0.8)
for bar, val in zip(bars, mean_stops):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
             f'{val:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax1.set_ylabel('평균 도달 정류장 수 (개)', fontsize=11)
ax1.set_title('시간대별 평균 도달 정류장 수', fontsize=12, fontweight='bold')
ax1.set_ylim(0, max(mean_stops) * 1.15)
ax1.grid(axis='y', alpha=0.3)

bars2 = ax2.bar(labels, blocked_cnt, color=colors, edgecolor='white', linewidth=0.8)
for bar, val in zip(bars2, blocked_cnt):
    pct = val / len(summary_df) * 100
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
             f'{val}개\n({pct:.1f}%)', ha='center', va='bottom', fontsize=9, fontweight='bold')
ax2.set_ylabel('정류장 0개 집계구 수 (완전 차단)', fontsize=11)
ax2.set_title('시간대별 완전 차단 집계구 수', fontsize=12, fontweight='bold')
ax2.set_ylim(0, max(blocked_cnt) * 1.2)
ax2.grid(axis='y', alpha=0.3)

fig.suptitle('폭염 진행에 따른 대중교통 접근성 변화 — 성동구 570개 집계구',
             fontsize=13, fontweight='bold')
plt.tight_layout()
save_fig(fig, 'fig9_catchment_summary_bar.png')

print("\n=== Task 5 완료 ===")
