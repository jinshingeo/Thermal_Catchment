"""
링크 임계성 분석 — Micro Scale TAVI
=====================================
목적:
  역 단위 TAVI(Macro)에서 나아가,
  Catchment 내 개별 링크가 접근성 차단에 얼마나 기여하는지 정량화

개념:
  hot link (UTCI ≥ 38°C) 중에서
  "이 링크가 서늘해진다면 몇 개의 노드가 접근성을 회복하는가?"
  → link_criticality = recovered_nodes / classic_nodes × 100 (%)

알고리즘:
  1. G_thermal (뜨거운 링크 제거된 그래프)에서 thermal_nodes 확보
  2. hot_edges 중 thermal_nodes와 인접한 "경계 링크" 식별
     (내부 고립 링크는 단독으로는 접근성 회복 불가 → 제외)
  3. 경계 링크 하나씩 G_thermal에 복원 → Dijkstra → 회복 노드 수 측정
  4. link_criticality 순위화 → 정책 우선순위 제안

정책 함의:
  criticality 높은 링크 = 이 도로의 열스트레스를 낮추면 접근성 회복 최대화
  → 그늘막·가로수·쿨링 미스트 등 열환경 개선 우선 투자 위치

출력:
  link_criticality_summary.json  — 역별 상위 링크 목록
  link_criticality_13h.csv       — 전체 링크 임계성 테이블
  figures/link_criticality_*.png — 역별 임계성 지도
"""

import os
import json
import numpy as np
import pandas as pd
import networkx as nx
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import contextily as ctx
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE      = os.path.dirname(os.path.abspath(__file__))
STP_BASE  = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH  = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
UTCI_PATH = os.path.join(BASE, 'link_utci_solweig.csv')
FIG_DIR   = os.path.join(BASE, 'figures')
OUT_DIR   = BASE
os.makedirs(FIG_DIR, exist_ok=True)

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
THRESHOLD   = 38.0
TARGET_HOUR = 13   # 폭염 피크 (민감도: 16시도 가능)
TOP_N       = 10   # 역별 상위 링크 수

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


# ── 1. 데이터 로드 ──────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

for u, v, data in G_base.edges(data=True):
    data['travel_time'] = data.get('length', 0) / WALK_SPEED

print("UTCI 데이터 로드 중...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
h_df = utci_df[(utci_df['hour'] == TARGET_HOUR) & (utci_df['utci_final'] >= THRESHOLD)]
hot_edges_set = set(zip(h_df['u'].astype(str), h_df['v'].astype(str)))
# edge → travel_time 빠른 조회용
edge_time = {
    (str(u), str(v)): d.get('travel_time', 0)
    for u, v, d in G_base.edges(data=True)
}
edge_time.update({(str(v), str(u)): t for (u, v), t in list(edge_time.items())})

print(f"  {TARGET_HOUR:02d}시 hot edges: {len(hot_edges_set):,}개")

# 역 노드
for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])


# ── 2. 링크 임계성 계산 함수 ────────────────────────────────────────────
def compute_link_criticality(G_base, station_node, hot_edges_set, edge_time):
    """
    Classic / Thermal Catchment 구성 후
    각 hot edge의 접근성 회복 기여도 계산

    Returns
    -------
    classic_nodes  : set
    thermal_nodes  : set
    criticality    : dict  {(u,v): {'recovered': int, 'criticality_pct': float}}
    """
    # Classic Catchment
    classic_dist  = nx.single_source_dijkstra_path_length(
        G_base, station_node, cutoff=TIME_BUDGET, weight='travel_time'
    )
    classic_nodes = set(classic_dist.keys())

    # Thermal Catchment
    G_thermal = G_base.copy()
    hot_list  = [
        (u, v) for u, v in G_thermal.edges()
        if (str(u), str(v)) in hot_edges_set or (str(v), str(u)) in hot_edges_set
    ]
    G_thermal.remove_edges_from(hot_list)

    thermal_dist  = nx.single_source_dijkstra_path_length(
        G_thermal, station_node, cutoff=TIME_BUDGET, weight='travel_time'
    )
    thermal_nodes = set(thermal_dist.keys())
    lost_nodes    = classic_nodes - thermal_nodes

    if not lost_nodes:
        return classic_nodes, thermal_nodes, {}

    # ── 경계 링크만 후보로 추림 ─────────────────────────────────────
    # thermal_nodes와 인접한 hot edge = 복원 시 직접 접근성 회복 가능
    candidate_edges = []
    for u, v in hot_list:
        if u in thermal_nodes or v in thermal_nodes:
            candidate_edges.append((u, v))

    # ── 링크별 임계성 측정 ───────────────────────────────────────────
    criticality = {}
    for u, v in candidate_edges:
        G_test = G_thermal.copy()
        t = edge_time.get((str(u), str(v)), edge_time.get((str(v), str(u)), 5.0))
        G_test.add_edge(u, v, travel_time=t)

        new_dist  = nx.single_source_dijkstra_path_length(
            G_test, station_node, cutoff=TIME_BUDGET, weight='travel_time'
        )
        new_nodes = set(new_dist.keys())
        recovered = new_nodes - thermal_nodes

        criticality[(u, v)] = {
            'recovered_count':    len(recovered),
            'criticality_pct':    round(len(recovered) / max(len(classic_nodes), 1) * 100, 2),
            'recovered_nodes':    recovered,
        }

    return classic_nodes, thermal_nodes, criticality


