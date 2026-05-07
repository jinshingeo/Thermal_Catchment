"""
3시간대 × 7역 Thermal Catchment 그리드 지도
=============================================
Method 4 (MRT ≥ 55°C Hard Cut) | 9시·13시·18시
3행(시간대) × 7열(역) 단일 플롯
"""

import os
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
MRT_PATH  = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
MRT_THRESH  = 55.0   # 교수님 논의 전 잠정값
TARGET_HOURS = [9, 13, 18]
HOUR_LABELS  = {9: '출근 (09시)', 13: '피크 (13시)', 18: '퇴근 (18시)'}

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171},
}


def compute_catchment(G_base, station_node, hot_edges_set):
    for u, v, data in G_base.edges(data=True):
        data['travel_time'] = data.get('length', 0) / WALK_SPEED

    classic_dist = nx.single_source_dijkstra_path_length(
        G_base, station_node, cutoff=TIME_BUDGET, weight='travel_time'
    )
    G_thermal = G_base.copy()
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

    classic_length = sum(
        data.get('length', 0)
        for u, v, data in G_base.edges(data=True)
        if u in classic_nodes and v in classic_nodes
    )
    thermal_length = sum(
        data.get('length', 0)
        for u, v, data in G_base.edges(data=True)
        if u in thermal_nodes and v in thermal_nodes
    )

    return {
        'classic_nodes':     classic_nodes,
        'thermal_nodes':     thermal_nodes,
        'classic_length_m':  classic_length,
        'thermal_length_m':  thermal_length,
        'reduction_pct_len': round((classic_length - thermal_length) / max(classic_length, 1) * 100, 1),
    }


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

print("MRT 데이터 로드 중...")
mrt_df = pd.read_csv(MRT_PATH, encoding='utf-8-sig')

for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])

# ── 캐치먼트 계산 ─────────────────────────────────────────────────────
print(f"\nMRT ≥ {MRT_THRESH}°C Hard Cut | 9시·13시·18시")
hot_by_hour = {}
for h in TARGET_HOURS:
    h_df = mrt_df[(mrt_df['hour'] == h) & (mrt_df['mrt'] >= MRT_THRESH)]
    hot_by_hour[h] = set(zip(h_df['u'].astype(str), h_df['v'].astype(str)))
    total = len(mrt_df[mrt_df['hour'] == h])
    print(f"  {h:02d}시 제거 링크: {len(h_df):,}/{total:,} ({len(h_df)/total*100:.1f}%)")

results = {}
for station_name, sinfo in STATIONS.items():
    results[station_name] = {}
    for h in TARGET_HOURS:
        G = G_base.copy()
        results[station_name][h] = compute_catchment(G, sinfo['node'], hot_by_hour[h])
        r = results[station_name][h]
        print(f"  [{station_name}] {h:02d}시 | "
              f"{r['classic_length_m']/1000:.1f}km → {r['thermal_length_m']/1000:.1f}km "
              f"(-{r['reduction_pct_len']}%)")


# ── 3행 × 7열 그리드 지도 ─────────────────────────────────────────────
print("\n그리드 지도 생성 중...")
station_names = list(STATIONS.keys())
n_rows = len(TARGET_HOURS)
n_cols = len(station_names)

fig, axes = plt.subplots(n_rows, n_cols, figsize=(28, 13))

for row_idx, h in enumerate(TARGET_HOURS):
    for col_idx, station_name in enumerate(station_names):
        ax = axes[row_idx][col_idx]
        sinfo  = STATIONS[station_name]
        result = results[station_name][h]

        classic = result['classic_nodes']
        thermal = result['thermal_nodes']

        def etype(idx):
            u, v = idx[0], idx[1]
            if u in thermal and v in thermal: return 'thermal'
            if u in classic  and v in classic: return 'lost'
            return 'outside'

        e = edges_wm.copy()
        e['etype'] = e.index.map(etype)

        e[e['etype'] == 'outside'].plot(
            ax=ax, color='#cccccc', linewidth=0.3, alpha=0.35, zorder=1)
        e[e['etype'] == 'lost'].plot(
            ax=ax, color='#E53935', linewidth=1.2, alpha=0.85, zorder=2)
        e[e['etype'] == 'thermal'].plot(
            ax=ax, color='#2E7D32', linewidth=1.2, alpha=0.9, zorder=3)

        sg = nodes_wm.loc[sinfo['node']].geometry
        ax.plot(sg.x, sg.y, '*', color='#FFD600', markersize=11, zorder=9,
                markeredgecolor='black', markeredgewidth=1.0)

        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                            zoom=14, alpha=0.35)
        except Exception:
            pass

        # 열 제목 (역 이름) — 첫 번째 행만
        if row_idx == 0:
            ax.set_title(station_name, fontsize=11, fontweight='bold', pad=4)

        # 감소율 텍스트
        red = result['reduction_pct_len']
        color = '#B71C1C' if red >= 70 else '#E65100' if red >= 40 else '#1B5E20'
        ax.text(0.5, 0.04, f'-{red:.1f}%',
                transform=ax.transAxes, ha='center', va='bottom',
                fontsize=10, fontweight='bold', color=color,
                bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.75, ec='none'))

        ax.set_axis_off()

    # 행 레이블 (시간대) — 왼쪽 첫 번째 열
    axes[row_idx][0].set_ylabel(HOUR_LABELS[h], fontsize=12, fontweight='bold',
                                 rotation=90, labelpad=6)
    axes[row_idx][0].yaxis.set_visible(True)
    axes[row_idx][0].tick_params(left=False, labelleft=False)

# 범례
handles = [
    mpatches.Patch(color='#2E7D32', label='접근 가능'),
    mpatches.Patch(color='#E53935', label='접근성 상실'),
    mpatches.Patch(color='#cccccc', label='캐치먼트 외부'),
    plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='#FFD600',
               markeredgecolor='black', markersize=11, label='역'),
]
fig.legend(handles=handles, loc='lower center', ncol=4,
           fontsize=11, bbox_to_anchor=(0.5, 0.01), framealpha=0.9)

fig.suptitle(
    f'성동구 역세권 Thermal Catchment — Method 4 (MRT ≥ {MRT_THRESH}°C Hard Cut)\n'
    'S-DoT IDW + SOLWEIG | 15분 도보 | 폭염일 기준 (2025.07.28~08.03)',
    fontsize=13, fontweight='bold', y=0.99
)

plt.tight_layout(rect=[0, 0.06, 1, 0.97])
out_path = os.path.join(FIG_DIR, 'catchment_grid_3h_7s.png')
fig.savefig(out_path, dpi=140, bbox_inches='tight')
plt.close()
print(f"\n저장: {out_path}")
