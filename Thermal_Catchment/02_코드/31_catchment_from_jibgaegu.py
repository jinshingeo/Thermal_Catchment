"""
Task 2 & 3 — 집계구 기점 Classic / Thermal Catchment 계산 (30분, 3개 시간대)
============================================================================
570개 집계구 중심점에서 출발하여 30분 내 도달 가능한 대중교통 정류장과
이동시간을 계산합니다.

  Classic  : 전체 보행 네트워크 기준 30분 도달권 (시간대 무관, 1회 계산)
  Thermal  : UTCI ≥ 38°C 링크 제거 후 30분 도달권
             - 폭염 전   (h10): 고온 링크 0개
             - 폭염 중간 (h13): 고온 링크 23.8%
             - 폭염 피크 (h14): 고온 링크 47.8%

입력:
  residential_population.csv          — 집계구 중심점 (lon, lat)
  link_utci_solweig.csv               — 링크별 시간대별 UTCI
  transit_stops_seongdong.csv         — 정류장 + node_id
  seongdong_walk_network.graphml      — OSM 보행 네트워크

출력 (→ 03_결과물/):
  catchment_classic_30min.json           — {집계구코드: {stop_id: travel_time_sec}}
  catchment_thermal_h10_30min.json       — 폭염 전
  catchment_thermal_h13_30min.json       — 폭염 중간
  catchment_thermal_h14_30min.json       — 폭염 피크
  catchment_summary_multihour.csv        — 집계구별 시간대별 도달 정류장 수 요약
"""

import os
import json
import time
import numpy as np
import pandas as pd
import networkx as nx
import osmnx as ox

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
os.makedirs(RES_DIR, exist_ok=True)

NET_PATH    = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
UTCI_PATH   = os.path.join(RES_DIR, 'link_utci_solweig.csv')
POP_PATH    = os.path.join(RES_DIR, 'residential_population.csv')
STOPS_PATH  = os.path.join(DATA_DIR, '네트워크', 'transit_stops_seongdong.csv')

WALK_SPEED  = 4.5 * 1000 / 3600   # m/s (= 1.25 m/s)
TIME_BUDGET = 30 * 60              # 1800초
THRESHOLD   = 38.0                 # UTCI °C 하드 컷

TARGET_HOURS = {
    10: '폭염전',
    13: '폭염중간',
    14: '폭염피크',
}


# ── 1. 데이터 로드 ────────────────────────────────────────────────────────
print("데이터 로드 중...")

print("  보행 네트워크...")
G = ox.load_graphml(NET_PATH)
print(f"    노드: {G.number_of_nodes():,} | 엣지: {G.number_of_edges():,}")

print("  UTCI 데이터...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
for h, label in TARGET_HOURS.items():
    n_hot = (utci_df[utci_df['hour'] == h]['utci_final'] >= THRESHOLD).sum()
    n_total = len(utci_df[utci_df['hour'] == h])
    print(f"    {h:2d}시 ({label}) 고온 링크: {n_hot:,}개 / {n_total:,}개 ({n_hot/n_total*100:.1f}%)")

print("  집계구 중심점...")
pop_df = pd.read_csv(POP_PATH, encoding='utf-8-sig')
print(f"    집계구 수: {len(pop_df):,}개")

print("  대중교통 정류장...")
stops_df = pd.read_csv(STOPS_PATH, encoding='utf-8-sig')
stops_df['node_id'] = stops_df['node_id'].astype(int)
print(f"    정류장 수: {len(stops_df):,}개 (지하철 {(stops_df.stop_type=='subway').sum()}개 + 버스 {(stops_df.stop_type=='bus').sum()}개)")


# ── 2. 네트워크 이동시간 가중치 설정 ──────────────────────────────────────
print("\n이동시간 가중치 설정 중...")
for u, v, data in G.edges(data=True):
    data['travel_time'] = data.get('length', 0) / WALK_SPEED


# ── 3. 집계구 → 최근접 네트워크 노드 ─────────────────────────────────────
print("집계구 중심점 → 최근접 네트워크 노드 매핑 중...")
origin_nodes = ox.nearest_nodes(G, X=pop_df['lon'].values, Y=pop_df['lat'].values)
pop_df['node_id'] = origin_nodes

node_to_stops = {}
for _, row in stops_df.iterrows():
    nid = int(row['node_id'])
    if nid not in node_to_stops:
        node_to_stops[nid] = []
    node_to_stops[nid].append(str(row['stop_id']))

stop_nodes_set = set(stops_df['node_id'].astype(int).unique())


# ── 4. 캐치먼트 계산 함수 ─────────────────────────────────────────────────
def compute_catchment_for_origin(graph, origin_node, stop_nodes, node_to_stops_map):
    try:
        dist_map = nx.single_source_dijkstra_path_length(
            graph, origin_node, cutoff=TIME_BUDGET, weight='travel_time'
        )
    except nx.NetworkXError:
        return {}
    result = {}
    for node, t in dist_map.items():
        if node in stop_nodes and node in node_to_stops_map:
            for sid in node_to_stops_map[node]:
                result[sid] = round(t, 1)
    return result


def build_thermal_graph(base_graph, hour):
    utci_h = utci_df[utci_df['hour'] == hour]
    hot = set(
        zip(utci_h[utci_h['utci_final'] >= THRESHOLD]['u'].astype(str),
            utci_h[utci_h['utci_final'] >= THRESHOLD]['v'].astype(str))
    )
    G_t = base_graph.copy()
    to_remove = [
        (u, v) for u, v in G_t.edges()
        if (str(u), str(v)) in hot or (str(v), str(u)) in hot
    ]
    G_t.remove_edges_from(to_remove)
    print(f"    제거된 링크: {len(to_remove):,}개 ({len(to_remove)/base_graph.number_of_edges()*100:.1f}%)")
    return G_t


# ── 5. Classic Catchment ─────────────────────────────────────────────────
print(f"\nClassic Catchment 계산 중 ({len(pop_df)}개 집계구)...")
classic_results = {}
t0 = time.time()
for i, row in pop_df.iterrows():
    code = str(int(float(row['집계구코드'])))
    classic_results[code] = compute_catchment_for_origin(
        G, int(row['node_id']), stop_nodes_set, node_to_stops
    )
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(pop_df)} ({time.time()-t0:.0f}초)")
print(f"  Classic 완료 ({time.time()-t0:.0f}초)")


