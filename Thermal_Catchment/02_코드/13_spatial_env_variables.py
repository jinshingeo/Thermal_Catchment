"""
Plan A: 역별 공간환경 변수 추출
================================
각 역의 Classic Catchment Zone 내 녹지 면적 비율 + 수계 거리 + 건물 높이 산출

변수 목록:
  1. green_ratio       - 전체 녹지(도시숲+마을숲+가로수+학교숲+경관숲) 면적 비율
  2. street_tree_ratio - 가로수 면적 비율
  3. urban_forest_ratio - 도시숲+마을숲+경관숲 면적 비율
  4. river_dist_m      - 역 노드에서 가장 가까운 수계(한강/하천)까지 거리 (m)
  5. mean_bld_height_m - catchment zone 내 평균 건물 높이 (층수×3m 추정)

catchment zone 정의: Classic catchment 노드들의 convex hull
"""

import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import contextily as ctx
import matplotlib
from shapely.geometry import Point, MultiPoint
from scipy.spatial import ConvexHull
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

# ── 경로 설정 ──────────────────────────────────────────────────────────
BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
STP_BASE    = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH    = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
UTCI_PATH   = os.path.join(STP_BASE, '04_분석결과/link_utci_by_hour_v3.csv')
GREEN_PATH  = '/Users/jin/Green_Space_2SFCA/코드/data/도시숲전체_면_서울_최종_중분류.shp'
BULD_PATH   = '/Users/jin/석사논문/TAVI/03_건물데이터/(도로명주소)건물_서울/TL_SPBD_BULD_11_202603.shp'
FIG_DIR     = os.path.join(RES_DIR, 'figures')
OUT_DIR     = BASE
os.makedirs(FIG_DIR, exist_ok=True)

# ── 파라미터 ───────────────────────────────────────────────────────────
WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
ALPHA       = 0.15

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353},  # OSM node 357874377
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171},
}

GREEN_TYPES = {
    '가로수': '가로수',
    '도시숲': '도시숲',
    '마을숲': '마을숲',
    '경관숲': '경관숲',
    '학교숲': '학교숲',
}


def utci_to_penalty(utci):
    if utci < 26:   return 0
    elif utci < 32: return 1
    elif utci < 38: return 2
    elif utci < 46: return 3
    else:           return 4


def compute_classic_catchment(G, station_node, utci_lookup, hour=13, alpha=ALPHA):
    for u, v, data in G.edges(data=True):
        data['classic_time'] = data.get('length', 0) / WALK_SPEED
    return nx.single_source_dijkstra_path_length(
        G, station_node, cutoff=TIME_BUDGET, weight='classic_time'
    )


def catchment_links_to_zone(G, classic_nodes, edges_utm, buffer_m=30):
    """
    Classic catchment 링크 → 링크 버퍼 기반 zone 생성
    (convex hull 대신 실제 도달 가능한 링크 집합으로 정의)
    - 양 끝 노드가 모두 classic_nodes에 포함된 링크만 선택
    - 각 링크를 buffer_m로 버퍼링 → 유니온
    """
    mask = (
        edges_utm.index.get_level_values(0).isin(classic_nodes) &
        edges_utm.index.get_level_values(1).isin(classic_nodes)
    )
    links_in = edges_utm[mask]
    if len(links_in) == 0:
        return None, 0
    zone = links_in.geometry.buffer(buffer_m).union_all()
    return zone, zone.area


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
_, edges_gdf = ox.graph_to_gdfs(G_base)
edges_utm = edges_gdf.to_crs('EPSG:5186')

print("UTCI 데이터 로드 중...")
link_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
utci_lookup = {}
for _, row in link_df.iterrows():
    utci_lookup[(str(row['u']), str(row['v']), int(row['hour']))] = row['utci_idw']
    utci_lookup[(str(row['v']), str(row['u']), int(row['hour']))] = row['utci_idw']

