"""
3시간대 × 7역 캐치먼트 지도 — 대중교통 정류장 오버레이 버전
=============================================================
Method 4 (MRT ≥ 55°C Hard Cut) | 9시·13시·18시
각 셀: 도로 네트워크(접근가능/상실/외부) + 정류장 점(접근가능/상실)
저장: Thermal_Catchment/03_결과물/figures/catchment_stops_grid_3h_7s.png
"""

import os
import numpy as np
import pandas as pd
import networkx as nx
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import contextily as ctx
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH   = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
MRT_PATH   = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
STOPS_CSV  = os.path.join(DATA_DIR, '네트워크', 'transit_stops_seongdong.csv')

WALK_SPEED   = 4.5 * 1000 / 3600
TIME_BUDGET  = 15 * 60
MRT_THRESH   = 55.0
TARGET_HOURS = [9, 13, 18]
HOUR_LABELS  = {9: '09시 (출근)', 13: '13시 (피크)', 18: '18시 (퇴근)'}

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171},
}

MRT_MAX = {9: 48.6, 13: 66.0, 18: 46.7}   # 사전 확인값


def build_thermal_graph(G_base, hot_edges_set):
    G_t = G_base.copy()
    G_t.remove_edges_from([
        (u, v) for u, v in G_t.edges()
        if (str(u), str(v)) in hot_edges_set or (str(v), str(u)) in hot_edges_set
    ])
    return G_t


def get_catchment(G, origin_node):
    dist = nx.single_source_dijkstra_path_length(
        G, origin_node, cutoff=TIME_BUDGET, weight='travel_time'
    )
    return set(dist.keys())


# ── 데이터 로드 ────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
for u, v, data in G_base.edges(data=True):
    data['travel_time'] = data.get('length', 0) / WALK_SPEED

nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

print("MRT 데이터 로드 중...")
mrt_df = pd.read_csv(MRT_PATH, encoding='utf-8-sig')

print("대중교통 정류장 로드 중...")
stops_df = pd.read_csv(STOPS_CSV, encoding='utf-8-sig')
stops_gdf = gpd.GeoDataFrame(
    stops_df,
    geometry=gpd.points_from_xy(stops_df['lon'], stops_df['lat']),
    crs='EPSG:4326'
).to_crs(epsg=3857)
stops_gdf['net_node'] = stops_gdf['node_id'].astype(int)
print(f"  정류장: 지하철={len(stops_gdf[stops_gdf['stop_type']=='subway'])}, 버스={len(stops_gdf[stops_gdf['stop_type']=='bus'])}")

for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])

# ── 시간대별 Thermal 그래프 + 역별 캐치먼트 사전 계산 ────────────────
print("\n캐치먼트 계산 중...")
hot_by_hour = {}
G_thermal_by_hour = {}
for h in TARGET_HOURS:
    h_df = mrt_df[(mrt_df['hour'] == h) & (mrt_df['mrt'] >= MRT_THRESH)]
    hot_by_hour[h] = set(zip(h_df['u'].astype(str), h_df['v'].astype(str)))
    G_thermal_by_hour[h] = build_thermal_graph(G_base, hot_by_hour[h])
    print(f"  {h:02d}시 제거 링크: {len(h_df):,}/15,608 ({len(h_df)/15608*100:.1f}%)")

results = {}
for sname, sinfo in STATIONS.items():
    results[sname] = {}
    for h in TARGET_HOURS:
        c = get_catchment(G_base, sinfo['node'])
        t = get_catchment(G_thermal_by_hour[h], sinfo['node'])
        stop_c = len(set(stops_gdf['net_node']) & c)
        stop_t = len(set(stops_gdf['net_node']) & t)
        results[sname][h] = {
            'classic': c, 'thermal': t,
            'stop_classic': stop_c, 'stop_thermal': stop_t,
            'stop_lost': stop_c - stop_t,
        }
        print(f"  [{sname}] {h:02d}시 | 정류장 {stop_c}→{stop_t} (-{stop_c-stop_t}개)")


# ── 3행 × 7열 그리드 지도 ─────────────────────────────────────────────
print("\n그리드 지도 생성 중...")
station_names = list(STATIONS.keys())
n_rows = len(TARGET_HOURS)
n_cols = len(station_names)

fig, axes = plt.subplots(n_rows, n_cols, figsize=(29, 14))

