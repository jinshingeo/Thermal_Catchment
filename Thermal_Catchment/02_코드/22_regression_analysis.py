"""
회귀분석: 열환경 접근성 감소 결정 요인
========================================
Option A — 역 단위 (n=7): 캐치먼트 환경 특성 → 접근성 감소율 상관분석
Option B — 링크 단위 (n=7,819): 도로 환경 특성 → UTCI 결정 OLS 회귀

기반 데이터: SOLWEIG 모델 (19~20번) — 메인 분석
"""

import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
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

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
THRESHOLD   = 38.0

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171},
}
STATION_NAMES = list(STATIONS.keys())

# 역별 한강/중랑천까지 직선거리 (EPSG:5186 기준, 수동 측정)
# 한강 북안 대략 y ≈ 200,000 (5186), 중랑천 서안 대략 x ≈ 211,000
RIVER_DIST_M = {
    '옥수역':   80,    # 한강 바로 인접
    '응봉역':   150,   # 한강+중랑천 합류 인근
    '서울숲역': 350,   # 한강 인근
    '뚝섬역':   220,   # 한강 바로 인근
    '성수역':   900,   # 내륙
    '행당역':   750,   # 내륙
    '왕십리역': 1100,  # 내륙
}

# ── 데이터 로드 ────────────────────────────────────────────────────────
print("데이터 로드 중...")
G_base = ox.load_graphml(NET_PATH)
G_base = G_base.to_undirected()

svf_df  = pd.read_csv(os.path.join(RES_DIR, 'link_svf_canopy.csv'), encoding='utf-8-sig')
sol_df  = pd.read_csv(os.path.join(RES_DIR, 'link_utci_solweig.csv'), encoding='utf-8-sig')
corr_df = pd.read_csv(os.path.join(RES_DIR, 'link_utci_corrected.csv'), encoding='utf-8-sig')

with open(os.path.join(RES_DIR, 'catchment_solweig_summary.json'), encoding='utf-8') as f:
    summary = json.load(f)

# bridge 정보 병합 (corr_df 기준, 13시만)
bridge_info = corr_df[corr_df['hour'] == 13][['u', 'v', 'bridge', 'highway']].copy()
bridge_info['is_bridge'] = bridge_info['bridge'].isin(['yes', "['yes', 'viaduct']", 'viaduct']).astype(int)
bridge_dict = {(int(r['u']), int(r['v'])): r['is_bridge'] for _, r in bridge_info.iterrows()}
bridge_dict.update({(int(r['v']), int(r['u'])): r['is_bridge'] for _, r in bridge_info.iterrows()})

# SOLWEIG 13시 데이터
sol13 = sol_df[sol_df['hour'] == 13].copy()
sol13['is_bridge']   = sol13.apply(lambda r: bridge_dict.get((int(r['u']), int(r['v'])), 0), axis=1)
sol13['is_hot']      = (sol13['utci_final'] >= THRESHOLD).astype(int)
print(f"  링크 수: {len(sol13):,} | hot 링크: {sol13['is_hot'].sum():,}개 ({sol13['is_hot'].mean()*100:.1f}%)")

# 역 노드
for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G_base, info['lon'], info['lat'])


# ══════════════════════════════════════════════════════════════════════
# Option A: 역 단위 상관분석 (n=7)
# ══════════════════════════════════════════════════════════════════════
print("\n=== Option A: 역 단위 상관분석 ===")

# 각 역의 Classic catchment 내 링크 환경 변수 집계
def get_classic_nodes(G, node):
    for u, v, d in G.edges(data=True):
        d['travel_time'] = d.get('length', 0) / WALK_SPEED
    return set(nx.single_source_dijkstra_path_length(
        G, node, cutoff=TIME_BUDGET, weight='travel_time').keys())

# sol13 u,v를 int로 정규화
sol13['u'] = sol13['u'].astype(int)
sol13['v'] = sol13['v'].astype(int)

