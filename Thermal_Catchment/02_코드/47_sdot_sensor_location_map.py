"""
S-DoT 57개 기상 센서 위치 지도
===============================
저장: 03_결과물/figures/교수님논의/00_SDot센서위치.png
"""

import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures', '교수님논의')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')

SDOT_PATH = '/Users/jin/석사논문/성동구_STP연구/04_분석결과/sdot_utci_v3_seongdong.csv'
JBG_SHP   = os.path.join(DATA_DIR, '행정경계', '통계지역경계(2016년+기준)', '집계구.shp')

# ── 데이터 로드 ──────────────────────────────────────────────────────────
sdot = pd.read_csv(SDOT_PATH, encoding='utf-8-sig')
sensors = sdot.drop_duplicates(subset='serial')[['serial', 'lat', 'lon', 'dong']].copy()
print(f"센서 수: {len(sensors)}개")

sensors_gdf = gpd.GeoDataFrame(
    sensors,
    geometry=gpd.points_from_xy(sensors['lon'], sensors['lat']),
    crs='EPSG:4326'
).to_crs(epsg=3857)

jbg = gpd.read_file(JBG_SHP, encoding='cp949')
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
jbg = jbg.set_crs(epsg=5179, allow_override=True).to_crs(epsg=3857)

# ── 지도 출력 ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 9))

jbg.plot(ax=ax, color='#f5f5f5', edgecolor='#aaaaaa', linewidth=0.5, zorder=1)

try:
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=13, alpha=0.35)
except Exception:
    pass

jbg.boundary.plot(ax=ax, color='#333333', linewidth=0.9, alpha=0.85, zorder=4)

sensors_gdf.plot(
    ax=ax,
    color='#E53935', markersize=70, zorder=6,
    edgecolors='white', linewidths=0.8,
    marker='o'
)

# 센서 번호 라벨
for i, row in sensors_gdf.iterrows():
    ax.annotate(
        f"{i+1}",
        xy=(row.geometry.x, row.geometry.y),
        xytext=(4, 4), textcoords='offset points',
        fontsize=6, color='#333333', zorder=7
    )

ax.set_title(
    f'S-DoT 기상 센서 위치 (n={len(sensors)}개)\n성동구 보행환경 열환경 모니터링 네트워크',
    fontsize=14, fontweight='bold', pad=12
)
ax.text(
    0.5, -0.02,
    '성동구 S-DoT (Smart Seoul Data of Things) | 센서 간격: 약 300~500 m',
    transform=ax.transAxes, ha='center', fontsize=10, color='#555555'
)
ax.set_axis_off()

plt.tight_layout()
out = os.path.join(FIG_DIR, '00_SDot센서위치.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print(f"저장: {out}")
