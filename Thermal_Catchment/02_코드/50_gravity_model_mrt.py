"""
MRT 기반 중력모델 접근성 분석
==============================
Classic / Thermal Catchment 각각에 대해 Gaussian 중력모델 적용

  A_i = Σ_j exp(-0.5 × (t_ij / t0)²)   [t0 = TIME_BUDGET = 15분]

  - Classic: 열환경 무시 네트워크
  - Thermal: MRT ≥ 55°C 링크 제거 네트워크

  중력 감소율(%) = (A_classic - A_thermal) / A_classic × 100

저장:
  03_결과물/gravity_mrt_results.csv
  03_결과물/figures/gravity_classic_map.png
  03_결과물/figures/gravity_thermal_map.png
  03_결과물/figures/gravity_reduction_map.png
  03_결과물/figures/gravity_vs_count_scatter.png
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH       = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
MRT_PATH       = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
JBG_SHP        = os.path.join(DATA_DIR, '행정경계', '통계지역경계(2016년+기준)', '집계구.shp')
STOPS_CSV      = os.path.join(DATA_DIR, '네트워크', 'transit_stops_seongdong.csv')
STOP_TIMES_TXT = '/Users/jin/석사논문/TAVI/GTFS_Korea/GTFSanalysis_2025/stop_times_cleaned.txt'
REG_CSV        = os.path.join(RES_DIR, 'regression_method4.csv')
OUT_CSV        = os.path.join(RES_DIR, 'gravity_mrt_results.csv')

# 지하철역 노선 수 (수동 입력)
SUBWAY_ROUTE_CNT = {
    'subway_왕십리역': 4,  # 2·5호선·분당선·경의중앙선
    'subway_행당역':   1,  # 5호선
    'subway_응봉역':   1,  # 경의중앙선
    'subway_뚝섬역':   1,  # 2호선
    'subway_성수역':   1,  # 2호선
    'subway_서울숲역': 1,  # 분당선
    'subway_옥수역':   2,  # 3호선·경의중앙선
}

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
TARGET_HOUR = 13
MRT_THRESH  = 55.0
T0          = TIME_BUDGET          # Gaussian decay 기준 (15분 = 900초)


# ── 1단계: 데이터 로드 ────────────────────────────────────────────────────
print("네트워크 로드 중...")
G = ox.load_graphml(NET_PATH).to_undirected()
for u, v, d in G.edges(data=True):
    d['travel_time'] = d.get('length', 0) / WALK_SPEED

print("MRT 데이터 로드 중...")
mrt_df = pd.read_csv(MRT_PATH, encoding='utf-8-sig')
h13 = mrt_df[mrt_df['hour'] == TARGET_HOUR].copy()
print(f"  13시 MRT: mean={h13['mrt'].mean():.1f}°C, "
      f"range={h13['mrt'].min():.1f}–{h13['mrt'].max():.1f}°C")

print("정류장 로드 중...")
stops_df = pd.read_csv(STOPS_CSV, encoding='utf-8-sig')

# ── 버스 노선 수 계산 (stop_times_cleaned.txt) ──
print("  버스 노선 수 계산 중...")
bus_ids = set(stops_df[stops_df['stop_type'] == 'bus']['stop_id'].tolist())
st = pd.read_csv(STOP_TIMES_TXT, usecols=['trip_id', 'stop_id'])
st['route_id'] = st['trip_id'].str.replace(r'_Ord\d+$', '', regex=True)
bus_route_cnt = (st[st['stop_id'].isin(bus_ids)]
                 .groupby('stop_id')['route_id'].nunique()
                 .to_dict())

# ── 정류장별 노선 수(가중치) 부여 ──
def get_weight(row):
    if row['stop_type'] == 'subway':
        return SUBWAY_ROUTE_CNT.get(row['stop_id'], 1)
    return bus_route_cnt.get(row['stop_id'], 1)

stops_df['weight'] = stops_df.apply(get_weight, axis=1)
stop_weight = dict(zip(stops_df['node_id'].astype(int), stops_df['weight']))
stop_set    = set(stop_weight.keys())
print(f"  정류장: {len(stop_set)}개 | 평균 노선 수: {stops_df['weight'].mean():.2f}")
print(f"  노선 수 분포: min={stops_df['weight'].min()} / "
      f"median={stops_df['weight'].median():.0f} / max={stops_df['weight'].max()}")

print("집계구 로드 중...")
jbg = gpd.read_file(JBG_SHP, encoding='cp949')
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
jbg = jbg.set_crs(epsg=5179, allow_override=True).to_crs(epsg=4326)
jbg['centroid']   = jbg.geometry.centroid
jbg['집계구코드'] = jbg['TOT_REG_CD'].astype(str)
jbg['net_node']   = ox.distance.nearest_nodes(
    G, jbg['centroid'].x.values, jbg['centroid'].y.values)

# 기존 count 기반 결과 (비교용)
reg_df = pd.read_csv(REG_CSV, encoding='utf-8-sig')
reg_df['집계구코드'] = reg_df['집계구코드'].astype(str)

# 유효 집계구만 (classic_cnt > 0)
jbg_valid = jbg[jbg['집계구코드'].isin(reg_df['집계구코드'])].copy()
jbg_valid = jbg_valid.merge(
    reg_df[['집계구코드', 'classic_cnt', 'thermal_cnt', 'tarr']],
    on='집계구코드'
)
jbg_valid = jbg_valid[jbg_valid['classic_cnt'] > 0].copy().reset_index(drop=True)
print(f"  유효 집계구: {len(jbg_valid)}개")


# ── 2단계: Thermal 그래프 구성 ────────────────────────────────────────────
print(f"\nMRT ≥ {MRT_THRESH}°C 링크 제거 중...")
hot_edges = set(zip(
    h13[h13['mrt'] >= MRT_THRESH]['u'].astype(str),
    h13[h13['mrt'] >= MRT_THRESH]['v'].astype(str)
))
G_thermal = G.copy()
G_thermal.remove_edges_from([
    (u, v) for u, v in G_thermal.edges()
    if (str(u), str(v)) in hot_edges or (str(v), str(u)) in hot_edges
])
print(f"  제거 링크: {G.number_of_edges() - G_thermal.number_of_edges():,}개")


# ── 3단계: Gaussian decay 함수 ────────────────────────────────────────────
def gaussian_decay(t_sec, t0=T0):
    return np.exp(-0.5 * (t_sec / t0) ** 2)


# ── 4단계: 집계구별 중력 접근성 계산 ─────────────────────────────────────
print(f"\n중력모델 계산 중 (n={len(jbg_valid)})...")
a_classic_list = []
a_thermal_list = []

for i, row in jbg_valid.iterrows():
    if i % 100 == 0:
        print(f"  {i}/{len(jbg_valid)}...")

    node = row['net_node']

    # Classic: Dijkstra → 정류장까지 이동시간 → 노선 수 가중 Gaussian 합산
    dist_c = nx.single_source_dijkstra_path_length(
        G, node, cutoff=TIME_BUDGET, weight='travel_time')
    a_c = sum(stop_weight[n] * gaussian_decay(t)
              for n, t in dist_c.items() if n in stop_set)

    # Thermal: 고온 링크 제거 네트워크
    dist_t = nx.single_source_dijkstra_path_length(
        G_thermal, node, cutoff=TIME_BUDGET, weight='travel_time')
    a_t = sum(stop_weight[n] * gaussian_decay(t)
              for n, t in dist_t.items() if n in stop_set)

    a_classic_list.append(a_c)
    a_thermal_list.append(a_t)

jbg_valid = jbg_valid.copy()
jbg_valid['A_classic']   = a_classic_list
jbg_valid['A_thermal']   = a_thermal_list
jbg_valid['A_loss']      = jbg_valid['A_classic'] - jbg_valid['A_thermal']
jbg_valid['gravity_reduction'] = np.where(
    jbg_valid['A_classic'] > 0,
    jbg_valid['A_loss'] / jbg_valid['A_classic'] * 100,
    0.0
)

print(f"\n=== 중력모델 결과 (노선 수 가중치 적용) ===")
print(f"  A_classic 평균:          {jbg_valid['A_classic'].mean():.3f}")
print(f"  A_thermal 평균:          {jbg_valid['A_thermal'].mean():.3f}")
print(f"  중력 감소율 평균:         {jbg_valid['gravity_reduction'].mean():.1f}%")
print(f"  단순 카운트 TARR 평균:    {jbg_valid['tarr'].mean():.1f}%")
print(f"  두 지표 상관계수:         {jbg_valid['gravity_reduction'].corr(jbg_valid['tarr']):.3f}")


# ── 5단계: 시각화 ─────────────────────────────────────────────────────────
jbg_wm = jbg_valid.to_crs(epsg=3857)

# Fig A: Classic / Thermal / 감소율 3패널 지도
fig, axes = plt.subplots(1, 3, figsize=(20, 7))
configs = [
    ('A_classic',         '중력모델 Classic 접근성\n(열환경 무시)',     'Blues',  None),
    ('A_thermal',         '중력모델 Thermal 접근성\n(MRT≥55°C 차단)',  'Blues',  None),
    ('gravity_reduction', '중력 기반 접근성 감소율 (%)\n(MRT 55°C 기준)', 'YlOrRd', 100),
]
for ax, (col, title, cmap, vmax) in zip(axes, configs):
    vmin = 0
    vmax_ = vmax if vmax else jbg_wm[col].quantile(0.98)
    norm  = mcolors.Normalize(vmin=vmin, vmax=vmax_)
    colors = [plt.get_cmap(cmap)(norm(v)) for v in jbg_wm[col]]
    jbg_wm.plot(ax=ax, color=colors, edgecolor='white', linewidth=0.3)
    jbg_wm.boundary.plot(ax=ax, color='#555555', linewidth=0.5, alpha=0.6)
    sm = plt.cm.ScalarMappable(cmap=plt.get_cmap(cmap), norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.01)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_axis_off()

fig.suptitle(
    f'MRT 기반 Gaussian 중력모델 접근성 (노선 수 가중치) — 성동구 집계구 (n={len(jbg_valid)})\n'
    f'13시 | 폭염일 평균 | t0=15분 | MRT 임계값 55°C | S_j = 정류장별 노선 수',
    fontsize=13, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'gravity_mrt_map.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\n저장: gravity_mrt_map.png")

# Fig B: 단순 카운트 TARR vs 중력 감소율 산점도
fig, ax = plt.subplots(figsize=(7, 6))
ax.scatter(jbg_valid['tarr'], jbg_valid['gravity_reduction'],
           alpha=0.5, s=20, color='#1565C0', edgecolors='none')
ax.plot([0, 100], [0, 100], 'r--', linewidth=1.5, label='y = x (1:1)')

# 회귀선
from numpy.polynomial import polynomial as P
x = jbg_valid['tarr'].values
y = jbg_valid['gravity_reduction'].values
mask = np.isfinite(x) & np.isfinite(y)
coef = np.polyfit(x[mask], y[mask], 1)
xfit = np.linspace(0, 100, 100)
ax.plot(xfit, np.polyval(coef, xfit), '#E53935', linewidth=2,
        label=f'회귀선 (기울기={coef[0]:.2f})')

r = np.corrcoef(x[mask], y[mask])[0, 1]
ax.set_xlabel('단순 카운트 기반 접근성 감소율 (%)', fontsize=12)
ax.set_ylabel('중력모델 기반 접근성 감소율 (%)', fontsize=12)
ax.set_title(
    f'단순 카운트 vs 중력모델(노선 수 가중) 접근성 감소율 비교\n'
    f'r = {r:.3f} | n={len(jbg_valid)} | MRT 55°C 기준, 13시',
    fontsize=11, fontweight='bold'
)
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
ax.set_xlim(0, 105); ax.set_ylim(0, 105)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'gravity_vs_count_scatter.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: gravity_vs_count_scatter.png")


# ── 6단계: CSV 저장 ───────────────────────────────────────────────────────
out_df = jbg_valid[['집계구코드', 'net_node', 'classic_cnt', 'thermal_cnt',
                     'tarr', 'A_classic', 'A_thermal', 'A_loss',
                     'gravity_reduction']].copy()
out_df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
print(f"저장: {OUT_CSV}")

print("\n=== 완료 ===")
print(f"  단순 TARR 평균:      {jbg_valid['tarr'].mean():.1f}%")
print(f"  중력 감소율 평균:    {jbg_valid['gravity_reduction'].mean():.1f}%")
print(f"  두 지표 상관:        r = {jbg_valid['gravity_reduction'].corr(jbg_valid['tarr']):.3f}")
