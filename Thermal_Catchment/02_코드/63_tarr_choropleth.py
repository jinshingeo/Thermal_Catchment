"""
집계구별 TARR 단계구분도 (슬라이드 9용)
Jenks 5단계, 연노랑→주황→빨강, 범례 좌상단, CartoDB Positron 베이스맵
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import contextily as ctx
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False

try:
    import mapclassify
    HAS_MAPCLASSIFY = True
except ImportError:
    HAS_MAPCLASSIFY = False

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJ    = os.path.dirname(BASE)
RES_DIR = os.path.join(PROJ, '03_결과물')
FIG_DIR = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

MC_PATH  = os.path.join(RES_DIR, 'monte_carlo_tarr.csv')
JBG_PATH = '/Users/jin/석사논문/통계지역경계/집계구.shp'
OUT_PATH = os.path.join(FIG_DIR, 'tarr_choropleth.png')

# ── 데이터 로드 및 조인 ─────────────────────────────────────────────────
print("데이터 로드...")
mc = pd.read_csv(MC_PATH)
mc['집계구코드'] = mc['집계구코드'].astype(str)

jbg = gpd.read_file(JBG_PATH)
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].to_crs('EPSG:3857')
jbg['TOT_REG_CD'] = jbg['TOT_REG_CD'].astype(str)

jbg_merged = jbg.merge(mc[['집계구코드', 'tarr_single']], left_on='TOT_REG_CD', right_on='집계구코드', how='left')
print(f"  조인 결과: {jbg_merged['tarr_single'].notna().sum()} / {len(jbg_merged)} 집계구")

valid  = jbg_merged.dropna(subset=['tarr_single']).copy()
no_val = jbg_merged[jbg_merged['tarr_single'].isna()].copy()
vals   = valid['tarr_single'].values

# ── 5단계 고정 급간 (0-20-40-60-80-100) ────────────────────────────────
breaks     = [0, 20, 40, 60, 80, 100]
colors_hex = ['#FFF2CC', '#FFCC99', '#FF9933', '#FF4400', '#990000']

def assign_class(v):
    for j in range(len(breaks) - 1):
        if v <= breaks[j + 1]:
            return j
    return len(breaks) - 2

valid['cls'] = valid['tarr_single'].apply(assign_class)

for j in range(len(colors_hex)):
    cnt = (valid['cls'] == j).sum()
    print(f"  [{breaks[j]}–{breaks[j+1]}%]: {cnt}개")

# ── 시각화 ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 12), dpi=150)

# TARR 없는 집계구 (옅은 회색)
if len(no_val):
    no_val.plot(ax=ax, facecolor='#EEEEEE', edgecolor='#CCCCCC', linewidth=0.3, zorder=2)

# TARR 단계구분도
for cls_idx, color in enumerate(colors_hex):
    subset = valid[valid['cls'] == cls_idx]
    if len(subset) == 0:
        continue
    subset.plot(ax=ax, facecolor=color, edgecolor='#888888', linewidth=0.3, alpha=0.9, zorder=3 + cls_idx)

# 베이스맵
try:
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=14, alpha=0.4)
except Exception:
    pass

# 범례
legend_patches = []
for j in range(len(colors_hex)):
    cnt = (valid['cls'] == j).sum()
    legend_patches.append(mpatches.Patch(
        facecolor=colors_hex[j], edgecolor='#555',
        label=f'{breaks[j]}–{breaks[j+1]}%  ({cnt}개)'
    ))

ax.legend(handles=legend_patches, title='TARR (%)', loc='upper left',
          fontsize=12, title_fontsize=13, framealpha=0.92,
          edgecolor='#999', fancybox=False,
          handleheight=1.8, handlelength=2.0,
          borderpad=1.0, labelspacing=0.7)

ax.set_axis_off()
plt.tight_layout()
plt.savefig(OUT_PATH, dpi=150, bbox_inches='tight')
plt.close()
print(f"저장 완료: {OUT_PATH}")
