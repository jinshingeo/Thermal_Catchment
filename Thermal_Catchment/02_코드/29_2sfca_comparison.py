"""
Classic vs Thermal 2SFCA 비교 분석
=====================================
Thermal Catchment Area 개념이 기존 2SFCA 접근성 측정에 미치는 영향 정량화

핵심 질문:
  "열환경을 반영하지 않은 Classic 2SFCA는 지하철 접근성을 얼마나 과대평가하는가?"

방법론:
  Classic 2SFCA  : 전체 보행 네트워크 기반 Catchment 사용
  Thermal 2SFCA  : UTCI ≥ 38°C 링크 제거 후 Thermal Catchment 사용
  거리감쇠 함수  : Gaussian (Shin & Park 2026, t0 = 15분)
  수요(Demand)   : 집계구별 거주인구 (새벽 01~05시 평균, Shin & Park 2026)
  공급(Supply)   : 지하철역 (S_j = 1, 동등 가중)

2SFCA 수식 (Gaussian decay, Dai 2011):
  Step 1: R_j = S_j / Σ_{i∈catchment(j)} D_i × G(t_ij, t0)
  Step 2: A_i = Σ_{j∈catchment(i)} R_j × G(t_ij, t0)

  G(t, t0) = (e^{-0.5(t/t0)^2} - e^{-0.5}) / (1 - e^{-0.5})  if t ≤ t0
           = 0                                                    if t > t0

입력:
  residential_population.csv       — 28_residential_population.py 산출
  seongdong_walk_network.graphml   — OSM 보행 네트워크
  link_utci_solweig.csv            — 링크별 UTCI (19_solweig_utci.py)

출력:
  2sfca_results.csv                — 집계구별 Classic/Thermal 접근성 지수
  2sfca_results.geojson
  figures/2sfca_comparison.png     — 비교 지도
  figures/2sfca_reduction.png      — 접근성 감소율 지도
"""

import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE      = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR  = os.path.dirname(BASE)                              # Thermal_Catchment/
RES_DIR   = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR   = os.path.join(RES_DIR, 'figures')
OUT_DIR   = RES_DIR

STP_BASE  = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH  = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
UTCI_PATH = os.path.join(RES_DIR, 'link_utci_solweig.csv')
POP_PATH  = os.path.join(RES_DIR, 'residential_population.csv')
POP_GEO   = os.path.join(RES_DIR, 'residential_population.geojson')

os.makedirs(FIG_DIR, exist_ok=True)

WALK_SPEED  = 4.5 * 1000 / 3600   # m/s
TIME_BUDGET = 15 * 60              # 900초
THRESHOLD   = 38.0                 # °C — UTCI 하드 컷 (Bröde et al. 2012)
TARGET_HOUR = 13                   # 폭염 피크 시간대

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171},
}

COLORS = {
    '왕십리역': '#E53935', '행당역': '#FB8C00', '응봉역': '#8E24AA',
    '뚝섬역':  '#43A047', '성수역': '#1E88E5', '서울숲역': '#00ACC1',
    '옥수역':  '#6D4C41',
}


# ── Gaussian 거리감쇠 함수 (Dai 2011, Shin & Park 2026) ──────────────────
def gaussian_decay(t, t0):
    """
    G(t, t0) — 이동시간 t, 임계시간 t0
    t ≤ t0: Gaussian decay
    t > t0: 0
    """
    if t > t0:
        return 0.0
    num = np.exp(-0.5 * (t / t0) ** 2) - np.exp(-0.5)
    den = 1 - np.exp(-0.5)
    return float(num / den)


# ── 1. 네트워크 로드 ────────────────────────────────────────────────────
print("네트워크 로드 중...")
G = ox.load_graphml(NET_PATH)
G = G.to_undirected()
for u, v, data in G.edges(data=True):
    data['travel_time'] = data.get('length', 0) / WALK_SPEED
