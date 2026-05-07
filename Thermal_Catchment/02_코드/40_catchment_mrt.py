"""
Method 4: MRT 직접 Hard Cut 기반 Thermal Catchment
===================================================
Method 3(link_utci_sdot_solweig.csv)의 MRT 컬럼을 그대로 사용.
UTCI 변환 없이 MRT 임계값으로 링크를 직접 제거한다.

UTCI 기반(Method 1~3) 한계:
  - UTCI 변환 시 공간 변이가 압축됨 (std 4.57°C → 1.7°C)
  - 폭염일 13시 기준 UTCI ≥38°C 비율 99.8% → Hard Cut 사실상 불가

MRT 직접 사용 근거:
  - MRT std=4.57°C로 공간 변이 양호
  - 임계값: Thorsson et al. (2007) MRT>50°C 부근 = 강한 열 스트레스 (문헌 확인 필요)
            55°C·58°C는 경험적 비교용 (교수님 논의 후 근거 확정 필요)

임계값 3개 비교:
  THRESH_LOW=50°C  THRESH_MID=55°C  THRESH_HIGH=58°C

출력:
  catchment_mrt_summary.json     — 방법별·역별·시간대별 결과
  figures/catchment_mrt_heatmap_{thresh}.png
  figures/catchment_mrt_vs_m1_13h.png  — Method 1 vs Method 4(55°C) 비교
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

# ── 경로 ─────────────────────────────────────────────────────────────────
BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
STP_BASE = '/Users/jin/석사논문/성동구_STP연구'
NET_PATH = os.path.join(STP_BASE, '01_네트워크/seongdong_walk_network.graphml')
M3_PATH  = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')   # Method 3 출력
M1_PATH  = os.path.join(RES_DIR, 'catchment_corrected_summary.json')  # Method 1 기준
os.makedirs(FIG_DIR, exist_ok=True)

# ── 파라미터 ──────────────────────────────────────────────────────────────
WALK_SPEED  = 4.5 * 1000 / 3600   # m/s
TIME_BUDGET = 15 * 60             # 900초
TARGET_HOURS = [7, 10, 13, 16]

MRT_THRESHOLDS = {
    'low':  50.0,   # Thorsson et al. (2007): MRT>50°C = 강한 열 스트레스 (문헌 검토 필요)
    'mid':  55.0,   # 경험적 기준: 분포 상위 약 38% (임계값 근거 교수님 논의 필요)
    'high': 58.0,   # 보수적 기준: 분포 상위 약 21%
}

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377, 'color': '#E53935'},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305, 'color': '#FB8C00'},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353, 'color': '#8E24AA'},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475, 'color': '#43A047'},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561, 'color': '#1E88E5'},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448, 'color': '#00ACC1'},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171, 'color': '#6D4C41'},
}


def compute_catchment(G_base, station_node, hot_edges_set):
    """Classic vs Thermal 캐치먼트 계산 (hot_edges_set: {(u_str, v_str)})
    감소율 기준: 노드 수(node_count) + 도로 길이(length_m) 병행 산출
    """
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
    lost_nodes    = classic_nodes - thermal_nodes

    # 길이 기반 감소율: 캐치먼트 내 양 끝점이 모두 포함된 엣지 길이 합산
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
    lost_length = classic_length - thermal_length

    return {
        'classic_nodes':      classic_nodes,
        'thermal_nodes':      thermal_nodes,
        'lost_nodes':         lost_nodes,
        'classic_count':      len(classic_nodes),
        'thermal_count':      len(thermal_nodes),
        'lost_count':         len(lost_nodes),
        'reduction_pct':      round(len(lost_nodes) / max(len(classic_nodes), 1) * 100, 1),
        'classic_length_m':   round(classic_length, 1),
        'thermal_length_m':   round(thermal_length, 1),
        'lost_length_m':      round(lost_length, 1),
        'reduction_pct_len':  round(lost_length / max(classic_length, 1) * 100, 1),
        'hot_edges_removed':  len(edges_to_remove),
    }


# ── 데이터 로드 ───────────────────────────────────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_base)
nodes_wm = nodes_gdf.to_crs(epsg=3857)
edges_wm = edges_gdf.to_crs(epsg=3857)

for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])

print("Method 3 MRT 데이터 로드 중...")
mrt_df = pd.read_csv(M3_PATH, encoding='utf-8-sig')
print(f"  {len(mrt_df):,}행 | 시간대 {sorted(mrt_df['hour'].unique())}")

h13_mrt = mrt_df[mrt_df['hour'] == 13]['mrt']
print(f"  MRT 13시: mean={h13_mrt.mean():.1f}  std={h13_mrt.std():.2f}  "
      f"min={h13_mrt.min():.1f}  max={h13_mrt.max():.1f}°C")

print("\n=== MRT 임계값별 링크 초과율 (13시) ===")
for label, thresh in MRT_THRESHOLDS.items():
    n_hot = (h13_mrt >= thresh).sum()
    print(f"  MRT ≥ {thresh}°C: {n_hot:,}개 ({n_hot/len(h13_mrt)*100:.1f}%)")


# ── 임계값별 Thermal Catchment 계산 ──────────────────────────────────────
all_results = {}   # all_results[thresh_label][station][hour] = result_dict

for label, thresh in MRT_THRESHOLDS.items():
    print(f"\n{'='*55}")
    print(f"Method 4 — MRT ≥ {thresh}°C Hard Cut (임계값: {label})")
    print('='*55)

    # 시간대별 hot edges set 구성
    hot_by_hour = {}
    for hour in TARGET_HOURS:
        h_df = mrt_df[(mrt_df['hour'] == hour) & (mrt_df['mrt'] >= thresh)]
        hot_by_hour[hour] = set(zip(h_df['u'].astype(str), h_df['v'].astype(str)))
        total = len(mrt_df[mrt_df['hour'] == hour])
        print(f"  {hour:02d}시 제거 대상: {len(h_df):,}개 / {total:,}개 ({len(h_df)/total*100:.1f}%)")

    all_results[label] = {}
    for station_name, sinfo in STATIONS.items():
        all_results[label][station_name] = {}
        for hour in TARGET_HOURS:
            G = G_base.copy()
            result = compute_catchment(G, sinfo['node'], hot_by_hour[hour])
            all_results[label][station_name][hour] = result
            print(f"  [{station_name}] {hour:02d}시 | "
                  f"길이 {result['classic_length_m']/1000:.2f}km → "
                  f"{result['thermal_length_m']/1000:.2f}km "
                  f"(-{result['reduction_pct_len']}%) | "
                  f"노드 기준 -{result['reduction_pct']}%")


# ── 시각화 1: 임계값별 히트맵 ────────────────────────────────────────────
station_names = list(STATIONS.keys())
for label, thresh in MRT_THRESHOLDS.items():
    data_matrix = np.array([
        [all_results[label][s][h]['reduction_pct'] for h in TARGET_HOURS]
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
                    fontsize=10, color='white' if val > 45 else 'black',
                    fontweight='bold')
    ax.set_title(
        f'Method 4: MRT 직접 Hard Cut — 역별 접근성 감소율\n'
        f'임계값: MRT ≥ {thresh}°C ({label}) | 15분 시간예산 | 2025.07.28~08.03',
        fontsize=11, fontweight='bold'
    )
    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, f'catchment_mrt_heatmap_{label}.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n저장: {out_path}")


# ── 시각화 2: Method 1 vs Method 4(mid=55°C) — 13시 역별 비교 ───────────
m1_summary = None
if os.path.exists(M1_PATH):
    with open(M1_PATH, encoding='utf-8') as f:
        m1_summary = json.load(f)

if m1_summary:
    # Method 1 결과 키 탐색 (h13 또는 13 형태)
    def get_m1_pct(s):
        sdata = m1_summary.get(s, {})
        for key in ['h13', 13, '13']:
            if key in sdata:
                return sdata[key].get('reduction_pct', 0)
        return 0

    m1_vals  = [get_m1_pct(s) for s in station_names]
    m4_vals  = [all_results['mid'][s][13]['reduction_pct'] for s in station_names]

    x = np.arange(len(station_names))
    w = 0.35
    fig, ax = plt.subplots(figsize=(13, 6))
    b1 = ax.bar(x - w/2, m1_vals, w,
                label='Method 1 (UTCI 약식, SVF 선형차감)', color='#42A5F5', edgecolor='gray')
    b2 = ax.bar(x + w/2, m4_vals, w,
                label='Method 4 (MRT 직접, ≥55°C 제거)', color='#EF6C00', edgecolor='gray')
    for bar, v in zip(b1, m1_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{v:.1f}%', ha='center', va='bottom', fontsize=8)
    for bar, v in zip(b2, m4_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{v:.1f}%', ha='center', va='bottom', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(station_names, fontsize=11)
    ax.set_ylabel('접근성 감소율 (%)', fontsize=11)
    ax.set_title(
        'Method 1 vs Method 4 — 13시 접근성 감소율 비교\n'
        'Method 1: UTCI ≥38°C 제거 (약식 SVF) | Method 4: MRT ≥55°C 제거 (S-DoT IDW)',
        fontsize=11, fontweight='bold'
    )
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    out_path = os.path.join(FIG_DIR, 'catchment_mrt_vs_m1_13h.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"저장: {out_path}")


# ── 시각화 3: Method 4(55°C) 13시 캐치먼트 지도 ─────────────────────────
print("\n13시 캐치먼트 지도 생성 중 (Method 4, MRT≥55°C)...")
fig, axes = plt.subplots(2, 4, figsize=(28, 14))
axes_flat = axes.flatten()

for ax, (station_name, sinfo) in zip(axes_flat, STATIONS.items()):
    result = all_results['mid'][station_name][13]
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
        f"{station_name} | 13시 | MRT≥55°C 제거\n"
        f"접근 {result['thermal_count']:,}  상실 {result['lost_count']:,} (-{result['reduction_pct']}%)",
        fontsize=9
    )
    ax.set_axis_off()

for i in range(len(STATIONS), len(axes_flat)):
    axes_flat[i].set_visible(False)

handles = [
    mpatches.Patch(color='#2E7D32', label='접근 가능 (MRT < 55°C)'),
    mpatches.Patch(color='#EF9A9A', label='접근성 상실'),
    mpatches.Patch(color='#cccccc', label='캐치먼트 외부'),
]
fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=11, bbox_to_anchor=(0.5, 0.01))
fig.suptitle(
    '성동구 전체 역 — Method 4: MRT 직접 Hard Cut Thermal Catchment (13시)\n'
    'S-DoT IDW 기상 + SOLWEIG MRT ≥55°C 링크 제거 | 시간예산 15분',
    fontsize=14, fontweight='bold'
)
plt.tight_layout(rect=[0, 0.06, 1, 1])
out_path = os.path.join(FIG_DIR, 'catchment_mrt_13h_mid.png')
fig.savefig(out_path, dpi=130, bbox_inches='tight')
plt.close()
print(f"저장: {out_path}")


# ── JSON 저장 ─────────────────────────────────────────────────────────────
summary = {
    'model':           'mrt_direct_hard_cut',
    'mrt_source':      'S-DoT IDW + SOLWEIG (Lindberg & Grimmond 2011)',
    'weather_period':  '2025-07-28 ~ 2025-08-03',
    'thresholds':      MRT_THRESHOLDS,
    'time_budget_min': 15,
    'walk_speed_kmh':  4.5,
    'references':      [
        'Thorsson et al. (2007) — MRT>50°C: strong heat stress (검토 필요)',
        '55°C 임계값: 경험적 기준 (문헌 근거 교수님 논의 후 확정)',
    ],
}
for label in MRT_THRESHOLDS:
    summary[label] = {}
    for station_name in STATIONS:
        summary[label][station_name] = {}
        for hour in TARGET_HOURS:
            r = all_results[label][station_name][hour]
            summary[label][station_name][f'h{hour:02d}'] = {
                'classic_nodes':     r['classic_count'],
                'thermal_nodes':     r['thermal_count'],
                'lost_count':        r['lost_count'],
                'reduction_pct':     r['reduction_pct'],
                'classic_length_m':  r['classic_length_m'],
                'thermal_length_m':  r['thermal_length_m'],
                'lost_length_m':     r['lost_length_m'],
                'reduction_pct_len': r['reduction_pct_len'],
                'hot_edges_removed': r['hot_edges_removed'],
            }

out_json = os.path.join(RES_DIR, 'catchment_mrt_summary.json')
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"\n결과 저장: {out_json}")


# ── 최종 요약 출력 ─────────────────────────────────────────────────────────
print("\n=== Method 4 최종 요약 (13시) ===")
print(f"{'역':<8} {'50°C':>8} {'55°C':>8} {'58°C':>8}")
print("-" * 38)
for s in station_names:
    vals = [all_results[l][s][13]['reduction_pct'] for l in ['low', 'mid', 'high']]
    print(f"{s:<8} {vals[0]:>6.1f}%  {vals[1]:>6.1f}%  {vals[2]:>6.1f}%")

if m1_summary:
    print("\n  (참고) Method 1 UTCI≥38°C 기준 13시:")
    for s in station_names:
        print(f"  {s:<8} {get_m1_pct(s):>6.1f}%")

print("\n=== Method 4 완료 ===")
