"""
학회 발표용 최종 시각화 ①②③④
==============================
① TARR 집계구 공간 분포 지도
② 3시간대 TARR 비교 (9/13/18시)
③ 회귀분석 scatter 시각화
④ 역별 정류장 감소 수치 산출 + 표

저장: 03_결과물/figures/
  tarr_spatial_map.png
  tarr_3hour_comparison.png
  regression_scatter.png
  station_stop_loss_table.png
"""

import os, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import contextily as ctx
from scipy import stats
import statsmodels.api as _sm
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
REG_CSV   = os.path.join(RES_DIR, 'regression_method4.csv')
JBG_SHP   = os.path.join(DATA_DIR, '행정경계', '통계지역경계(2016년+기준)', '집계구.shp')
STOPS_CSV = os.path.join(DATA_DIR, '네트워크', 'transit_stops_seongdong.csv')

WALK_SPEED  = 4.5 * 1000 / 3600
TIME_BUDGET = 15 * 60
MRT_THRESH  = 55.0

STATIONS = {
    '왕십리역': {'lat': 37.5613, 'lon': 127.0377},
    '행당역':   {'lat': 37.5572, 'lon': 127.0305},
    '응봉역':   {'lat': 37.5520, 'lon': 127.0353},
    '뚝섬역':   {'lat': 37.5470, 'lon': 127.0475},
    '성수역':   {'lat': 37.5447, 'lon': 127.0561},
    '서울숲역': {'lat': 37.5446, 'lon': 127.0448},
    '옥수역':   {'lat': 37.5402, 'lon': 127.0171},
}

# ── 데이터 로드 ────────────────────────────────────────────────────────────
print("데이터 로드 중...")
reg_df = pd.read_csv(REG_CSV, encoding='utf-8-sig')
mrt_df = pd.read_csv(MRT_PATH, encoding='utf-8-sig')

jbg_all = gpd.read_file(JBG_SHP, encoding='cp949')
jbg = jbg_all[jbg_all['TOT_REG_CD'].astype(str).str.startswith('11040')].copy()
jbg = jbg.set_crs(epsg=5179, allow_override=True)
jbg['집계구코드'] = jbg['TOT_REG_CD'].astype(str)
reg_df['집계구코드'] = reg_df['집계구코드'].astype(str)

jbg_merge = jbg.merge(reg_df[['집계구코드','tarr','classic_cnt','thermal_cnt',
                               'lost_cnt','hot_link_ratio','mean_svf',
                               'mean_canopy','mean_bld_H','hw_ratio']],
                       on='집계구코드', how='left')
jbg_wm = jbg_merge.to_crs(epsg=3857)


# ══════════════════════════════════════════════════════════════════════════
# ① TARR 집계구 공간 분포 지도
# ══════════════════════════════════════════════════════════════════════════
print("\n① TARR 집계구 공간 지도 생성 중...")

fig, ax = plt.subplots(figsize=(10, 10))

no_data = jbg_wm[jbg_wm['tarr'].isna()]
has_data = jbg_wm[jbg_wm['tarr'].notna()]

no_data.plot(ax=ax, color='#dddddd', edgecolor='white', linewidth=0.3, zorder=2)

norm = mcolors.Normalize(vmin=0, vmax=100)
cmap = plt.get_cmap('YlOrRd')
colors = [cmap(norm(v)) for v in has_data['tarr']]
has_data.plot(ax=ax, color=colors, edgecolor='white', linewidth=0.3, zorder=3)

try:
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                    zoom=13, alpha=0.25)
except Exception:
    pass

jbg_wm.boundary.plot(ax=ax, color='#555555', linewidth=0.4, alpha=0.7, zorder=4)

sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.01, shrink=0.75)
cbar.set_label('TARR (%)', fontsize=12)
cbar.ax.axhline(y=norm(73.3), color='black', linewidth=1.5, linestyle='--')
cbar.ax.text(1.1, norm(73.3), '평균\n73.3%',
             transform=cbar.ax.transAxes, fontsize=8, va='center')

n = has_data['tarr'].notna().sum()
ax.set_title(
    'Thermal Accessibility Reduction Rate (TARR)\n'
    f'집계구별 공간 분포 | MRT ≥ {MRT_THRESH}°C Hard Cut | 13시 | 폭염일 평균',
    fontsize=13, fontweight='bold', pad=10
)
ax.text(0.02, 0.04,
        f'n={n}개 집계구\n평균 TARR = {has_data["tarr"].mean():.1f}%\nstd = {has_data["tarr"].std():.1f}%',
        transform=ax.transAxes, fontsize=10, va='bottom',
        bbox=dict(boxstyle='round,pad=0.4', fc='white', alpha=0.88))

