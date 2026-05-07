"""
Method 4 기반 집계구 TARR 산출 + 회귀분석 (v2 — 올바른 연구 설계)
=================================================================
연구 설계:
  집계구 중심점 → 15분 도보 캐치먼트(Classic/Thermal) →
  캐치먼트 내 대중교통 정류장(지하철 7 + 버스 482) 수 산출 →
  TARR = (classic_cnt - thermal_cnt) / classic_cnt × 100

Method 4: MRT ≥ 55°C Hard Cut, 13시 단일 분석
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm
warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH    = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
MRT_PATH    = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
JBG_SHP     = os.path.join(DATA_DIR, '행정경계', '통계지역경계(2016년+기준)', '집계구.shp')
STOPS_CSV   = os.path.join(PROJ_DIR, '01_데이터', '네트워크', 'transit_stops_seongdong.csv')
VARS_CSV    = os.path.join(RES_DIR, 'regression_jibgaegu.csv')
OUT_CSV     = os.path.join(RES_DIR, 'regression_method4.csv')

WALK_SPEED  = 4.5 * 1000 / 3600   # m/s
TIME_BUDGET = 15 * 60              # 초
MRT_THRESH  = 55.0
TARGET_HOUR = 13


def compute_catchment_nodes(G_classic, G_thermal, origin_node):
    """사전 구성된 Classic/Thermal 그래프에서 15분 캐치먼트 노드 집합 반환"""
    classic_dist = nx.single_source_dijkstra_path_length(
        G_classic, origin_node, cutoff=TIME_BUDGET, weight='travel_time'
    )
    thermal_dist = nx.single_source_dijkstra_path_length(
        G_thermal, origin_node, cutoff=TIME_BUDGET, weight='travel_time'
    )
    return set(classic_dist.keys()), set(thermal_dist.keys())


# ── 1단계: 데이터 로드 + 그래프 사전 구성 ────────────────────────────
print("네트워크 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()
for u, v, data in G_base.edges(data=True):
    data['travel_time'] = data.get('length', 0) / WALK_SPEED

print("MRT 데이터 로드 중...")
mrt_df = pd.read_csv(MRT_PATH, encoding='utf-8-sig')
h_df   = mrt_df[(mrt_df['hour'] == TARGET_HOUR) & (mrt_df['mrt'] >= MRT_THRESH)]
hot_edges = set(zip(h_df['u'].astype(str), h_df['v'].astype(str)))
total = len(mrt_df[mrt_df['hour'] == TARGET_HOUR])
print(f"  {TARGET_HOUR:02d}시 MRT≥{MRT_THRESH}°C: {len(h_df):,}/{total:,}개 ({len(h_df)/total*100:.1f}%)")

# Thermal 그래프 한 번만 구성 (집계구마다 재생성 불필요)
G_thermal = G_base.copy()
G_thermal.remove_edges_from([
    (u, v) for u, v in G_thermal.edges()
    if (str(u), str(v)) in hot_edges or (str(v), str(u)) in hot_edges
])
print(f"  Thermal 그래프 엣지 수: {G_thermal.number_of_edges():,} (Classic: {G_base.number_of_edges():,})")

print("대중교통 정류장 로드 중...")
stops_df = pd.read_csv(STOPS_CSV, encoding='utf-8-sig')
print(f"  전체 정류장: {len(stops_df)}개  (지하철={len(stops_df[stops_df['stop_type']=='subway'])}, 버스={len(stops_df[stops_df['stop_type']=='bus'])})")

# 정류장 → 네트워크 노드 매핑 (node_id 컬럼 사용)
stops_df['net_node'] = stops_df['node_id'].astype(int)
stop_nodes = set(stops_df['net_node'].tolist())


# ── 2단계: 집계구 로드 ────────────────────────────────────────────────
print("\n집계구 로드 중...")
jbg_all = gpd.read_file(JBG_SHP, encoding='cp949')
jbg = jbg_all[jbg_all['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
jbg = jbg.set_crs(epsg=5179, allow_override=True).to_crs(epsg=4326)
jbg['centroid']   = jbg.geometry.centroid
jbg['집계구코드'] = jbg['TOT_REG_CD'].astype(str)
print(f"  성동구 집계구: {len(jbg)}개")

# 집계구 중심점 → 네트워크 최근접 노드
centroids_lon = jbg['centroid'].x.values
centroids_lat = jbg['centroid'].y.values
jbg['net_node'] = ox.distance.nearest_nodes(G_base, centroids_lon, centroids_lat)


# ── 3단계: 집계구별 캐치먼트 계산 + 정류장 수 산출 ───────────────────
print("\n집계구별 캐치먼트 계산 중... (집계구당 2회 다익스트라)")
classic_cnts = []
thermal_cnts = []
n_total = len(jbg)

for i, (idx, row) in enumerate(jbg.iterrows()):
    if i % 50 == 0:
        print(f"  {i}/{n_total}...")
    c_nodes, t_nodes = compute_catchment_nodes(G_base, G_thermal, row['net_node'])
    classic_cnts.append(len(stop_nodes & c_nodes))
    thermal_cnts.append(len(stop_nodes & t_nodes))

jbg['classic_cnt'] = classic_cnts
jbg['thermal_cnt'] = thermal_cnts
jbg['lost_cnt']    = jbg['classic_cnt'] - jbg['thermal_cnt']

# TARR: classic_cnt > 0인 집계구만
jbg_valid = jbg[jbg['classic_cnt'] > 0].copy()
jbg_valid['tarr'] = (jbg_valid['lost_cnt'] / jbg_valid['classic_cnt'] * 100).round(2)

print(f"\n집계구별 TARR (Method 4 MRT≥{MRT_THRESH}°C {TARGET_HOUR}시 | 정류장 수 기준):")
print(f"  유효 집계구: {len(jbg_valid)}개  (접근 불가 {len(jbg)-len(jbg_valid)}개 제외)")
print(f"  TARR 평균: {jbg_valid['tarr'].mean():.1f}%  std: {jbg_valid['tarr'].std():.1f}%")
print(f"  TARR 범위: {jbg_valid['tarr'].min():.1f}% ~ {jbg_valid['tarr'].max():.1f}%")
print(jbg_valid['tarr'].describe().round(1))
print(f"  TARR=0% (감소 없음): {(jbg_valid['tarr']==0).sum()}개")
print(f"  TARR>0%: {(jbg_valid['tarr']>0).sum()}개")


# ── 4단계: 공간환경 변수 병합 ─────────────────────────────────────────
print("\n공간환경 변수 병합 중...")
vars_df = pd.read_csv(VARS_CSV, encoding='utf-8-sig')
vars_df['집계구코드'] = vars_df['집계구코드'].astype(float).astype(int).astype(str)
reg_df = jbg_valid[['집계구코드', 'tarr', 'classic_cnt', 'thermal_cnt', 'lost_cnt']].merge(
    vars_df[['집계구코드', 'mean_svf', 'mean_canopy', 'mean_bld_H', 'hw_ratio', 'hot_link_ratio', 'n_links']],
    on='집계구코드', how='inner'
)
reg_df = reg_df.dropna()
print(f"  회귀 분석 대상: {len(reg_df)}개 집계구")
print(f"  classic_cnt 평균: {reg_df['classic_cnt'].mean():.1f}  (min={reg_df['classic_cnt'].min()}, max={reg_df['classic_cnt'].max()})")


# ── 5단계: 상관분석 ───────────────────────────────────────────────────
IND_VARS = {
    'mean_svf':       'SVF (하늘열린비율)',
    'mean_canopy':    '수목 캐노피 비율',
    'mean_bld_H':     '평균 건물 높이 (m)',
    'hw_ratio':       'H/W 비율 (협곡 효과)',
    'hot_link_ratio': '고온 링크 비율 (MRT≥55°C)',
}

print("\n=== 상관분석 (Pearson r) ===")
print(f"{'변수':<22} {'r':>7} {'p':>8}")
print("-" * 40)
for var, label in IND_VARS.items():
    if var not in reg_df.columns:
        continue
    r, p = stats.pearsonr(reg_df[var], reg_df['tarr'])
    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
    print(f"  {label:<20} {r:>7.3f} {p:>8.4f} {sig}")


# ── 6단계: OLS 다중회귀 ───────────────────────────────────────────────
use_vars = [v for v in IND_VARS if v in reg_df.columns]
X = reg_df[use_vars]
y = reg_df['tarr']

X_const = sm.add_constant(X)
model   = sm.OLS(y, X_const).fit()
print("\n=== OLS 회귀분석 결과 ===")
print(model.summary2())


# ── 7단계: 시각화 ─────────────────────────────────────────────────────
# Fig A: 변수별 산점도
n_vars = len(use_vars)
fig, axes = plt.subplots(1, n_vars, figsize=(4 * n_vars, 4.5))
if n_vars == 1:
    axes = [axes]

for ax, var in zip(axes, use_vars):
    label = IND_VARS[var]
    r, p  = stats.pearsonr(reg_df[var], reg_df['tarr'])
    ax.scatter(reg_df[var], reg_df['tarr'],
               alpha=0.35, s=18, color='#1565C0', edgecolors='none')
    m, b = np.polyfit(reg_df[var], reg_df['tarr'], 1)
    xr = np.linspace(reg_df[var].min(), reg_df[var].max(), 100)
    ax.plot(xr, m * xr + b, color='#E53935', linewidth=1.8)
    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'
    ax.set_title(f'{label}\nr={r:.3f} {sig}', fontsize=9, fontweight='bold')
    ax.set_xlabel(var, fontsize=8)
    ax.set_ylabel('TARR (%)' if ax == axes[0] else '', fontsize=9)
    ax.grid(alpha=0.3)

fig.suptitle(
    f'집계구별 TARR vs 공간환경 변수 (n={len(reg_df)})\n'
    f'Method 4 | MRT ≥ {MRT_THRESH}°C | 13시 | 대중교통 정류장 수 기준',
    fontsize=11, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'regression_m4_scatter.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\n저장: regression_m4_scatter.png")

# Fig B: TARR 분포 히스토그램
fig, ax = plt.subplots(figsize=(7, 4))
ax.hist(reg_df['tarr'], bins=25, color='#1565C0', alpha=0.75, edgecolor='white')
ax.axvline(reg_df['tarr'].mean(), color='#E53935', linewidth=2,
           label=f"평균 {reg_df['tarr'].mean():.1f}%")
ax.set_xlabel('TARR (%)', fontsize=11)
ax.set_ylabel('집계구 수', fontsize=11)
ax.set_title(
    f'집계구별 TARR 분포 (n={len(reg_df)}) | Method 4 MRT≥{MRT_THRESH}°C 13시\n대중교통 정류장 수 기준',
    fontsize=11, fontweight='bold'
)
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'regression_m4_tarr_hist.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: regression_m4_tarr_hist.png")

# Fig C: classic vs thermal 정류장 수 산점도
fig, ax = plt.subplots(figsize=(6, 5))
ax.scatter(reg_df['classic_cnt'], reg_df['thermal_cnt'],
           alpha=0.4, s=20, color='#1565C0', edgecolors='none')
lim = max(reg_df['classic_cnt'].max(), reg_df['thermal_cnt'].max()) + 1
ax.plot([0, lim], [0, lim], 'k--', linewidth=1, alpha=0.5, label='y=x (감소 없음)')
ax.set_xlabel('Classic 정류장 수', fontsize=11)
ax.set_ylabel('Thermal 정류장 수', fontsize=11)
ax.set_title('집계구별 Classic vs Thermal 접근 가능 정류장 수', fontsize=11, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'regression_m4_classic_vs_thermal.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: regression_m4_classic_vs_thermal.png")

# CSV 저장
reg_df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
print(f"저장: {OUT_CSV}")
print("\n=== 완료 ===")