# ── 3. 전체 역 분석 실행 ────────────────────────────────────────────────
print(f"\n=== 링크 임계성 분석 ({TARGET_HOUR:02d}시) ===")
all_results   = {}
all_link_rows = []

for station_name, sinfo in STATIONS.items():
    print(f"\n[{station_name}] 분석 중...", end=' ')
    classic_nodes, thermal_nodes, criticality = compute_link_criticality(
        G_base, sinfo['node'], hot_edges_set, edge_time
    )
    classic_count = len(classic_nodes)
    thermal_count = len(thermal_nodes)
    reduction_pct = round((classic_count - thermal_count) / max(classic_count, 1) * 100, 1)

    # 상위 N개 링크
    ranked = sorted(criticality.items(), key=lambda x: -x[1]['criticality_pct'])
    top_links = [
        {
            'station':         station_name,
            'u':               str(u),
            'v':               str(v),
            'recovered_count': d['recovered_count'],
            'criticality_pct': d['criticality_pct'],
        }
        for (u, v), d in ranked[:TOP_N]
    ]

    all_results[station_name] = {
        'classic_count':  classic_count,
        'thermal_count':  thermal_count,
        'reduction_pct':  reduction_pct,
        'candidate_links': len(criticality),
        'top_links':       top_links,
    }

    for (u, v), d in criticality.items():
        all_link_rows.append({
            'station':         station_name,
            'u':               str(u),
            'v':               str(v),
            'recovered_count': d['recovered_count'],
            'criticality_pct': d['criticality_pct'],
        })

    if top_links:
        top1 = top_links[0]
        print(f"후보 {len(criticality)}개 | "
              f"최고 임계 링크: ({top1['u'][:6]}…,{top1['v'][:6]}…) "
              f"→ {top1['criticality_pct']}% ({top1['recovered_count']}노드 회복)")
    else:
        print("hot edge 없음 (UTCI < 38°C)")

link_df = pd.DataFrame(all_link_rows)


# ── 4. 순위 출력 ─────────────────────────────────────────────────────────
print(f"\n=== 역별 상위 1위 링크 요약 ({TARGET_HOUR:02d}시) ===")
print(f"{'역':<8} {'reduction_pct':>14} {'최고임계링크 회복률':>20}")
print("-" * 48)
for stn, res in all_results.items():
    tl = res['top_links']
    top_str = f"{tl[0]['criticality_pct']:.1f}%" if tl else "—"
    print(f"{stn:<8} {res['reduction_pct']:>13.1f}%  {top_str:>18}")


# ── 5. 시각화: 역별 임계성 지도 ──────────────────────────────────────────
print("\n시각화 생성 중...")

# 임계성 컬러맵 (0=흰색, 최대=진빨강)
cmap   = cm.get_cmap('YlOrRd')
norm   = mcolors.Normalize(vmin=0, vmax=link_df['criticality_pct'].max() if len(link_df) else 1)

