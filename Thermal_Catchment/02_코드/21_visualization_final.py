"""
논문용 최종 시각화
===================
Figure 1: 두 모델 히트맵 나란히 (IDW+SVF vs SOLWEIG)
Figure 2: 응봉동 vs 성수동 대조 지도 (13시, 두 모델)
Figure 3: 시간대별 감소율 꺾은선
Figure 4: 13시 취약성 종합 바 차트
"""

import os, json
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
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
STP_BASE = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

# ── 데이터 로드 ────────────────────────────────────────────────────────
with open(os.path.join(RES_DIR, 'catchment_corrected_summary.json'), encoding='utf-8') as f:
    d_idw = json.load(f)
with open(os.path.join(RES_DIR, 'catchment_solweig_summary.json'), encoding='utf-8') as f:
    d_sol = json.load(f)

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377, 'color': '#E53935'},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305, 'color': '#FB8C00'},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353, 'color': '#8E24AA'},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475, 'color': '#43A047'},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561, 'color': '#1E88E5'},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448, 'color': '#00ACC1'},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171, 'color': '#6D4C41'},
}
STATION_NAMES = list(STATIONS.keys())
TARGET_HOURS  = [7, 10, 13, 16]

idw_mat = np.array([[d_idw[s][f'h{h:02d}']['reduction_pct'] for h in TARGET_HOURS] for s in STATION_NAMES])
sol_mat = np.array([[d_sol[s][f'h{h:02d}']['reduction_pct'] for h in TARGET_HOURS] for s in STATION_NAMES])


# ══════════════════════════════════════════════════════════════════════
# Figure 1: 두 모델 히트맵 나란히
# ══════════════════════════════════════════════════════════════════════
print("Figure 1 생성 중...")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for ax, mat, title, label in [
    (axes[0], idw_mat, 'IDW+SVF 보정 모델', '(a)'),
    (axes[1], sol_mat, 'SOLWEIG 물리 모델', '(b)'),
]:
    im = ax.imshow(mat, cmap='YlOrRd', aspect='auto', vmin=0, vmax=85)
    plt.colorbar(im, ax=ax, label='접근성 감소율 (%)', shrink=0.85)
    ax.set_xticks(range(len(TARGET_HOURS)))
    ax.set_xticklabels([f'{h}시' for h in TARGET_HOURS], fontsize=12)
    ax.set_yticks(range(len(STATION_NAMES)))
    ax.set_yticklabels(STATION_NAMES, fontsize=12)
    for i, s in enumerate(STATION_NAMES):
        for j in range(len(TARGET_HOURS)):
            v = mat[i, j]
            color = 'white' if v > 45 else 'black'
            ax.text(j, i, f'{v:.0f}%', ha='center', va='center',
                    fontsize=10, color=color, fontweight='bold')
    ax.set_title(f'{label} {title}', fontsize=13, fontweight='bold', pad=10)

fig.suptitle('성동구 역별 도보 접근성 감소율 — 두 모델 비교\n'
             'UTCI ≥ 38°C 링크 회피 | 시간예산 15분 | 2025.07.28~08.03',
             fontsize=13, fontweight='bold')
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig1_heatmap_comparison.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: fig1_heatmap_comparison.png")


# ══════════════════════════════════════════════════════════════════════
# Figure 2: 응봉역 vs 성수역 대조 지도 (13시, 두 모델)
# ══════════════════════════════════════════════════════════════════════
print("Figure 2 생성 중 (네트워크 로드)...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

utci_idw = pd.read_csv(os.path.join(RES_DIR, 'link_utci_corrected.csv'), encoding='utf-8-sig')
utci_sol = pd.read_csv(os.path.join(RES_DIR, 'link_utci_solweig.csv'),   encoding='utf-8-sig')

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
THRESHOLD   = 38.0

for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])

def get_hot_set(df, hour, col):
    h = df[(df['hour'] == hour) & (df[col] >= THRESHOLD)]
    return set(zip(h['u'].astype(str), h['v'].astype(str)))

def get_catchment(G, node, hot_set):
    for u, v, d in G.edges(data=True):
        d['travel_time'] = d.get('length', 0) / WALK_SPEED
    classic = set(nx.single_source_dijkstra_path_length(G, node, cutoff=TIME_BUDGET, weight='travel_time').keys())
    G2 = G.copy()
    G2.remove_edges_from([(u,v) for u,v in G2.edges() if (str(u),str(v)) in hot_set or (str(v),str(u)) in hot_set])
    thermal = set(nx.single_source_dijkstra_path_length(G2, node, cutoff=TIME_BUDGET, weight='travel_time').keys())
    return classic, thermal