# sol13에 (u,v) → 환경 변수 딕셔너리
sol13_dict = {(int(r['u']), int(r['v'])): r for _, r in sol13.iterrows()}
sol13_dict.update({(int(r['v']), int(r['u'])): r for _, r in sol13.iterrows()})

station_vars = []
for sname in STATION_NAMES:
    sinfo = STATIONS[sname]
    classic_nodes = get_classic_nodes(G_base.copy(), sinfo['node'])

    # classic catchment 내 링크 필터
    link_svfs, link_canopy, link_hot, link_bridge = [], [], [], []
    for u, v in G_base.edges():
        if u in classic_nodes or v in classic_nodes:
            key = (int(u), int(v))
            if key in sol13_dict:
                r = sol13_dict[key]
                link_svfs.append(float(r['svf']))
                link_canopy.append(float(r['canopy_ratio']))
                link_hot.append(int(r['is_hot']))
                link_bridge.append(int(r['is_bridge']))

    n_links = len(link_svfs)
    station_vars.append({
        'station':        sname,
        'reduction_pct':  summary[sname]['h13']['reduction_pct'],
        'classic_nodes':  summary[sname]['h13']['classic_nodes'],
        'mean_svf':       np.mean(link_svfs)   if link_svfs   else np.nan,
        'mean_canopy':    np.mean(link_canopy) if link_canopy else np.nan,
        'hot_link_ratio': np.mean(link_hot)    if link_hot    else np.nan,
        'bridge_ratio':   np.mean(link_bridge) if link_bridge else np.nan,
        'river_dist_m':   RIVER_DIST_M[sname],
        'n_links':        n_links,
    })
    print(f"  {sname}: 감소율={station_vars[-1]['reduction_pct']}%  "
          f"SVF={station_vars[-1]['mean_svf']:.3f}  "
          f"교량={station_vars[-1]['bridge_ratio']*100:.1f}%  "
          f"하천거리={RIVER_DIST_M[sname]}m")

df_station = pd.DataFrame(station_vars)
df_station.to_csv(os.path.join(RES_DIR, 'regression_station_vars.csv'), index=False, encoding='utf-8-sig')

# 상관계수
target   = 'reduction_pct'
features = ['mean_svf', 'hot_link_ratio', 'bridge_ratio', 'river_dist_m', 'mean_canopy']
feat_labels = {
    'mean_svf':       '평균 SVF\n(개방도)',
    'hot_link_ratio': '고온링크\n비율',
    'bridge_ratio':   '교량링크\n비율',
    'river_dist_m':   '하천까지\n거리(m)',
    'mean_canopy':    '평균 캐노피\n비율',
}

print("\n  [Pearson 상관계수 vs 접근성 감소율]")
corr_results = {}
for f in features:
    r, p = stats.pearsonr(df_station[f], df_station[target])
    corr_results[f] = {'r': r, 'p': p}
    sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
    print(f"  {f:<20}: r={r:+.3f}  p={p:.3f} {sig}")

# ── Figure A: 산점도 매트릭스 ──────────────────────────────────────
print("\n  Figure A 생성 중...")
colors_map = {'응봉역':'#8E24AA','서울숲역':'#00ACC1','뚝섬역':'#43A047',
              '왕십리역':'#E53935','성수역':'#1E88E5','행당역':'#FB8C00','옥수역':'#6D4C41'}

fig, axes = plt.subplots(1, len(features), figsize=(16, 4))

