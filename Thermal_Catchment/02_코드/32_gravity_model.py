"""
Task 4 — 중력모형 기반 대중교통 접근성 계산 (3개 시간대)
=========================================================
폭염 전(10시) / 폭염 중간(13시) / 폭염 피크(14시) 각각에 대해
Classic / Thermal 접근성 지수(A_i), TARR, AAL 산출

  A_i = Σ_j G(t_ij, t0=30min),  G = exp(-0.5*(t/t0)²)
  TARR_i (%) = (A_classic - A_thermal) / A_classic × 100
  AAL_i      =  A_classic - A_thermal

출력 (→ 03_결과물/):
  gravity_results_multihour.csv
"""

import os
import json
import numpy as np
import pandas as pd

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')

SUMMARY_PATH = os.path.join(RES_DIR, 'catchment_summary_multihour.csv')
CLASSIC_PATH = os.path.join(RES_DIR, 'catchment_classic_30min.json')

TARGET_HOURS = {
    10: '폭염전',
    13: '폭염중간',
    14: '폭염피크',
}
T0_SEC = 30 * 60


# ── 1. 데이터 로드 ────────────────────────────────────────────────────────
print("데이터 로드 중...")
with open(CLASSIC_PATH, encoding='utf-8') as f:
    classic = json.load(f)

thermal = {}
for hour in TARGET_HOURS:
    path = os.path.join(RES_DIR, f'catchment_thermal_h{hour}_30min.json')
    with open(path, encoding='utf-8') as f:
        thermal[hour] = json.load(f)

summary_df = pd.read_csv(SUMMARY_PATH, encoding='utf-8-sig')
summary_df['집계구코드'] = summary_df['집계구코드'].astype(float).astype(int).astype(str)
print(f"  집계구 수: {len(summary_df):,}개")


# ── 2. 중력모형 계산 ──────────────────────────────────────────────────────
def gaussian_decay(t_sec, t0=T0_SEC):
    return np.exp(-0.5 * (t_sec / t0) ** 2)

def gravity_score(catchment_dict):
    if not catchment_dict:
        return 0.0
    return sum(gaussian_decay(t) for t in catchment_dict.values())


print("중력모형 접근성 계산 중...")
rows = []
for _, row in summary_df.iterrows():
    code = str(row['집계구코드'])
    a_classic = gravity_score(classic.get(code, {}))
    r = {
        '집계구코드':      code,
        'residential_pop': row['residential_pop'],
        'lon':             row['lon'],
        'lat':             row['lat'],
        'a_classic':       round(a_classic, 4),
    }
    for hour in TARGET_HOURS:
        r[f'a_thermal_h{hour}'] = round(gravity_score(thermal[hour].get(code, {})), 4)
    rows.append(r)

results_df = pd.DataFrame(rows)


# ── 3. TARR / AAL 계산 ────────────────────────────────────────────────────
for hour, label in TARGET_HOURS.items():
    col_t = f'a_thermal_h{hour}'
    results_df[f'aal_h{hour}'] = (results_df['a_classic'] - results_df[col_t]).round(4)
    results_df[f'tarr_h{hour}'] = np.where(
        results_df['a_classic'] > 0,
        (results_df[f'aal_h{hour}'] / results_df['a_classic'] * 100).round(2),
        0.0
    )


# ── 4. Thermal-prone / robust 분류 (피크 시간대 14시 기준) ─────────────────
print("분류 중 (TARR 3분위, 폭염 피크 14시 기준)...")
valid = results_df[results_df['a_classic'] > 0]['tarr_h14']
q33   = valid.quantile(0.33)
q67   = valid.quantile(0.67)

def classify(row):
    if row['a_classic'] == 0:
        return 'no_access'
    if row['tarr_h14'] <= q33:
        return 'thermal_robust'
    if row['tarr_h14'] >= q67:
        return 'thermal_prone'
    return 'moderate'

results_df['category'] = results_df.apply(classify, axis=1)
print(f"  TARR 33th: {q33:.1f}%  |  67th: {q67:.1f}%")


# ── 5. 요약 출력 ─────────────────────────────────────────────────────────
print("\n=== 접근성 분석 결과 ===")
print(f"  Classic 평균 A_i: {results_df['a_classic'].mean():.3f}")
for hour, label in TARGET_HOURS.items():
    mean_a    = results_df[f'a_thermal_h{hour}'].mean()
    mean_tarr = results_df[results_df['a_classic']>0][f'tarr_h{hour}'].mean()
    blocked   = (results_df[f'a_thermal_h{hour}'] == 0).sum()
    print(f"  {hour}시 ({label}): A_i={mean_a:.3f}  TARR={mean_tarr:.1f}%  완전차단={blocked}개")

print(f"\n  분류 (폭염 피크 14시 기준):")
for cat, cnt in results_df['category'].value_counts().items():
    print(f"    {cat:20s}: {cnt}개 ({cnt/len(results_df)*100:.1f}%)")


# ── 6. 저장 ──────────────────────────────────────────────────────────────
out_path = os.path.join(RES_DIR, 'gravity_results_multihour.csv')
results_df.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f"\n저장: {out_path}")
print("\n=== Task 4 완료 ===")
print("다음 단계: 33_visualization.py 실행")
