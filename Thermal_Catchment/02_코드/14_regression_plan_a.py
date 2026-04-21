"""
Plan A: 공간환경 변수 → Catchment 감소율 회귀분석
==================================================
종속변수: reduction_pct_h13 (13시 기준 접근성 감소율)
독립변수: river_dist_m, green_ratio_pct

n=7 (역 7개) → 탐색적 분석, 방향성 파악 목적
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from scipy import stats
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
FIG_DIR = os.path.join(RES_DIR, 'figures')

# ── 데이터 로드 ──────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(RES_DIR, 'spatial_env_variables.csv'), encoding='utf-8-sig')
print("=== 입력 데이터 ===")
print(df[['station', 'river_dist_m', 'green_ratio_pct', 'reduction_pct_h13']].to_string(index=False))

# ── 단순회귀 1: river_dist_m → reduction_pct ─────────────────────────────
print("\n\n=== 단순회귀 1: 수계거리 → 감소율 ===")
x1 = df['river_dist_m'].values
y  = df['reduction_pct_h13'].values

slope1, intercept1, r1, p1, se1 = stats.linregress(x1, y)
r2_1 = r1**2
print(f"  β(수계거리) = {slope1:.4f}  (100m당 {slope1*100:.2f}%p)")
print(f"  절편       = {intercept1:.2f}")
print(f"  r          = {r1:.3f}")
print(f"  R²         = {r2_1:.3f}")
print(f"  p-value    = {p1:.4f}  {'★ 유의 (p<0.05)' if p1 < 0.05 else '(비유의)'}")

# ── 단순회귀 2: green_ratio_pct → reduction_pct ──────────────────────────
print("\n=== 단순회귀 2: 녹지비율 → 감소율 ===")
x2 = df['green_ratio_pct'].values

slope2, intercept2, r2, p2, se2 = stats.linregress(x2, y)
r2_2 = r2**2
print(f"  β(녹지비율) = {slope2:.4f}  (1%p당 {slope2:.2f}%p)")
print(f"  절편        = {intercept2:.2f}")
print(f"  r           = {r2:.3f}")
print(f"  R²          = {r2_2:.3f}")
print(f"  p-value     = {p2:.4f}  {'★ 유의 (p<0.05)' if p2 < 0.05 else '(비유의)'}")

# ── 다중회귀: river_dist + green_ratio → reduction_pct ───────────────────
print("\n=== 다중회귀: 수계거리 + 녹지비율 → 감소율 ===")
try:
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score

    X = df[['river_dist_m', 'green_ratio_pct']].values
    model = LinearRegression().fit(X, y)
    y_pred = model.predict(X)
    r2_multi = r2_score(y, y_pred)

    # p-value 계산 (F-통계량 기반)
    n, k = len(y), 2
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - y.mean())**2)
    f_stat = (r2_multi / k) / ((1 - r2_multi) / (n - k - 1))
    p_multi = 1 - stats.f.cdf(f_stat, k, n - k - 1)

    print(f"  β(수계거리)  = {model.coef_[0]:.4f}")
    print(f"  β(녹지비율)  = {model.coef_[1]:.4f}")
    print(f"  절편         = {model.intercept_:.2f}")
    print(f"  R²           = {r2_multi:.3f}")
    print(f"  F-통계량     = {f_stat:.2f},  p = {p_multi:.4f}  "
          f"{'★ 유의 (p<0.05)' if p_multi < 0.05 else '(비유의)'}")
    print(f"\n  예측값 vs 실제값:")
    for i, row in df.iterrows():
        print(f"    {row['station']}: 실제 {row['reduction_pct_h13']:.1f}%  "
              f"예측 {y_pred[i]:.1f}%  잔차 {row['reduction_pct_h13']-y_pred[i]:+.1f}%")
except ImportError:
    print("  sklearn 없음 — 단순회귀 결과만 사용")
    model = None

# ── 시각화 ───────────────────────────────────────────────────────────────
colors = ['#E53935','#FB8C00','#8E24AA','#43A047','#1E88E5','#00ACC1','#6D4C41']
station_labels = df['station'].str.replace('역', '')

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

for ax, xvar, xlabel, slope, intercept, r_val, p_val in [
    (axes[0], 'river_dist_m',   '수계까지 거리 (m)',   slope1, intercept1, r1, p1),
    (axes[1], 'green_ratio_pct', '녹지 비율 (%)', slope2, intercept2, r2, p2),
]:
    x = df[xvar].values
    for i, (xi, yi, label) in enumerate(zip(x, y, station_labels)):
        ax.scatter(xi, yi, color=colors[i], s=120, zorder=3)
        ax.annotate(label, (xi, yi), textcoords='offset points',
                    xytext=(6, 3), fontsize=9)

    # 회귀선
    xseq = np.linspace(x.min()*0.95, x.max()*1.05, 100)
    ax.plot(xseq, slope*xseq + intercept, 'k--', linewidth=1.5, alpha=0.6)

    sig_mark = '★' if p_val < 0.05 else ''
    ax.set_title(f'r = {r_val:.2f},  R² = {r_val**2:.2f},  p = {p_val:.3f} {sig_mark}',
                 fontsize=10)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel('Catchment 감소율 13시 (%)', fontsize=11)
    ax.grid(True, alpha=0.3)

fig.suptitle(
    'Plan A 회귀분석: 공간환경 변수 → Thermal Catchment 감소율\n'
    f'(성동구 7개 역, α={0.15}, 15분 시간예산)',
    fontsize=12, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'regression_plan_a.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"\n시각화 저장: figures/regression_plan_a.png")

# ── 해석 요약 ────────────────────────────────────────────────────────────
print("\n\n=== 해석 요약 ===")
print(f"수계거리: r={r1:.2f}, p={p1:.3f} → {'수계 가까울수록 감소율 높음' if slope1 < 0 else '수계 가까울수록 감소율 낮음'}")
print(f"녹지비율: r={r2:.2f}, p={p2:.3f} → {'녹지 많을수록 감소율 높음' if slope2 > 0 else '녹지 많을수록 감소율 낮음'}")
print("\n주의: n=7로 통계적 유의성 해석에 한계 있음 — 탐색적 분석으로 제시 필요")
