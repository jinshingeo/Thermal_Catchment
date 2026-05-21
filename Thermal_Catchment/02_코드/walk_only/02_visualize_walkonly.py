"""
Walk-Only 분석 시각화
1) TARR 단계구분도 (0-20-40-60-80-100 고정 급간)
2) Classic vs Thermal Catchment 대비 지도 3개
"""

import os, warnings, json
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import contextily as ctx
from shapely.geometry import Point
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(BASE)
TC_DIR   = os.path.dirname(CODE_DIR)
RES_DIR  = os.path.join(TC_DIR, '03_결과물')
OUT_DIR  = os.path.join(RES_DIR, 'walk_only')
FIG_DIR  = os.path.join(OUT_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH  = os.path.join(OUT_DIR, 'seongdong_walkonly_network.graphml')
MRT_PATH  = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
TARR_CSV  = os.path.join(OUT_DIR, 'tarr_walkonly.csv')
JBG_SHP   = '/Users/jin/석사논문/통계지역경계/집계구.shp'

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
MRT_THRESH  = 55.0
HOUR        = 13

# ── 데이터 로드 ──────────────────────────────────────────────────────────
print("데이터 로드...")
G = ox.load_graphml(NET_PATH).to_undirected()
for u, v, d in G.edges(data=True):
    d['travel_time'] = d.get('length', 0) / WALK_SPEED

mrt_df = pd.read_csv(MRT_PATH, encoding='utf-8-sig')
h13 = mrt_df[mrt_df['hour'] == HOUR].copy()
G_nodes = set(str(n) for n in G.nodes())
hot_edges = {(str(int(r['u'])), str(int(r['v']))) for _, r in h13.iterrows()
             if r['mrt'] >= MRT_THRESH and str(int(r['u'])) in G_nodes}
hot_edges |= {(v, u) for u, v in hot_edges}

tarr_df = pd.read_csv(TARR_CSV, encoding='utf-8-sig')
tarr_df['집계구코드'] = tarr_df['집계구코드'].astype(str)

jbg = gpd.read_file(JBG_SHP)
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
if jbg.crs is None:
    jbg = jbg.set_crs('EPSG:5179', allow_override=True)
jbg = jbg.to_crs('EPSG:3857')
jbg['TOT_REG_CD'] = jbg['TOT_REG_CD'].astype(str)
jbg = jbg.merge(tarr_df[['집계구코드', 'tarr']], left_on='TOT_REG_CD', right_on='집계구코드', how='left')

nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
edges_gdf = edges_gdf.reset_index()
edges_gdf['u'] = edges_gdf['u'].astype(str)
edges_gdf['v'] = edges_gdf['v'].astype(str)
edges_gdf_wm = edges_gdf.to_crs('EPSG:3857')
nodes_gdf_wm = nodes_gdf.to_crs('EPSG:3857')


# ── 1. TARR 단계구분도 ────────────────────────────────────────────────────
print("\nTARR 단계구분도 생성...")

breaks = [0, 20, 40, 60, 80, 100]
colors = ['#FFFFCC', '#FECC5C', '#FD8D3C', '#F03B20', '#BD0026']
labels = []
for i in range(len(colors)):
    lo, hi = breaks[i], breaks[i+1]
    mask = (jbg['tarr'] >= lo) & (jbg['tarr'] <= hi if hi == 100 else jbg['tarr'] < hi)
    cnt = mask.sum()
    labels.append(f"{lo}–{hi}%  ({cnt}개)")

def assign_class(v):
    for j in range(len(breaks) - 1):
        if v <= breaks[j + 1]:
            return j
    return len(breaks) - 2

valid_jbg  = jbg.dropna(subset=['tarr']).copy()
no_val_jbg = jbg[jbg['tarr'].isna()].copy()
valid_jbg['cls'] = valid_jbg['tarr'].apply(assign_class)

fig, ax = plt.subplots(figsize=(10, 10), dpi=150)

# 집계구 먼저 그려서 extent 확보
if len(no_val_jbg):
    no_val_jbg.plot(ax=ax, facecolor='#EEEEEE', edgecolor='#CCCCCC', linewidth=0.3, zorder=2)
for i, color in enumerate(colors):
    subset = valid_jbg[valid_jbg['cls'] == i]
    if len(subset):
        subset.plot(ax=ax, facecolor=color, edgecolor='#888888', linewidth=0.3, alpha=0.9, zorder=3 + i)

# 베이스맵은 나중에
try:
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=14, alpha=0.4)
except Exception:
    pass

labels = []
for i in range(len(colors)):
    lo, hi = breaks[i], breaks[i+1]
    cnt = (valid_jbg['cls'] == i).sum()
    labels.append(f"{lo}–{hi}%  ({cnt}개)")
patches = [mpatches.Patch(facecolor=colors[i], edgecolor='#555', label=labels[i]) for i in range(len(colors))]
patches.append(mpatches.Patch(facecolor='#EEEEEE', edgecolor='#CCCCCC', label='정류장 0개 (제외)'))
ax.legend(handles=patches, loc='upper left', fontsize=12,
          framealpha=0.92, title='TARR (Walk-Only)', title_fontsize=13,
          edgecolor='#999', fancybox=False, handleheight=1.8, handlelength=2.0,
          borderpad=1.0, labelspacing=0.7)

