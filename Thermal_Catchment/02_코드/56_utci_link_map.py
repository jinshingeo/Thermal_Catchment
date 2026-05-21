"""
링크별 UTCI 공간 분포 시각화 (13시)
MRT 지도와 동일 스타일: Jenks 5단계, 연주황→빨강, 범례 좌상단, 집계구 경계 옅은 회색
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.colors import BoundaryNorm
import contextily as ctx
import warnings
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False


BASE    = os.path.dirname(os.path.abspath(__file__))
PROJ    = os.path.dirname(BASE)
RES_DIR = os.path.join(PROJ, '03_결과물')
FIG_DIR = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

STP_BASE = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
MRT_PATH = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
JBG_PATH = '/Users/jin/석사논문/통계지역경계/집계구.shp'
OUT_PATH = os.path.join(FIG_DIR, 'utci_link_choropleth_13h.png')

HOUR = 13

# ── 데이터 로드 ─────────────────────────────────────────────────────────
print("네트워크 로드...")
G = ox.load_graphml(NET_PATH)
_, edges = ox.graph_to_gdfs(G)
edges_utm = edges.to_crs('EPSG:5186').reset_index().copy()
edges_utm['u'] = edges_utm['u'].astype(str)
edges_utm['v'] = edges_utm['v'].astype(str)

print("UTCI 데이터 로드...")
df = pd.read_csv(MRT_PATH)
h13 = df[df['hour'] == HOUR].copy()
h13['u'] = h13['u'].astype(str)
h13['v'] = h13['v'].astype(str)

edges_merged = edges_utm.merge(h13[['u', 'v', 'utci_final']], on=['u', 'v'], how='left')
edges_merged = edges_merged.to_crs('EPSG:3857')

valid  = edges_merged.dropna(subset=['utci_final']).copy()
no_val = edges_merged[edges_merged['utci_final'].isna()].copy()
print(f"  UTCI 범위: {valid['utci_final'].min():.1f} ~ {valid['utci_final'].max():.1f}°C")
print(f"  UTCI 평균: {valid['utci_final'].mean():.1f}°C")

# ── 분류: UTCI 공식 열 스트레스 급간 (Bröde et al. 2012) ──────────────
# 데이터 범위 33.4–56.4°C → 해당 구간 3개
UTCI_BREAKS  = [32, 38, 46, 57]          # 상한은 데이터 최대값 올림
UTCI_LABELS  = ['강한 열 스트레스 (32–38°C)',
                 '매우 강한 열 스트레스 (38–46°C)',
                 '극한 열 스트레스 (>46°C)']
colors_hex   = ['#FF9933', '#FF2200', '#7A0000']

def assign_class(val):
    for j in range(len(UTCI_BREAKS) - 1):
        if val < UTCI_BREAKS[j + 1]:
            return j
    return len(UTCI_BREAKS) - 2

valid['cls'] = valid['utci_final'].apply(assign_class)

for j, lbl in enumerate(UTCI_LABELS):
    cnt = (valid['cls'] == j).sum()
    print(f"  {lbl}: {cnt:,}개 ({cnt/len(valid)*100:.1f}%)")

# ── 집계구 경계 ──────────────────────────────────────────────────────────
print("집계구 경계 로드...")
jbg = gpd.read_file(JBG_PATH)
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].to_crs('EPSG:3857')

# ── 시각화 ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 12), dpi=150)

# 배경 링크 — extent 확정
no_val.plot(ax=ax, color='#CCCCCC', linewidth=0.4, alpha=0.5, zorder=2)

# UTCI 링크 — 급간별 색상
for cls_idx, color in enumerate(colors_hex):
    subset = valid[valid['cls'] == cls_idx]
    if len(subset) == 0:
        continue
    lw = 1.0 if cls_idx < 4 else 1.4
    subset.plot(ax=ax, color=color, linewidth=lw, alpha=0.9, zorder=3 + cls_idx)

# 베이스맵
try:
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=14, alpha=0.6)
except Exception:
    pass

# 집계구 경계 — 가장 뒤, 옅은 회색
jbg.plot(ax=ax, facecolor='none', edgecolor='#AAAAAA', linewidth=0.6, alpha=0.6, zorder=1)

# 범례
legend_patches = []
for j, lbl in enumerate(UTCI_LABELS):
    cnt = (valid['cls'] == j).sum()
    legend_patches.append(mpatches.Patch(
        facecolor=colors_hex[j], edgecolor='#555',
        label=f'{lbl}  ({cnt:,}개)'
    ))
legend_patches.append(mpatches.Patch(
    facecolor='none', edgecolor='#AAAAAA', linewidth=1.0, label='집계구 경계'
))

ax.legend(handles=legend_patches, title='UTCI (°C)', loc='upper left',
          fontsize=12, title_fontsize=13, framealpha=0.92,
          edgecolor='#999', fancybox=False,
          handleheight=1.8, handlelength=2.0,
          borderpad=1.0, labelspacing=0.7)

ax.set_title('링크별 UTCI 공간 분포\n13시 기준 | 성동구 | 도시숲 캐노피(10m) 반영',
             fontsize=13, fontweight='bold', pad=12)
ax.set_axis_off()

plt.tight_layout()
plt.savefig(OUT_PATH, dpi=150, bbox_inches='tight')
plt.close()
print(f"\n저장 완료: {OUT_PATH}")
