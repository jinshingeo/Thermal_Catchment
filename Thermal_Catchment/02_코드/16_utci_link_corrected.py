"""
링크별 SVF + 가로수 캐노피 기반 UTCI 보정
==========================================
보정 공식:
  UTCI_corrected = UTCI_idw - ΔUTCI_svf - ΔUTCI_canopy

  ΔUTCI_svf    = SVF_COEFF    × (1 − SVF)          × solar_factor(hour)
  ΔUTCI_canopy = CANOPY_COEFF × canopy_ratio         × solar_factor(hour)

계수 근거 (Lindberg & Grimmond 2011, Chen & Ng 2012):
  SVF_COEFF    = 8.0°C  — 완전 개활지(SVF=1) → 완전 협곡(SVF=0) 시 MRT 차이 기반
  CANOPY_COEFF = 2.5°C  — 수목 캐노피 완전 덮임 시 추가 복사 차단
  (야간: solar_factor=0 → 보정 없음)

solar_factor(hour): 서울 여름 태양 고도각 기반 일사 가중치 (0~1)
  낮 12~13시 = 1.0, 새벽/밤 = 0.0
"""

import os
import numpy as np
import pandas as pd

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
STP_BASE  = '/Users/jin/석사논문/성동구_STP연구'
UTCI_PATH = os.path.join(STP_BASE, '04_분석결과/link_utci_by_hour_v3.csv')
SVF_PATH  = os.path.join(RES_DIR, 'link_svf_canopy.csv')
OUT_PATH  = os.path.join(RES_DIR, 'link_utci_corrected.csv')

SVF_COEFF    = 8.0   # °C — SVF에 의한 최대 UTCI 감소
CANOPY_COEFF = 2.5   # °C — 가로수 캐노피에 의한 최대 UTCI 감소

# 서울 여름(7~8월) 태양 고도각 기반 일사 가중치
# 일출 약 05:20, 일몰 약 19:40 / 최고 고도각 12~13시
SOLAR_FACTOR = {
    0: 0.00,  1: 0.00,  2: 0.00,  3: 0.00,  4: 0.00,
    5: 0.05,  6: 0.20,  7: 0.40,  8: 0.60,  9: 0.75,
    10: 0.88, 11: 0.95, 12: 1.00, 13: 1.00, 14: 0.95,
    15: 0.88, 16: 0.75, 17: 0.60, 18: 0.40, 19: 0.20,
    20: 0.05, 21: 0.00, 22: 0.00, 23: 0.00,
}

# ── 데이터 로드 ────────────────────────────────────────────────────────
print("UTCI 데이터 로드 중...")
utci_df = pd.read_csv(UTCI_PATH, encoding='utf-8-sig')
print(f"  {len(utci_df):,}행 | 링크 {utci_df[['u','v']].drop_duplicates().shape[0]:,}개 × {utci_df['hour'].nunique()}시간")

print("SVF/캐노피 데이터 로드 중...")
svf_df = pd.read_csv(SVF_PATH, encoding='utf-8-sig')
print(f"  링크 {len(svf_df):,}개 | SVF 평균 {svf_df['svf'].mean():.3f} | 캐노피 평균 {svf_df['canopy_ratio'].mean()*100:.1f}%")

# ── 병합 ───────────────────────────────────────────────────────────────
# SVF는 무방향 링크(7,819개), UTCI는 양방향(15,459개)
# 정방향(u,v) 매칭 + 역방향(v,u) 매칭을 SVF 딕셔너리로 처리
print("\nUTCI ↔ SVF 병합 중...")
svf_dict = {}
for _, row in svf_df.iterrows():
    key = (int(row['u']), int(row['v']))
    svf_dict[key] = (row['svf'], row['canopy_ratio'])
    svf_dict[(int(row['v']), int(row['u']))] = (row['svf'], row['canopy_ratio'])  # 역방향

def lookup_svf(u, v):
    return svf_dict.get((int(u), int(v)), (np.nan, np.nan))

utci_df[['svf', 'canopy_ratio']] = pd.DataFrame(
    [lookup_svf(u, v) for u, v in zip(utci_df['u'], utci_df['v'])],
    index=utci_df.index
)
merged = utci_df.copy()