print("녹지 데이터 로드 중 (성동구 필터)...")
green_raw = gpd.read_file(GREEN_PATH)   # EPSG:5186
# 성동구 범위로 클리핑 (approx bbox in EPSG:5186)
# 성동구: 37.535~37.565 N, 127.015~127.065 E → 5186 좌표 변환
bbox_wgs = gpd.GeoDataFrame(
    geometry=[Point(127.015, 37.535), Point(127.065, 37.565)], crs='EPSG:4326'
).to_crs('EPSG:5186')
xmin, ymin = bbox_wgs.geometry[0].x, bbox_wgs.geometry[0].y
xmax, ymax = bbox_wgs.geometry[1].x, bbox_wgs.geometry[1].y
green = green_raw.cx[xmin:xmax, ymin:ymax].copy()
green['area_m2'] = green.geometry.area
print(f"  성동구 내 녹지: {len(green)}개 ({green['U2_NAM'].value_counts().to_dict()})")

print("건물 데이터 로드 중 (성동구 필터)...")
buld_raw = gpd.read_file(BULD_PATH)   # EPSG:5179
seongdong_buld = buld_raw[buld_raw['SIG_CD'] == '11200'].copy()
seongdong_buld['height_m'] = seongdong_buld['GRO_FLO_CO'].clip(lower=1) * 3
seongdong_buld = seongdong_buld.to_crs('EPSG:5186')
seongdong_buld['geometry'] = seongdong_buld.geometry.buffer(0)  # invalid geometry 수정
seongdong_buld = seongdong_buld[seongdong_buld.geometry.is_valid].copy()
print(f"  성동구 건물: {len(seongdong_buld):,}개 | 평균 높이 {seongdong_buld['height_m'].mean():.1f}m")

print("수계 데이터 로드 중 (OSM)...")
waterways = ox.features_from_place(
    "Seongdong-gu, Seoul, South Korea",
    tags={"waterway": ["river", "stream"]}
)
waterways_utm = waterways.to_crs('EPSG:5186')
# 선형 geometry만 추출 (river/stream)
water_lines = waterways_utm[waterways_utm.geometry.geom_type.isin(['LineString', 'MultiLineString'])]
water_union = water_lines.geometry.unary_union
print(f"  수계 {len(water_lines)}개 로드 완료")

# 역 노드 탐색
for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])

# ── 변수 추출 ──────────────────────────────────────────────────────────
print("\n공간환경 변수 추출 중...")
rows = []

for station_name, sinfo in STATIONS.items():
    G = G_base.copy()
    classic_dist = compute_classic_catchment(G, sinfo['node'], utci_lookup)
    classic_nodes = set(classic_dist.keys())

    # 1. Catchment zone = classic catchment 링크 버퍼 유니온 (링크 단위 평가)
    zone, catchment_area_m2 = catchment_links_to_zone(G, classic_nodes, edges_utm, buffer_m=30)
    if zone is None:
        print(f"  [{station_name}] catchment zone 생성 실패 — 스킵")
        continue
    poly_gdf = gpd.GeoDataFrame(geometry=[zone], crs='EPSG:5186')

    # 2. 녹지 면적 교차
    green_clip = gpd.clip(green, poly_gdf)
    green_clip = green_clip[green_clip.geometry.is_valid & ~green_clip.geometry.is_empty].copy()
    green_clip['clipped_area'] = green_clip.geometry.area

    total_green   = green_clip['clipped_area'].sum()
    street_tree   = green_clip[green_clip['U2_NAM'] == '가로수']['clipped_area'].sum()
    urban_forest  = green_clip[green_clip['U2_NAM'].isin(['도시숲', '마을숲', '경관숲'])]['clipped_area'].sum()
    school_forest = green_clip[green_clip['U2_NAM'] == '학교숲']['clipped_area'].sum()

    green_ratio        = total_green   / catchment_area_m2 * 100
    street_tree_ratio  = street_tree   / catchment_area_m2 * 100
    urban_forest_ratio = urban_forest  / catchment_area_m2 * 100

    # 3. 건물 평균 높이 (catchment zone 내)
    buld_clip = gpd.clip(seongdong_buld[['height_m', 'geometry']], poly_gdf)
    mean_bld_height = buld_clip['height_m'].mean() if len(buld_clip) > 0 else np.nan

    # 4. 역 노드 → 수계 최단거리
    station_pt_utm = gpd.GeoDataFrame(
        geometry=[Point(sinfo['lon'], sinfo['lat'])], crs='EPSG:4326'
    ).to_crs('EPSG:5186').geometry[0]
    river_dist_m = station_pt_utm.distance(water_union)

    # 5. catchment zone 내 평균 UTCI (13시)
    utci_vals = [
        utci_lookup.get((str(u), str(v), 13),
        utci_lookup.get((str(v), str(u), 13), np.nan))
        for u, v, _ in G.edges(data=True)
        if u in classic_nodes or v in classic_nodes
    ]
    mean_utci = np.nanmean(utci_vals)

    rows.append({
        'station':             station_name,
        'lat':                 sinfo['lat'],
        'lon':                 sinfo['lon'],
        'catchment_nodes':     len(classic_nodes),
        'catchment_area_m2':   round(catchment_area_m2),
        'green_ratio_pct':     round(green_ratio, 2),
        'street_tree_ratio_pct': round(street_tree_ratio, 2),
        'urban_forest_ratio_pct': round(urban_forest_ratio, 2),
        'river_dist_m':        round(river_dist_m),
        'mean_utci_13h':       round(mean_utci, 1),
        'mean_bld_height_m':   round(mean_bld_height, 1),
    })

    print(f"  [{station_name}] catchment {catchment_area_m2/1e6:.2f}km² | "
          f"녹지 {green_ratio:.1f}% | 수계거리 {river_dist_m:.0f}m | "
          f"건물높이 {mean_bld_height:.1f}m | UTCI {mean_utci:.1f}°C")

