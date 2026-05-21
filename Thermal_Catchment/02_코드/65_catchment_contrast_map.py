"""
목적 B: 도시 형태 대비 — 집계구 기점 Classic vs Thermal Catchment 지도
서울숲역 인근 고TARR(100%) vs 성수역 인근 저TARR(25%)
범례 없음, 지도만 2장 출력
"""

import os, warnings, json
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJ    = os.path.dirname(BASE)
RES_DIR = os.path.join(PROJ, '03_결과물')
FIG_DIR = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH   = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
MRT_PATH   = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
JBG_PATH   = '/Users/jin/석사논문/통계지역경계/집계구.shp'

WALK_SPEED  = 4.5 * 1000 / 3600  # m/s
TIME_BUDGET = 15 * 60            # 900초
MRT_THRESH  = 55.0
HOUR        = 13

# 대표 집계구 3개
TARGETS = {
    'high': {
        'code':     '1104066020008',
        'net_node': 3856575391,
        'label':    '서울숲역 인근\n(TARR 100%)',
        'out':      'catchment_contrast_high.png',
    },
    'low': {
        'code':     '1104068010102',
        'net_node': 436855717,
        'label':    '성수역 인근\n(TARR 25%)',
        'out':      'catchment_contrast_low.png',
    },
    'eungbong': {
        'code':     '1104058010102',
        'net_node': 7838649561,
        'label':    '응봉역 인근\n(TARR 68%)',
        'out':      'catchment_contrast_eungbong.png',
    },
}

# ── 데이터 로드 ─────────────────────────────────────────────────────────
print("네트워크 로드...")
G = ox.load_graphml(NET_PATH)
G = G.to_undirected()
for u, v, d in G.edges(data=True):
    d['travel_time'] = d.get('length', 0) / WALK_SPEED

print("MRT 데이터 로드...")
mrt_df = pd.read_csv(MRT_PATH)
h13 = mrt_df[mrt_df['hour'] == HOUR][['u', 'v', 'mrt']].copy()
hot_edges = set()
for _, row in h13.iterrows():
    if row['mrt'] >= MRT_THRESH:
        hot_edges.add((str(int(row['u'])), str(int(row['v']))))
        hot_edges.add((str(int(row['v'])), str(int(row['u']))))
print(f"  Hot edges (MRT≥{MRT_THRESH}°C): {len(hot_edges)//2:,}개")

print("집계구 로드...")
jbg = gpd.read_file(JBG_PATH)
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].to_crs('EPSG:3857')
jbg['TOT_REG_CD'] = jbg['TOT_REG_CD'].astype(str)

nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
edges_gdf = edges_gdf.reset_index()
edges_gdf['u'] = edges_gdf['u'].astype(str)
edges_gdf['v'] = edges_gdf['v'].astype(str)
edges_gdf_wm = edges_gdf.to_crs('EPSG:3857')


def compute_catchment(origin_node):
    # Classic
    classic = set(nx.single_source_dijkstra_path_length(
        G, origin_node, cutoff=TIME_BUDGET, weight='travel_time'
    ).keys())

    # Thermal: hot edges 제거
    G_th = G.copy()
    remove = [(u, v) for u, v in G_th.edges()
              if (str(u), str(v)) in hot_edges]
    G_th.remove_edges_from(remove)
    for u, v, d in G_th.edges(data=True):
        d['travel_time'] = d.get('length', 0) / WALK_SPEED

    thermal = set(nx.single_source_dijkstra_path_length(
        G_th, origin_node, cutoff=TIME_BUDGET, weight='travel_time'
    ).keys())

    return classic, thermal


def make_map(target_key):
    cfg = TARGETS[target_key]
    print(f"\n[{target_key}] {cfg['label'].replace(chr(10),' ')} 계산 중...")

    origin_node = cfg['net_node']
    classic_nodes, thermal_nodes = compute_catchment(origin_node)
    lost_nodes = classic_nodes - thermal_nodes

    tarr = len(lost_nodes) / max(len(classic_nodes), 1) * 100
    print(f"  Classic: {len(classic_nodes):,} / Thermal: {len(thermal_nodes):,} / TARR: {tarr:.1f}%")

    # 엣지 분류
    def edge_type(row):
        u, v = str(int(row['u'])), str(int(row['v']))
        u_int, v_int = int(u), int(v)
        in_classic = (u_int in classic_nodes) and (v_int in classic_nodes)
        in_thermal = (u_int in thermal_nodes) and (v_int in thermal_nodes)
        if in_thermal:
            return 'thermal'
        elif in_classic:
            return 'lost'
        else:
            return 'outside'

    edges_gdf_wm['etype'] = edges_gdf_wm.apply(edge_type, axis=1)

    # 집계구 경계 & 해당 집계구
    target_jbg = jbg[jbg['TOT_REG_CD'] == cfg['code']]

    # ── 지도 범위: origin 기준 1,800m 버퍼 ──────────────────────────────
    nodes_gdf_wm = nodes_gdf.to_crs('EPSG:3857')
    ox_node = nodes_gdf_wm.loc[origin_node]
    cx_m, cy_m = ox_node.geometry.x, ox_node.geometry.y
    PAD = 1600
    xlim = (cx_m - PAD, cx_m + PAD)
    ylim = (cy_m - PAD, cy_m + PAD)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)

    # 베이스맵
    try:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=15, alpha=0.7)
    except Exception:
        pass

    # 전체 성동구 집계구 경계 (옅은 회색)
    jbg.plot(ax=ax, facecolor='none', edgecolor='#CCCCCC', linewidth=0.4, zorder=2)

    # 네트워크 엣지 — outside는 생략, lost(빨강), thermal(초록)
    e_lost    = edges_gdf_wm[edges_gdf_wm['etype'] == 'lost']
    e_thermal = edges_gdf_wm[edges_gdf_wm['etype'] == 'thermal']

    if len(e_lost):
        e_lost.plot(ax=ax, color='#E53935', linewidth=1.4, alpha=0.85, zorder=4)
    if len(e_thermal):
        e_thermal.plot(ax=ax, color='#43A047', linewidth=1.4, alpha=0.85, zorder=3)

    # 출발 집계구 강조
    if len(target_jbg):
        target_jbg.plot(ax=ax, facecolor='#FFF9C4', edgecolor='#F57F17',
                        linewidth=2.0, alpha=0.7, zorder=5)

    ax.set_axis_off()
    plt.tight_layout(pad=0)

    out_path = os.path.join(FIG_DIR, cfg['out'])
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  저장: {out_path}")


make_map('high')
make_map('low')
make_map('eungbong')
print("\n완료.")
