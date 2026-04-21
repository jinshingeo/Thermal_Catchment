"""
SOLWEIG 기반 Thermal Catchment 분석
=====================================
19번(SOLWEIG UTCI)을 기반으로 캐치먼트 계산
기존 17번(IDW+SVF 보정) 결과와 비교

입력:
  link_utci_solweig.csv   — 19_solweig_utci.py 산출 (Open-Meteo + SVF 기반 MRT)
  seongdong_walk_network  — OSM 보행 네트워크

방법:
  UTCI_final ≥ 38°C → 링크 제거 (hard cut)
  Classic:  전체 그래프, 15분 이동
  Thermal:  뜨거운 링크 제거 후 15분 이동
  PPA 감소율 = (Classic - Thermal) / Classic × 100
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
STP_BASE  = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH  = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
UTCI_PATH = os.path.join(RES_DIR, 'link_utci_solweig.csv')
REF_PATH  = os.path.join(RES_DIR, 'catchment_corrected_summary.json')   # 17번 결과
FIG_DIR   = os.path.join(RES_DIR, 'figures')
OUT_DIR   = BASE
os.makedirs(FIG_DIR, exist_ok=True)

WALK_SPEED  = 4.5 * 1000 / 3600   # m/s
TIME_BUDGET = 15 * 60              # 900초 (Moreno et al. 2021)
THRESHOLD   = 38.0                 # °C (Bröde et al. 2012 "very strong heat stress")

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


def compute_catchment(G, station_node, hot_edges_set):
    """Classic vs Thermal 캐치먼트 계산"""
    for u, v, data in G.edges(data=True):
        data['travel_time'] = data.get('length', 0) / WALK_SPEED

    classic_dist = nx.single_source_dijkstra_path_length(
        G, station_node, cutoff=TIME_BUDGET, weight='travel_time'
    )

    G_thermal = G.copy()
    edges_to_remove = [
        (u, v) for u, v in G_thermal.edges()
        if (str(u), str(v)) in hot_edges_set or (str(v), str(u)) in hot_edges_set
    ]
    G_thermal.remove_edges_from(edges_to_remove)

    thermal_dist = nx.single_source_dijkstra_path_length(
        G_thermal, station_node, cutoff=TIME_BUDGET, weight='travel_time'
    )

    classic_nodes = set(classic_dist.keys())
    thermal_nodes = set(thermal_dist.keys())
    lost_nodes    = classic_nodes - thermal_nodes

    return {
        'classic_nodes':    classic_nodes,
        'thermal_nodes':    thermal_nodes,
        'lost_nodes':       lost_nodes,
        'classic_count':    len(classic_nodes),
        'thermal_count':    len(thermal_nodes),
        'lost_count':       len(lost_nodes),
        'reduction_pct':    round(len(lost_nodes) / max(len(classic_nodes), 1) * 100, 1),
        'hot_edges_removed':len(edges_to_remove),
    }


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

print("SOLWEIG UTCI 데이터 로드 중...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
print(f"  {len(utci_df):,}행 로드 완료 | utci_final 평균: {utci_df['utci_final'].mean():.1f}°C")

# 시간대별 hot edges set 구성 (u,v 튜플 → set)
hot_edges_by_hour = {}
for hour in TARGET_HOURS:
    h_df = utci_df[(utci_df['hour'] == hour) & (utci_df['utci_final'] >= THRESHOLD)]
    hot_edges_by_hour[hour] = set(zip(h_df['u'].astype(str), h_df['v'].astype(str)))
    total = len(utci_df[utci_df['hour'] == hour])
    print(f"  {hour:02d}시 제거 대상: {len(h_df):,}개 / 전체 {total:,}개 ({len(h_df)/total*100:.1f}%)")

# 역 노드 탐색
for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])


# ── 분석 실행 ──────────────────────────────────────────────────────────
print("\n=== SOLWEIG 기반 Thermal Catchment 계산 ===")
all_results = {}
for station_name, sinfo in STATIONS.items():
    all_results[station_name] = {}
    for hour in TARGET_HOURS:
        G = G_base.copy()
        result = compute_catchment(G, sinfo['node'], hot_edges_by_hour[hour])
        all_results[station_name][hour] = result
        print(f"  [{station_name}] {hour:02d}시 | "
              f"Classic {result['classic_count']:,} → Thermal {result['thermal_count']:,} "
              f"(-{result['reduction_pct']}%) | 제거링크 {result['hot_edges_removed']:,}개")


# ── 시각화 1: 히트맵 ──────────────────────────────────────────────────
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
    f'성동구 역별 도보 접근성 감소율 (SOLWEIG 기반 UTCI)\n'
    f'링크 회피 모델: UTCI_final ≥ {THRESHOLD}°C 링크 제거 | 15분 시간예산 | 2025.07.28~08.03',
    fontsize=11, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'catchment_solweig_heatmap.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\n저장: figures/catchment_solweig_heatmap.png")


# ── 시각화 2: IDW+SVF 보정(17번) vs SOLWEIG(20번) 비교 ──────────────
ref_summary = None
if os.path.exists(REF_PATH):
    with open(REF_PATH, encoding='utf-8') as f:
        ref_summary = json.load(f)

if ref_summary:
    ref_vals = [ref_summary[s]['h13']['reduction_pct'] for s in station_names]
    new_vals = [all_results[s][13]['reduction_pct'] for s in station_names]

    x = np.arange(len(station_names))
    w = 0.35
    fig, ax = plt.subplots(figsize=(12, 6))
    b1 = ax.bar(x - w/2, ref_vals, w, label='IDW+SVF 보정 (16~17번)', color='#42A5F5', edgecolor='gray')
    b2 = ax.bar(x + w/2, new_vals, w, label='SOLWEIG 기반 (19~20번)', color='#EF6C00', edgecolor='gray')
    for bar, v in zip(b1, ref_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{v:.1f}%', ha='center', va='bottom', fontsize=8)
    for bar, v in zip(b2, new_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{v:.1f}%', ha='center', va='bottom', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(station_names, fontsize=11)
    ax.set_ylabel('접근성 감소율 (%)', fontsize=11)
    ax.set_title(
        'IDW+SVF 보정 vs SOLWEIG 기반 — 13시 접근성 감소율 비교\n'
        f'UTCI_final ≥ {THRESHOLD}°C 링크 회피 | 시간예산 15분',
        fontsize=11, fontweight='bold'
    )
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'catchment_solweig_vs_idwsvf.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("저장: figures/catchment_solweig_vs_idwsvf.png")


# ── 시각화 3: 13시 캐치먼트 지도 ────────────────────────────────────
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
    mpatches.Patch(color='#2E7D32', label='접근 가능 (UTCI_final < 38°C)'),
    mpatches.Patch(color='#EF9A9A', label='접근성 상실 (우회 불가 또는 초과)'),
    mpatches.Patch(color='#cccccc', label='캐치먼트 외부'),
]
fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=11, bbox_to_anchor=(0.5, 0.01))
fig.suptitle(
    '성동구 전체 역 — SOLWEIG 기반 Thermal Catchment (13시)\n'
    f'Open-Meteo 기상 + SVF 기반 MRT → UTCI_final ≥ {THRESHOLD}°C 링크 제거 | 시간예산 15분',
    fontsize=14, fontweight='bold'
)
plt.tight_layout(rect=[0, 0.06, 1, 1])
fig.savefig(os.path.join(FIG_DIR, 'catchment_solweig_13h.png'), dpi=130, bbox_inches='tight')
plt.close()
print("저장: figures/catchment_solweig_13h.png")


# ── 결과 저장 ────────────────────────────────────────────────────────
summary = {
    'model':            'solweig_hard_cut',
    'utci_source':      'open-meteo + svf mrt (Lindberg 2008)',
    'weather_period':   '2025-07-28 ~ 2025-08-03 (7일 평균)',
    'threshold_utci':   THRESHOLD,
    'time_budget_min':  15,
    'walk_speed_kmh':   4.5,
}
for station_name in STATIONS:
    summary[station_name] = {'line': STATIONS[station_name]['line']}
    for hour in TARGET_HOURS:
        r = all_results[station_name][hour]
        summary[station_name][f'h{hour:02d}'] = {
            'classic_nodes':    r['classic_count'],
            'thermal_nodes':    r['thermal_count'],
            'lost_count':       r['lost_count'],
            'reduction_pct':    r['reduction_pct'],
            'hot_edges_removed':r['hot_edges_removed'],
        }

out_json = os.path.join(OUT_DIR, 'catchment_solweig_summary.json')
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

# ── 최종 비교 출력 ───────────────────────────────────────────────────
print("\n=== 최종 결과: IDW+SVF vs SOLWEIG (13시) ===")
print(f"{'역':<8} {'IDW+SVF':>8} {'SOLWEIG':>8} {'차이':>8}")
print("-" * 38)
for s in station_names:
    sol = all_results[s][13]['reduction_pct']
    if ref_summary:
        idw = ref_summary[s]['h13']['reduction_pct']
        print(f"{s:<8} {idw:>6.1f}%   {sol:>6.1f}%  {sol-idw:>+6.1f}%p")
    else:
        print(f"{s:<8}   ---     {sol:>6.1f}%")

print(f"\n결과 저장: {out_json}")
print("시각화: catchment_solweig_heatmap.png / _vs_idwsvf.png / _13h.png")
