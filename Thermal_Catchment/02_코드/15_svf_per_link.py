"""
링크별 SVF (Sky View Factor) + 가로수 캐노피 비율 계산
======================================================
SVF 계산 방법: Oke (1987) H/W Street Canyon 공식

  SVF = 1 / √(1 + (H/W)²)

  H = 링크 버퍼 20m 내 건물 평균 높이 (층수 × 3m)
  W = 도로 유형(highway)별 표준 폭 (국토부 도로설계기준 참고)

  SVF = 1.0 → 완전 개활지 (교량, 광장, 건물 없음)
  SVF ≈ 0.5 → H/W ≈ 1.0 (6층 건물, 6m 도로)
  SVF ≈ 0.3 → H/W ≈ 3.0 (고층 빌딩 협곡)

참고문헌:
  Oke, T. R. (1987). Boundary Layer Climates (2nd ed.). Routledge.

캐노피 비율: 링크 버퍼 15m 내 가로수 면적 / 버퍼 면적
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
STP_BASE   = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH   = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
GREEN_PATH = '/Users/jin/Green_Space_2SFCA/코드/data/도시숲전체_면_서울_최종_중분류.shp'
BULD_PATH  = '/Users/jin/석사논문/TAVI/03_건물데이터/(도로명주소)건물_서울/TL_SPBD_BULD_11_202603.shp'
OUT_PATH   = os.path.join(RES_DIR, 'link_svf_canopy.csv')

BULD_BUFFER  = 20   # m — H 계산을 위한 링크 주변 건물 탐색 반경
CANOPY_BUFFER = 15  # m — 가로수 캐노피 측정 링크 버퍼

# 도로 유형별 표준 폭 (m) — 국토부 도로설계기준 / OSM 실측 통계
# 양방향 차로 포함 전체 노면폭 기준
WIDTH_BY_HIGHWAY = {
    'trunk':            24.0,
    'trunk_link':       10.0,
    'primary':          16.0,
    'primary_link':      8.0,
    'secondary':        12.0,
    'secondary_link':    6.0,
    'tertiary':          9.0,
    'tertiary_link':     6.0,
    'residential':       6.0,
    'living_street':     5.0,
    'service':           5.0,
    'footway':           3.0,
    'pedestrian':        4.0,
    'path':              2.0,
    'steps':             2.0,
    'corridor':          3.0,
    'unclassified':      6.0,
}
DEFAULT_WIDTH = 6.0  # 미분류 기본값


def get_width(highway_val):
    """OSM highway 태그 → 도로 폭 반환 (리스트형 태그 처리)"""
    if isinstance(highway_val, list):
        highway_val = highway_val[0]
    if isinstance(highway_val, str) and highway_val.startswith('['):
        # "[' footway', 'steps']" 형식 처리
        import ast
        try:
            vals = ast.literal_eval(highway_val)
            highway_val = vals[0] if vals else 'unclassified'
        except Exception:
            highway_val = 'unclassified'
    return WIDTH_BY_HIGHWAY.get(str(highway_val).strip(), DEFAULT_WIDTH)


# ── 네트워크 로드 ───────────────────────────────────────────────────────
print("네트워크 로드 중...")
G = ox.load_graphml(NET_PATH)
G = G.to_undirected()
_, edges_gdf = ox.graph_to_gdfs(G)
edges_utm = edges_gdf.to_crs('EPSG:5186').copy()
print(f"  링크 수: {len(edges_utm):,}")

# ── 건물 데이터 로드 ────────────────────────────────────────────────────
print("건물 데이터 로드 중...")
buld_raw = gpd.read_file(BULD_PATH)
buld = buld_raw[buld_raw['SIG_CD'] == '11200'][['GRO_FLO_CO', 'geometry']].copy()
buld['height_m'] = buld['GRO_FLO_CO'].clip(lower=1) * 3
buld = buld.to_crs('EPSG:5186')
buld['geometry'] = buld.geometry.buffer(0)
buld = buld[buld.geometry.is_valid].copy().reset_index(drop=True)
buld_sindex = buld.sindex
print(f"  성동구 건물: {len(buld):,}개 | 평균높이 {buld['height_m'].mean():.1f}m")

# ── 녹지(가로수) 데이터 로드 ────────────────────────────────────────────
print("가로수 데이터 로드 중...")
green_raw = gpd.read_file(GREEN_PATH)
bbox_gdf = gpd.GeoDataFrame(
    geometry=[Point(127.015, 37.535), Point(127.065, 37.565)], crs='EPSG:4326'
).to_crs('EPSG:5186')
xmin, ymin = bbox_gdf.geometry[0].x, bbox_gdf.geometry[0].y
xmax, ymax = bbox_gdf.geometry[1].x, bbox_gdf.geometry[1].y
green = green_raw.cx[xmin:xmax, ymin:ymax].copy()
street_trees = green[green['U2_NAM'] == '가로수'].copy().reset_index(drop=True)
tree_sindex = street_trees.sindex
print(f"  성동구 가로수: {len(street_trees):,}개")


# ── SVF 계산 함수 (Oke 1987) ────────────────────────────────────────────
def calc_svf_hw(link_geom, highway_val):
    """
    Oke(1987) H/W street canyon 공식으로 SVF 계산
      H = 링크 버퍼 20m 내 건물 평균 높이
      W = 도로 유형별 표준 폭
      SVF = 1 / sqrt(1 + (H/W)^2)
    건물이 없으면 SVF = 1.0 (개활지)
    """
    W = get_width(highway_val)
    buf = link_geom.buffer(BULD_BUFFER)

    candidates_idx = list(buld_sindex.intersection(buf.bounds))
    if not candidates_idx:
        return 1.0, 0.0, W   # svf, H, W

    cands = buld.iloc[candidates_idx]
    cands = cands[cands.geometry.intersects(buf)]
    if len(cands) == 0:
        return 1.0, 0.0, W

    H = float(cands['height_m'].mean())
    svf = 1.0 / np.sqrt(1.0 + (H / W) ** 2)
    return round(svf, 4), round(H, 1), W


def calc_canopy_ratio(link_geom):
    """링크 버퍼 내 가로수 캐노피 비율"""
    buf = link_geom.buffer(CANOPY_BUFFER)
    candidates_idx = list(tree_sindex.intersection(buf.bounds))
    if not candidates_idx:
        return 0.0
    cands = street_trees.iloc[candidates_idx]
    cands = cands[cands.geometry.intersects(buf)]
    if len(cands) == 0:
        return 0.0
    clipped_area = cands.geometry.intersection(buf).area.sum()
    return round(float(clipped_area / buf.area), 4)


# ── 전체 링크 계산 ──────────────────────────────────────────────────────
print(f"\n링크별 SVF(H/W) + 캐노피 계산 시작 (총 {len(edges_utm):,}개)...")
rows = []
total = len(edges_utm)

for i, (idx, row) in enumerate(edges_utm.iterrows()):
    if i % 1000 == 0:
        print(f"  진행: {i:,}/{total:,} ({i/total*100:.0f}%)")

    u, v    = idx[0], idx[1]
    hw      = row.get('highway', 'unclassified')
    svf, H, W = calc_svf_hw(row.geometry, hw)
    canopy  = calc_canopy_ratio(row.geometry)

    rows.append({
        'u':            u,
        'v':            v,
        'svf':          svf,
        'mean_bld_H':   H,
        'road_W':       W,
        'HW_ratio':     round(H / W, 3) if W > 0 else 0,
        'canopy_ratio': canopy,
        'highway':      hw,
    })

df_out = pd.DataFrame(rows)
df_out.to_csv(OUT_PATH, index=False, encoding='utf-8-sig')

# ── 결과 요약 ───────────────────────────────────────────────────────────
print(f"\n저장 완료: {OUT_PATH}")
print(f"\n=== SVF 분포 (Oke 1987 H/W 공식) ===")
print(f"  min:  {df_out['svf'].min():.3f}")
print(f"  mean: {df_out['svf'].mean():.3f}")
print(f"  max:  {df_out['svf'].max():.3f}")
print(f"  std:  {df_out['svf'].std():.3f}")

bins   = [0, 0.3, 0.5, 0.7, 0.9, 1.01]
labels = ['<0.3 (밀집협곡)', '0.3~0.5 (반폐쇄)', '0.5~0.7 (일반주거)', '0.7~0.9 (준개활)', '0.9~1.0 (개활지/교량)']
df_out['svf_cat'] = pd.cut(df_out['svf'], bins=bins, labels=labels, right=False)
print(f"\n  구간별:")
print(df_out['svf_cat'].value_counts().sort_index().to_string())

print(f"\n=== H/W 비율 분포 ===")
print(df_out['HW_ratio'].describe().round(2))

print(f"\n=== highway 유형별 평균 SVF ===")
hw_svf = df_out.groupby('highway')['svf'].agg(['mean','count']).sort_values('mean')
# 주요 유형만 출력
major = ['trunk','primary','secondary','tertiary','residential','footway','path','service','steps']
print(hw_svf[hw_svf.index.isin(major)].round(3).to_string())

print(f"\n=== 캐노피 비율 ===")
print(f"  가로수 없는 링크: {(df_out['canopy_ratio']==0).sum():,}개 ({(df_out['canopy_ratio']==0).mean()*100:.0f}%)")
print(f"  캐노피 > 10%:    {(df_out['canopy_ratio']>0.1).sum():,}개")
print(f"  평균 캐노피:      {df_out['canopy_ratio'].mean()*100:.2f}%")