FOCUS = ['응봉역', '성수역']
HOUR  = 13

hot_idw = get_hot_set(utci_idw, HOUR, 'utci_corrected')
hot_sol = get_hot_set(utci_sol, HOUR, 'utci_final')

catchments = {}
for sname in FOCUS:
    sinfo = STATIONS[sname]
    c_idw, t_idw = get_catchment(G_base.copy(), sinfo['node'], hot_idw)
    c_sol, t_sol = get_catchment(G_base.copy(), sinfo['node'], hot_sol)
    catchments[sname] = {
        'idw': (c_idw, t_idw),
        'sol': (c_sol, t_sol),
    }

# 2×2 지도: 행=역(응봉/성수), 열=모델(IDW/SOLWEIG)
fig, axes = plt.subplots(2, 2, figsize=(16, 14))
model_labels = ['IDW+SVF 보정', 'SOLWEIG 물리']
model_keys   = ['idw', 'sol']

for row, sname in enumerate(FOCUS):
    for col, (mkey, mlabel) in enumerate(zip(model_keys, model_labels)):
        ax = axes[row][col]
        classic, thermal = catchments[sname][mkey]
        lost = classic - thermal

        def etype(idx):
            u, v = idx[0], idx[1]
            if u in thermal and v in thermal: return 'thermal'
            if u in classic  and v in classic: return 'lost'
            return 'outside'

        e = edges_wm.copy()
        e['etype'] = e.index.map(etype)
        e[e['etype']=='outside'].plot(ax=ax, color='#dddddd', linewidth=0.3, alpha=0.5, zorder=1)
        e[e['etype']=='lost'].plot(   ax=ax, color='#F44336', linewidth=1.2, alpha=0.9, zorder=2)
        e[e['etype']=='thermal'].plot(ax=ax, color='#2E7D32', linewidth=1.5, alpha=0.9, zorder=3)

        snode = STATIONS[sname]['node']
        sg = nodes_wm.loc[snode].geometry
        ax.plot(sg.x, sg.y, 'o', color='#FFD600', markersize=12, zorder=9,
                markeredgecolor='black', markeredgewidth=1.5)

        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=15, alpha=0.4)
        except Exception:
            pass

        red_pct = d_idw[sname][f'h{HOUR:02d}']['reduction_pct'] if mkey == 'idw' \
                  else d_sol[sname][f'h{HOUR:02d}']['reduction_pct']

        ax.set_title(
            f'{sname}  |  {mlabel}\n'
            f'접근 {len(thermal):,}개 / 상실 {len(lost):,}개  →  감소율 {red_pct:.1f}%',
            fontsize=11, fontweight='bold'
        )
        ax.set_axis_off()

        # 행 레이블
        if col == 0:
            ax.set_ylabel(sname, fontsize=13, fontweight='bold', labelpad=12)

handles = [
    mpatches.Patch(color='#2E7D32', label='접근 가능 (UTCI < 38°C)'),
    mpatches.Patch(color='#F44336', label='접근성 상실 (우회 불가 / 시간 초과)'),
    mpatches.Patch(color='#dddddd', label='캐치먼트 외부'),
]
fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=11, bbox_to_anchor=(0.5, 0.01))
fig.suptitle(f'응봉역 vs 성수역 — Thermal Catchment 비교 ({HOUR}시)\n'
             '열취약 교통 결절(응봉) vs 녹지 인접 결절(성수)',
             fontsize=14, fontweight='bold')
