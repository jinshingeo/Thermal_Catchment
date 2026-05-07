"""
UTCI 산출 입력변수 + MRT + UTCI 시각화 (교수님 논의용)
======================================================
저장 위치: 03_결과물/figures/method3/

출력 파일:
  input_sdot_sensor_map.png      : S-DoT 센서 위치 + 13시 기온 지도
  input_meteo_3h_grid.png        : 3시간대 × (Tair / RH / va) 3×3 링크 지도
  link_mrt_3h_grid.png           : 3시간대 MRT 링크 지도
  link_utci_3h_grid.png          : 3시간대 UTCI 링크 지도
"""

import os
import numpy as np
import pandas as pd
import networkx as nx
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import contextily as ctx
from pyproj import Transformer
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures', 'method3')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH    = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
UTCI_PATH   = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
SDOT_PATH   = '/Users/jin/석사논문/성동구_STP연구/04_분석결과/sdot_utci_v3_seongdong.csv'
JBG_SHP     = os.path.join(PROJ_DIR, '01_데이터', '행정경계',
                            '통계지역경계(2016년+기준)', '집계구.shp')

TARGET_HOURS = [9, 13, 18]
HOUR_LABELS  = {9: '09시\n(출근)', 13: '13시\n(피크)', 18: '18시\n(퇴근)'}


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G = ox.load_graphml(NET_PATH)
G = G.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
edges_wm = edges_gdf.to_crs(epsg=3857).reset_index()
edges_wm['u_str'] = edges_wm['u'].astype(str)
edges_wm['v_str'] = edges_wm['v'].astype(str)

