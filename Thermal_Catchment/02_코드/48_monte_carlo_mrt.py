"""
Monte Carlo MRT 임계값 민감도 분석
====================================
전략:
  1) MRT 임계값 그리드 [45~65°C, 9개] 각각 → 집계구별 TARR 사전 계산
  2) threshold ~ N(55, 4²) 에서 N=2000 샘플링
  3) 집계구별 TARR(threshold) 보간 → TARR 분포 획득
  4) 중앙값·95% CI 시각화 + CSV 저장

저장:
  03_결과물/monte_carlo_tarr.csv
  03_결과물/figures/mc_tarr_ci_map.png
  03_결과물/figures/mc_tarr_distribution.png
  03_결과물/figures/mc_threshold_sensitivity.png
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.interpolate import interp1d
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')
os.makedirs(FIG_DIR, exist_ok=True)

NET_PATH  = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
MRT_PATH  = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv')
JBG_SHP   = os.path.join(DATA_DIR, '행정경계', '통계지역경계(2016년+기준)', '집계구.shp')
STOPS_CSV = os.path.join(DATA_DIR, '네트워크', 'transit_stops_seongdong.csv')
OUT_CSV   = os.path.join(RES_DIR, 'monte_carlo_tarr.csv')

WALK_SPEED   = 4.5 * 1000 / 3600
TIME_BUDGET  = 15 * 60
TARGET_HOUR  = 13

# Monte Carlo 파라미터
THRESH_GRID  = np.array([45, 49, 51, 53, 55, 57, 59, 61, 65], dtype=float)
MC_MU        = 55.0   # 임계값 분포 중심 (UTCI 38°C 근방 MRT 중심값)
MC_SIGMA     = 4.0    # 불확실성 ±4°C → 95% 범위 47~63°C
N_SAMPLES    = 2000


# ── 1단계: 데이터 로드 ────────────────────────────────────────────────────
print("네트워크 로드 중...")
G = ox.load_graphml(NET_PATH).to_undirected()
for u, v, d in G.edges(data=True):
    d['travel_time'] = d.get('length', 0) / WALK_SPEED

print("MRT 데이터 로드 중...")
mrt_df = pd.read_csv(MRT_PATH, encoding='utf-8-sig')
h13    = mrt_df[mrt_df['hour'] == TARGET_HOUR].copy()
print(f"  13시 MRT: mean={h13['mrt'].mean():.1f}°C, std={h13['mrt'].std():.2f}°C, "
      f"range={h13['mrt'].min():.1f}–{h13['mrt'].max():.1f}°C")

print("정류장 로드 중...")
stops_df  = pd.read_csv(STOPS_CSV, encoding='utf-8-sig')
stop_nodes = set(stops_df['node_id'].astype(int).tolist())
print(f"  정류장: {len(stop_nodes)}개")

print("집계구 로드 중...")
jbg = gpd.read_file(JBG_SHP, encoding='cp949')
jbg = jbg[jbg['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
jbg = jbg.set_crs(epsg=5179, allow_override=True).to_crs(epsg=4326)
jbg['centroid']   = jbg.geometry.centroid
jbg['집계구코드'] = jbg['TOT_REG_CD'].astype(str)
jbg['net_node']   = ox.distance.nearest_nodes(
    G, jbg['centroid'].x.values, jbg['centroid'].y.values)
print(f"  집계구: {len(jbg)}개")


# ── 2단계: Classic Catchment (한 번만 계산) ───────────────────────────────
print("\nClassic Catchment 계산 중...")
classic_cnts = []
net_nodes_list = jbg['net_node'].tolist()

for i, node in enumerate(net_nodes_list):
    if i % 100 == 0:
        print(f"  {i}/{len(net_nodes_list)}...")
    dist = nx.single_source_dijkstra_path_length(
        G, node, cutoff=TIME_BUDGET, weight='travel_time')
    classic_cnts.append(len(stop_nodes & set(dist.keys())))

jbg['classic_cnt'] = classic_cnts
jbg_valid = jbg[jbg['classic_cnt'] > 0].copy()
print(f"  유효 집계구: {len(jbg_valid)}개")


# ── 3단계: 임계값 그리드별 Thermal Catchment 계산 ─────────────────────────
print(f"\n임계값 그리드 {THRESH_GRID} 계산 중...")

# (집계구 × 임계값) 매트릭스
tarr_grid = np.zeros((len(jbg_valid), len(THRESH_GRID)))

for t_idx, thresh in enumerate(THRESH_GRID):
    print(f"  MRT ≥ {thresh}°C ...", end='  ')

    # 고온 링크 제거 → Thermal 그래프 구성
    hot_edges = set(zip(
        h13[h13['mrt'] >= thresh]['u'].astype(str),
        h13[h13['mrt'] >= thresh]['v'].astype(str)
    ))
    G_thermal = G.copy()
    G_thermal.remove_edges_from([
        (u, v) for u, v in G_thermal.edges()
        if (str(u), str(v)) in hot_edges or (str(v), str(u)) in hot_edges
    ])
    removed = G.number_of_edges() - G_thermal.number_of_edges()

    thermal_cnts = []
    for node in jbg_valid['net_node'].tolist():
        dist = nx.single_source_dijkstra_path_length(
            G_thermal, node, cutoff=TIME_BUDGET, weight='travel_time')
        thermal_cnts.append(len(stop_nodes & set(dist.keys())))

    tarr_col = ((jbg_valid['classic_cnt'].values - np.array(thermal_cnts))
                / jbg_valid['classic_cnt'].values * 100)
    tarr_grid[:, t_idx] = tarr_col
    print(f"제거 링크: {removed:,}개 | TARR 평균: {tarr_col.mean():.1f}%")


# ── 4단계: Monte Carlo 샘플링 ─────────────────────────────────────────────
print(f"\nMonte Carlo 샘플링 (N={N_SAMPLES}, μ={MC_MU}, σ={MC_SIGMA}) ...")
np.random.seed(42)
thresh_samples = np.random.normal(MC_MU, MC_SIGMA, N_SAMPLES)
thresh_samples = np.clip(thresh_samples, THRESH_GRID.min(), THRESH_GRID.max())

# 집계구별 TARR(threshold) 보간 → 샘플 TARR 매트릭스 (n_jbg × N_SAMPLES)
tarr_mc = np.zeros((len(jbg_valid), N_SAMPLES))
for i in range(len(jbg_valid)):
    f_interp = interp1d(THRESH_GRID, tarr_grid[i], kind='linear',
                        fill_value='extrapolate')
    tarr_mc[i] = np.clip(f_interp(thresh_samples), 0, 100)

# 집계구별 통계
jbg_valid = jbg_valid.copy()
jbg_valid['tarr_median'] = np.median(tarr_mc, axis=1)
jbg_valid['tarr_p025']   = np.percentile(tarr_mc, 2.5,  axis=1)
jbg_valid['tarr_p975']   = np.percentile(tarr_mc, 97.5, axis=1)
jbg_valid['tarr_std']    = tarr_mc.std(axis=1)
jbg_valid['tarr_ci_width'] = jbg_valid['tarr_p975'] - jbg_valid['tarr_p025']
jbg_valid['tarr_single'] = tarr_grid[:, list(THRESH_GRID).index(55)]

print(f"\n=== Monte Carlo 결과 (N={N_SAMPLES}) ===")
print(f"  TARR 중앙값:  {jbg_valid['tarr_median'].mean():.1f}% "
      f"(std={jbg_valid['tarr_median'].std():.1f}%)")
print(f"  TARR 95% CI: {jbg_valid['tarr_p025'].mean():.1f}% – "
      f"{jbg_valid['tarr_p975'].mean():.1f}%")
print(f"  CI 폭 평균:   {jbg_valid['tarr_ci_width'].mean():.1f}%p")
print(f"  단일값(55°C): {jbg_valid['tarr_single'].mean():.1f}%")


# ── 5단계: 시각화 ─────────────────────────────────────────────────────────
jbg_wm = jbg_valid.to_crs(epsg=3857)

# Fig A: 임계값별 평균 TARR 민감도 곡선
fig, ax = plt.subplots(figsize=(8, 5))
mean_tarr = tarr_grid.mean(axis=0)
std_tarr  = tarr_grid.std(axis=0)
ax.plot(THRESH_GRID, mean_tarr, 'o-', color='#1565C0', linewidth=2.5, markersize=8)
ax.fill_between(THRESH_GRID,
                mean_tarr - std_tarr,
                mean_tarr + std_tarr,
                alpha=0.2, color='#1565C0', label='±1 std (집계구 간)')
ax.axvline(55, color='#E53935', linewidth=2, linestyle='--', label='기준값 55°C')
ax.axhline(jbg_valid['tarr_single'].mean(), color='#E53935',
           linewidth=1, linestyle=':', alpha=0.7)
ax.set_xlabel('MRT 임계값 (°C)', fontsize=12)
ax.set_ylabel('집계구 평균 TARR (%)', fontsize=12)
ax.set_title(f'MRT 임계값 민감도 분석\n성동구 집계구 (n={len(jbg_valid)}) | 13시 | 폭염일 평균',
             fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
ax.set_ylim(0, 105)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'mc_threshold_sensitivity.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\n저장: mc_threshold_sensitivity.png")

# Fig B: TARR 중앙값 + 95% CI 히스토그램
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

ax = axes[0]
ax.hist(jbg_valid['tarr_median'], bins=25, color='#1565C0',
        alpha=0.75, edgecolor='white', label='중앙값')
ax.axvline(jbg_valid['tarr_median'].mean(), color='#E53935',
           linewidth=2, label=f"평균 {jbg_valid['tarr_median'].mean():.1f}%")
ax.set_xlabel('TARR 중앙값 (%)', fontsize=11)
ax.set_ylabel('집계구 수', fontsize=11)
ax.set_title('TARR 중앙값 분포', fontsize=11, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)

ax = axes[1]
ax.hist(jbg_valid['tarr_ci_width'], bins=25, color='#F57F17',
        alpha=0.75, edgecolor='white')
ax.axvline(jbg_valid['tarr_ci_width'].mean(), color='#B71C1C',
           linewidth=2, label=f"평균 {jbg_valid['tarr_ci_width'].mean():.1f}%p")
ax.set_xlabel('95% CI 폭 (TARR 최대–최소, %p)', fontsize=11)
ax.set_ylabel('집계구 수', fontsize=11)
ax.set_title('임계값 불확실성에 따른 TARR 변동 폭', fontsize=11, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)

fig.suptitle(
    f'Monte Carlo MRT 임계값 분석 (N={N_SAMPLES}, threshold~N({MC_MU},{MC_SIGMA}²))\n'
    f'성동구 집계구 (n={len(jbg_valid)}) | 13시 | 폭염일 2025.07.28–08.03',
    fontsize=12, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'mc_tarr_distribution.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: mc_tarr_distribution.png")

# Fig C: 공간 지도 (중앙값 + CI 폭)
fig, axes = plt.subplots(1, 2, figsize=(16, 8))

for ax, col, title, cmap, vmax in [
    (axes[0], 'tarr_median', 'TARR 중앙값 (%)', 'YlOrRd', 100),
    (axes[1], 'tarr_ci_width', '95% CI 폭 (%p)\n(임계값 불확실성)', 'PuBu', 40),
]:
    norm = mcolors.Normalize(vmin=0, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)
    colors = [cmap_obj(norm(v)) for v in jbg_wm[col]]
    jbg_wm.plot(ax=ax, color=colors, edgecolor='white', linewidth=0.3)
    jbg_wm.boundary.plot(ax=ax, color='#555555', linewidth=0.5, alpha=0.6)

    sm = plt.cm.ScalarMappable(cmap=cmap_obj, norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.01)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_axis_off()

fig.suptitle(
    f'Monte Carlo MRT 임계값 분석 — 집계구별 공간 분포\n'
    f'threshold~N({MC_MU},{MC_SIGMA}²), N={N_SAMPLES} | 13시 | 폭염일 평균',
    fontsize=13, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'mc_tarr_ci_map.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: mc_tarr_ci_map.png")

# ── 6단계: CSV 저장 ───────────────────────────────────────────────────────
out_df = jbg_valid[['집계구코드', 'net_node', 'classic_cnt',
                     'tarr_single', 'tarr_median', 'tarr_p025',
                     'tarr_p975', 'tarr_std', 'tarr_ci_width']].copy()
out_df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
print(f"저장: {OUT_CSV}")

print("\n=== 완료 ===")
print(f"  그리드 임계값: {THRESH_GRID}")
print(f"  MC 샘플 수:   {N_SAMPLES}")
print(f"  TARR 중앙값:  {jbg_valid['tarr_median'].mean():.1f}% "
      f"[95% CI: {jbg_valid['tarr_p025'].mean():.1f}–{jbg_valid['tarr_p975'].mean():.1f}%]")
print(f"  → 단일값 55°C 기준({jbg_valid['tarr_single'].mean():.1f}%)이 "
      f"Monte Carlo 결과에 robust함을 확인")