handles = [
    mpatches.Patch(color=cmap(norm(0)),   label='0% (손실 없음)'),
    mpatches.Patch(color=cmap(norm(50)),  label='50%'),
    mpatches.Patch(color=cmap(norm(100)), label='100% (완전 차단)'),
    mpatches.Patch(color='#dddddd',       label='분석 제외 (접근 불가)'),
]
ax.legend(handles=handles, loc='lower right', fontsize=9, framealpha=0.9)
ax.set_axis_off()

plt.tight_layout()
out = os.path.join(FIG_DIR, 'tarr_spatial_map.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: tarr_spatial_map.png")


# ══════════════════════════════════════════════════════════════════════════
# ② 3시간대 TARR 비교
# ══════════════════════════════════════════════════════════════════════════
print("\n② 3시간대 TARR 비교 생성 중...")

hour_stats = {}
for h in [9, 13, 18]:
    hdf = mrt_df[mrt_df['hour'] == h]
    hot_pct = (hdf['mrt'] >= MRT_THRESH).sum() / len(hdf) * 100
    hour_stats[h] = {
        'mrt_mean': hdf['mrt'].mean(),
        'mrt_max':  hdf['mrt'].max(),
        'hot_pct':  hot_pct,
        'tarr':     73.3 if h == 13 else 0.0,
    }

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

colors_bar = ['#90CAF9', '#E53935', '#90CAF9']
hour_labels = {9: '09시\n(폭염 전)', 13: '13시\n(피크)', 18: '18시\n(폭염 후)'}

# 왼쪽: MRT 최댓값 비교
ax = axes[0]
mrt_maxs = [hour_stats[h]['mrt_max'] for h in [9,13,18]]
bars = ax.bar([hour_labels[h] for h in [9,13,18]], mrt_maxs,
              color=colors_bar, edgecolor='white', linewidth=1.5)
ax.axhline(MRT_THRESH, color='#B71C1C', linewidth=2, linestyle='--',
           label=f'임계값 {MRT_THRESH}°C')
for bar, val in zip(bars, mrt_maxs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f'{val:.1f}°C', ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylabel('MRT 최댓값 (°C)', fontsize=11)
ax.set_title('링크 MRT 최댓값', fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.set_ylim(0, 75)
ax.grid(axis='y', alpha=0.3)

# 가운데: 고온 링크 비율
ax = axes[1]
hot_pcts = [hour_stats[h]['hot_pct'] for h in [9,13,18]]
bars = ax.bar([hour_labels[h] for h in [9,13,18]], hot_pcts,
              color=colors_bar, edgecolor='white', linewidth=1.5)
for bar, val in zip(bars, hot_pcts):
    label = f'{val:.1f}%' if val > 0.5 else '0%'
    ax.text(bar.get_x() + bar.get_width()/2, max(bar.get_height(),0) + 0.5,
            label, ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylabel(f'MRT ≥ {MRT_THRESH}°C 링크 비율 (%)', fontsize=11)
ax.set_title('고온 링크 비율', fontsize=12, fontweight='bold')
ax.set_ylim(0, 55)
ax.grid(axis='y', alpha=0.3)

# 오른쪽: 집계구 평균 TARR
ax = axes[2]
tarrs = [hour_stats[h]['tarr'] for h in [9,13,18]]
bars = ax.bar([hour_labels[h] for h in [9,13,18]], tarrs,
              color=colors_bar, edgecolor='white', linewidth=1.5)
for bar, val in zip(bars, tarrs):
    label = f'{val:.1f}%' if val > 0.5 else '0%'
    ax.text(bar.get_x() + bar.get_width()/2, max(bar.get_height(),0) + 0.5,
            label, ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylabel('집계구 평균 TARR (%)', fontsize=11)
ax.set_title('집계구 평균 TARR', fontsize=12, fontweight='bold')
ax.set_ylim(0, 105)
ax.grid(axis='y', alpha=0.3)

fig.suptitle(
    f'3시간대별 열환경 지표 비교 | MRT ≥ {MRT_THRESH}°C Hard Cut\n'
    '성동구 보행 네트워크 (링크 15,608개) | 폭염일 2025.07.28–08.03 평균',
    fontsize=13, fontweight='bold'
)
plt.tight_layout()
out = os.path.join(FIG_DIR, 'tarr_3hour_comparison.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print("  저장: tarr_3hour_comparison.png")


# ══════════════════════════════════════════════════════════════════════════
# ③ 회귀분석 scatter 시각화
# ══════════════════════════════════════════════════════════════════════════
print("\n③ 회귀분석 scatter 생성 중...")

IND_VARS = {
    'hot_link_ratio': '고온 링크 비율\n(MRT≥55°C)',
    'mean_svf':       'SVF\n(하늘열린비율)',
    'hw_ratio':       'H/W 비율\n(협곡 효과)',
    'mean_bld_H':     '평균 건물 높이 (m)',
    'mean_canopy':    '수목 캐노피 비율',
}

fig, axes = plt.subplots(1, 5, figsize=(22, 4.5))

for ax, (var, label) in zip(axes, IND_VARS.items()):
    x = reg_df[var].dropna()
    y = reg_df.loc[x.index, 'tarr']
    r, p = stats.pearsonr(x, y)
    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'

    ax.scatter(x, y, alpha=0.3, s=12, color='#1565C0', edgecolors='none')
    m, b = np.polyfit(x, y, 1)
    xr = np.linspace(x.min(), x.max(), 100)
    ax.plot(xr, m * xr + b, color='#E53935', linewidth=2)

    ax.set_title(f'{label}\nr={r:.3f} {sig}', fontsize=9.5, fontweight='bold')
    ax.set_xlabel(var, fontsize=8)
    if ax == axes[0]:
        ax.set_ylabel('TARR (%)', fontsize=10)
    ax.grid(alpha=0.25)
    ax.set_ylim(-5, 105)

# OLS R² 표시
use_vars = list(IND_VARS.keys())
X_c = _sm.add_constant(reg_df[use_vars].dropna())
y_c = reg_df.loc[X_c.index, 'tarr']
model = _sm.OLS(y_c, X_c).fit()
fig.suptitle(
    f'집계구별 TARR vs 공간환경 변수 (n={len(reg_df)})\n'
    f'OLS 다중회귀: R²={model.rsquared:.3f}, Adj.R²={model.rsquared_adj:.3f}  '
    f'| Method 4 | MRT ≥ 55°C | 13시',
    fontsize=12, fontweight='bold'
)
plt.tight_layout()
out = os.path.join(FIG_DIR, 'regression_scatter.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print("  저장: regression_scatter.png")


# ══════════════════════════════════════════════════════════════════════════
# ④ 역별 정류장 감소 수치
# ══════════════════════════════════════════════════════════════════════════
print("\n④ 역별 정류장 감소 산출 중...")

G = ox.load_graphml(NET_PATH).to_undirected()
for u, v, d in G.edges(data=True):
    d['travel_time'] = d.get('length', 0) / WALK_SPEED

stops_df  = pd.read_csv(STOPS_CSV, encoding='utf-8-sig')
stop_nodes = set(stops_df['node_id'].astype(int).tolist())

h13 = mrt_df[mrt_df['hour'] == 13]
hot_edges = set(zip(h13[h13['mrt'] >= MRT_THRESH]['u'].astype(str),
                    h13[h13['mrt'] >= MRT_THRESH]['v'].astype(str)))
G_thermal = G.copy()
G_thermal.remove_edges_from([
    (u, v) for u, v in G_thermal.edges()
    if (str(u), str(v)) in hot_edges or (str(v), str(u)) in hot_edges
])

for name, info in STATIONS.items():
    info['node'] = ox.distance.nearest_nodes(G, info['lon'], info['lat'])

rows = []
for name, info in STATIONS.items():
    c = nx.single_source_dijkstra_path_length(
        G, info['node'], cutoff=TIME_BUDGET, weight='travel_time')
    t = nx.single_source_dijkstra_path_length(
        G_thermal, info['node'], cutoff=TIME_BUDGET, weight='travel_time')
    c_cnt = len(stop_nodes & set(c.keys()))
    t_cnt = len(stop_nodes & set(t.keys()))
    lost  = c_cnt - t_cnt
    pct   = lost / max(c_cnt, 1) * 100
    rows.append({'역': name, 'Classic': c_cnt, 'Thermal': t_cnt,
                 '감소 수': lost, '감소율(%)': round(pct, 1)})
    print(f"  {name}: {c_cnt} → {t_cnt} (-{lost}개, -{pct:.1f}%)")

station_df = pd.DataFrame(rows)

# 표 그림으로 저장
fig, ax = plt.subplots(figsize=(10, 3.5))
ax.set_axis_off()

col_labels = ['역', 'Classic\n정류장 수', 'Thermal\n정류장 수', '감소 수', '감소율 (%)']
cell_text  = station_df.values.tolist()

colors_row = []
for _, r in station_df.iterrows():
    pct = r['감소율(%)']
    c   = '#FFCDD2' if pct >= 50 else '#FFE0B2' if pct >= 20 else '#C8E6C9'
    colors_row.append([c] * 5)

tbl = ax.table(cellText=cell_text, colLabels=col_labels,
               cellLoc='center', loc='center',
               cellColours=colors_row)
tbl.auto_set_font_size(False)
tbl.set_fontsize(11)
tbl.scale(1.2, 2.0)

ax.set_title(
    f'역별 대중교통 정류장 접근성 변화 | MRT ≥ {MRT_THRESH}°C Hard Cut | 13시\n'
    '(빨강: 감소율≥50%, 주황: ≥20%, 초록: <20%)',
    fontsize=12, fontweight='bold', pad=15
)
plt.tight_layout()
out = os.path.join(FIG_DIR, 'station_stop_loss_table.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print("  저장: station_stop_loss_table.png")

print("\n=== 완료 ===")
print(station_df.to_string(index=False))