plt.tight_layout(rect=[0, 0.06, 1, 1])
fig.savefig(os.path.join(FIG_DIR, 'fig2_eungbong_vs_seongsu.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: fig2_eungbong_vs_seongsu.png")


# ══════════════════════════════════════════════════════════════════════
# Figure 3: 시간대별 감소율 꺾은선 (두 모델, 주요 역)
# ══════════════════════════════════════════════════════════════════════
print("Figure 3 생성 중...")

HIGHLIGHT = ['응봉역', '서울숲역', '성수역', '왕십리역']
colors_hl  = {'응봉역': '#8E24AA', '서울숲역': '#00ACC1', '성수역': '#1E88E5', '왕십리역': '#E53935'}

fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

for ax, mat, title, label in [
    (axes[0], d_idw, 'IDW+SVF 보정 모델', '(a)'),
    (axes[1], d_sol, 'SOLWEIG 물리 모델', '(b)'),
]:
    for sname in STATION_NAMES:
        vals = [mat[sname][f'h{h:02d}']['reduction_pct'] for h in TARGET_HOURS]
        if sname in HIGHLIGHT:
            ax.plot(TARGET_HOURS, vals, '-o', color=colors_hl[sname],
                    linewidth=2.5, markersize=7, label=sname, zorder=4)
            ax.text(TARGET_HOURS[-1] + 0.2, vals[-1], sname,
                    fontsize=9, color=colors_hl[sname], va='center')
        else:
            ax.plot(TARGET_HOURS, vals, '-o', color='#BDBDBD',
                    linewidth=1.2, markersize=4, alpha=0.6, zorder=2)

    ax.axhspan(0, 20,  alpha=0.05, color='green',  label='_nolegend_')
    ax.axhspan(50, 100, alpha=0.05, color='red',   label='_nolegend_')
    ax.axhline(50, color='#E53935', linestyle='--', linewidth=0.8, alpha=0.5)

    ax.set_xticks(TARGET_HOURS)
    ax.set_xticklabels([f'{h}시' for h in TARGET_HOURS], fontsize=11)
    ax.set_xlabel('시간대', fontsize=11)
    ax.set_ylim(-2, 90)
    ax.set_title(f'{label} {title}', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.spines[['top', 'right']].set_visible(False)

axes[0].set_ylabel('도보 접근성 감소율 (%)', fontsize=11)

fig.suptitle('성동구 역별 시간대별 도보 접근성 감소율\n'
             '(UTCI ≥ 38°C 링크 회피 | 시간예산 15분)',
             fontsize=13, fontweight='bold')
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig3_timeseries.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: fig3_timeseries.png")


# ══════════════════════════════════════════════════════════════════════
# Figure 4: 13시 취약성 종합 바 차트
# ══════════════════════════════════════════════════════════════════════
print("Figure 4 생성 중...")

idw_13 = [d_idw[s]['h13']['reduction_pct'] for s in STATION_NAMES]
sol_13 = [d_sol[s]['h13']['reduction_pct'] for s in STATION_NAMES]

# 정렬: IDW 기준 내림차순
order = np.argsort(idw_13)[::-1]
names_sorted = [STATION_NAMES[i] for i in order]
idw_sorted   = [idw_13[i] for i in order]
sol_sorted   = [sol_13[i] for i in order]

x = np.arange(len(names_sorted))
w = 0.38

fig, ax = plt.subplots(figsize=(12, 6))
b1 = ax.bar(x - w/2, idw_sorted, w, label='IDW+SVF 보정', color='#42A5F5', edgecolor='white', linewidth=0.5)
b2 = ax.bar(x + w/2, sol_sorted, w, label='SOLWEIG 물리', color='#EF6C00',  edgecolor='white', linewidth=0.5)

for bar, v in zip(b1, idw_sorted):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{v:.0f}%', ha='center', va='bottom', fontsize=9, color='#1565C0')
for bar, v in zip(b2, sol_sorted):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{v:.0f}%', ha='center', va='bottom', fontsize=9, color='#E65100')

# 50% 기준선
ax.axhline(50, color='#B71C1C', linestyle='--', linewidth=1.2, alpha=0.7, label='50% 기준선')

# 취약 구간 배경
ax.axhspan(50, 90, alpha=0.04, color='red')
ax.text(len(names_sorted) - 0.5, 55, '고취약 구간 (>50%)',
        fontsize=8, color='#B71C1C', alpha=0.7, ha='right')

ax.set_xticks(x)
ax.set_xticklabels(names_sorted, fontsize=12)
ax.set_ylabel('도보 접근성 감소율 (%)', fontsize=11)
ax.set_ylim(0, 90)
ax.legend(fontsize=11, loc='upper right')
ax.grid(axis='y', alpha=0.3)
ax.spines[['top', 'right']].set_visible(False)
ax.set_title('성동구 역별 폭염 시 도보 접근성 감소율 (13시)\n'
             '두 가지 UTCI 계산 방법 비교 | UTCI ≥ 38°C 링크 회피 모델',
             fontsize=13, fontweight='bold')

plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig4_vulnerability_bar.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: fig4_vulnerability_bar.png")


print("\n=== 시각화 완료 ===")
print(f"  fig1_heatmap_comparison.png  — 두 모델 히트맵 나란히")
print(f"  fig2_eungbong_vs_seongsu.png — 응봉 vs 성수 대조 지도")
print(f"  fig3_timeseries.png          — 시간대별 꺾은선")
print(f"  fig4_vulnerability_bar.png   — 13시 취약성 바 차트")
