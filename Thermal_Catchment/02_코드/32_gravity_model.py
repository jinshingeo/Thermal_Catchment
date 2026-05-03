"""
Task 4 — 중력모형 기반 대중교통 접근성 계산
============================================
집계구별 Classic / Thermal 접근성 지수(A_i) 계산 후
TARR(Thermal Accessibility Reduction Rate)와 AAL(Absolute Accessibility Loss) 산출

  A_i = Σ_j W_j × G(t_ij, t0=30min)
  G(t, t0) = exp(-0.5 × (t/t0)²)   — Gaussian 거리감쇠
  W_j = 1 (지하철·버스 동등, 추후 확장 가능)

  TARR_i (%) = (A_classic - A_thermal) / A_classic × 100
  AAL_i      =  A_classic - A_thermal

입력 (← 03_결과물/):
  catchment_classic_30min.json
  catchment_thermal_30min.json
  catchment_summary_30min.csv      — 집계구 기본 정보

출력 (→ 03_결과물/):
  gravity_results_30min.csv        — 집계구별 A_classic, A_thermal, TARR, AAL, 분류
"""

import os
import json
import numpy as np
import pandas as pd

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')

CLASSIC_PATH = os.path.join(RES_DIR, 'catchment_classic_30min.json')
THERMAL_PATH = os.path.join(RES_DIR, 'catchment_thermal_30min.json')
SUMMARY_PATH = os.path.join(RES_DIR, 'catchment_summary_30min.csv')

T0_SEC = 30 * 60   # Gaussian 감쇠 기준 시간 (1800초)


# ── 1. 데이터 로드 ────────────────────────────────────────────────────────
print("데이터 로드 중...")
with open(CLASSIC_PATH, encoding='utf-8') as f:
    classic = json.load(f)
with open(THERMAL_PATH, encoding='utf-8') as f:
    thermal = json.load(f)

summary_df = pd.read_csv(SUMMARY_PATH, encoding='utf-8-sig')
summary_df['집계구코드'] = summary_df['집계구코드'].astype(float).astype(int).astype(str)

print(f"  집계구 수: {len(summary_df):,}개")


# ── 2. 중력모형 접근성 계산 ───────────────────────────────────────────────
def gaussian_decay(t_sec, t0=T0_SEC):
    return np.exp(-0.5 * (t_sec / t0) ** 2)


def gravity_score(catchment_dict):
    """
    catchment_dict: {stop_id: travel_time_sec}
    반환: 접근성 지수 (float)
    """
    if not catchment_dict:
        return 0.0
    return sum(gaussian_decay(t) for t in catchment_dict.values())


print("중력모형 접근성 계산 중...")
rows = []
for _, row in summary_df.iterrows():
    code = str(row['집계구코드'])
    a_classic = gravity_score(classic.get(code, {}))
    a_thermal = gravity_score(thermal.get(code, {}))
    rows.append({
        '집계구코드':    code,
        'residential_pop': row['residential_pop'],
        'lon':           row['lon'],
        'lat':           row['lat'],
        'n_classic_stops': row['n_classic_stops'],
        'n_thermal_stops': row['n_thermal_stops'],
        'a_classic':     round(a_classic, 4),
        'a_thermal':     round(a_thermal, 4),
    })

results_df = pd.DataFrame(rows)


# ── 3. TARR / AAL 계산 ────────────────────────────────────────────────────
print("TARR / AAL 계산 중...")

results_df['aal'] = (results_df['a_classic'] - results_df['a_thermal']).round(4)

# TARR: a_classic == 0 이면 0으로 처리 (Classic 접근 불가 집계구)
results_df['tarr'] = np.where(
    results_df['a_classic'] > 0,
    (results_df['aal'] / results_df['a_classic'] * 100).round(2),
    0.0
)


# ── 4. Thermal-robust / Thermal-prone 분류 ────────────────────────────────
# TARR 분포 기반 3분위수 컷: 하위 33% = robust, 상위 33% = prone, 나머지 = moderate
# (a_classic == 0 인 집계구는 'no_access'로 별도 처리)
print("Thermal-robust / Thermal-prone 분류 중...")

valid = results_df[results_df['a_classic'] > 0]['tarr']
q33 = valid.quantile(0.33)
q67 = valid.quantile(0.67)

def classify(row):
    if row['a_classic'] == 0:
        return 'no_access'
    if row['tarr'] <= q33:
        return 'thermal_robust'
    if row['tarr'] >= q67:
        return 'thermal_prone'
    return 'moderate'

results_df['category'] = results_df.apply(classify, axis=1)

print(f"  TARR 33th percentile: {q33:.1f}%  |  67th: {q67:.1f}%")


# ── 5. 요약 통계 출력 ────────────────────────────────────────────────────
print("\n=== 접근성 분석 결과 ===")
print(f"  Classic 평균 A_i     : {results_df['a_classic'].mean():.3f}")
print(f"  Thermal 평균 A_i     : {results_df['a_thermal'].mean():.3f}")
print(f"  평균 TARR            : {results_df[results_df['a_classic']>0]['tarr'].mean():.1f}%")
print(f"  평균 AAL             : {results_df['aal'].mean():.3f}")
print(f"\n  분류 분포:")
for cat, cnt in results_df['category'].value_counts().items():
    pct = cnt / len(results_df) * 100
    print(f"    {cat:20s}: {cnt:3d}개 ({pct:.1f}%)")

print(f"\n  TARR 상위 10 집계구 (Thermal-prone):")
top10 = results_df[results_df['a_classic']>0].nlargest(10, 'tarr')[
    ['집계구코드','a_classic','a_thermal','tarr','aal']
]
print(top10.to_string(index=False))


# ── 6. 저장 ──────────────────────────────────────────────────────────────
out_path = os.path.join(RES_DIR, 'gravity_results_30min.csv')
results_df.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f"\n저장: {out_path}")
print("\n=== Task 4 완료 ===")
print("다음 단계: 33_visualization.py 실행 (Task 5)")