print("UTCI 데이터 로드 중...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
utci_df['u_str'] = utci_df['u'].astype(str)
utci_df['v_str'] = utci_df['v'].astype(str)

print("S-DoT 데이터 로드 중...")
sdot = pd.read_csv(SDOT_PATH, encoding='utf-8-sig')
sensor_avg = (sdot.groupby(['serial', 'lat', 'lon', 'hour'])[['temp', 'humi', 'v']]
              .mean().reset_index())

print("집계구 경계 로드 중...")
jbg_all = gpd.read_file(JBG_SHP, encoding='cp949')
jbg = jbg_all[jbg_all['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
jbg = jbg.set_crs(epsg=5179, allow_override=True).to_crs(epsg=3857)


def make_edge_gdf(hour, col):
    """시간대별 링크 GeoDataFrame with value column"""
    h_df = utci_df[utci_df['hour'] == hour][['u_str', 'v_str', col]].copy()
    merged = edges_wm.merge(h_df, on=['u_str', 'v_str'], how='left')
    merged2 = edges_wm.merge(
        h_df.rename(columns={'u_str': 'v_str', 'v_str': 'u_str'}),
        on=['u_str', 'v_str'], how='left'
    )
    merged[col] = merged[col].fillna(merged2[col])
    return merged


def add_basemap(ax):
    try:
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=13, alpha=0.25)
    except Exception:
        pass


def add_boundary(ax):
    jbg.boundary.plot(ax=ax, color='#333333', linewidth=0.5, alpha=0.6, zorder=5)


# ══════════════════════════════════════════════════════════════════════
# Fig 1: S-DoT 센서 위치 + 13시 기온 지도
# ══════════════════════════════════════════════════════════════════════
print("\n[Fig1] S-DoT 센서 위치 지도 생성 중...")
s13 = sensor_avg[sensor_avg['hour'] == 13].copy()
s13_gdf = gpd.GeoDataFrame(
    s13, geometry=gpd.points_from_xy(s13['lon'], s13['lat']),
    crs='EPSG:4326'
).to_crs(epsg=3857)

fig, ax = plt.subplots(figsize=(9, 8))
jbg.plot(ax=ax, color='#f5f5f5', edgecolor='#aaaaaa', linewidth=0.5, zorder=1)
add_basemap(ax)
add_boundary(ax)

sc = ax.scatter(s13_gdf.geometry.x, s13_gdf.geometry.y,
                c=s13_gdf['temp'], cmap='RdYlBu_r',
                vmin=s13_gdf['temp'].min(), vmax=s13_gdf['temp'].max(),
                s=80, zorder=6, edgecolors='black', linewidths=0.5)
cbar = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.01)
cbar.set_label('기온 (°C)', fontsize=11)

ax.set_title(
    f'S-DoT 기상 센서 위치 및 13시 기온 분포\n'
    f'(n={len(s13_gdf)}개 센서 | 폭염일 2025.07.28~08.03 평균)',
    fontsize=12, fontweight='bold'
)
ax.set_axis_off()
plt.tight_layout()
out = os.path.join(FIG_DIR, 'input_sdot_sensor_map.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {out}")


# ══════════════════════════════════════════════════════════════════════
# Fig 2: 3시간대 × 3변수 (Tair / RH / va) 링크 지도 (3×3)
# ══════════════════════════════════════════════════════════════════════
print("\n[Fig2] 기상변수 3×3 그리드 지도 생성 중...")

VARS = {
    'Tair_idw': {'label': '기온 (°C)',     'cmap': 'RdYlBu_r', 'vmin': None, 'vmax': None},
    'RH_idw':   {'label': '상대습도 (%)', 'cmap': 'YlGnBu',   'vmin': 40,   'vmax': 95},
    'va_idw':   {'label': '풍속 (m/s)',   'cmap': 'PuBu',     'vmin': 0.5,  'vmax': 3.0},
}
var_keys = list(VARS.keys())

fig, axes = plt.subplots(3, 3, figsize=(21, 20))

for col_idx, var in enumerate(var_keys):
    vinfo = VARS[var]
    # 전체 범위 자동 계산 (Tair만)
    if vinfo['vmin'] is None:
        all_vals = utci_df[utci_df['hour'].isin(TARGET_HOURS)][var].dropna()
        vmin, vmax = all_vals.min(), all_vals.max()
    else:
        vmin, vmax = vinfo['vmin'], vinfo['vmax']

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(vinfo['cmap'])

    for row_idx, h in enumerate(TARGET_HOURS):
        ax = axes[row_idx][col_idx]
        e = make_edge_gdf(h, var)

        # 색상 매핑
        colors = [cmap(norm(v)) if not np.isnan(v) else '#cccccc'
                  for v in e[var]]
        e.plot(ax=ax, color=colors, linewidth=1.2, zorder=3)
        add_basemap(ax)
        add_boundary(ax)

        # 열 제목 (첫 행만)
        if row_idx == 0:
            ax.set_title(vinfo['label'], fontsize=13, fontweight='bold', pad=5)

        # 행 레이블 (첫 열만)
        if col_idx == 0:
            ax.set_ylabel(HOUR_LABELS[h], fontsize=12, fontweight='bold',
                          rotation=0, labelpad=55)

        # 통계 텍스트
        vals = e[var].dropna()
        ax.text(0.02, 0.04,
                f'mean={vals.mean():.1f}  std={vals.std():.2f}',
                transform=ax.transAxes, fontsize=8.5,
                bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8))
        ax.set_axis_off()

    # 컬러바 (마지막 행 아래)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes[:, col_idx], fraction=0.025, pad=0.02,
                        orientation='horizontal', location='bottom')
    cbar.set_label(vinfo['label'], fontsize=10)

fig.suptitle(
    '기상 입력변수 링크별 공간분포 (S-DoT IDW 보간)\n'
    'Method 3 | 폭염일 2025.07.28~08.03 시간대 평균',
    fontsize=14, fontweight='bold', y=1.01
)
plt.tight_layout()
out = os.path.join(FIG_DIR, 'input_meteo_3h_grid.png')
fig.savefig(out, dpi=130, bbox_inches='tight')
plt.close()
print(f"  저장: {out}")


# ══════════════════════════════════════════════════════════════════════
# Fig 3: 3시간대 MRT 링크 지도 (1×3)
# ══════════════════════════════════════════════════════════════════════
print("\n[Fig3] MRT 링크 지도 생성 중...")

all_mrt = utci_df[utci_df['hour'].isin(TARGET_HOURS)]['mrt'].dropna()
mrt_vmin, mrt_vmax = all_mrt.min(), all_mrt.max()
mrt_norm = mcolors.Normalize(vmin=mrt_vmin, vmax=mrt_vmax)
mrt_cmap = plt.get_cmap('plasma')

fig, axes = plt.subplots(1, 3, figsize=(21, 8))

for col_idx, h in enumerate(TARGET_HOURS):
    ax = axes[col_idx]
    e = make_edge_gdf(h, 'mrt')
    colors = [mrt_cmap(mrt_norm(v)) if not np.isnan(v) else '#cccccc'
              for v in e['mrt']]
    e.plot(ax=ax, color=colors, linewidth=1.3, zorder=3)
    add_basemap(ax)
    add_boundary(ax)

    vals = e['mrt'].dropna()
    pct55 = (vals >= 55).sum() / len(vals) * 100
    ax.set_title(f'{HOUR_LABELS[h].replace(chr(10), " ")}\n'
                 f'mean={vals.mean():.1f}°C  std={vals.std():.1f}°C  '
                 f'≥55°C: {pct55:.1f}%',
                 fontsize=11, fontweight='bold')
    ax.set_axis_off()