# ── 저장 ───────────────────────────────────────────────────────────────
df = pd.DataFrame(rows)

# reduction_pct 붙이기 (catchment 분석 결과에서)
summary_path = os.path.join(OUT_DIR, 'catchment_all_stations_summary.json')
with open(summary_path, encoding='utf-8') as f:
    summary = json.load(f)

for hour in [7, 10, 13, 16]:
    df[f'reduction_pct_h{hour:02d}'] = df['station'].map(
        lambda s: summary.get(s, {}).get(f'h{hour:02d}', {}).get('reduction_pct', np.nan)
    )

out_csv = os.path.join(OUT_DIR, 'spatial_env_variables.csv')
df.to_csv(out_csv, index=False, encoding='utf-8-sig')
print(f"\n저장 완료: {out_csv}")
print(df[['station', 'green_ratio_pct', 'street_tree_ratio_pct',
           'river_dist_m', 'mean_bld_height_m', 'mean_utci_13h',
           'reduction_pct_h13']].to_string(index=False))

# ── 시각화: 변수 간 산점도 ─────────────────────────────────────────────
print("\n산점도 생성 중...")
fig, axes = plt.subplots(1, 4, figsize=(20, 5))

vars_x = ['green_ratio_pct', 'river_dist_m', 'mean_bld_height_m', 'mean_utci_13h']
labels_x = ['녹지 비율 (%)', '수계까지 거리 (m)', '평균 건물 높이 (m)', '평균 UTCI 13시 (°C)']
colors = ['#43A047', '#1E88E5', '#E53935', '#FB8C00', '#8E24AA', '#00ACC1', '#6D4C41']

for ax, xvar, xlabel in zip(axes, vars_x, labels_x):
    for i, row in df.iterrows():
        ax.scatter(row[xvar], row['reduction_pct_h13'],
                   color=colors[i % len(colors)], s=120, zorder=3)
        ax.annotate(row['station'].replace('역', ''),
                    (row[xvar], row['reduction_pct_h13']),
                    textcoords='offset points', xytext=(5, 3), fontsize=8)

    # 회귀선
    x = df[xvar].values
    y = df['reduction_pct_h13'].values
    if len(x) > 2:
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        xseq = np.linspace(x.min(), x.max(), 100)
        ax.plot(xseq, p(xseq), 'k--', linewidth=1, alpha=0.5)
        corr = np.corrcoef(x, y)[0, 1]
        ax.set_title(f'r = {corr:.2f}', fontsize=10)

    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel('접근성 감소율 (13시, %)', fontsize=10)
    ax.grid(True, alpha=0.3)

fig.suptitle('공간환경 변수 vs Catchment 감소율 (13시)\nPlan A 회귀분석 사전 탐색',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'spatial_env_scatter.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: figures/spatial_env_scatter.png")
