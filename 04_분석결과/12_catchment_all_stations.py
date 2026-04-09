"""
성동구 전체 지하철역 Thermal Catchment 분석
============================================
- 7개 역 × 4시간대 × Classic/Thermal catchment
- 역별 reduction_pct 비교 테이블 및 시각화
- Plan A 회귀분석을 위한 종속변수 생성
"""

import os
import json
import numpy as np
import pandas as pd
import networkx as nx
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import contextily as ctx
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

# ── 경로 설정 ──────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
NET_PATH  = os.path.join(BASE, '../01_네트워크/seongdong_walk_network.graphml')
UTCI_PATH = os.path.join(BASE, 'link_utci_by_hour_v3.csv')
FIG_DIR   = os.path.join(BASE, 'figures')
OUT_DIR   = BASE
os.makedirs(FIG_DIR, exist_ok=True)

# ── 파라미터 ───────────────────────────────────────────────────────────
WALK_SPEED  = 4.5 * 1000 / 3600   # m/s
TIME_BUDGET = 30 * 60             # 초 (30분)
ALPHA       = 0.15

TARGET_HOURS = [7, 10, 13, 16]

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377, 'color': '#E53935', 'line': '2호선/수분당/중앙'},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305, 'color': '#FB8C00', 'line': '5호선'},
    '응봉역':   {'lat': 37.5435, 'lon': 127.0361, 'color': '#8E24AA', 'line': '경의중앙선'},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475, 'color': '#43A047', 'line': '2호선'},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561, 'color': '#1E88E5', 'line': '2호선'},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448, 'color': '#00ACC1', 'line': '수인분당선'},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171, 'color': '#6D4C41', 'line': '3호선/중앙선'},
}


def utci_to_penalty(utci: float) -> int:
    if utci < 26:   return 0
    elif utci < 32: return 1
    elif utci < 38: return 2
    elif utci < 46: return 3
    else:           return 4


def compute_catchment(G, station_node, utci_lookup, hour, alpha):
    for u, v, data in G.edges(data=True):
        data['classic_time'] = data.get('length', 0) / WALK_SPEED

    classic_dist = nx.single_source_dijkstra_path_length(
        G, station_node, cutoff=TIME_BUDGET, weight='classic_time'
    )

    for u, v, data in G.edges(data=True):
        base_time = data.get('length', 0) / WALK_SPEED
        utci = utci_lookup.get((str(u), str(v), hour),
               utci_lookup.get((str(v), str(u), hour), 35.0))
        penalty = utci_to_penalty(utci)
        data['thermal_time'] = base_time * (1 + alpha * penalty)

    thermal_dist = nx.single_source_dijkstra_path_length(
        G, station_node, cutoff=TIME_BUDGET, weight='thermal_time'
    )

    classic_nodes = set(classic_dist.keys())
    thermal_nodes = set(thermal_dist.keys())
    lost_nodes    = classic_nodes - thermal_nodes

    return {
        'classic_nodes': classic_nodes,
        'thermal_nodes': thermal_nodes,
        'lost_nodes':    lost_nodes,
        'classic_count': len(classic_nodes),
        'thermal_count': len(thermal_nodes),
        'lost_count':    len(lost_nodes),
        'reduction_pct': round(len(lost_nodes) / max(len(classic_nodes), 1) * 100, 1),
    }


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

print("UTCI 데이터 로드 중...")
link_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
utci_lookup = {}
for _, row in link_df.iterrows():
    utci_lookup[(str(row['u']), str(row['v']), int(row['hour']))] = row['utci_idw']
    utci_lookup[(str(row['v']), str(row['u']), int(row['hour']))] = row['utci_idw']
print(f"  {len(utci_lookup):,}개 로드 완료")

# 역 노드 탐색
for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])
    print(f"  {name}: 노드 {info['node']}")