ax.set_title(f'Walk-Only TARR 단계구분도\nMRT≥{MRT_THRESH}°C Hard Cut | 13시 | 간선도로 제거',
             fontsize=13, fontweight='bold')
ax.set_axis_off()
plt.tight_layout()
out = os.path.join(FIG_DIR, 'tarr_choropleth_walkonly.png')
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print(f"  저장: {out}")


# ── 2. Classic vs Thermal 대비 지도 ─────────────────────────────────────
print("\n대비 지도 생성...")

# 대표 집계구: tarr_walkonly.csv에서 고TARR / 저TARR / 중간 선택
valid = tarr_df[tarr_df['classic_stops'] > 10].copy()
high_row = valid.nlargest(1, 'tarr').iloc[0]
low_row  = valid.nsmallest(1, 'tarr').iloc[0]
# 응봉역 인근 고정 (net_node=7838649561, code=1104058010102)
mid_row  = tarr_df[tarr_df['집계구코드'] == '1104058010102'].iloc[0]

TARGETS = {
    'high': {
        'code':     str(high_row['집계구코드']),
        'net_node': int(high_row['net_node']),
        'tarr':     high_row['tarr'],
        'out':      'contrast_high_walkonly.png',
    },
    'low': {
        'code':     str(low_row['집계구코드']),
        'net_node': int(low_row['net_node']),
        'tarr':     low_row['tarr'],
        'out':      'contrast_low_walkonly.png',
    },
    'eungbong': {
        'code':     str(mid_row['집계구코드']),
        'net_node': int(mid_row['net_node']),
        'tarr':     mid_row['tarr'],
        'out':      'contrast_eungbong_walkonly.png',
    },
}


def compute_catchment(origin):
    classic = set(nx.single_source_dijkstra_path_length(
        G, origin, cutoff=TIME_BUDGET, weight='travel_time').keys())
    G_th = G.copy()
    G_th.remove_edges_from([
        (u, v) for u, v in G_th.edges()
        if (str(u), str(v)) in hot_edges
    ])
    thermal = set(nx.single_source_dijkstra_path_length(
        G_th, origin, cutoff=TIME_BUDGET, weight='travel_time').keys())
    return classic, thermal


def edge_type(row, classic_nodes, thermal_nodes):
    u_int = int(row['u']) if row['u'].isdigit() else None
    v_int = int(row['v']) if row['v'].isdigit() else None
    if u_int is None or v_int is None:
        return 'outside'
    if u_int in thermal_nodes and v_int in thermal_nodes:
        return 'thermal'
    if u_int in classic_nodes and v_int in classic_nodes:
        return 'lost'
    return 'outside'


for key, cfg in TARGETS.items():
    origin = cfg['net_node']
    if origin not in G.nodes():
        print(f"  [{key}] 노드 {origin} 없음, 건너뜀")
        continue

    classic_nodes, thermal_nodes = compute_catchment(origin)
    actual_tarr = len(classic_nodes - thermal_nodes) / max(len(classic_nodes), 1) * 100
    print(f"  [{key}] code={cfg['code']} | Classic:{len(classic_nodes):,} Thermal:{len(thermal_nodes):,} TARR:{actual_tarr:.1f}%")

    edges_gdf_wm['etype'] = edges_gdf_wm.apply(
        lambda r: edge_type(r, classic_nodes, thermal_nodes), axis=1)

    target_jbg = jbg[jbg['TOT_REG_CD'] == cfg['code']]

    ox_node = nodes_gdf_wm.loc[origin]
    cx_m, cy_m = ox_node.geometry.x, ox_node.geometry.y
    PAD = 1600

    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    ax.set_xlim(cx_m - PAD, cx_m + PAD)
    ax.set_ylim(cy_m - PAD, cy_m + PAD)

    try:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=15, alpha=0.7)
    except Exception:
        pass

    jbg.plot(ax=ax, facecolor='none', edgecolor='#CCCCCC', linewidth=0.4, zorder=2)

    e_lost    = edges_gdf_wm[edges_gdf_wm['etype'] == 'lost']
    e_thermal = edges_gdf_wm[edges_gdf_wm['etype'] == 'thermal']
    if len(e_lost):
        e_lost.plot(ax=ax, color='#E53935', linewidth=1.4, alpha=0.85, zorder=4)
    if len(e_thermal):
        e_thermal.plot(ax=ax, color='#43A047', linewidth=1.4, alpha=0.85, zorder=3)

    if len(target_jbg):
        target_jbg.plot(ax=ax, facecolor='#FFF9C4', edgecolor='#F57F17',
                        linewidth=2.0, alpha=0.7, zorder=5)

    ax.set_axis_off()
    plt.tight_layout(pad=0)
    out = os.path.join(FIG_DIR, cfg['out'])
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"    저장: {out}")

print("\n완료.")
