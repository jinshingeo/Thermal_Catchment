"""
IDW 보간 링크별 기온(Tair) · 상대습도(RH) 3D 지도 — 57_3d_maps.py 동일 시점
Jenks 5단계, 범례 없음, transparent
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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
FIG_DIR = os.path.join(RES_DIR, 'figures', '3d_maps')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH  = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
DATA_PATH = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
JBG_PATH  = '/Users/jin/석사논문/통계지역경계/집계구.shp'

ELEV    = 35
AZIM    = -65
FIGSIZE = (12, 12)
DPI     = 150
Z_MAX   = 1500
HOUR    = 13

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
edges_utm = edges.to_crs('EPSG:5186').reset_index().copy()
edges_utm['u'] = edges_utm['u'].astype(str)
edges_utm['v'] = edges_utm['v'].astype(str)

print("Tair/RH 데이터 로드...")
df = pd.read_csv(DATA_PATH)
h13 = df[df['hour'] == HOUR][['u', 'v', 'Tair_idw', 'RH_idw']].copy()
h13['u'] = h13['u'].astype(str)
h13['v'] = h13['v'].astype(str)
edges_merged = edges_utm.merge(h13, on=['u', 'v'], how='left')


def jenks_breaks(values, k=5):
    if HAS_MAPCLASSIFY:
        clf = mapclassify.NaturalBreaks(values, k=k)
        breaks = [float(np.floor(values.min()))] + list(clf.bins)
        breaks[-1] = float(np.ceil(values.max()))
    else:
        percs = np.linspace(0, 100, k + 1)
        breaks = [np.percentile(values, p) for p in percs]
        breaks[0] = float(np.floor(values.min()))
        breaks[-1] = float(np.ceil(values.max()))
    return [round(b, 1) for b in breaks]


def assign_class(val, breaks):
    for j in range(len(breaks) - 1):
        if val <= breaks[j + 1]:
            return j
    return len(breaks) - 2


def make_3d_choropleth(col, colors_hex, out_filename):
    valid  = edges_merged.dropna(subset=[col]).copy()
    no_val = edges_merged[edges_merged[col].isna()].copy()
    vals   = valid[col].values

    breaks = jenks_breaks(vals, k=5)
    valid['cls'] = valid[col].apply(assign_class, args=(breaks,))
    print(f"  {col} 급간: {breaks}")

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

    # 값 없는 링크 (회색 배경)
    for geom in no_val.geometry:
        xs, ys = geom.xy
        ox_, oy_ = n(xs, ys)
        ax.plot(ox_, oy_, 0, color='#CCCCCC', linewidth=0.5, alpha=0.5, zorder=2)

    # 값 있는 링크 — 급간별 색상
    for cls_idx, color in enumerate(colors_hex):
        subset = valid[valid['cls'] == cls_idx]
        lw = 1.0 if cls_idx < 4 else 1.4
        for geom in subset.geometry:
            xs, ys = geom.xy
            ox_, oy_ = n(xs, ys)
            ax.plot(ox_, oy_, 0, color=color, linewidth=lw, alpha=0.9, zorder=3 + cls_idx)

    out_path = os.path.join(FIG_DIR, out_filename)
    plt.savefig(out_path, dpi=DPI, bbox_inches='tight', transparent=True)
    plt.close()
    print(f"  저장: {out_path}")


print("\n[지도1] 기온(Tair_idw)...")
tair_colors = ['#FFF2CC', '#FFCC99', '#FF9933', '#FF4400', '#990000']
make_3d_choropleth('Tair_idw', tair_colors, '3d_tair_link_13h.png')

print("\n[지도2] 상대습도(RH_idw)...")
rh_colors = ['#EBF5FB', '#AED6F1', '#5DADE2', '#2471A3', '#1A5276']
make_3d_choropleth('RH_idw', rh_colors, '3d_rh_link_13h.png')

print("\n완료.")
