"""
성동구 3D/동일시점 시각화 3장
 1. 3d_buildings.png  — 집계구 + 네트워크 + 건물 3D 압출
 2. 3d_green.png      — 집계구 + 네트워크 + 녹지 (동일 시점)
 3. 3d_stops.png      — 집계구 + 네트워크 + 정류장 (동일 시점)
범례·제목 없음, 동일 figsize/elev/azim
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import Point
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False

# ── 경로 ────────────────────────────────────────────────────────────────
BULD_PATH  = '/Users/jin/석사논문/TAVI/03_건물데이터/(도로명주소)건물_서울/TL_SPBD_BULD_11_202603.shp'
JBG_PATH   = '/Users/jin/석사논문/통계지역경계/집계구.shp'
GREEN_PATH = '/Users/jin/Green_Space_2SFCA/코드/data/도시숲전체_면_서울_최종_중분류.shp'
NET_PATH   = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
STOPS_PATH = '/Users/jin/석사논문/TAVI/gtfs_KTDB/stops.txt'
# 지하철역 좌표 (MRT Hard Cut 분석 대상 7개역)
SUBWAY_STATIONS = {
    '왕십리역': (37.5613, 127.0377),
    '행당역':   (37.5572, 127.0305),
    '응봉역':   (37.5520, 127.0353),
    '뚝섬역':   (37.5470, 127.0475),
    '성수역':   (37.5447, 127.0561),
    '서울숲역': (37.5446, 127.0448),
    '옥수역':   (37.5402, 127.0171),
}
OUT_DIR    = '/Users/jin/석사논문/TAVI/Thermal_Catchment/03_결과물/figures/3d_maps'
os.makedirs(OUT_DIR, exist_ok=True)

# ── 공통 뷰 파라미터 ────────────────────────────────────────────────────
ELEV    = 35
AZIM    = -65
FIGSIZE = (12, 12)
DPI     = 150
Z_EXAG  = 10        # 건물 높이 과장 (시각적 가독성)

# ── 데이터 로드 ─────────────────────────────────────────────────────────
print("집계구 로드...")
jbg = gpd.read_file(JBG_PATH)
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].to_crs('EPSG:5186')
xmin, ymin, xmax, ymax = jbg.total_bounds
cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
seongdong = jbg.union_all()  # 성동구 전체 경계 폴리곤

def n(arr_x, arr_y):
    return np.array(arr_x) - cx, np.array(arr_y) - cy

print("네트워크 로드...")
G = ox.load_graphml(NET_PATH)
_, edges = ox.graph_to_gdfs(G)
edges = edges.to_crs('EPSG:5186').reset_index()

print("건물 로드...")
buld = gpd.read_file(BULD_PATH)
buld = buld[buld['SIG_CD'] == '11200'][['GRO_FLO_CO', 'geometry']].copy()
buld['height_m'] = buld['GRO_FLO_CO'].clip(lower=1) * 3
buld = buld.to_crs('EPSG:5186').cx[xmin:xmax, ymin:ymax]
buld = buld[buld.geometry.is_valid & ~buld.geometry.is_empty].copy()
buld['geometry'] = buld.geometry.simplify(10)
print(f"  건물 {len(buld):,}개")

print("녹지 로드...")
green = gpd.read_file(GREEN_PATH)
green = green.cx[xmin:xmax, ymin:ymax].to_crs('EPSG:5186')
green = gpd.clip(green, jbg)          # 성동구 경계로 클립
green['geometry'] = green.geometry.simplify(5)
green = green[green.geometry.is_valid & ~green.geometry.is_empty]
print(f"  녹지 클립 후: {len(green):,}개")

print("정류장 로드...")
stops_df = pd.read_csv(STOPS_PATH)
stops_gdf = gpd.GeoDataFrame(
    stops_df,
    geometry=gpd.points_from_xy(stops_df.stop_lon, stops_df.stop_lat),
    crs='EPSG:4326'
).to_crs('EPSG:5186')
bus_stops = gpd.sjoin(stops_gdf, jbg[['geometry']], how='inner', predicate='within')  # 성동구 내부만
print(f"  버스정류장 클립 후: {len(bus_stops):,}개")

subway_df = pd.DataFrame(
    [(name, lat, lon) for name, (lat, lon) in SUBWAY_STATIONS.items()],
    columns=['station', 'lat', 'lon']
)
subway_gdf = gpd.GeoDataFrame(
    subway_df,
    geometry=gpd.points_from_xy(subway_df.lon, subway_df.lat),
    crs='EPSG:4326'
).to_crs('EPSG:5186')

# ── 축 범위 ─────────────────────────────────────────────────────────────
X_RANGE = xmax - xmin
Y_RANGE = ymax - ymin
Z_MAX   = int(buld['height_m'].quantile(0.99)) * Z_EXAG + 200

def make_ax():
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
    return fig, ax

def draw_jbg(ax):
    for geom in jbg.geometry:
        polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
        for poly in polys:
            xs, ys = poly.exterior.xy
            ox_, oy_ = n(xs, ys)
            ax.plot(ox_, oy_, 0, color='#DDDDDD', linewidth=0.5, zorder=1)

def draw_network(ax):
    for geom in edges.geometry:
        xs, ys = geom.xy
        ox_, oy_ = n(xs, ys)
        ax.plot(ox_, oy_, 0, color='#AAAAAA', linewidth=0.5, alpha=0.6, zorder=2)

def polys_from_geom(geom):
    return [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)

# ═══════════════════════════════════════════════════════════════════════
# 지도 1: 3D 건물
# ═══════════════════════════════════════════════════════════════════════
print("\n[지도1] 3D 건물...")
fig1, ax1 = make_ax()
draw_jbg(ax1)
draw_network(ax1)

MAX_H = buld['height_m'].quantile(0.99)
cmap  = plt.cm.Greys

faces, facecolors, edgecolors = [], [], []

for _, row in buld.iterrows():
    h = row['height_m'] * Z_EXAG
    t = min(row['height_m'] / MAX_H, 1.0)  # 0~1 높이 비율
    roof_c = mcolors.to_rgba(cmap(0.35 + t * 0.55), alpha=0.97)
    wall_c = mcolors.to_rgba(cmap(0.25 + t * 0.45), alpha=0.90)

    for poly in polys_from_geom(row.geometry):
        if poly.is_empty or not poly.is_valid:
            continue
        ext = list(poly.exterior.coords)
        xs = [p[0] - cx for p in ext]
        ys = [p[1] - cy for p in ext]

        # 지붕
        faces.append(list(zip(xs, ys, [h] * len(ext))))
        facecolors.append(roof_c)
        edgecolors.append((0, 0, 0, 0.06))

        # 벽
        for i in range(len(ext) - 1):
            wall = [(xs[i],   ys[i],   0),
                    (xs[i+1], ys[i+1], 0),
                    (xs[i+1], ys[i+1], h),
                    (xs[i],   ys[i],   h)]
            faces.append(wall)
            facecolors.append(wall_c)
            edgecolors.append((0, 0, 0, 0.03))

print(f"  face 수: {len(faces):,}")
col = Poly3DCollection(faces, zsort='average')
col.set_facecolors(facecolors)
col.set_edgecolors(edgecolors)
col.set_linewidth(0.0)
ax1.add_collection3d(col)

plt.savefig(os.path.join(OUT_DIR, '3d_buildings.png'), dpi=DPI,
            bbox_inches='tight', transparent=True)
plt.close(fig1)
print("  저장: 3d_buildings.png")

# ═══════════════════════════════════════════════════════════════════════
# 지도 2: 녹지
# ═══════════════════════════════════════════════════════════════════════
print("\n[지도2] 녹지...")
fig2, ax2 = make_ax()
draw_jbg(ax2)
draw_network(ax2)

gfaces, gcols = [], []
for _, row in green.iterrows():
    for poly in polys_from_geom(row.geometry):
        if poly.is_empty or not poly.is_valid:
            continue
        ext = list(poly.exterior.coords)
        xs = [p[0] - cx for p in ext]
        ys = [p[1] - cy for p in ext]
        gfaces.append(list(zip(xs, ys, [0] * len(ext))))
        gcols.append(mcolors.to_rgba('#4CAF50', alpha=0.75))

gcol = Poly3DCollection(gfaces)
gcol.set_facecolors(gcols)
gcol.set_edgecolors([(0, 0, 0, 0)])
ax2.add_collection3d(gcol)

plt.savefig(os.path.join(OUT_DIR, '3d_green.png'), dpi=DPI,
            bbox_inches='tight', transparent=True)
plt.close(fig2)
print("  저장: 3d_green.png")

# ═══════════════════════════════════════════════════════════════════════
# 지도 3: 정류장
# ═══════════════════════════════════════════════════════════════════════
print("\n[지도3] 정류장...")
fig3, ax3 = make_ax()
draw_jbg(ax3)
draw_network(ax3)

bx, by = n(bus_stops.geometry.x.values, bus_stops.geometry.y.values)
ax3.scatter(bx, by, 0, s=12, c='#FF6600', alpha=0.75, depthshade=False, zorder=5)

sx, sy = n(subway_gdf.geometry.x.values, subway_gdf.geometry.y.values)
ax3.scatter(sx, sy, 0, s=100, c='#0047AB', alpha=1.0, depthshade=False,
            edgecolors='white', linewidths=1.0, zorder=6)

plt.savefig(os.path.join(OUT_DIR, '3d_stops.png'), dpi=DPI,
            bbox_inches='tight', transparent=True)
plt.close(fig3)
print("  저장: 3d_stops.png")

print(f"\n완료: {OUT_DIR}")