node_coords = {n: (d['x'], d['y']) for n, d in G.nodes(data=True)}
print(f"  노드 {len(G.nodes):,}개 | 엣지 {len(G.edges):,}개")


# ── 2. UTCI 로드 → 13시 기준 뜨거운 엣지 식별 ──────────────────────────
print(f"\nUTCI 로드 중 ({TARGET_HOUR}시 기준)...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
utci_13  = utci_df[utci_df['hour'] == TARGET_HOUR].copy()
hot_edges = set(
    zip(utci_13[utci_13['utci_final'] >= THRESHOLD]['u'],
        utci_13[utci_13['utci_final'] >= THRESHOLD]['v'])
)
print(f"  뜨거운 엣지: {len(hot_edges):,}개 (UTCI ≥ {THRESHOLD}°C)")

# Thermal 그래프: 뜨거운 엣지 제거
G_thermal = G.copy()
removed = [(u, v) for u, v in list(G_thermal.edges())
           if (u, v) in hot_edges or (v, u) in hot_edges]
G_thermal.remove_edges_from(removed)
print(f"  제거 후 엣지: {len(G_thermal.edges):,}개")


# ── 3. 거주인구 로드 → 최근접 노드 매핑 ──────────────────────────────────
print("\n거주인구 데이터 로드 중...")
pop_df = pd.read_csv(POP_PATH, encoding='utf-8-sig')
pop_df  = pop_df[pop_df['residential_pop'] > 0].copy()
print(f"  집계구 수: {len(pop_df):,}개")

print("  집계구 → 최근접 OSM 노드 매핑...")
pop_df['osm_node'] = [
    ox.distance.nearest_nodes(G, row['lon'], row['lat'])
    for _, row in pop_df.iterrows()
]
print("  매핑 완료")


# ── 4. 역별 Dijkstra → Classic / Thermal 이동시간 딕셔너리 ────────────────
print(f"\n역별 Catchment 계산 ({TARGET_HOUR}시 기준)...")

station_data = {}
for stn, info in STATIONS.items():
    stn_node = ox.distance.nearest_nodes(G, info['lon'], info['lat'])

    # Classic Dijkstra
    dist_classic = nx.single_source_dijkstra_path_length(
        G, stn_node, cutoff=TIME_BUDGET, weight='travel_time'
    )
    # Thermal Dijkstra
    dist_thermal = nx.single_source_dijkstra_path_length(
        G_thermal, stn_node, cutoff=TIME_BUDGET, weight='travel_time'
    )

    station_data[stn] = {
        'node':    stn_node,
        'classic': dist_classic,   # {node_id: travel_time}
        'thermal': dist_thermal,
    }
    print(f"  [{stn}] classic={len(dist_classic):,} / thermal={len(dist_thermal):,} 노드")


# ── 5. 2SFCA Step 1: 역별 supply-demand ratio ─────────────────────────────
print("\n2SFCA Step 1: Supply-Demand Ratio 계산...")

for stn in STATIONS:
    for mode in ['classic', 'thermal']:
        dist_dict = station_data[stn][mode]
        # 집계구 중 이 역의 catchment 안에 있는 것들
        denom = 0.0
        for _, row in pop_df.iterrows():
            node = row['osm_node']
            t = dist_dict.get(node, np.inf)
            g = gaussian_decay(t, TIME_BUDGET)
            denom += row['residential_pop'] * g

        # S_j = 1 (모든 역 동등)
        r = 1.0 / denom if denom > 0 else 0.0
        station_data[stn][f'R_{mode}'] = r

    print(f"  [{stn}] R_classic={station_data[stn]['R_classic']:.6f} | "
          f"R_thermal={station_data[stn]['R_thermal']:.6f}")


# ── 6. 2SFCA Step 2: 집계구별 접근성 지수 ────────────────────────────────
print("\n2SFCA Step 2: 집계구별 접근성 지수 계산...")

results = []
for _, row in pop_df.iterrows():
    node = row['osm_node']
    A_classic = 0.0
    A_thermal = 0.0

    for stn in STATIONS:
        # Classic
        t_c = station_data[stn]['classic'].get(node, np.inf)
        g_c = gaussian_decay(t_c, TIME_BUDGET)
        A_classic += station_data[stn]['R_classic'] * g_c

        # Thermal
        t_t = station_data[stn]['thermal'].get(node, np.inf)
        g_t = gaussian_decay(t_t, TIME_BUDGET)
        A_thermal += station_data[stn]['R_thermal'] * g_t

    # 감소율
    if A_classic > 0:
        reduction = (A_classic - A_thermal) / A_classic * 100
    else:
        reduction = 0.0

    results.append({
        '집계구코드':   row['집계구코드'],
        'residential_pop': row['residential_pop'],
        'lon':          row['lon'],
        'lat':          row['lat'],
        'A_classic':    round(A_classic, 8),
        'A_thermal':    round(A_thermal, 8),
        'A_reduction_pct': round(reduction, 2),
    })

result_df = pd.DataFrame(results)
print(f"  처리 완료: {len(result_df):,}개 집계구")


# ── 7. 결과 요약 ──────────────────────────────────────────────────────────
print("\n=== 2SFCA 비교 결과 요약 (13시 기준) ===")
print(f"  Classic 2SFCA  평균: {result_df['A_classic'].mean():.6f}")
print(f"  Thermal 2SFCA  평균: {result_df['A_thermal'].mean():.6f}")
print(f"  접근성 감소율  평균: {result_df['A_reduction_pct'].mean():.1f}%")
print(f"  접근성 감소율  최대: {result_df['A_reduction_pct'].max():.1f}%")
print(f"  A_thermal = 0 집계구 수 (완전 접근 불가): "
      f"{(result_df['A_thermal'] == 0).sum():,}개")

# 인구 가중 평균 감소율
pop_weighted = (
    (result_df['A_reduction_pct'] * result_df['residential_pop']).sum()
    / result_df['residential_pop'].sum()
)
print(f"  인구 가중 평균 감소율: {pop_weighted:.1f}%")
affected_pop = result_df[result_df['A_reduction_pct'] > 0]['residential_pop'].sum()
print(f"  접근성 감소 영향 인구: {affected_pop:,.0f}명")


# ── 8. 저장 ──────────────────────────────────────────────────────────────
out_csv = os.path.join(OUT_DIR, '2sfca_results.csv')
result_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
print(f"\n저장: {out_csv}")

# GeoJSON
if os.path.exists(POP_GEO):
    pop_gdf = gpd.read_file(POP_GEO)
    pop_gdf['집계구코드'] = pop_gdf['집계구코드'].astype(str)
    result_df['집계구코드'] = result_df['집계구코드'].astype(str)
    merged = pop_gdf.merge(
        result_df[['집계구코드', 'A_classic', 'A_thermal', 'A_reduction_pct']],
        on='집계구코드', how='left'
    )
    out_geo = os.path.join(OUT_DIR, '2sfca_results.geojson')
    merged.to_file(out_geo, driver='GeoJSON')
    print(f"저장: {out_geo}")
else:
    merged = None


# ── 9. 시각화 ─────────────────────────────────────────────────────────────
print("\n시각화 생성 중...")

try:
    import contextily as ctx

    fig, axes = plt.subplots(1, 3, figsize=(20, 7))

    if merged is not None:
        gdf_plot = merged.to_crs(epsg=3857)
    else:
        gdf_plot = gpd.GeoDataFrame(
            result_df,
            geometry=gpd.points_from_xy(result_df['lon'], result_df['lat']),
            crs='EPSG:4326'
        ).to_crs(epsg=3857)

    # 역 위치
    stn_gdf = gpd.GeoDataFrame(
        list(STATIONS.keys()),
        geometry=gpd.points_from_xy(
            [v['lon'] for v in STATIONS.values()],
            [v['lat'] for v in STATIONS.values()]
        ),
        columns=['station'],
        crs='EPSG:4326'
    ).to_crs(epsg=3857)

    cmaps = ['YlOrRd', 'YlOrRd', 'Reds']
    cols  = ['A_classic', 'A_thermal', 'A_reduction_pct']
    titles = [
        'Classic 2SFCA\n(열환경 미반영)',
        f'Thermal 2SFCA\n(UTCI ≥ {THRESHOLD}°C 하드 컷)',
        '접근성 감소율 (%)\nClassic → Thermal',
    ]

    for ax, col, cmap, title in zip(axes, cols, cmaps, titles):
        if col in gdf_plot.columns and gdf_plot[col].notna().any():
            gdf_plot.plot(column=col, ax=ax, cmap=cmap,
                         legend=True, alpha=0.75,
                         missing_kwds={'color': 'lightgrey'})
        stn_gdf.plot(ax=ax, color='black', marker='*', markersize=120,
                     zorder=5)
        for _, s in stn_gdf.iterrows():
            ax.annotate(s['station'], (s.geometry.x, s.geometry.y),
                        textcoords='offset points', xytext=(4, 4),
                        fontsize=7, color='black')
        try:
            ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron,
                           zoom=14, alpha=0.4)
        except Exception:
            pass
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_axis_off()

    plt.suptitle(
        'Classic vs Thermal 2SFCA 비교 — 서울 성동구 지하철역\n'
        f'Gaussian 거리감쇠 | 시간예산 15분 | {TARGET_HOUR}시 (폭염 피크)',
        fontsize=13, fontweight='bold'
    )
    plt.tight_layout()
    out_fig = os.path.join(FIG_DIR, '2sfca_comparison.png')
    fig.savefig(out_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"저장: figures/2sfca_comparison.png")

