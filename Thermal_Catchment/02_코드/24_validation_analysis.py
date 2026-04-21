"""
Thermal Catchment Validation — reduction_pct vs 실제 승하차 비율
=================================================================
검증 논리:
  Thermal Catchment reduction_pct가 높은 역
  → 폭염 시간대에 보행 접근이 어려워짐
  → 실제 역 이용자 수(승하차 인원)가 상대적으로 적을 것

검증 방법:
  [Cross-sectional 분석] (n=7 역)
    X: reduction_pct (%) — Thermal Catchment 감소율 (모델)
    Y: ridership_ratio (%) — 시간대별 승하차 / 일일 합계 (실측)

  통계:
    - Pearson r    : 선형 상관 (정규분포 가정)
    - Spearman ρ   : 순위 상관 (n=7 소표본, 비모수 — 더 적합)
    - p-value      : 유의성 검정

  [시간대별 분석]
    7시  → reduction_pct=0 (폭염 없음, baseline)
    10시 → 부분 열스트레스
    13시 → 최대 열스트레스 (폭염 피크)
    16시 → 오후 지속 열스트레스
"""

import os
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
VAL_PATH = os.path.join(RES_DIR, 'subway_validation_ready.csv')
CT_PATH  = os.path.join(RES_DIR, 'catchment_solweig_summary.json')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

TARGET_HOURS = [7, 10, 13, 16]

# ── 1. 데이터 로드 ──────────────────────────────────────────────────────
print("데이터 로드 중...")
val_df = pd.read_csv(VAL_PATH, encoding='utf-8-sig')

with open(CT_PATH, encoding='utf-8') as f:
    ct = json.load(f)

# ── 2. 역별·시간대별 롱 포맷 테이블 구성 ────────────────────────────────
print("롱 포맷 테이블 구성 중...")
rows = []
for _, row in val_df.iterrows():
    stn = row['station']
    for h in TARGET_HOURS:
        # Thermal Catchment reduction_pct
        hkey = f'h{h:02d}'
        r_pct = ct.get(stn, {}).get(hkey, {}).get('reduction_pct', np.nan)

        # 승하차 비율
        ratio = row[f'ratio_h{h:02d}']
        total = row['total_daily']

        rows.append({
            'station':       stn,
            'hour':          h,
            'reduction_pct': r_pct,
            'ratio':         ratio,
            'ratio_pct':     ratio * 100,
            'total_daily':   total,
        })

long_df = pd.DataFrame(rows)

# ── 3. 시간대별 상관분석 ─────────────────────────────────────────────────
print("\n=== 시간대별 상관분석 결과 ===")
print(f"{'시각':<6} {'Pearson r':>10} {'p(Pearson)':>12} {'Spearman ρ':>12} {'p(Spearman)':>13} {'해석'}")
print("-" * 75)

corr_results = {}
for h in TARGET_HOURS:
    sub = long_df[long_df['hour'] == h].dropna(subset=['reduction_pct', 'ratio_pct'])

    if sub['reduction_pct'].std() < 0.01:
        print(f"{h:02d}시    reduction_pct=0 (폭염 없음, baseline — 분석 제외)")
        corr_results[h] = None
        continue

    x = sub['reduction_pct'].values
    y = sub['ratio_pct'].values

    pr, pp = stats.pearsonr(x, y)
    sr, sp = stats.spearmanr(x, y)

    sig_p = '**' if pp < 0.05 else ('*' if pp < 0.10 else 'n.s.')
    sig_s = '**' if sp < 0.05 else ('*' if sp < 0.10 else 'n.s.')

    print(f"{h:02d}시    {pr:>+9.3f}  {pp:>11.4f}{sig_p}  {sr:>+11.3f}  {sp:>12.4f}{sig_s}  "
          f"{'음(-)상관 ✓' if pr < 0 else '양(+)상관'}")

    corr_results[h] = {
        'pearson_r':   round(pr, 4),
        'pearson_p':   round(pp, 4),
        'spearman_r':  round(sr, 4),
        'spearman_p':  round(sp, 4),
        'n':           len(sub),
        'data':        sub.copy(),
    }

print("\n  ** p<0.05  * p<0.10  n.s. not significant")

# ── 4. 역별 순위 비교 (Spearman 직관 확인) ────────────────────────────
print("\n=== 13시 역별 순위 비교 ===")
h13 = long_df[long_df['hour'] == 13].dropna().sort_values('reduction_pct', ascending=False)
h13 = h13.copy()
h13['rank_reduction'] = h13['reduction_pct'].rank(ascending=False).astype(int)
h13['rank_ratio']     = h13['ratio_pct'].rank(ascending=True).astype(int)  # 비율 낮을수록 좋은 순위
h13['rank_match']     = (h13['rank_reduction'] == h13['rank_ratio'])
print(h13[['station', 'reduction_pct', 'ratio_pct',
           'rank_reduction', 'rank_ratio', 'rank_match']].to_string(index=False))

