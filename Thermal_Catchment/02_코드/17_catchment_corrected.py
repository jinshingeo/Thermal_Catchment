"""
SVF 보정 UTCI 기반 Thermal Catchment 분석
==========================================
기존 catchment와의 차이:
  - 속도 패널티(×계수) 대신 링크 제거(hard cut) 방식
  - 임계값 이상인 링크를 그래프에서 물리적으로 제거
  - 사람이 "이 길은 너무 더워서 돌아간다" → 우회로가 없거나 너무 길면 접근 불가

  UTCI_corrected ≥ THRESHOLD → 링크 제거
  Classic: 전체 그래프, 단순 이동시간
  Thermal: 뜨거운 링크 제거 후 그래프, 단순 이동시간
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
import contextily as ctx
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
STP_BASE   = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH   = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
UTCI_PATH  = os.path.join(RES_DIR, 'link_utci_corrected.csv')
FIG_DIR    = os.path.join(RES_DIR, 'figures')
OUT_DIR    = BASE
os.makedirs(FIG_DIR, exist_ok=True)

WALK_SPEED   = 4.5 * 1000 / 3600
TIME_BUDGET  = 15 * 60
THRESHOLD    = 38.0   # °C — 강한 열스트레스 이상 링크 회피 (UTCI 국제 카테고리)

TARGET_HOURS = [7, 10, 13, 16]

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377, 'color': '#E53935', 'line': '2호선/수분당/중앙'},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305, 'color': '#FB8C00', 'line': '5호선'},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353, 'color': '#8E24AA', 'line': '경의중앙선'},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475, 'color': '#43A047', 'line': '2호선'},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561, 'color': '#1E88E5', 'line': '2호선'},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448, 'color': '#00ACC1', 'line': '수인분당선'},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171, 'color': '#6D4C41', 'line': '3호선/중앙선'},
}


def compute_catchment_corrected(G, station_node, hot_edges_set, hour):
    """
    Classic catchment: 전체 그래프, 이동시간만
    Thermal catchment: UTCI_corrected ≥ THRESHOLD 링크 제거 후 Dijkstra
    """
    # Classic
    for u, v, data in G.edges(data=True):
        data['travel_time'] = data.get('length', 0) / WALK_SPEED

    classic_dist = nx.single_source_dijkstra_path_length(
        G, station_node, cutoff=TIME_BUDGET, weight='travel_time'
    )

    # Thermal: 뜨거운 링크 제거
    G_thermal = G.copy()
    edges_to_remove = [
        (u, v) for u, v in G_thermal.edges()
        if (str(u), str(v), hour) in hot_edges_set or (str(v), str(u), hour) in hot_edges_set
    ]
    G_thermal.remove_edges_from(edges_to_remove)

    thermal_dist = nx.single_source_dijkstra_path_length(
        G_thermal, station_node, cutoff=TIME_BUDGET, weight='travel_time'
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
        'hot_edges_removed': len(edges_to_remove),
    }


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

print("보정 UTCI 로드 중...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
print(f"  {len(utci_df):,}행 로드 완료")

# 시간대별 hot edges set 미리 구성 (빠른 조회)
hot_edges_by_hour = {}
for hour in TARGET_HOURS:
    h_df = utci_df[(utci_df['hour'] == hour) & (utci_df['utci_corrected'] >= THRESHOLD)]
    hot_edges_by_hour[hour] = set(zip(h_df['u'].astype(str), h_df['v'].astype(str), h_df['hour']))
    print(f"  {hour:02d}시 제거 대상 링크: {len(h_df):,}개 / 전체 {len(utci_df[utci_df['hour']==hour]):,}개 "
          f"({len(h_df)/len(utci_df[utci_df['hour']==hour])*100:.1f}%)")

# 역 노드 탐색
for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])

# ── 분석 실행 ──────────────────────────────────────────────────────────
print("\n=== 보정 UTCI 기반 캐치먼트 계산 ===")
all_results = {}
for station_name, sinfo in STATIONS.items():
    all_results[station_name] = {}
    for hour in TARGET_HOURS:
        G = G_base.copy()
        result = compute_catchment_corrected(G, sinfo['node'], hot_edges_by_hour[hour], hour)
        all_results[station_name][hour] = result
        print(f"  [{station_name}] {hour:02d}시 | "
              f"Classic {result['classic_count']:,} → Thermal {result['thermal_count']:,} "
              f"(-{result['reduction_pct']}%) | 제거링크 {result['hot_edges_removed']:,}개")

# ── 시각화 1: 히트맵 ───────────────────────────────────────────────────
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
        ax.text(j, i, f'{val:.1f}%', ha='center', va='center',
                fontsize=10, color='white' if val > 45 else 'black', fontweight='bold')
ax.set_title(
    f'성동구 역별 도보 접근성 감소율 (SVF 보정 UTCI 기반)\n'
    f'링크 회피 모델: UTCI_corrected ≥ {THRESHOLD}°C 링크 제거, 15분 시간예산',
    fontsize=11, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'catchment_corrected_heatmap.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\n저장: figures/catchment_corrected_heatmap.png")

# ── 시각화 2: 기존 vs 보정 비교 (13시) ───────────────────────────────
# 기존 결과 로드
old_json_path = os.path.join(OUT_DIR, 'catchment_all_stations_summary.json')
with open(old_json_path, encoding='utf-8') as f:
    old_summary = json.load(f)

station_list  = list(STATIONS.keys())
old_vals = [old_summary[s]['h13']['reduction_pct'] for s in station_list]
new_vals = [all_results[s][13]['reduction_pct'] for s in station_list]

x = np.arange(len(station_list))
width = 0.35
fig, ax = plt.subplots(figsize=(12, 6))
bars1 = ax.bar(x - width/2, old_vals, width, label='기존 (UTCI_idw + 속도패널티)', color='#EF9A9A', edgecolor='gray')
bars2 = ax.bar(x + width/2, new_vals, width, label='보정 (SVF 보정 UTCI + 링크회피)', color='#42A5F5', edgecolor='gray')

for bar, v in zip(bars1, old_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{v:.1f}%', ha='center', va='bottom', fontsize=8)
for bar, v in zip(bars2, new_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{v:.1f}%', ha='center', va='bottom', fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(station_list, fontsize=11)
ax.set_ylabel('접근성 감소율 (%)', fontsize=11)
ax.set_title(
    '기존 모델 vs SVF 보정 모델 — 13시 접근성 감소율 비교\n'
    f'(SVF 보정: 그늘진 도로는 UTCI 최대 8°C 감소 반영)',
    fontsize=11, fontweight='bold'
)
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'catchment_corrected_vs_old.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: figures/catchment_corrected_vs_old.png")

# ── 시각화 3: 13시 캐치먼트 지도 (멀티패널) ──────────────────────────
print("\n13시 캐치먼트 지도 생성 중...")
fig, axes = plt.subplots(2, 4, figsize=(28, 14))
axes_flat = axes.flatten()

for ax, (station_name, sinfo) in zip(axes_flat, STATIONS.items()):
    result = all_results[station_name][13]
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

    sg = nodes_wm.loc[sinfo['node']].geometry
    ax.plot(sg.x, sg.y, 'o', color='#FFD600', markersize=10, zorder=8,
            markeredgecolor='black', markeredgewidth=1.5)
    try:
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=14, alpha=0.45)
    except Exception:
        pass
    ax.set_title(
        f"{station_name} | 13시\n"
        f"접근 {result['thermal_count']:,}  상실 {result['lost_count']:,} (-{result['reduction_pct']}%)",
        fontsize=9
    )
    ax.set_axis_off()

for i in range(len(STATIONS), len(axes_flat)):
    axes_flat[i].set_visible(False)

handles = [
    mpatches.Patch(color='#2E7D32', label='접근 가능 (UTCI_corrected < 38°C)'),
    mpatches.Patch(color='#EF9A9A', label='접근성 상실 (우회 불가 또는 우회 시 시간 초과)'),
    mpatches.Patch(color='#cccccc', label='캐치먼트 외부'),
]
fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=11, bbox_to_anchor=(0.5, 0.01))
fig.suptitle(
    '성동구 전체 역 — SVF 보정 UTCI 기반 Thermal Catchment (13시)\n'
    f'링크 회피 모델: UTCI_corrected ≥ {THRESHOLD}°C 링크 제거 | 시간예산 15분',
    fontsize=14, fontweight='bold'
)
plt.tight_layout(rect=[0, 0.06, 1, 1])
fig.savefig(os.path.join(FIG_DIR, 'catchment_corrected_13h.png'), dpi=130, bbox_inches='tight')
plt.close()
print("저장: figures/catchment_corrected_13h.png")

# ── 결과 저장 ──────────────────────────────────────────────────────────
summary = {'model': 'svf_corrected_hard_cut', 'threshold_utci': THRESHOLD,
           'time_budget_min': 15, 'walk_speed_kmh': 4.5}
for station_name in STATIONS:
    summary[station_name] = {'line': STATIONS[station_name]['line']}
    for hour in TARGET_HOURS:
        r = all_results[station_name][hour]
        summary[station_name][f'h{hour:02d}'] = {
            'classic_nodes': r['classic_count'],
            'thermal_nodes': r['thermal_count'],
            'lost_count':    r['lost_count'],
            'reduction_pct': r['reduction_pct'],
            'hot_edges_removed': r['hot_edges_removed'],
        }

out_json = os.path.join(OUT_DIR, 'catchment_corrected_summary.json')
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

# ── 콘솔 최종 비교 ─────────────────────────────────────────────────────
print("\n=== 최종 결과: 기존 모델 vs SVF 보정 모델 (13시) ===")
print(f"{'역':<8} {'기존':>8} {'보정후':>8} {'차이':>8}")
print("-" * 36)
for s in station_list:
    old = old_summary[s]['h13']['reduction_pct']
    new = all_results[s][13]['reduction_pct']
    print(f"{s:<8} {old:>6.1f}%  {new:>6.1f}%  {new-old:>+6.1f}%p")
print(f"\n결과 저장: {out_json}")