except Exception as e:
    print(f"시각화 오류: {e}")


# ── 10. 감소율 분포 막대 그래프 ──────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
counts, edges = np.histogram(result_df['A_reduction_pct'].dropna(), bins=bins)
pops = []
for lo, hi in zip(edges[:-1], edges[1:]):
    mask = (result_df['A_reduction_pct'] >= lo) & (result_df['A_reduction_pct'] < hi)
    pops.append(result_df.loc[mask, 'residential_pop'].sum())

x = range(len(counts))
ax.bar(x, pops, color='#E53935', alpha=0.8, edgecolor='white')
ax.set_xticks(x)
ax.set_xticklabels([f'{int(lo)}~{int(hi)}%' for lo, hi in zip(edges[:-1], edges[1:])],
                   rotation=30, ha='right')
ax.set_xlabel('접근성 감소율 구간', fontsize=11)
ax.set_ylabel('거주인구 (명)', fontsize=11)
ax.set_title(
    '접근성 감소율 구간별 거주인구 분포\n'
    'Classic → Thermal 2SFCA 전환 시 영향 인구',
    fontsize=11, fontweight='bold'
)
ax.grid(axis='y', alpha=0.3)
for i, (cnt, pop) in enumerate(zip(counts, pops)):
    if pop > 0:
        ax.text(i, pop + max(pops)*0.01, f'{pop:,.0f}', ha='center',
                va='bottom', fontsize=8)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, '2sfca_reduction_dist.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: figures/2sfca_reduction_dist.png")

print("\n=== 완료 ===")
print("핵심 해석:")
print("  Classic 2SFCA 대비 Thermal 2SFCA의 접근성 감소")
print("  = 기존 방법이 열환경을 무시함으로써 과대평가한 접근성 규모")
print("\n참고문헌:")
print("  - Shin & Park (2026) ISPRS IJGI: 거주인구 추정 방법, Gaussian 2SFCA")
print("  - Bröde et al. (2012): UTCI 38°C 임계값")