sm = cm.ScalarMappable(cmap=mrt_cmap, norm=mrt_norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=axes, fraction=0.015, pad=0.02, orientation='vertical')
cbar.set_label('MRT (°C)', fontsize=12)

# MRT 55°C 기준선 표시
cbar.ax.axhline(y=mrt_norm(55.0), color='white', linewidth=2, linestyle='--')
cbar.ax.text(1.1, mrt_norm(55.0), '55°C\n(Hard Cut)',
             transform=cbar.ax.transAxes, fontsize=9, va='center', color='black')

fig.suptitle(
    '링크별 평균복사온도 (MRT) 공간분포\n'
    'SOLWEIG 약식 (Lindberg & Grimmond 2011) | S-DoT IDW + Open-Meteo GHI',
    fontsize=13, fontweight='bold'
)
plt.tight_layout()
out = os.path.join(FIG_DIR, 'link_mrt_3h_grid.png')
fig.savefig(out, dpi=130, bbox_inches='tight')
plt.close()
print(f"  저장: {out}")


# ══════════════════════════════════════════════════════════════════════
# Fig 4: 3시간대 UTCI 링크 지도 (1×3)
# ══════════════════════════════════════════════════════════════════════
print("\n[Fig4] UTCI 링크 지도 생성 중...")

# UTCI 스트레스 카테고리 기준 색상
UTCI_BINS   = [0, 26, 32, 38, 46, 80]
UTCI_COLORS = ['#4575b4', '#91bfdb', '#fee090', '#fc8d59', '#d73027']
UTCI_LABELS = ['< 26°C\n(no stress)', '26~32°C\n(moderate)', '32~38°C\n(strong)',
               '38~46°C\n(very strong)', '> 46°C\n(extreme)']
utci_norm  = mcolors.BoundaryNorm(UTCI_BINS, len(UTCI_COLORS))
utci_cmap  = mcolors.ListedColormap(UTCI_COLORS)

fig, axes = plt.subplots(1, 3, figsize=(21, 8))

for col_idx, h in enumerate(TARGET_HOURS):
    ax = axes[col_idx]
    e = make_edge_gdf(h, 'utci_m3')
    colors = [utci_cmap(utci_norm(v)) if not np.isnan(v) else '#cccccc'
              for v in e['utci_m3']]
    e.plot(ax=ax, color=colors, linewidth=1.3, zorder=3)
    add_basemap(ax)
    add_boundary(ax)

    vals = e['utci_m3'].dropna()
    pct38 = (vals >= 38).sum() / len(vals) * 100
    pct46 = (vals >= 46).sum() / len(vals) * 100
    ax.set_title(f'{HOUR_LABELS[h].replace(chr(10), " ")}\n'
                 f'mean={vals.mean():.1f}°C  ≥38°C: {pct38:.1f}%  ≥46°C: {pct46:.1f}%',
                 fontsize=11, fontweight='bold')
    ax.set_axis_off()

# 카테고리 범례
from matplotlib.patches import Patch
handles = [Patch(color=c, label=l) for c, l in zip(UTCI_COLORS, UTCI_LABELS)]
fig.legend(handles=handles, loc='lower center', ncol=5, fontsize=10,
           bbox_to_anchor=(0.5, -0.02), framealpha=0.9, title='UTCI 열 스트레스 분류 (Bröde et al. 2012)')

fig.suptitle(
    '링크별 UTCI 공간분포\n'
    'pythermalcomfort (Bröde et al. 2012) | S-DoT IDW 기상 + SOLWEIG MRT',
    fontsize=13, fontweight='bold'
)
plt.tight_layout(rect=[0, 0.06, 1, 1])
out = os.path.join(FIG_DIR, 'link_utci_3h_grid.png')
fig.savefig(out, dpi=130, bbox_inches='tight')
plt.close()
print(f"  저장: {out}")

print("\n=== 완료 ===")
print(f"저장 위치: {FIG_DIR}")
for f in sorted(os.listdir(FIG_DIR)):
    if f.endswith('.png'):
        print(f"  {f}")