for ax, feat in zip(axes, features):
    x = df_station[feat].values
    y = df_station[target].values
    r, p = corr_results[feat]['r'], corr_results[feat]['p']

    for _, row in df_station.iterrows():
        ax.scatter(row[feat], row[target],
                   color=colors_map[row['station']], s=120, zorder=3,
                   edgecolors='white', linewidths=0.8)
        ax.annotate(row['station'].replace('역',''), (row[feat], row[target]),
                    textcoords='offset points', xytext=(5, 3), fontsize=7.5)

    # 추세선
    if len(x) > 2:
        z = np.polyfit(x, y, 1)
        xr = np.linspace(x.min(), x.max(), 50)
        ax.plot(xr, np.polyval(z, xr), '--', color='gray', linewidth=1, alpha=0.7)

    sig = '***' if p < 0.01 else ('**' if p < 0.05 else ('*' if p < 0.1 else ''))
    ax.set_xlabel(feat_labels[feat], fontsize=9)
    ax.set_ylabel('접근성 감소율 (%)' if feat == features[0] else '', fontsize=9)
    ax.set_title(f'r = {r:+.2f}{sig}', fontsize=10, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.spines[['top','right']].set_visible(False)

fig.suptitle('역 단위 환경 변수 vs 접근성 감소율 상관분석 (n=7, SOLWEIG 13시)\n'
             '* p<0.1  ** p<0.05  *** p<0.01',
             fontsize=11, fontweight='bold')
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'figA_station_scatter.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: figA_station_scatter.png")


# ══════════════════════════════════════════════════════════════════════
# Option B: 링크 단위 로지스틱 회귀 (n=7,819)
# DV: is_hot (UTCI_final ≥ 38°C = 1)
# IV: mean_bld_H, road_W, is_bridge  ← SVF 계산 이전 원자료 (비순환)
# ══════════════════════════════════════════════════════════════════════
print("\n=== Option B: 링크 단위 로지스틱 회귀 ===")
print("  DV: is_hot (UTCI_final ≥ 38°C)  IV: 건물높이·도로폭·교량여부")

# svf_df에서 mean_bld_H, road_W 가져와서 sol13에 병합
svf_merge = svf_df[['u','v','mean_bld_H','road_W']].copy()
svf_merge['u'] = svf_merge['u'].astype(int)
svf_merge['v'] = svf_merge['v'].astype(int)

reg_df = sol13.merge(svf_merge, on=['u','v'], how='left')
# 역방향도 시도
missing = reg_df['mean_bld_H'].isna()
if missing.any():
    rev = svf_merge.rename(columns={'u':'v','v':'u'})
    reg_df.loc[missing, ['mean_bld_H','road_W']] = \
        sol13[missing].merge(rev, on=['u','v'], how='left')[['mean_bld_H','road_W']].values

reg_df = reg_df.dropna(subset=['mean_bld_H','road_W','is_bridge','is_hot'])
print(f"  분석 링크: {len(reg_df):,}개 | hot 비율: {reg_df['is_hot'].mean()*100:.1f}%")

X_cols = ['mean_bld_H', 'road_W', 'is_bridge']
X = sm.add_constant(reg_df[X_cols])
y = reg_df['is_hot']

logit_model = sm.Logit(y, X).fit(disp=False)
print(logit_model.summary())

# Odds Ratio
OR   = np.exp(logit_model.params)
OR_ci = np.exp(logit_model.conf_int())
print(f"\n  Odds Ratio:")
for name in X_cols:
    print(f"  {name:<15}: OR={OR[name]:.4f}  95%CI [{OR_ci.loc[name,0]:.4f}, {OR_ci.loc[name,1]:.4f}]  p={logit_model.pvalues[name]:.4f}")

# 표준화 계수 (비교용)
scaler = StandardScaler()
X_std  = scaler.fit_transform(reg_df[X_cols])
logit_std = sm.Logit(y, sm.add_constant(X_std)).fit(disp=False)
betas = logit_std.params[1:]

print(f"\n  표준화 로짓 계수:")
for name, b in zip(X_cols, betas):
    print(f"  {name:<15}: β = {b:+.4f}")

# ── Figure B-1: OR 막대 + 표준화 계수 ────────────────────────────
print("\n  Figure B 생성 중...")
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

var_labels = ['건물 평균\n높이(m)', '도로 폭\n(m)', '교량\n여부']
pvals = [logit_model.pvalues[c] for c in X_cols]

# B-1: Odds Ratio (로그스케일)
ax = axes[0]
or_vals = [OR[c] for c in X_cols]
ci_low  = [OR_ci.loc[c, 0] for c in X_cols]
ci_high = [OR_ci.loc[c, 1] for c in X_cols]
colors_b = ['#E53935' if o > 1 else '#1E88E5' for o in or_vals]

y_pos = np.arange(len(X_cols))
ax.barh(y_pos, or_vals, color=colors_b, edgecolor='white', height=0.5, alpha=0.85)
ax.errorbar(or_vals, y_pos,
            xerr=[np.array(or_vals)-np.array(ci_low),
                  np.array(ci_high)-np.array(or_vals)],
            fmt='none', color='black', capsize=5, linewidth=1.5)
ax.axvline(1.0, color='black', linewidth=1.2, linestyle='--')
ax.set_yticks(y_pos)
ax.set_yticklabels(var_labels, fontsize=10)
for i, (o, p) in enumerate(zip(or_vals, pvals)):
    sig = '***' if p<0.001 else ('**' if p<0.05 else ('*' if p<0.1 else 'n.s.'))
    ax.text(o + 0.01, i, f'OR={o:.3f} {sig}', va='center', fontsize=9)
ax.set_xlabel('Odds Ratio (기준선=1.0)', fontsize=10)
ax.set_title(f'(a) Odds Ratio (95% CI)\nPseudo R² = {logit_model.prsquared:.3f}  n={len(reg_df):,}',
             fontsize=10, fontweight='bold')
ax.grid(axis='x', alpha=0.3)
ax.spines[['top','right']].set_visible(False)

# B-2: 표준화 로짓 계수 (상대적 영향력)
ax = axes[1]
beta_colors = ['#E53935' if b > 0 else '#1E88E5' for b in betas]
ax.barh(y_pos, betas, color=beta_colors, edgecolor='white', height=0.5, alpha=0.85)
ax.axvline(0, color='black', linewidth=0.8)
ax.set_yticks(y_pos)
ax.set_yticklabels(var_labels, fontsize=10)
for i, b in enumerate(betas):
    ax.text(b + (0.01 if b >= 0 else -0.01), i,
            f'{b:+.3f}', va='center',
            ha='left' if b >= 0 else 'right', fontsize=9)
ax.set_xlabel('표준화 로짓 계수 (β)', fontsize=10)
ax.set_title('(b) 표준화 계수\n상대적 영향력 비교', fontsize=10, fontweight='bold')
ax.grid(axis='x', alpha=0.3)
ax.spines[['top','right']].set_visible(False)

fig.suptitle('링크 단위 로지스틱 회귀: 고온링크(UTCI≥38°C) 결정 요인 (SOLWEIG 13시, n=7,819)\n'
             'logit(is_hot) = β₀ + β₁·건물높이 + β₂·도로폭 + β₃·교량 + ε\n'
             '* p<0.1  ** p<0.05  *** p<0.001',
             fontsize=11, fontweight='bold')
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'figB_link_logistic.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: figB_link_logistic.png")


# ── Figure B-2: 건물높이·교량별 hot 비율 시각화 ──────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 건물높이 구간별 hot 비율
ax = axes[0]
reg_df['bld_cat'] = pd.cut(reg_df['mean_bld_H'],
                            bins=[0, 6, 12, 24, 48, 200],
                            labels=['1-2층\n(~6m)', '3-4층\n(~12m)',
                                    '5-8층\n(~24m)', '9-16층\n(~48m)', '초고층\n(48m+)'])
hot_by_bld = reg_df.groupby('bld_cat', observed=True)['is_hot'].mean() * 100
cnt_by_bld = reg_df.groupby('bld_cat', observed=True)['is_hot'].count()

bars = ax.bar(range(len(hot_by_bld)), hot_by_bld.values,
              color='#EF9A9A', edgecolor='white')
ax.set_xticks(range(len(hot_by_bld)))
ax.set_xticklabels(hot_by_bld.index, fontsize=9)
for i, (v, n) in enumerate(zip(hot_by_bld.values, cnt_by_bld.values)):
    ax.text(i, v + 1, f'{v:.0f}%\n(n={n})', ha='center', fontsize=8)
ax.set_ylabel('고온링크 비율 (%)', fontsize=10)
ax.set_xlabel('주변 건물 평균 높이 구간', fontsize=10)
ax.set_title('(a) 건물 높이 구간별 고온링크 비율\n(높을수록 SVF↓ → UTCI↓)', fontsize=10, fontweight='bold')
ax.axhline(reg_df['is_hot'].mean()*100, color='gray', linestyle='--',
           linewidth=1, label=f'전체 평균 {reg_df["is_hot"].mean()*100:.0f}%')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)
