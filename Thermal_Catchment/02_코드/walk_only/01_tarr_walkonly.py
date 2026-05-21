"""
Walk-Only 네트워크 기반 집계구 TARR 계산
=========================================
간선도로(trunk/primary/secondary + links) 제거 후
MRT ≥ 55°C Hard Cut Thermal Catchment 재계산
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
warnings.filterwarnings('ignore')

BASE     = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(BASE)           # 02_코드
TC_DIR   = os.path.dirname(CODE_DIR)      # Thermal_Catchment
RES_DIR  = os.path.join(TC_DIR, '03_결과물')
OUT_DIR  = os.path.join(RES_DIR, 'walk_only')
os.makedirs(OUT_DIR, exist_ok=True)

NET_PATH  = os.path.join(OUT_DIR, 'seongdong_walkonly_network.graphml')
MRT_PATH  = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
JBG_SHP   = '/Users/jin/석사논문/통계지역경계/집계구.shp'
STOPS_CSV = os.path.join(TC_DIR, '01_데이터', '네트워크', 'transit_stops_seongdong.csv')
OUT_CSV   = os.path.join(OUT_DIR, 'tarr_walkonly.csv')

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
MRT_THRESH  = 55.0
TARGET_HOUR = 13

print("Walk-Only 네트워크 로드...")
G = ox.load_graphml(NET_PATH).to_undirected()
for u, v, d in G.edges(data=True):
    d['travel_time'] = d.get('length', 0) / WALK_SPEED
print(f"  노드 {G.number_of_nodes():,} / 엣지 {G.number_of_edges():,}")

print("MRT 데이터 로드...")
mrt_df = pd.read_csv(MRT_PATH, encoding='utf-8-sig')
h13 = mrt_df[mrt_df['hour'] == TARGET_HOUR].copy()
hot_edges = set(zip(
    h13[h13['mrt'] >= MRT_THRESH]['u'].astype(str),
    h13[h13['mrt'] >= MRT_THRESH]['v'].astype(str)
))
print(f"  Hot edges (MRT≥{MRT_THRESH}°C): {len(hot_edges):,}개")

# walk-only 네트워크에서 실제로 존재하는 hot edges만 필터
G_nodes = set(str(n) for n in G.nodes())
hot_edges_valid = {(u, v) for u, v in hot_edges if u in G_nodes and v in G_nodes}
print(f"  Walk-only 네트워크 내 hot edges: {len(hot_edges_valid):,}개")

print("정류장 로드...")
stops_df   = pd.read_csv(STOPS_CSV, encoding='utf-8-sig')
stop_nodes = set(stops_df['node_id'].astype(int).tolist())
# walk-only 네트워크에 실제로 있는 정류장만
stop_nodes_valid = stop_nodes & set(G.nodes())
print(f"  전체 정류장: {len(stop_nodes)}개 → walk-only 내 포함: {len(stop_nodes_valid)}개")

print("집계구 로드...")
jbg = gpd.read_file(JBG_SHP)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg.to_crs('EPSG:4326')
jbg['집계구코드'] = jbg['TOT_REG_CD'].astype(str)
jbg['centroid']  = jbg.geometry.centroid
jbg['net_node']  = ox.distance.nearest_nodes(
    G, jbg['centroid'].x.values, jbg['centroid'].y.values)
print(f"  집계구: {len(jbg)}개")

# Thermal 그래프 미리 구성
print("\nThermal 그래프 구성...")
G_thermal = G.copy()
remove = [(u, v) for u, v in G_thermal.edges()
          if (str(u), str(v)) in hot_edges_valid or (str(v), str(u)) in hot_edges_valid]
G_thermal.remove_edges_from(remove)
print(f"  제거된 엣지: {len(remove):,}개")

print("\n집계구별 TARR 계산 중...")
rows = []
for i, row in jbg.iterrows():
    node = row['net_node']
    if i % 100 == 0:
        print(f"  {list(jbg.index).index(i)}/{len(jbg)}...")

    classic_dist  = nx.single_source_dijkstra_path_length(
        G, node, cutoff=TIME_BUDGET, weight='travel_time')
    thermal_dist  = nx.single_source_dijkstra_path_length(
        G_thermal, node, cutoff=TIME_BUDGET, weight='travel_time')

    classic_stops = len(stop_nodes_valid & set(classic_dist.keys()))
    thermal_stops = len(stop_nodes_valid & set(thermal_dist.keys()))
    tarr = (classic_stops - thermal_stops) / max(classic_stops, 1) * 100

    rows.append({
        '집계구코드':    row['집계구코드'],
        'net_node':      node,
        'classic_stops': classic_stops,
        'thermal_stops': thermal_stops,
        'tarr':          round(tarr, 2),
    })

result = pd.DataFrame(rows)
result.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')

valid = result[result['classic_stops'] > 0]
print(f"\n=== Walk-Only TARR 결과 (MRT≥{MRT_THRESH}°C, 13시) ===")
print(f"  유효 집계구: {len(valid)}개 (classic_stops>0)")
print(f"  TARR 평균:   {valid['tarr'].mean():.1f}%")
print(f"  TARR 중앙값: {valid['tarr'].median():.1f}%")
print(f"  완전차단:    {(valid['tarr'] == 100).sum()}개 ({(valid['tarr'] == 100).mean()*100:.1f}%)")
print(f"  ≥50% 감소:   {(valid['tarr'] >= 50).sum()}개 ({(valid['tarr'] >= 50).mean()*100:.1f}%)")
print(f"  정류장 접근 수 - Classic 평균: {valid['classic_stops'].mean():.1f}개 / Thermal 평균: {valid['thermal_stops'].mean():.1f}개")
print(f"\n저장: {OUT_CSV}")