# ── 전체 분석 실행 ─────────────────────────────────────────────────────
print("\n전체 역 catchment 계산 중...")
all_results = {}
for station_name, sinfo in STATIONS.items():
    all_results[station_name] = {}
    for hour in TARGET_HOURS:
        G = G_base.copy()
        result = compute_catchment(G, sinfo['node'], utci_lookup, hour, ALPHA)
        all_results[station_name][hour] = result
        print(f"  [{station_name}] {hour:02d}시 | "
              f"Classic {result['classic_count']:,} → Thermal {result['thermal_count']:,} "
              f"(-{result['reduction_pct']}%)")

# ── 시각화 1: 역별 reduction_pct 히트맵 ───────────────────────────────
print("\n히트맵 생성 중...")
station_names = list(STATIONS.keys())
data_matrix = np.array([
    [all_results[s][h]['reduction_pct'] for h in TARGET_HOURS]
    for s in station_names
])

fig, ax = plt.subplots(figsize=(9, 6))
im = ax.imshow(data_matrix, cmap='YlOrRd', aspect='auto', vmin=0, vmax=80)
plt.colorbar(im, ax=ax, label='접근성 감소율 (%)')

ax.set_xticks(range(len(TARGET_HOURS)))
ax.set_xticklabels([f'{h}시' for h in TARGET_HOURS], fontsize=11)
ax.set_yticks(range(len(station_names)))
ax.set_yticklabels(station_names, fontsize=11)

for i, s in enumerate(station_names):
    for j, h in enumerate(TARGET_HOURS):
        val = data_matrix[i, j]
        color = 'white' if val > 45 else 'black'
        ax.text(j, i, f'{val:.1f}%', ha='center', va='center',
                fontsize=10, color=color, fontweight='bold')

ax.set_title(
    f'성동구 전체 지하철역 — 시간대별 도보 접근성 감소율\n'
    f'(Classic vs Thermal Catchment, α={ALPHA}, 30분 시간예산)',
    fontsize=12, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'catchment_heatmap_all_stations.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: catchment_heatmap_all_stations.png")

# ── 시각화 2: 시간대별 감소율 꺾은선 그래프 (역별 색상) ──────────────
fig, ax = plt.subplots(figsize=(10, 6))
for station_name, sinfo in STATIONS.items():
    losses = [all_results[station_name][h]['reduction_pct'] for h in TARGET_HOURS]
    ax.plot(TARGET_HOURS, losses, 'o-', label=f"{station_name} ({sinfo['line']})",
            color=sinfo['color'], linewidth=2, markersize=7)

ax.axhline(0, color='gray', linewidth=0.8, linestyle='--')
ax.set_xlabel('시각 (시)', fontsize=12)
ax.set_ylabel('접근성 감소율 (%)', fontsize=12)
ax.set_title(
    f'성동구 전체 역 시간대별 Catchment 감소율 (α={ALPHA})',
    fontsize=13, fontweight='bold'
)
ax.legend(fontsize=9, loc='upper left')
ax.set_xticks(TARGET_HOURS)
ax.set_xticklabels([f'{h}시' for h in TARGET_HOURS])
ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'catchment_timeseries_all_stations.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: catchment_timeseries_all_stations.png")

# ── 시각화 3: 13시 전체 역 catchment 지도 (멀티패널) ─────────────────
print("\n13시 전체 역 catchment 지도 생성 중...")
n_stations = len(STATIONS)
fig, axes = plt.subplots(2, 4, figsize=(28, 14))
axes_flat = axes.flatten()

def plot_station_catchment(ax, nodes_wm, edges_wm, result, station_node, station_name, hour):
    classic = result['classic_nodes']
    thermal = result['thermal_nodes']

    def etype(idx):
        u, v = idx[0], idx[1]
        if u in thermal and v in thermal: return 'thermal'
        if u in classic  and v in classic: return 'lost'
        return 'outside'

    e = edges_wm.copy()
    e['etype'] = e.index.map(etype)

    e[e['etype'] == 'outside'].plot(ax=ax, color='#cccccc', linewidth=0.3, alpha=0.4, zorder=1)
    e[e['etype'] == 'lost'].plot(ax=ax, color='#EF9A9A', linewidth=1.0, alpha=0.85, zorder=2)
    e[e['etype'] == 'thermal'].plot(ax=ax, color='#2E7D32', linewidth=1.2, alpha=0.9, zorder=3)

    sg = nodes_wm.loc[station_node].geometry
    ax.plot(sg.x, sg.y, '*', color='#FFD600', markersize=16, zorder=8,
            markeredgecolor='black', markeredgewidth=0.6)

    try:
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=14, alpha=0.45)
    except Exception:
        pass

    ax.set_title(
        f"{station_name} | {hour:02d}시\n"
        f"접근 {result['thermal_count']:,}개  상실 {result['lost_count']:,}개 (-{result['reduction_pct']}%)",
        fontsize=9
    )
    ax.set_axis_off()