# ── 6. Thermal Catchment — 3개 시간대 ────────────────────────────────────
thermal_results = {}
for hour, label in TARGET_HOURS.items():
    print(f"\nThermal Catchment — {hour}시 ({label}) 계산 중...")
    G_thermal = build_thermal_graph(G, hour)
    results = {}
    t0 = time.time()
    for i, row in pop_df.iterrows():
        code = str(int(float(row['집계구코드'])))
        results[code] = compute_catchment_for_origin(
            G_thermal, int(row['node_id']), stop_nodes_set, node_to_stops
        )
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(pop_df)} ({time.time()-t0:.0f}초)")
    thermal_results[hour] = results
    print(f"  {hour}시 완료 ({time.time()-t0:.0f}초)")


# ── 7. 요약 통계 ─────────────────────────────────────────────────────────
print("\n요약 통계 계산 중...")
summary_rows = []
for _, row in pop_df.iterrows():
    code = str(int(float(row['집계구코드'])))
    r = {
        '집계구코드': code,
        'residential_pop': row['residential_pop'],
        'lon': row['lon'],
        'lat': row['lat'],
        'n_classic_stops': len(classic_results.get(code, {})),
    }
    for hour, label in TARGET_HOURS.items():
        r[f'n_thermal_h{hour}'] = len(thermal_results[hour].get(code, {}))
    summary_rows.append(r)

summary_df = pd.DataFrame(summary_rows)

print(f"\n  전체 집계구: {len(summary_df)}개")
print(f"  Classic 평균 도달: {summary_df['n_classic_stops'].mean():.1f}개")
for hour, label in TARGET_HOURS.items():
    col = f'n_thermal_h{hour}'
    mean_stops = summary_df[col].mean()
    blocked = (summary_df[col] == 0).sum()
    print(f"  Thermal {hour}시 ({label}): 평균 {mean_stops:.1f}개, 완전차단 {blocked}개 ({blocked/len(summary_df)*100:.1f}%)")


# ── 8. 저장 ──────────────────────────────────────────────────────────────
classic_path = os.path.join(RES_DIR, 'catchment_classic_30min.json')
with open(classic_path, 'w', encoding='utf-8') as f:
    json.dump(classic_results, f, ensure_ascii=False)
print(f"\n저장: {classic_path}")

for hour, label in TARGET_HOURS.items():
    path = os.path.join(RES_DIR, f'catchment_thermal_h{hour}_30min.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(thermal_results[hour], f, ensure_ascii=False)
    print(f"저장: {path}")

summary_path = os.path.join(RES_DIR, 'catchment_summary_multihour.csv')
summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
print(f"저장: {summary_path}")

print("\n=== Task 2 & 3 완료 ===")
print("다음 단계: 32_gravity_model.py 실행")