for station_name, sinfo in STATIONS.items():
    res = all_results[station_name]
    if not res['top_links']:
        continue

    # 이 역의 링크 임계성 딕셔너리
    crit_dict = {
        (row['u'], row['v']): row['criticality_pct']
        for row in res['top_links']
    }
    # full criticality (not just top N, for coloring all edges)
    _, _, criticality_full = compute_link_criticality(
        G_base, sinfo['node'], hot_edges_set, edge_time
    )

    fig, ax = plt.subplots(figsize=(11, 9))

    # 배경 엣지 (회색)
    edges_wm.plot(ax=ax, color='#cccccc', linewidth=0.4, alpha=0.5, zorder=1)

    # hot edges 중 임계성에 따라 색상
    plotted = set()
    for (u, v), d in sorted(criticality_full.items(),
                             key=lambda x: x[1]['criticality_pct']):
        c_pct = d['criticality_pct']
        color = cmap(norm(c_pct))
        lw    = 1.5 + c_pct * 0.08   # 임계성 높을수록 두껍게

        try:
            geom = edges_wm.loc[(u, v)].geometry if (u, v) in edges_wm.index \
                   else edges_wm.loc[(v, u)].geometry
            if hasattr(geom, '__iter__'):
                for g in geom:
                    ax.plot(*g.xy, color=color, linewidth=lw, alpha=0.9, zorder=4)
            else:
                ax.plot(*geom.xy, color=color, linewidth=lw, alpha=0.9, zorder=4)
            plotted.add((u, v))
        except (KeyError, Exception):
            pass

    # 역 위치 마커
    sg = nodes_wm.loc[sinfo['node']].geometry
    ax.plot(sg.x, sg.y, '*', color='#FFD600', markersize=16, zorder=10,
            markeredgecolor='black', markeredgewidth=1.2)

    # 컬러바
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('링크 임계성 (%)\n(복원 시 접근성 회복률)', fontsize=9)

    try:
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=15, alpha=0.4)
    except Exception:
        pass

    top1 = res['top_links'][0] if res['top_links'] else {}
    ax.set_title(
        f"{station_name} — 링크 임계성 지도 ({TARGET_HOUR:02d}시)\n"
        f"reduction_pct={res['reduction_pct']}% | "
        f"최고 임계 링크 회복률={top1.get('criticality_pct', 0):.1f}%",
        fontsize=11, fontweight='bold'
    )
    ax.set_axis_off()
    plt.tight_layout()
    fname = os.path.join(FIG_DIR, f'link_criticality_{station_name}_{TARGET_HOUR:02d}h.png')
    fig.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  저장: figures/link_criticality_{station_name}_{TARGET_HOUR:02d}h.png")


# ── 6. 통합 비교: 역별 상위 링크 임계성 막대 그래프 ─────────────────────
fig, ax = plt.subplots(figsize=(12, 6))
stations_with_data = [s for s in STATIONS if all_results[s]['top_links']]
x    = np.arange(len(stations_with_data))
tops = [all_results[s]['top_links'][0]['criticality_pct'] for s in stations_with_data]
reds = [all_results[s]['reduction_pct'] for s in stations_with_data]

bars = ax.bar(x, tops, color=[COLORS[s] for s in stations_with_data],
              alpha=0.85, edgecolor='gray', label='최고 임계 링크 회복률 (%)')
for bar, val in zip(bars, tops):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

ax2 = ax.twinx()
ax2.plot(x, reds, 'o--', color='#37474F', linewidth=1.8, markersize=7,
         label='역 단위 reduction_pct (%)')
ax2.set_ylabel('reduction_pct (%)', fontsize=10, color='#37474F')

ax.set_xticks(x)
ax.set_xticklabels(stations_with_data, fontsize=11)
ax.set_ylabel('링크 임계성 — 최고 회복률 (%)', fontsize=10)
ax.set_title(
    f'역별 최고 임계 링크 회복률 vs reduction_pct ({TARGET_HOUR:02d}시)\n'
    '막대: 단일 링크 복원 시 최대 접근성 회복률 | 점선: 역 전체 감소율',
    fontsize=11, fontweight='bold'
)
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc='upper right')
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, f'link_criticality_comparison_{TARGET_HOUR:02d}h.png'),
            dpi=150, bbox_inches='tight')
plt.close()
print(f"\n저장: figures/link_criticality_comparison_{TARGET_HOUR:02d}h.png")


# ── 7. 저장 ─────────────────────────────────────────────────────────────
out_json = os.path.join(OUT_DIR, 'link_criticality_summary.json')
out_csv  = os.path.join(OUT_DIR, 'link_criticality_13h.csv')

# JSON: top links만
summary = {
    'hour':      TARGET_HOUR,
    'threshold': THRESHOLD,
    'stations':  {}
}
for stn, res in all_results.items():
    summary['stations'][stn] = {
        'reduction_pct':   res['reduction_pct'],
        'candidate_links': res['candidate_links'],
        'top_links': [
            {k: v for k, v in lk.items() if k != 'station'}
            for lk in res['top_links']
        ]
    }

with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

link_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
print(f"저장: {out_json}")
print(f"저장: {out_csv}")

print("\n=== 완료 ===")
print("프레임워크 해석:")
print("  Macro: TAVI(역) → 어느 역이 취약한가")
print("  Micro: link_criticality(링크) → 어느 도로를 개선해야 하는가")
