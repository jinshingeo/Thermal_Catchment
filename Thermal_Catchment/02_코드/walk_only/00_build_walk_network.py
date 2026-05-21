"""
기존 seongdong_walk_network.graphml에서 차량 중심 간선도로 제거
제거: trunk, trunk_link, primary, primary_link, secondary, secondary_link
유지: residential, footway, service, tertiary, path, living_street,
      steps, pedestrian, unclassified, corridor, tertiary_link
"""

import osmnx as ox
import networkx as nx

SRC_NET  = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
OUT_NET  = '/Users/jin/석사논문/TAVI/Thermal_Catchment/03_결과물/walk_only/seongdong_walkonly_network.graphml'

REMOVE_TYPES = {
    'trunk', 'trunk_link',
    'primary', 'primary_link',
    'secondary', 'secondary_link',
}

print("원본 네트워크 로드...")
G = ox.load_graphml(SRC_NET)
print(f"  원본: 노드 {G.number_of_nodes():,} / 엣지 {G.number_of_edges():,}")

# highway 타입이 REMOVE_TYPES에 해당하는 엣지 수집
remove_edges = []
for u, v, k, data in G.edges(keys=True, data=True):
    hw = data.get('highway', '')
    if isinstance(hw, list):
        types = set(hw)
    else:
        types = {hw}
    if types & REMOVE_TYPES:
        remove_edges.append((u, v, k))

print(f"  제거 대상 엣지: {len(remove_edges):,}개")
G.remove_edges_from(remove_edges)

# 고립 노드 제거 후 최대 연결 요소만 유지
G.remove_nodes_from(list(nx.isolates(G)))
if G.is_directed():
    largest = max(nx.weakly_connected_components(G), key=len)
else:
    largest = max(nx.connected_components(G), key=len)
G = G.subgraph(largest).copy()

print(f"  필터링 후: 노드 {G.number_of_nodes():,} / 엣지 {G.number_of_edges():,}")

ox.save_graphml(G, OUT_NET)
print(f"  저장: {OUT_NET}")
