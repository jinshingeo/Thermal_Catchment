"""
출퇴근 시간대 Thermal Catchment 분석 (Method 3 — S-DoT IDW + SOLWEIG)
=======================================================================
분석 시간대:
  09시 — 출근 시간대 (UTCI 38°C 초과율 ~4%)
  13시 — 폭염 피크   (UTCI 38°C 초과율 ~99.8%) → "피크 보행 불가" 발견
  18시 — 퇴근 시간대 (UTCI 38°C 초과율 ~24%)

입력:
  link_utci_sdot_solweig.csv — S-DoT 57개 IDW 보간 기상 + SOLWEIG MRT → utci_m3
  seongdong_walk_network.graphml

방법:
  utci_m3 ≥ 38°C → 링크 제거 (Hard Cut)
  임계값 근거: Bröde et al. (2012) "very strong heat stress" 진입점
  Classic(전체) vs Thermal(열 링크 제거) 캐치먼트 비교
  reduction_pct = (Classic - Thermal) / Classic × 100
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
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

STP_BASE  = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH  = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
UTCI_PATH = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
OUT_JSON  = os.path.join(RES_DIR, 'catchment_commute_summary.json')

WALK_SPEED  = 4.5 * 1000 / 3600  # m/s
TIME_BUDGET = 15 * 60             # 900초
THRESHOLD   = 38.0                # Bröde et al. (2012)
UTCI_COL    = 'utci_m3'

TARGET_HOURS = [9, 13, 18]
HOUR_LABELS  = {9: '출근(09시)', 13: '피크(13시)', 18: '퇴근(18시)'}

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377, 'color': '#E53935'},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305, 'color': '#FB8C00'},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353, 'color': '#8E24AA'},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475, 'color': '#43A047'},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561, 'color': '#1E88E5'},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448, 'color': '#00ACC1'},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171, 'color': '#6D4C41'},
}


def compute_catchment(G, station_node, hot_edges_set):
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
        'classic_nodes':     classic_nodes,
        'thermal_nodes':     thermal_nodes,
        'lost_nodes':        lost_nodes,
        'classic_count':     len(classic_nodes),
        'thermal_count':     len(thermal_nodes),
        'lost_count':        len(lost_nodes),
        'reduction_pct':     round(len(lost_nodes) / max(len(classic_nodes), 1) * 100, 1),
        'hot_edges_removed': len(edges_to_remove),
    }


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

print("S-DoT IDW + SOLWEIG UTCI 데이터 로드 중...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
print(f"  {len(utci_df):,}행 로드 | 컬럼: {list(utci_df.columns)}")

# 시간대별 초과율 확인
print("\n시간대별 UTCI 초과율:")
for h in TARGET_HOURS:
    h_all = utci_df[utci_df['hour'] == h]
    h_hot = h_all[h_all[UTCI_COL] >= THRESHOLD]
    pct = len(h_hot) / len(h_all) * 100
    print(f"  {h:02d}시: 평균 {h_all[UTCI_COL].mean():.1f}°C | "
          f"38°C 초과 {len(h_hot):,}/{len(h_all):,} ({pct:.1f}%) — {HOUR_LABELS[h]}")

# Hot edges set 구성
hot_edges_by_hour = {}
for h in TARGET_HOURS:
    h_df = utci_df[(utci_df['hour'] == h) & (utci_df[UTCI_COL] >= THRESHOLD)]
    hot_edges_by_hour[h] = set(zip(h_df['u'].astype(str), h_df['v'].astype(str)))

# 역 노드 탐색
for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])


# ── 분석 실행 ──────────────────────────────────────────────────────────
print("\n=== Thermal Catchment 계산 (출퇴근 3시간대) ===")
all_results = {}
for station_name, sinfo in STATIONS.items():
    all_results[station_name] = {}
    for h in TARGET_HOURS:
        G = G_base.copy()
        result = compute_catchment(G, sinfo['node'], hot_edges_by_hour[h])
        all_results[station_name][h] = result
        print(f"  [{station_name}] {h:02d}시 | "
              f"Classic {result['classic_count']:,} → Thermal {result['thermal_count']:,} "
              f"(-{result['reduction_pct']}%) | 제거링크 {result['hot_edges_removed']:,}개")


# ── 시각화 1: 히트맵 (역 × 시간대) ──────────────────────────────────
station_names = list(STATIONS.keys())
data_matrix = np.array([
    [all_results[s][h]['reduction_pct'] for h in TARGET_HOURS]
    for s in station_names
])

fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(data_matrix, cmap='YlOrRd', aspect='auto', vmin=0, vmax=100)
plt.colorbar(im, ax=ax, label='접근성 감소율 (%)')
ax.set_xticks(range(len(TARGET_HOURS)))
ax.set_xticklabels([HOUR_LABELS[h] for h in TARGET_HOURS], fontsize=11)
ax.set_yticks(range(len(station_names)))
ax.set_yticklabels(station_names, fontsize=11)
for i, s in enumerate(station_names):
    for j, h in enumerate(TARGET_HOURS):
        val = data_matrix[i, j]
        ax.text(j, i, f'{val:.1f}%', ha='center', va='center',
                fontsize=10, color='white' if val > 50 else 'black', fontweight='bold')
ax.set_title(
    '성동구 역별 Thermal Catchment 감소율\n'
    f'Method 3 (S-DoT IDW + SOLWEIG) | UTCI ≥ {THRESHOLD}°C 링크 제거\n'
    '폭염일 기준 (2025.07.28~08.03)',
    fontsize=11, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'catchment_commute_heatmap.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\n저장: catchment_commute_heatmap.png")


# ── 시각화 2: 시간대별 바차트 ──────────────────────────────────────
colors = ['#4CAF50', '#F44336', '#2196F3']  # 9시=초록, 13시=빨강, 18시=파랑
x = np.arange(len(station_names))
width = 0.25

fig, ax = plt.subplots(figsize=(13, 6))
for j, (h, col) in enumerate(zip(TARGET_HOURS, colors)):
    vals = [all_results[s][h]['reduction_pct'] for s in station_names]
    bars = ax.bar(x + (j - 1) * width, vals, width, label=HOUR_LABELS[h],
                  color=col, alpha=0.85, edgecolor='gray', linewidth=0.5)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                f'{v:.1f}%', ha='center', va='bottom', fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(station_names, fontsize=11)
ax.set_ylabel('접근성 감소율 (%)', fontsize=11)
ax.set_ylim(0, 110)
ax.axhline(100, color='black', linewidth=0.8, linestyle='--', alpha=0.4, label='100% (완전 상실)')
ax.set_title(
    '시간대별 Thermal Catchment 감소율 비교\n'
    f'Method 3 | UTCI ≥ {THRESHOLD}°C Hard Cut | 폭염일 기준',
    fontsize=12, fontweight='bold'
)
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'catchment_commute_barchart.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: catchment_commute_barchart.png")


# ── 시각화 3: 9시·18시 캐치먼트 지도 (2행 × 7열) ─────────────────
for target_hour in [9, 18]:
    fig, axes = plt.subplots(1, 7, figsize=(28, 5))
    for ax, (station_name, sinfo) in zip(axes, STATIONS.items()):
        result = all_results[station_name][target_hour]
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
            f"{station_name}\n"
            f"접근 {result['thermal_count']:,} / 상실 {result['lost_count']:,}\n"
            f"감소 {result['reduction_pct']}%",
            fontsize=8
        )
        ax.set_axis_off()

    handles = [
        mpatches.Patch(color='#2E7D32', label='접근 가능'),
        mpatches.Patch(color='#EF9A9A', label='접근성 상실'),
        mpatches.Patch(color='#cccccc', label='캐치먼트 외부'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=10, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle(
        f'성동구 Thermal Catchment — {HOUR_LABELS[target_hour]}\n'
        f'Method 3 (S-DoT IDW + SOLWEIG) | UTCI ≥ {THRESHOLD}°C 링크 제거 | 폭염일 기준',
        fontsize=13, fontweight='bold'
    )
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    fname = f'catchment_commute_{target_hour:02d}h_map.png'
    fig.savefig(os.path.join(FIG_DIR, fname), dpi=130, bbox_inches='tight')
    plt.close()
    print(f"저장: {fname}")


# ── 결과 저장 ────────────────────────────────────────────────────────
summary = {
    'model':          'commute_hours_hard_cut',
    'method':         'Method 3 — S-DoT IDW 보간 기상 + SOLWEIG MRT → UTCI',
    'utci_source':    'link_utci_sdot_solweig.csv (utci_m3)',
    'utci_column':    UTCI_COL,
    'threshold_utci': THRESHOLD,
    'threshold_ref':  'Bröde et al. (2012) — very strong heat stress 진입점',
    'time_budget_min': 15,
    'walk_speed_kmh':  4.5,
    'weather_period':  '2025-07-28 ~ 2025-08-03 (폭염일 7일)',
    'analysis_hours':  TARGET_HOURS,
    'exceedance_pct':  {},
}

for h in TARGET_HOURS:
    h_all = utci_df[utci_df['hour'] == h]
    h_hot = h_all[h_all[UTCI_COL] >= THRESHOLD]
    summary['exceedance_pct'][str(h)] = round(len(h_hot) / len(h_all) * 100, 1)

for station_name in STATIONS:
    summary[station_name] = {}
    for h in TARGET_HOURS:
        r = all_results[station_name][h]
        summary[station_name][f'h{h:02d}'] = {
            'label':             HOUR_LABELS[h],
            'classic_nodes':     r['classic_count'],
            'thermal_nodes':     r['thermal_count'],
            'lost_count':        r['lost_count'],
            'reduction_pct':     r['reduction_pct'],
            'hot_edges_removed': r['hot_edges_removed'],
        }

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"\n결과 저장: {OUT_JSON}")

print("\n=== 완료 ===")
print("생성 파일:")
print("  catchment_commute_heatmap.png   — 역×시간대 히트맵")
print("  catchment_commute_barchart.png  — 시간대 비교 바차트")
print("  catchment_commute_09h_map.png   — 출근 시간대 캐치먼트 지도")
print("  catchment_commute_18h_map.png   — 퇴근 시간대 캐치먼트 지도")
print("  catchment_commute_summary.json  — 수치 결과")
