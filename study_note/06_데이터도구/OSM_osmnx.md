# OSM & osmnx — 보행 네트워크 데이터

## OSM (OpenStreetMap)

### 한 줄 정의
> 전 세계 자원봉사자들이 함께 만드는 **오픈소스 지도** — 구글맵의 오픈소스 버전

### 이 연구에서 어떻게 썼나
- 성동구 보행 가능 도로망 추출
- 건물 폴리곤 추출 → SVF 계산에 활용
- **링크 15,608개, 노드 수 ~8,000개** 규모의 보행 네트워크

### 한계
- 자원봉사자 입력 데이터 → 일부 누락 가능 (지하 통로, 실내 경로 미포함)
- 지하도, 아파트 단지 내부 경로 등이 빠질 수 있음

---

## osmnx

### 한 줄 정의
> Python에서 OSM 데이터를 가져와 **네트워크 분석** 을 할 수 있게 해주는 라이브러리

### 주요 기능

```python
import osmnx as ox

# 1. 네트워크 불러오기
G = ox.load_graphml(NET_PATH).to_undirected()

# 2. 집계구 중심점에서 가장 가까운 노드 찾기
jbg['net_node'] = ox.distance.nearest_nodes(
    G, jbg['centroid'].x.values, jbg['centroid'].y.values
)
```

- `load_graphml`: 저장된 네트워크 파일 불러오기
- `nearest_nodes`: GPS 좌표에서 가장 가까운 네트워크 노드 찾기

### networkx와의 관계
osmnx로 네트워크를 가져온 후, **networkx** 라이브러리의 Dijkstra 알고리즘으로 경로를 계산합니다.

```python
import networkx as nx

dist = nx.single_source_dijkstra_path_length(
    G, node, cutoff=TIME_BUDGET, weight='travel_time'
)
```

---

## 이 연구의 네트워크 특성

| 항목 | 값 |
|------|-----|
| 범위 | 서울특별시 성동구 |
| 링크 수 | **15,608개** |
| 가중치 | travel_time = length / WALK_SPEED |
| 네트워크 타입 | 무방향(undirected) — 양방향 보행 가능 |

---

## 관련 개념
- [[집계구]] — osmnx로 가장 가까운 노드를 연결하는 대상
- [[Catchment_Area]] — osmnx 네트워크 위에서 Dijkstra로 계산
