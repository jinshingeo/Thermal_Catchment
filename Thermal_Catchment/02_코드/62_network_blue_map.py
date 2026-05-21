"""
집계구 경계 + 보행 네트워크(파란색) 3D 지도 — 57_3d_maps.py 동일 시점
범례·제목 없음, transparent
"""

import os, warnings
import numpy as np
import geopandas as gpd
import osmnx as ox
import matplotlib
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJ    = os.path.dirname(BASE)
RES_DIR = os.path.join(PROJ, '03_결과물')
FIG_DIR = os.path.join(RES_DIR, 'figures', '3d_maps')
os.makedirs(FIG_DIR, exist_ok=True)

JBG_PATH = '/Users/jin/석사논문/통계지역경계/집계구.shp'
NET_PATH = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
OUT_PATH = os.path.join(FIG_DIR, '3d_network_blue.png')

ELEV    = 35
AZIM    = -65
FIGSIZE = (12, 12)
DPI     = 150
Z_MAX   = 1500

# ── 데이터 로드 ─────────────────────────────────────────────────────────
print("집계구 로드...")
jbg = gpd.read_file(JBG_PATH)
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].to_crs('EPSG:5186')
xmin, ymin, xmax, ymax = jbg.total_bounds
cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
X_RANGE = xmax - xmin
Y_RANGE = ymax - ymin

def n(arr_x, arr_y):
    return np.array(arr_x) - cx, np.array(arr_y) - cy

print("네트워크 로드...")
G = ox.load_graphml(NET_PATH)
_, edges = ox.graph_to_gdfs(G)
edges = edges.to_crs('EPSG:5186').reset_index()

# ── 3D 축 설정 ──────────────────────────────────────────────────────────
fig = plt.figure(figsize=FIGSIZE, dpi=DPI, facecolor='none')
ax  = fig.add_subplot(111, projection='3d')
ax.set_xlim(xmin - cx, xmax - cx)
ax.set_ylim(ymin - cy, ymax - cy)
ax.set_zlim(0, Z_MAX)
ax.set_box_aspect([X_RANGE, Y_RANGE, Z_MAX * 0.7])
ax.view_init(elev=ELEV, azim=AZIM)
ax.set_axis_off()
for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
    pane.fill = False
    pane.set_edgecolor('none')
ax.grid(False)

# 집계구 경계
for geom in jbg.geometry:
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    for poly in polys:
        xs, ys = poly.exterior.xy
        ox_, oy_ = n(xs, ys)
        ax.plot(ox_, oy_, 0, color='#DDDDDD', linewidth=0.5, zorder=1)

# 보행 네트워크 (파란색)
for geom in edges.geometry:
    xs, ys = geom.xy
    ox_, oy_ = n(xs, ys)
    ax.plot(ox_, oy_, 0, color='#2471A3', linewidth=0.6, alpha=0.75, zorder=2)

plt.savefig(OUT_PATH, dpi=DPI, bbox_inches='tight', transparent=True)
plt.close()
print(f"저장 완료: {OUT_PATH}")
