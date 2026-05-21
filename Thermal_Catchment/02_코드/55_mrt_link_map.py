"""
링크별 MRT 공간 분포 시각화 (13시)
단계구분도: 자연분류(Jenks) 5개 급간, 노랑→주황→빨강
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import contextily as ctx
from matplotlib.cm import ScalarMappable
from matplotlib.colors import BoundaryNorm
import matplotlib
import warnings
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

STP_BASE  = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH  = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
MRT_PATH  = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
JBG_PATH  = '/Users/jin/석사논문/통계지역경계/집계구.shp'
OUT_PATH  = os.path.join(FIG_DIR, 'mrt_link_choropleth_13h.png')

HOUR     = 13
MRT_THRESH = 55.0

# ── 데이터 로드 ─────────────────────────────────────────────────────────
print("네트워크 로드...")
G = ox.load_graphml(NET_PATH)
_, edges = ox.graph_to_gdfs(G)
edges_utm = edges.to_crs('EPSG:5186').reset_index().copy()
edges_utm['u'] = edges_utm['u'].astype(str)
edges_utm['v'] = edges_utm['v'].astype(str)

print("MRT 데이터 로드...")
mrt_df = pd.read_csv(MRT_PATH)
h13 = mrt_df[mrt_df['hour'] == HOUR].copy()
h13['u'] = h13['u'].astype(str)
h13['v'] = h13['v'].astype(str)

edges_merged = edges_utm.merge(
    h13[['u', 'v', 'mrt']],
    on=['u', 'v'],
    how='left'
)
edges_merged = edges_merged.to_crs('EPSG:3857')

valid = edges_merged.dropna(subset=['mrt'])
print(f"  MRT 있는 링크: {len(valid):,} / {len(edges_merged):,}")
print(f"  MRT 범위: {valid['mrt'].min():.1f} ~ {valid['mrt'].max():.1f}°C")
print(f"  MRT ≥ {MRT_THRESH}°C: {(valid['mrt'] >= MRT_THRESH).sum():,}개 ({(valid['mrt'] >= MRT_THRESH).mean()*100:.1f}%)")

# ── 분류 (Jenks 자연분류 5단계) ──────────────────────────────────────────
vals = valid['mrt'].values

if HAS_MAPCLASSIFY:
    clf = mapclassify.NaturalBreaks(vals, k=5)
    breaks = [vals.min()] + list(clf.bins)
else:
    # 백분위수 기반 대체
    breaks = [vals.min(),
              np.percentile(vals, 20),
              np.percentile(vals, 40),
              np.percentile(vals, 60),
              np.percentile(vals, 80),
              vals.max()]

breaks = [round(b, 1) for b in breaks]
breaks[0] = float(np.floor(vals.min()))
breaks[-1] = float(np.ceil(vals.max()))

print(f"\n분류 급간 (Jenks): {breaks}")

# ── 색상 설정: 노랑 → 주황 → 빨강 ──────────────────────────────────────
colors_hex = ['#FFCC99', '#FF9933', '#FF6600', '#FF2200', '#990000']
cmap = mcolors.ListedColormap(colors_hex)
norm = BoundaryNorm(breaks, ncolors=len(colors_hex))

# 링크별 색상 인덱스 할당
def assign_class(val):
    for j in range(len(breaks) - 1):
        if val <= breaks[j + 1]:
            return j
    return len(breaks) - 2

valid = valid.copy()
valid['cls'] = valid['mrt'].apply(assign_class)

# 집계구 경계 로드
print("집계구 경계 로드...")
jbg = gpd.read_file(JBG_PATH)
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].to_crs('EPSG:3857')

# 배경(MRT 없는 링크) 별도
no_mrt = edges_merged[edges_merged['mrt'].isna()].copy()

# ── 시각화 ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 12), dpi=150)

# 배경 링크 (회색) — extent 먼저 확정
no_mrt.plot(ax=ax, color='#CCCCCC', linewidth=0.4, alpha=0.5, zorder=2)

# MRT 링크 — 급간별 색상
for cls_idx, color in enumerate(colors_hex):
    subset = valid[valid['cls'] == cls_idx]
    if len(subset) == 0:
        continue
    lw = 1.0 if cls_idx < 4 else 1.4
    subset.plot(ax=ax, color=color, linewidth=lw, alpha=0.9, zorder=3 + cls_idx)

# 베이스맵 (extent 확정 후)
try:
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=14, alpha=0.6)
except Exception:
    pass

# 집계구 경계 — 베이스맵 바로 위, 링크 아래
jbg.plot(ax=ax, facecolor='none', edgecolor='#AAAAAA', linewidth=0.6, alpha=0.6, zorder=1)

hot = valid[valid['mrt'] >= MRT_THRESH]

# 범례 패치
legend_patches = []
for j in range(len(colors_hex)):
    lo = breaks[j]
    hi = breaks[j + 1]
    cnt = (valid['cls'] == j).sum()
    label = f'{lo:.1f}–{hi:.1f}°C  ({cnt:,}개)'
    legend_patches.append(mpatches.Patch(facecolor=colors_hex[j], edgecolor='#555', label=label))

legend_patches.append(mpatches.Patch(facecolor='none', edgecolor='#888888',
                                      linewidth=1.0, label='집계구 경계'))

ax.legend(handles=legend_patches, title='MRT (°C)', loc='upper left',
          fontsize=12, title_fontsize=13, framealpha=0.92,
          edgecolor='#999', fancybox=False,
          handleheight=1.8, handlelength=2.0,
          borderpad=1.0, labelspacing=0.7)

ax.set_title(f'링크별 평균복사온도(MRT) 공간 분포\n13시 기준 | 성동구 | 도시숲 캐노피(10m) 반영',
             fontsize=13, fontweight='bold', pad=12)
ax.set_axis_off()

plt.tight_layout()
plt.savefig(OUT_PATH, dpi=150, bbox_inches='tight')
plt.close()
print(f"\n저장 완료: {OUT_PATH}")
