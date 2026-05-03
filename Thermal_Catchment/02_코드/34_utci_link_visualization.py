"""
UTCI 5단계 링크 시각화
======================
성동구 보행 네트워크 각 링크의 UTCI를 5단계로 분류하여 지도 위에 표시

UTCI 5단계 (Bröde et al. 2012):
  0: < 26°C  — No / Slight thermal stress
  1: 26~32°C — Moderate heat stress
  2: 32~38°C — Strong heat stress
  3: 38~46°C — Very strong heat stress  ← hard cut 기준
  4: > 46°C  — Extreme heat stress

출력 (→ 03_결과물/figures/):
  fig5_utci_links_13h.png     — 13시 기준 링크별 UTCI 단계 지도
  fig6_utci_hourly.png        — 시간대별 UTCI ≥ 38°C 링크 비율 변화
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import contextily as ctx

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH  = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
UTCI_PATH = os.path.join(RES_DIR, 'link_utci_solweig.csv')
TARGET_HOUR = 13

UTCI_BINS   = [-np.inf, 26, 32, 38, 46, np.inf]
UTCI_LABELS = [0, 1, 2, 3, 4]
UTCI_COLORS = {
    0: '#4575b4',   # 파랑 — No/Slight stress
    1: '#a8d96c',   # 연두 — Moderate
    2: '#fee08b',   # 노랑 — Strong
    3: '#f46d43',   # 주황빨강 — Very strong
    4: '#a50026',   # 진빨강 — Extreme
}
UTCI_NAMES = {
    0: '< 26°C  (약한 열스트레스)',
    1: '26–32°C (보통)',
    2: '32–38°C (강함)',
    3: '38–46°C (매우 강함)',
    4: '> 46°C  (극심)',
}


# ── 한국어 폰트 ───────────────────────────────────────────────────────────
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
print("네트워크 로드 중...")
G = ox.load_graphml(NET_PATH)
edges_gdf = ox.graph_to_gdfs(G, nodes=False, edges=True).reset_index()
edges_gdf['u'] = edges_gdf['u'].astype(str)
edges_gdf['v'] = edges_gdf['v'].astype(str)
edges_gdf = edges_gdf.to_crs(epsg=3857)
print(f"  엣지 수: {len(edges_gdf):,}개")

print("UTCI 데이터 로드 중...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
utci_df['u'] = utci_df['u'].astype(str)
utci_df['v'] = utci_df['v'].astype(str)


# ── 2. 13시 기준 join ──────────────────────────────────────────────────────
print(f"{TARGET_HOUR}시 기준 데이터 join 중...")
utci_13h = utci_df[utci_df['hour'] == TARGET_HOUR][['u', 'v', 'utci_final']].copy()
utci_13h['utci_class'] = pd.cut(
    utci_13h['utci_final'],
    bins=UTCI_BINS,
    labels=UTCI_LABELS,
    right=False
).astype(int)

gdf = edges_gdf.merge(utci_13h, on=['u', 'v'], how='left')
# NaN = UTCI 데이터 없는 링크 (음영·미계산 링크), -1로 구분
gdf['utci_class'] = gdf['utci_class'].fillna(-1).astype(int)

total = len(gdf)
no_data = (gdf['utci_class'] == -1).sum()
print(f"\n  UTCI 단계별 링크 수 ({TARGET_HOUR}시):")
print(f"    데이터 없음 (음영·미계산): {no_data:,}개 ({no_data/total*100:.1f}%)")
for cls in UTCI_LABELS:
    cnt = (gdf['utci_class'] == cls).sum()
    if cnt > 0:
        print(f"    단계 {cls} {UTCI_NAMES[cls]}: {cnt:,}개 ({cnt/total*100:.1f}%)")


# ── Fig 5: 13시 UTCI 단계별 링크 지도 ────────────────────────────────────
print(f"\nFig 5: {TARGET_HOUR}시 UTCI 링크 단계 지도...")
fig, ax = plt.subplots(figsize=(11, 10))

# 데이터 없는 링크 먼저 (회색 배경)
no_data_gdf = gdf[gdf['utci_class'] == -1]
if len(no_data_gdf) > 0:
    no_data_gdf.plot(ax=ax, color='#d0d0d0', linewidth=0.5, zorder=1)
# UTCI 단계별: 낮은 것부터 그려 높은 단계가 위에 오도록
for cls in UTCI_LABELS:
    sub = gdf[gdf['utci_class'] == cls]
    if len(sub) == 0:
        continue
    lw = 0.7 if cls < 3 else 1.3
    sub.plot(ax=ax, color=UTCI_COLORS[cls], linewidth=lw, zorder=cls + 2)

try:
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=14)
except Exception:
    pass

ax.set_title(f'성동구 보행 네트워크 링크별 UTCI 열스트레스 단계\n({TARGET_HOUR}시 기준, SOLWEIG 기반)',
             fontsize=13, fontweight='bold', pad=12)
ax.axis('off')

present_classes = [c for c in UTCI_LABELS if (gdf['utci_class'] == c).sum() > 0]
patches = [mpatches.Patch(color='#d0d0d0', label='데이터 없음 (음영·미계산 링크)')]
patches += [mpatches.Patch(color=UTCI_COLORS[c], label=UTCI_NAMES[c]) for c in present_classes]
ax.legend(handles=patches, loc='lower right', fontsize=9,
          framealpha=0.9, title='UTCI 열스트레스 단계', title_fontsize=9)

path = os.path.join(FIG_DIR, 'fig5_utci_links_13h.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  저장: {path}")


# ── Fig 6: 시간대별 UTCI ≥ 38°C 링크 비율 ────────────────────────────────
print("Fig 6: 시간대별 고온 링크 비율...")
n_total = utci_df[['u', 'v']].drop_duplicates().shape[0]

hourly = (
    utci_df[utci_df['utci_final'] >= 38]
    .groupby('hour')['u']
    .count()
    .reindex(range(24), fill_value=0)
)
pct = hourly / n_total * 100

fig, ax = plt.subplots(figsize=(11, 5))
bars = ax.bar(range(24), pct.values, color=[
    '#f46d43' if h == TARGET_HOUR else '#aec7e8' for h in range(24)
], edgecolor='white', linewidth=0.5)

ax.axhline(y=pct[TARGET_HOUR], color='#d73027', linestyle='--', linewidth=1, alpha=0.7)
ax.annotate(f'{TARGET_HOUR}시 {pct[TARGET_HOUR]:.1f}%',
            xy=(TARGET_HOUR, pct[TARGET_HOUR]),
            xytext=(TARGET_HOUR + 1.2, pct[TARGET_HOUR] + 0.5),
            fontsize=10, color='#d73027')

ax.set_xlabel('시간 (시)', fontsize=11)
ax.set_ylabel('UTCI ≥ 38°C 링크 비율 (%)', fontsize=11)
ax.set_title('시간대별 UTCI ≥ 38°C (Very Strong Heat Stress) 링크 비율\n성동구 보행 네트워크',
             fontsize=12, fontweight='bold')
ax.set_xticks(range(24))
ax.set_xlim(-0.5, 23.5)
ax.grid(axis='y', alpha=0.3)

path = os.path.join(FIG_DIR, 'fig6_utci_hourly.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  저장: {path}")

# ── Fig 7: 13시 MRT 공간 분포 지도 ──────────────────────────────────────
print("Fig 7: MRT 공간 분포 지도...")
mrt_13h = utci_df[utci_df['hour'] == TARGET_HOUR][['u', 'v', 'mrt']].copy()
mrt_13h['u'] = mrt_13h['u'].astype(str)
mrt_13h['v'] = mrt_13h['v'].astype(str)

gdf_mrt = edges_gdf.merge(mrt_13h, on=['u', 'v'], how='left')
has_mrt  = gdf_mrt[gdf_mrt['mrt'].notna()]
no_mrt   = gdf_mrt[gdf_mrt['mrt'].isna()]

vmin_mrt = has_mrt['mrt'].quantile(0.02)
vmax_mrt = has_mrt['mrt'].quantile(0.98)

fig, ax = plt.subplots(figsize=(11, 10))
if len(no_mrt) > 0:
    no_mrt.plot(ax=ax, color='#e0e0e0', linewidth=0.5, zorder=1)
has_mrt.plot(column='mrt', ax=ax, cmap='RdYlBu_r',
             vmin=vmin_mrt, vmax=vmax_mrt,
             linewidth=0.8, zorder=2)

try:
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=14)
except Exception:
    pass

ax.set_title(f'성동구 보행 네트워크 링크별 평균복사온도 (MRT)\n({TARGET_HOUR}시 기준, SVF 기반 SOLWEIG)',
             fontsize=13, fontweight='bold', pad=12)
ax.axis('off')

sm = plt.cm.ScalarMappable(cmap='RdYlBu_r',
                            norm=plt.Normalize(vmin=vmin_mrt, vmax=vmax_mrt))
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
cbar.set_label('MRT (°C)', fontsize=11)

path = os.path.join(FIG_DIR, 'fig7_mrt_links_13h.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  저장: {path}")


# ── Fig 8: MRT vs UTCI 산점도 (SVF 색상) ─────────────────────────────────
print("Fig 8: MRT vs UTCI 산점도...")
h13_sample = utci_df[utci_df['hour'] == TARGET_HOUR].copy()

fig, ax = plt.subplots(figsize=(8, 6))
sc = ax.scatter(h13_sample['mrt'], h13_sample['utci_final'],
                c=h13_sample['svf'], cmap='RdYlGn',
                s=3, alpha=0.4, linewidths=0)

ax.axvline(x=38, color='#d73027', linestyle='--', linewidth=1.2, alpha=0.8,
           label='UTCI 38°C (임계값)')
ax.axhline(y=38, color='#d73027', linestyle='--', linewidth=1.2, alpha=0.8)

cbar = fig.colorbar(sc, ax=ax, pad=0.02)
cbar.set_label('SVF (하늘열린비율)', fontsize=10)

ax.set_xlabel('MRT (°C)', fontsize=11)
ax.set_ylabel('UTCI (°C)', fontsize=11)
ax.set_title(f'MRT–UTCI 관계 (SVF 색상, {TARGET_HOUR}시)\n'
             f'MRT std={h13_sample["mrt"].std():.1f}°C  →  UTCI std={h13_sample["utci_final"].std():.2f}°C',
             fontsize=11, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(alpha=0.3)

path = os.path.join(FIG_DIR, 'fig8_mrt_utci_scatter.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"  저장: {path}")

print("\n=== UTCI 시각화 완료 ===")