ax.spines[['top','right']].set_visible(False)

# 교량 vs 일반도로 hot 비율 + UTCI 분포
ax = axes[1]
groups_utci = [reg_df[reg_df['is_bridge']==0]['utci_final'].values,
               reg_df[reg_df['is_bridge']==1]['utci_final'].values]
bp = ax.boxplot(groups_utci, tick_labels=['일반도로', '교량'],
                patch_artist=True, widths=0.45,
                medianprops=dict(color='black', linewidth=2))
bp['boxes'][0].set_facecolor('#90CAF9')
bp['boxes'][1].set_facecolor('#FFAB91')

t_val, p_val = stats.ttest_ind(groups_utci[0], groups_utci[1])
hot_road   = reg_df[reg_df['is_bridge']==0]['is_hot'].mean()*100
hot_bridge = reg_df[reg_df['is_bridge']==1]['is_hot'].mean()*100

ax.axhline(THRESHOLD, color='#E53935', linestyle='--', linewidth=1.2,
           alpha=0.7, label=f'임계값 {THRESHOLD}°C')
ax.set_ylabel('UTCI_final (°C)', fontsize=10)
ax.set_title(f'(b) 교량 vs 일반도로 UTCI 분포\n'
             f'고온링크 비율: 일반 {hot_road:.0f}% vs 교량 {hot_bridge:.0f}%  (t={t_val:.1f}, p={p_val:.3f})',
             fontsize=10, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)