for row_idx, h in enumerate(TARGET_HOURS):
    for col_idx, sname in enumerate(station_names):
        ax = axes[row_idx][col_idx]
        sinfo  = STATIONS[sname]
        res    = results[sname][h]
        classic = res['classic']
        thermal = res['thermal']

        # 도로 네트워크 분류
        def etype(idx):
            u, v = idx[0], idx[1]
            if u in thermal and v in thermal:
                return 'thermal'
            if u in classic and v in classic:
                return 'lost'
            return 'outside'

        e = edges_wm.copy()
        e['etype'] = e.index.map(etype)

        e[e['etype'] == 'outside'].plot(
            ax=ax, color='#d0d0d0', linewidth=0.25, alpha=0.3, zorder=1)
        e[e['etype'] == 'lost'].plot(
            ax=ax, color='#E53935', linewidth=1.1, alpha=0.8, zorder=2)
        e[e['etype'] == 'thermal'].plot(
            ax=ax, color='#2E7D32', linewidth=1.1, alpha=0.85, zorder=3)

        # 대중교통 정류장 점 표시
        def stop_color(node):
            if node in thermal:
                return 'thermal'
            if node in classic:
                return 'lost'
            return 'outside'

        stops_copy = stops_gdf.copy()
        stops_copy['stype'] = stops_copy['net_node'].apply(stop_color)

        # 버스 정류장
        bus = stops_copy[stops_copy['stop_type'] == 'bus']
        for stype, color, z, sz in [
            ('outside', '#bbbbbb', 3, 6),
            ('lost',    '#FF7043', 4, 9),
            ('thermal', '#43A047', 4, 9),
        ]:
            sub = bus[bus['stype'] == stype]
            if len(sub):
                sub.plot(ax=ax, color=color, markersize=sz, alpha=0.85,
                         zorder=z, marker='o', edgecolors='white', linewidths=0.3)

        # 지하철역 (별 모양)
        subway = stops_copy[stops_copy['stop_type'] == 'subway']
        for _, row in subway.iterrows():
            sc = '#43A047' if row['stype'] == 'thermal' else \
                 '#FF7043' if row['stype'] == 'lost' else '#bbbbbb'
            ax.plot(row.geometry.x, row.geometry.y, '*',
                    color=sc, markersize=10, zorder=8,
                    markeredgecolor='black', markeredgewidth=0.5)

        # 기준 역 (큰 별)
        sg = nodes_wm.loc[sinfo['node']].geometry
        ax.plot(sg.x, sg.y, '*', color='#FFD600', markersize=14, zorder=10,
                markeredgecolor='black', markeredgewidth=1.0)

        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                            zoom=14, alpha=0.3)
        except Exception:
            pass

        # 열 제목 (역 이름) — 첫 번째 행만
        if row_idx == 0:
            ax.set_title(sname, fontsize=11, fontweight='bold', pad=4)

        # 정류장 감소 정보
        sc = res['stop_classic']
        st = res['stop_thermal']
        sl = res['stop_lost']
        pct = sl / max(sc, 1) * 100
        txt_color = '#B71C1C' if pct >= 50 else '#E65100' if pct >= 20 else '#1B5E20'
        label = (f'{sc}→{st}개\n(-{sl}개, -{pct:.0f}%)'
                 if sl > 0 else f'{sc}개\n(감소 없음)')
        ax.text(0.5, 0.04, label,
                transform=ax.transAxes, ha='center', va='bottom',
                fontsize=8.5, fontweight='bold', color=txt_color,
                bbox=dict(boxstyle='round,pad=0.25', fc='white', alpha=0.82, ec='none'))

        ax.set_axis_off()

    # 행 레이블 (시간대) — 왼쪽
    mrt_max = MRT_MAX[h]
    label_txt = f"{HOUR_LABELS[h]}\n(MRT 최고 {mrt_max}°C)"
    axes[row_idx][0].set_ylabel(label_txt, fontsize=10, fontweight='bold',
                                 rotation=90, labelpad=6)
    axes[row_idx][0].yaxis.set_visible(True)
    axes[row_idx][0].tick_params(left=False, labelleft=False)


# ── 범례 ──────────────────────────────────────────────────────────────
handles = [
    mpatches.Patch(color='#2E7D32', label='접근 가능 (도로)'),
    mpatches.Patch(color='#E53935', label='접근성 상실 (도로)'),
    mpatches.Patch(color='#d0d0d0', label='캐치먼트 외부'),
    mlines.Line2D([], [], marker='o', color='w', markerfacecolor='#43A047',
                  markeredgecolor='white', markersize=8, label='버스 (접근 가능)'),
    mlines.Line2D([], [], marker='o', color='w', markerfacecolor='#FF7043',
                  markeredgecolor='white', markersize=8, label='버스 (접근성 상실)'),
    mlines.Line2D([], [], marker='*', color='w', markerfacecolor='#FFD600',
                  markeredgecolor='black', markersize=12, label='기준 역'),
]
fig.legend(handles=handles, loc='lower center', ncol=6,
           fontsize=10, bbox_to_anchor=(0.5, 0.005), framealpha=0.92)

fig.suptitle(
    f'성동구 역세권 Thermal Catchment — Method 4 (MRT ≥ {MRT_THRESH}°C Hard Cut)\n'
    '대중교통 정류장 접근성 변화 | 15분 도보 | 폭염일 (2025.07.28~08.03)',
    fontsize=13, fontweight='bold', y=0.995
)

plt.tight_layout(rect=[0, 0.045, 1, 0.975])
out_path = os.path.join(FIG_DIR, 'catchment_stops_grid_3h_7s.png')
fig.savefig(out_path, dpi=140, bbox_inches='tight')
plt.close()
print(f"\n저장: {out_path}")
print("=== 완료 ===")