for ax, (station_name, sinfo) in zip(axes_flat, STATIONS.items()):
    G = G_base.copy()
    result = all_results[station_name][13]
    plot_station_catchment(ax, nodes_wm, edges_wm, result, sinfo['node'], station_name, 13)

# 마지막 빈 칸 숨기기
for i in range(n_stations, len(axes_flat)):
    axes_flat[i].set_visible(False)

handles = [
    mpatches.Patch(color='#2E7D32', label='폭염에도 접근 가능 (Thermal)'),
    mpatches.Patch(color='#EF9A9A', label='접근성 상실 (Lost)'),
    mpatches.Patch(color='#cccccc', label='catchment 외부'),
]
fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=11,
           bbox_to_anchor=(0.5, 0.01))

fig.suptitle(
    '성동구 전체 지하철역 — 폭염(13시) 도보 Catchment 비교\n'
    f'UTCI 기반 열 패널티 (α={ALPHA}) | 시간예산 30분',
    fontsize=15, fontweight='bold'
)
plt.tight_layout(rect=[0, 0.06, 1, 1])
fig.savefig(os.path.join(FIG_DIR, 'catchment_all_stations_13h.png'), dpi=130, bbox_inches='tight')
plt.close()
print("  저장: catchment_all_stations_13h.png")

# ── 결과 저장 ──────────────────────────────────────────────────────────
summary = {'alpha': ALPHA, 'time_budget_min': 30, 'walk_speed_kmh': 4.5}
for station_name in STATIONS:
    summary[station_name] = {
        'line': STATIONS[station_name]['line'],
        'lat':  STATIONS[station_name]['lat'],
        'lon':  STATIONS[station_name]['lon'],
    }
    for hour in TARGET_HOURS:
        r = all_results[station_name][hour]
        summary[station_name][f'h{hour:02d}'] = {
            'classic_nodes': r['classic_count'],
            'thermal_nodes': r['thermal_count'],
            'lost_nodes':    r['lost_count'],
            'reduction_pct': r['reduction_pct'],
        }

out_json = os.path.join(OUT_DIR, 'catchment_all_stations_summary.json')
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"\n결과 저장: {out_json}")

# ── 콘솔 요약 ──────────────────────────────────────────────────────────
print("\n=== 최종 결과 요약 (13시 기준) ===")
print(f"{'역':<8} {'노선':<14} {'Classic':>8} {'Thermal':>8} {'감소율':>8}")
print("-" * 52)
for station_name, sinfo in STATIONS.items():
    r = all_results[station_name][13]
    print(f"{station_name:<8} {sinfo['line']:<14} "
          f"{r['classic_count']:>8,} {r['thermal_count']:>8,} "
          f"-{r['reduction_pct']:>5.1f}%")

# Plan A 종속변수 테이블 저장
rows = []
for station_name, sinfo in STATIONS.items():
    for hour in TARGET_HOURS:
        r = all_results[station_name][hour]
        rows.append({
            'station':       station_name,
            'line':          sinfo['line'],
            'lat':           sinfo['lat'],
            'lon':           sinfo['lon'],
            'hour':          hour,
            'classic_count': r['classic_count'],
            'thermal_count': r['thermal_count'],
            'lost_count':    r['lost_count'],
            'reduction_pct': r['reduction_pct'],
        })

df_out = pd.DataFrame(rows)
csv_path = os.path.join(OUT_DIR, 'catchment_all_stations_table.csv')
df_out.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f"\nPlan A 종속변수 테이블 저장: {csv_path}")