still_missing = merged['svf'].isna().sum()
merged['svf']          = merged['svf'].fillna(svf_df['svf'].mean())
merged['canopy_ratio'] = merged['canopy_ratio'].fillna(0.0)
match_rate = (1 - still_missing / len(merged)) * 100
print(f"  매칭률: {match_rate:.1f}%  (미매칭 {still_missing:,}행 → 평균값 대체)")

# ── 보정 계산 ──────────────────────────────────────────────────────────
merged['solar_factor']  = merged['hour'].map(SOLAR_FACTOR)
merged['delta_svf']     = (SVF_COEFF    * (1 - merged['svf'])       * merged['solar_factor']).round(2)
merged['delta_canopy']  = (CANOPY_COEFF * merged['canopy_ratio']     * merged['solar_factor']).round(2)
merged['utci_corrected']= (merged['utci_idw'] - merged['delta_svf'] - merged['delta_canopy']).round(2)
merged['utci_corrected']= merged['utci_corrected'].clip(lower=20.0)  # 물리적 하한선

# ── 저장 ───────────────────────────────────────────────────────────────
cols_out = ['u', 'v', 'hour', 'utci_idw', 'svf', 'canopy_ratio',
            'solar_factor', 'delta_svf', 'delta_canopy', 'utci_corrected',
            'bridge', 'highway']
merged[cols_out].to_csv(OUT_PATH, index=False, encoding='utf-8-sig')
print(f"\n저장 완료: {OUT_PATH}")

# ── 결과 요약 ───────────────────────────────────────────────────────────
print("\n=== 보정 효과 요약 (13시 기준) ===")
h13 = merged[merged['hour'] == 13].copy()

print(f"\n원본 UTCI_idw 분포:")
print(f"  min {h13['utci_idw'].min():.1f}°C | mean {h13['utci_idw'].mean():.1f}°C | max {h13['utci_idw'].max():.1f}°C")

print(f"\n보정 후 UTCI_corrected 분포:")
print(f"  min {h13['utci_corrected'].min():.1f}°C | mean {h13['utci_corrected'].mean():.1f}°C | max {h13['utci_corrected'].max():.1f}°C")

print(f"\nSVF 보정 Δ (13시):")
print(f"  평균 -{h13['delta_svf'].mean():.1f}°C | 최대 -{h13['delta_svf'].max():.1f}°C")
print(f"캐노피 보정 Δ (13시):")
print(f"  평균 -{h13['delta_canopy'].mean():.1f}°C | 최대 -{h13['delta_canopy'].max():.1f}°C")

print(f"\n임계값(38°C) 기준 링크 수 변화 (13시):")
n_orig_hot = (h13['utci_idw'] >= 38).sum()
n_corr_hot = (h13['utci_corrected'] >= 38).sum()
print(f"  원본:  {n_orig_hot:,}개 ({n_orig_hot/len(h13)*100:.1f}%) 이 ≥38°C → 제거 대상")
print(f"  보정후: {n_corr_hot:,}개 ({n_corr_hot/len(h13)*100:.1f}%) 이 ≥38°C → 제거 대상")
print(f"  그늘/가로수로 구제된 링크: {n_orig_hot - n_corr_hot:,}개")

print(f"\n교량 vs 일반 도로 비교 (13시, 보정 후):")
br = h13[h13['bridge'].isin(['yes', "['yes', 'viaduct']", 'viaduct'])]
nbr= h13[~h13['bridge'].isin(['yes', "['yes', 'viaduct']", 'viaduct'])]
print(f"  교량:    UTCI_idw {br['utci_idw'].mean():.1f}°C → 보정 후 {br['utci_corrected'].mean():.1f}°C  (Δ -{br['delta_svf'].mean():.1f}°C)")
print(f"  일반도로: UTCI_idw {nbr['utci_idw'].mean():.1f}°C → 보정 후 {nbr['utci_corrected'].mean():.1f}°C  (Δ -{nbr['delta_svf'].mean():.1f}°C)")
