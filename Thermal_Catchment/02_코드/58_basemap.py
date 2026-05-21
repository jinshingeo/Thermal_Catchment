"""
성동구 OSM 베이스맵 — 3D 지도들의 배경용
동일 figsize/DPI, 제목·범례 없음, 흰 배경 유지
"""

import os, warnings
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import contextily as ctx
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False

JBG_PATH = '/Users/jin/석사논문/통계지역경계/집계구.shp'
OUT_DIR  = '/Users/jin/석사논문/TAVI/Thermal_Catchment/03_결과물/figures/3d_maps'
os.makedirs(OUT_DIR, exist_ok=True)

FIGSIZE = (12, 12)
DPI     = 150

# 성동구 경계
jbg = gpd.read_file(JBG_PATH)
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].to_crs('EPSG:3857')

xmin, ymin, xmax, ymax = jbg.total_bounds
pad = 300  # 여백 (m)

fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)

# 성동구 경계 마스크 (외곽선만)
jbg.plot(ax=ax, facecolor='none', edgecolor='none')
ax.set_xlim(xmin - pad, xmax + pad)
ax.set_ylim(ymin - pad, ymax + pad)

# OSM 베이스맵
ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=14)

ax.set_axis_off()
plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
plt.savefig(os.path.join(OUT_DIR, 'basemap_osm.png'), dpi=DPI,
            bbox_inches='tight', facecolor='white')
plt.close()
print("저장 완료: basemap_osm.png")
