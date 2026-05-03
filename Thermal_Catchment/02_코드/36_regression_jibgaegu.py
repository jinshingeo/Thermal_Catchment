"""
집계구 단위 TARR 회귀분석 (n=570)
===================================
집계구별 TARR(14시 폭염 피크 기준)을 종속변수로,
네트워크 기반 공간환경 변수를 독립변수로 OLS 회귀분석

독립변수 (집계구 내 링크 평균):
  mean_svf          — 평균 하늘열린비율 (높을수록 고온 노출)
  hot_link_ratio    — UTCI ≥ 38°C 링크 비율 (14시)
  mean_canopy       — 평균 수목 캐노피 피복률 (높을수록 쿨링)
  mean_bld_H        — 평균 건물 높이 (높을수록 그늘)
  mean_road_W       — 평균 도로 폭 (넓을수록 노출)
  hw_ratio          — 평균 H/W 비율 (협곡 효과)

출력 (→ 03_결과물/):
  regression_jibgaegu.csv      — 집계구별 변수 + TARR
  figures/fig11_regression.png
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
DATA_DIR = os.path.join(PROJ_DIR, '01_데이터')

NET_PATH     = '/Users/jin/석사논문/성동구_STP연구/01_네트워크/seongdong_walk_network.graphml'
SVF_PATH     = os.path.join(RES_DIR, 'link_svf_canopy.csv')
UTCI_PATH    = os.path.join(RES_DIR, 'link_utci_solweig.csv')
GRAVITY_PATH = os.path.join(RES_DIR, 'gravity_results_multihour.csv')
BOUNDARY_SHP = os.path.join(DATA_DIR, '행정경계',
                            '통계지역경계(2016년+기준)', '집계구.shp')

TARGET_HOUR = 14
THRESHOLD   = 38.0


# ── 한국어 폰트 ───────────────────────────────────────────────────────────
def set_korean_font():
    for path in ['/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                 '/Library/Fonts/NanumGothic.ttf']:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            plt.rcParams['font.family'] = fm.FontProperties(fname=path).get_name()
            break
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()


# ── 1. 데이터 로드 ────────────────────────────────────────────────────────
print("데이터 로드 중...")
gravity_df = pd.read_csv(GRAVITY_PATH, encoding='utf-8-sig')
gravity_df['집계구코드'] = gravity_df['집계구코드'].astype(float).astype(int).astype(str)
gravity_df = gravity_df[gravity_df['a_classic'] > 0].copy()  # no_access 제외
print(f"  분석 집계구: {len(gravity_df)}개 (Classic 접근 불가 6개 제외)")

svf_df  = pd.read_csv(SVF_PATH, encoding='utf-8-sig')
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
utci_h  = utci_df[utci_df['hour'] == TARGET_HOUR][['u','v','utci_final']].copy()
utci_h['is_hot'] = (utci_h['utci_final'] >= THRESHOLD).astype(int)

svf_df['u'] = svf_df['u'].astype(str)
svf_df['v'] = svf_df['v'].astype(str)
utci_h['u'] = utci_h['u'].astype(str)
utci_h['v'] = utci_h['v'].astype(str)
link_df = svf_df.merge(utci_h[['u','v','utci_final','is_hot']], on=['u','v'], how='left')
link_df['is_hot'] = link_df['is_hot'].fillna(0)


# ── 2. 네트워크 → 집계구 공간 조인 ──────────────────────────────────────
print("링크 → 집계구 공간 조인 중...")
G = ox.load_graphml(NET_PATH)
edges_gdf = ox.graph_to_gdfs(G, nodes=False, edges=True).reset_index()
edges_gdf['u'] = edges_gdf['u'].astype(str)
edges_gdf['v'] = edges_gdf['v'].astype(str)
edges_gdf = edges_gdf.to_crs(epsg=5179)

jibgaegu = gpd.read_file(BOUNDARY_SHP, encoding='cp949')
code_col  = next(c for c in jibgaegu.columns
                 if str(jibgaegu[c].iloc[0]).startswith('11') and len(str(jibgaegu[c].iloc[0])) >= 10)
jibgaegu[code_col] = jibgaegu[code_col].astype(str)
seongdong = jibgaegu[jibgaegu[code_col].str.startswith('1104')].copy()
if seongdong.crs is None:
    seongdong = seongdong.set_crs(epsg=5179)

# 링크 중심점 → 집계구 공간 조인
edges_gdf['geometry'] = edges_gdf.geometry.centroid
joined = gpd.sjoin(edges_gdf[['u','v','geometry']], seongdong[[code_col,'geometry']],
                   how='left', predicate='within')
joined = joined.rename(columns={code_col: '집계구코드'}).dropna(subset=['집계구코드'])
joined['집계구코드'] = joined['집계구코드'].astype(str)
print(f"  매핑된 링크: {len(joined):,}개")


# ── 3. 집계구 단위 공간환경 변수 집계 ────────────────────────────────────
print("집계구별 변수 집계 중...")
link_merged = joined[['u','v','집계구코드']].merge(link_df, on=['u','v'], how='left')

agg = link_merged.groupby('집계구코드').agg(
    mean_svf       = ('svf',        'mean'),
    mean_canopy    = ('canopy_ratio','mean'),
    mean_bld_H     = ('mean_bld_H', 'mean'),
    mean_road_W    = ('road_W',     'mean'),
    hw_ratio       = ('HW_ratio',   'mean'),
    hot_link_ratio = ('is_hot',     'mean'),
    n_links        = ('u',          'count'),
).reset_index()

print(f"  집계 완료: {len(agg)}개 집계구")


# ── 4. 회귀 데이터 병합 ───────────────────────────────────────────────────
reg_df = gravity_df[['집계구코드','tarr_h14','residential_pop']].merge(
    agg, on='집계구코드', how='inner')
reg_df = reg_df.dropna()
print(f"  최종 분석 집계구: {len(reg_df)}개")


# ── 5. 상관분석 ───────────────────────────────────────────────────────────
print("\n=== 집계구 TARR vs 공간환경 변수 상관분석 (n={}) ===".format(len(reg_df)))
vars_of_interest = {
    'mean_svf':       '평균 SVF (하늘열린비율)',
    'hot_link_ratio': '고온 링크 비율 (UTCI≥38°C)',
    'mean_canopy':    '평균 수목 캐노피 비율',
    'mean_bld_H':     '평균 건물 높이 (m)',
    'mean_road_W':    '평균 도로 폭 (m)',
    'hw_ratio':       '평균 H/W 비율',
}

corr_results = {}
for var, label in vars_of_interest.items():
    r, p = stats.pearsonr(reg_df[var], reg_df['tarr_h14'])
    sr, sp = stats.spearmanr(reg_df[var], reg_df['tarr_h14'])
    corr_results[var] = {'label': label, 'pearson_r': r, 'pearson_p': p,
                         'spearman_r': sr, 'spearman_p': sp}
    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
    print(f"  {label:25s}: r={r:.3f} (p={p:.3f}{sig})  ρ={sr:.3f}")


# ── 6. OLS 회귀 ───────────────────────────────────────────────────────────
try:
    import statsmodels.api as sm
    X = reg_df[list(vars_of_interest.keys())].copy()
    X = (X - X.mean()) / X.std()  # 표준화
    X = sm.add_constant(X)
    y = reg_df['tarr_h14']
    model = sm.OLS(y, X).fit()
    print(f"\n=== OLS 회귀 결과 ===")
    print(f"  R² = {model.rsquared:.3f}  |  Adj. R² = {model.rsquared_adj:.3f}")
    print(f"  F-stat p = {model.f_pvalue:.4f}")
    print(model.summary2().tables[1][['Coef.','Std.Err.','t','P>|t|']].to_string())
    ols_r2 = model.rsquared
except ImportError:
    print("statsmodels 없음 — 상관분석만 수행")
    ols_r2 = None


# ── 7. 시각화 ─────────────────────────────────────────────────────────────
print("\n시각화 중...")
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
axes = axes.flatten()

for ax, (var, label) in zip(axes, vars_of_interest.items()):
    r  = corr_results[var]['pearson_r']
    p  = corr_results[var]['pearson_p']
    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''

    ax.scatter(reg_df[var], reg_df['tarr_h14'],
               alpha=0.3, s=15, color='#2c7bb6', linewidths=0)

    # 회귀선
    m, b = np.polyfit(reg_df[var], reg_df['tarr_h14'], 1)
    x_line = np.linspace(reg_df[var].min(), reg_df[var].max(), 100)
    ax.plot(x_line, m*x_line+b, color='#d7191c', linewidth=1.5)

    ax.set_xlabel(label, fontsize=9)
    ax.set_ylabel('TARR (%, 14시)' if ax == axes[0] else '', fontsize=9)
    ax.set_title(f'r = {r:.3f}{sig}', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)

fig.suptitle(f'집계구 TARR vs 공간환경 변수 (n={len(reg_df)}, 폭염 피크 14시)',
             fontsize=13, fontweight='bold')
plt.tight_layout()
path = os.path.join(FIG_DIR, 'fig11_regression.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"저장: {path}")

# 저장
reg_df.to_csv(os.path.join(RES_DIR, 'regression_jibgaegu.csv'), index=False, encoding='utf-8-sig')
print(f"저장: regression_jibgaegu.csv")
print("\n=== 집계구 회귀분석 완료 ===")
