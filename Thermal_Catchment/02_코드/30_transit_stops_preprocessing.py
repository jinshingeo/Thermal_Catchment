"""
Task 1 — 대중교통 정류장 전처리
================================
성동구 내 버스정류장(stops.txt) + 지하철역 통합 공급 레이어 구성

입력:
  03_건물데이터/stops.txt                        — GTFS 버스정류장 (전국, lat/lon 포함)
  01_데이터/행정경계/통계지역경계.../집계구.shp   — 성동구 집계구 경계

출력 (→ 01_데이터/네트워크/):
  transit_stops_seongdong.csv  — stop_id, stop_name, lat, lon, stop_type, node_id
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
NET_DIR  = os.path.join(DATA_DIR, '네트워크')
OUT_DIR  = NET_DIR
os.makedirs(OUT_DIR, exist_ok=True)

STOPS_TXT = os.path.join(os.path.dirname(PROJ_DIR), '03_건물데이터', 'stops.txt')
BOUNDARY_SHP = os.path.join(DATA_DIR, '행정경계',
               '통계지역경계(2016년+기준)', '집계구.shp')
NET_PATH  = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
SEONGDONG_PREFIX = '1104'

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171},
}


# ── 1. 성동구 경계 로드 ────────────────────────────────────────────────────
print("성동구 경계 로드 중...")
jibgaegu = gpd.read_file(BOUNDARY_SHP, encoding='cp949')

code_col = None
for c in jibgaegu.columns:
    sample = str(jibgaegu[c].iloc[0])
    if sample.startswith('11') and len(sample) >= 10:
        code_col = c
        break
if code_col is None:
    for candidate in ['집계구코드', 'TOT_REG_CD']:
        if candidate in jibgaegu.columns:
            code_col = candidate
            break

jibgaegu[code_col] = jibgaegu[code_col].astype(str)
seongdong_gdf = jibgaegu[jibgaegu[code_col].str.startswith(SEONGDONG_PREFIX)].copy()
if seongdong_gdf.crs is None:
    seongdong_gdf = seongdong_gdf.set_crs(epsg=5179)
seongdong_gdf = seongdong_gdf.to_crs(epsg=4326)
seongdong_boundary = seongdong_gdf.union_all()
print(f"  성동구 집계구 수: {len(seongdong_gdf)}개")


# ── 2. 버스정류장 로드 및 성동구 내 필터 ─────────────────────────────────
print("\n버스정류장 로드 및 공간 필터링 중...")
stops_df = pd.read_csv(STOPS_TXT)
stops_gdf = gpd.GeoDataFrame(
    stops_df,
    geometry=[Point(row.stop_lon, row.stop_lat) for _, row in stops_df.iterrows()],
    crs='EPSG:4326'
)

stops_seongdong = stops_gdf[stops_gdf.geometry.within(seongdong_boundary)].copy()
print(f"  전체 버스정류장: {len(stops_df):,}개")
print(f"  성동구 내 버스정류장: {len(stops_seongdong):,}개")

bus_stops = pd.DataFrame({
    'stop_id':   stops_seongdong['stop_id'].values,
    'stop_name': stops_seongdong['stop_name'].values,
    'lat':       stops_seongdong['stop_lat'].values,
    'lon':       stops_seongdong['stop_lon'].values,
    'stop_type': 'bus',
})


# ── 3. 지하철역 추가 ──────────────────────────────────────────────────────
subway_rows = [
    {'stop_id': f'subway_{name}', 'stop_name': name,
     'lat': info['lat'], 'lon': info['lon'], 'stop_type': 'subway'}
    for name, info in STATIONS.items()
]
subway_stops = pd.DataFrame(subway_rows)

transit_stops = pd.concat([subway_stops, bus_stops], ignore_index=True)
print(f"\n통합 대중교통 정류장: {len(transit_stops)}개")
print(f"  지하철: {len(subway_stops)}개 | 버스: {len(bus_stops)}개")


# ── 4. 네트워크 최근접 노드 매핑 ─────────────────────────────────────────
print("\n보행 네트워크 로드 중...")
G = ox.load_graphml(NET_PATH)
print(f"  노드 수: {G.number_of_nodes():,} | 엣지 수: {G.number_of_edges():,}")

print("정류장 → 최근접 네트워크 노드 매핑 중...")
node_ids = ox.nearest_nodes(
    G,
    X=transit_stops['lon'].values,
    Y=transit_stops['lat'].values
)
transit_stops['node_id'] = node_ids
print(f"  매핑 완료: {len(transit_stops)}개 정류장")


# ── 5. 저장 ──────────────────────────────────────────────────────────────
out_path = os.path.join(OUT_DIR, 'transit_stops_seongdong.csv')
transit_stops.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f"\n저장: {out_path}")

print("\n=== Task 1 완료 ===")
print(f"  지하철 {len(subway_stops)}개 + 버스 {len(bus_stops)}개 = {len(transit_stops)}개 정류장")