ax.spines[['top','right']].set_visible(False)

fig.suptitle('링크 환경 특성별 고온 위험 분포 (SOLWEIG 13시)',
             fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'figB2_link_distribution.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: figB2_link_distribution.png")


# ── 결과 저장 ─────────────────────────────────────────────────────
results_summary = {
    'option_A': {
        'n': 7,
        'correlations': {
            f: {'r': round(v['r'], 4), 'p': round(v['p'], 4)}
            for f, v in corr_results.items()
        }
    },
    'option_B': {
        'n':            int(len(reg_df)),
        'method':       'logistic_regression',
        'pseudo_r2':    round(logit_model.prsquared, 4),
        'odds_ratios':  {
            name: {'OR':     round(float(OR[name]), 4),
                   'pvalue': round(float(logit_model.pvalues[name]), 6)}
            for name in X_cols
        }
    }
}
with open(os.path.join(RES_DIR, 'regression_results.json'), 'w', encoding='utf-8') as f:
    json.dump(results_summary, f, ensure_ascii=False, indent=2)

print("\n=== 완료 ===")
print("  figA_station_scatter.png    — 역 단위 상관분석")
print("  figB_link_logistic.png      — 링크 단위 로지스틱 회귀 계수")
print("  figB2_link_distribution.png — 건물높이·교량별 UTCI 분포")
print(f"  regression_results.json     — 수치 요약")
print(f"\n  Logit Pseudo R² = {logit_model.prsquared:.3f}  (링크 단위)")