match_rate = h13['rank_match'].mean() * 100
print(f"\n  순위 일치율: {match_rate:.0f}% ({h13['rank_match'].sum()}/{len(h13)} 역)")

# ── 5. 시각화 ─────────────────────────────────────────────────────────
COLORS = {
    '왕십리역': '#E53935', '행당역': '#FB8C00', '응봉역': '#8E24AA',
    '뚝섬역':  '#43A047', '성수역': '#1E88E5', '서울숲역': '#00ACC1',
    '옥수역':  '#6D4C41',
}

# 시간대별 산점도 (2×2 grid)
fig, axes = plt.subplots(2, 2, figsize=(14, 12))
axes_flat = axes.flatten()

for ax, h in zip(axes_flat, TARGET_HOURS):
    if corr_results[h] is None:
        ax.text(0.5, 0.5, f'{h:02d}시\nUTCI < 38°C\nreduction_pct = 0\n(폭염 없음)',
                ha='center', va='center', fontsize=13, color='gray',
                transform=ax.transAxes)
        ax.set_title(f'{h:02d}시 — Baseline (폭염 없음)', fontsize=11)
        ax.set_axis_off()
        continue

    sub = corr_results[h]['data']
    pr  = corr_results[h]['pearson_r']
    pp  = corr_results[h]['pearson_p']
    sr  = corr_results[h]['spearman_r']
    sp  = corr_results[h]['spearman_p']

    for _, row in sub.iterrows():
        c = COLORS.get(row['station'], '#555555')
        ax.scatter(row['reduction_pct'], row['ratio_pct'],
                   s=150, color=c, zorder=5,
                   edgecolors='white', linewidth=0.8)
        ax.annotate(row['station'],
                    (row['reduction_pct'], row['ratio_pct']),
                    textcoords='offset points', xytext=(7, 4),
                    fontsize=8.5, color=c, fontweight='bold')

    # 추세선
    x = sub['reduction_pct'].values.astype(float)
    y = sub['ratio_pct'].values.astype(float)
    if np.std(x) > 0 and np.std(y) > 0:
        try:
            z = np.polyfit(x, y, 1)
            p_fn = np.poly1d(z)
            xl = np.linspace(x.min() - 2, x.max() + 2, 100)
            ax.plot(xl, p_fn(xl), '--', color='#555555',
                    linewidth=1.5, alpha=0.7)
        except Exception:
            pass

    sig_p = '**' if pp < 0.05 else ('*' if pp < 0.10 else 'n.s.')
    sig_s = '**' if sp < 0.05 else ('*' if sp < 0.10 else 'n.s.')
    ax.set_title(
        f'{h:02d}시 | Pearson r={pr:+.3f}{sig_p}  Spearman ρ={sr:+.3f}{sig_s}',
        fontsize=10, fontweight='bold'
    )
    ax.set_xlabel('Thermal Catchment reduction_pct (%)', fontsize=9)
    ax.set_ylabel('시간대 승하차 비율 (%, 일일 대비)', fontsize=9)
    ax.grid(True, alpha=0.3)

fig.suptitle(
    'Thermal Catchment reduction_pct vs 실제 지하철 승하차 비율\n'
    '성동구 7개 역 | UTCI ≥ 38°C 하드 컷 | 2023·2024 여름 평균',
    fontsize=13, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'validation_4panel.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\n저장: figures/validation_4panel.png")

# ── 6. 요약: 검증 결과 해석 출력 ─────────────────────────────────────
print("\n=== 검증 결과 해석 ===")
for h in [10, 13, 16]:
    if corr_results[h]:
        r  = corr_results[h]['pearson_r']
        sr = corr_results[h]['spearman_r']
        pp = corr_results[h]['pearson_p']
        sp = corr_results[h]['spearman_p']
        direction = "음(-)의 상관 → 모델과 일치 ✓" if r < 0 else "양(+)의 상관 → 모델과 불일치 ✗"
        sig = "유의(p<0.05)" if pp < 0.05 else ("경계(p<0.10)" if pp < 0.10 else "비유의")
        print(f"\n  {h:02d}시:")
        print(f"    Pearson  r = {r:+.3f} ({sig}, p={pp:.4f}) — {direction}")
        print(f"    Spearman ρ = {sr:+.3f} (p={sp:.4f}) — 소표본 신뢰도")

# ── 7. 결과 저장 ─────────────────────────────────────────────────────
result_summary = {}
for h in TARGET_HOURS:
    if corr_results[h]:
        result_summary[f'h{h:02d}'] = {
            k: v for k, v in corr_results[h].items() if k != 'data'
        }

out_json = os.path.join(RES_DIR, 'validation_summary.json')
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(result_summary, f, ensure_ascii=False, indent=2)
print(f"\n결과 저장: {out_json}")
print("\n=== 완료 ===")
