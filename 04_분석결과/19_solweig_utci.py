"""
SOLWEIG 기반 링크별 UTCI 계산 (Open-Meteo 기상 입력)
=====================================================
참고문헌:
  Lindberg et al. (2008)   — SOLWEIG 원전 (복사플럭스 기반 MRT 계산)
  Lindberg et al. (2018)   — UMEP (합성 DSM → SVF 활용)
  Bröde et al. (2012)      — UTCI 계산 절차 및 카테고리
  Chen & Ng (2012)         — 수목 캐노피 UTCI 감소 효과

MRT 계산 방법론 (Lindberg et al. 2008 단순화):
  낮:  MRT = Tair + Δ_sun × SVF
       Δ_sun = 0.5 × √(GHI × max(cos_z, 0))   [태양고도·일사량 연동]
  야간: MRT = Tair - 2.0 × SVF                  [개활지 복사냉각 효과]

  · SVF=1 (개활지): 태양복사 최대 노출 → MRT 가장 높음
  · SVF=0 (협곡):  태양복사 차단       → MRT ≈ Tair
  · 근거: Lindberg & Grimmond (2011) — 서울형 여름 조건 피크 Δ_MRT≈14-16°C

입력 기상: Open-Meteo archive (2025-07-28 ~ 2025-08-03, 7일 시간대별 평균)
           → 기존 S-DoT/ASOS v3 분석과 동일 기간 매칭

출력:
  link_utci_solweig.csv  — 링크별·시간별 MRT 및 UTCI (solweig 기반)
"""

import os
import numpy as np
import pandas as pd
import requests
from pythermalcomfort.models import utci

BASE     = os.path.dirname(os.path.abspath(__file__))
SVF_PATH = os.path.join(BASE, 'link_svf_canopy.csv')
OUT_PATH = os.path.join(BASE, 'link_utci_solweig.csv')

# 기존 S-DoT/ASOS 분석 기간과 동일하게 맞춤 (v3: 7일 평균)
START_DATE = '2025-07-28'
END_DATE   = '2025-08-03'

CANOPY_COEFF = 2.5   # °C — 수목 캐노피 최대 UTCI 감소 (Chen & Ng 2012)

# 서울 여름 태양 고도각 기반 일사 가중치 (solar_factor — 캐노피 보정용)
SOLAR_FACTOR = {
    0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00,
    5: 0.05, 6: 0.20, 7: 0.40, 8: 0.60, 9: 0.75,
    10: 0.88, 11: 0.95, 12: 1.00, 13: 1.00, 14: 0.95,
    15: 0.88, 16: 0.75, 17: 0.60, 18: 0.40, 19: 0.20,
    20: 0.05, 21: 0.00, 22: 0.00, 23: 0.00,
}


# ── 태양 고도각 계산 ────────────────────────────────────────────────────
def cos_solar_zenith(hour, lat=37.55, lon=127.04, doy=210):
    """
    서울 기준 태양 천정각 코사인 계산
    doy=210 : July 29 (연간 대표일 고정)
    """
    lat_r = np.radians(lat)
    # 태양 적위
    decl  = np.radians(23.45 * np.sin(np.radians(360 / 365 * (284 + doy))))
    # 균시차 포함 태양시 (경도 127°, UTC+9 → 표준시 중심선 135°에서 -0.53h 보정)
    lon_correction = (lon - 135.0) / 15.0   # ≈ -0.53시간
    solar_time     = hour + lon_correction   # KST → 태양시 근사
    hour_angle     = np.radians(15.0 * (solar_time - 12.0))
    cos_z = (np.sin(lat_r) * np.sin(decl) +
             np.cos(lat_r) * np.cos(decl) * np.cos(hour_angle))
    return float(max(cos_z, 0.0))


# ── MRT 계산 (SOLWEIG 단순화 — Lindberg et al. 2008) ───────────────────
def compute_mrt(Tair, GHI, svf, cos_z):
    """
    낮: MRT = Tair + 0.5*√(GHI*cos_z) * svf
       - 완전 개활지(SVF=1): 최대 태양복사 노출 → 피크 Δ≈14°C (848W/m², cos_z=0.93)
       - 완전 협곡(SVF=0) : 태양복사 차단 → MRT=Tair
    야간: MRT = Tair - 2.0*svf
       - 개활지(SVF=1) : 장파복사 방출 → 약간 냉각
       - 협곡(SVF=0)  : 건물 장파 포집 → 기온 유지
    """
    if GHI > 10:   # 주간
        delta_sun = 0.5 * np.sqrt(GHI * cos_z)
        return Tair + delta_sun * svf
    else:           # 야간
        return Tair - 2.0 * svf


# ── 1. Open-Meteo 기상 데이터 취득 (7일 평균) ──────────────────────────
print(f"Open-Meteo Archive API에서 기상 데이터 취득 중...")
print(f"  기간: {START_DATE} ~ {END_DATE} (S-DoT/ASOS v3 분석 기간)")
print("  위치: 서울 성동구 중심 (lat=37.550, lon=127.040)")

url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude":   37.550,
    "longitude":  127.040,
    "start_date": START_DATE,
    "end_date":   END_DATE,
    "hourly": [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "shortwave_radiation",
    ],
    "timezone":        "Asia/Seoul",
    "wind_speed_unit": "ms",
}

resp = requests.get(url, params=params, timeout=30)
resp.raise_for_status()
raw = resp.json()['hourly']

weather_all = pd.DataFrame({
    'dt':   pd.to_datetime(raw['time']),
    'Tair': raw['temperature_2m'],
    'RH':   raw['relative_humidity_2m'],
    'va':   raw['wind_speed_10m'],
    'GHI':  raw['shortwave_radiation'],
})
weather_all['hour'] = weather_all['dt'].dt.hour

# 7일 시간대별 평균 (v3 기존 방법과 동일)
weather = (weather_all
           .groupby('hour')[['Tair', 'RH', 'va', 'GHI']]
           .mean()
           .reset_index())
weather['va'] = weather['va'].clip(lower=0.5)

print(f"  취득 완료: {len(weather_all)}행 → 시간대별 평균 {len(weather)}개")
print(f"  기온 평균(일간): {weather['Tair'].mean():.1f}°C / 13시 평균: {weather[weather['hour']==13]['Tair'].iloc[0]:.1f}°C")
print(f"  최대 일사(13시): {weather[weather['hour']==13]['GHI'].iloc[0]:.0f} W/m²")

# 7일 평균 기상 요약 저장
weather.to_csv(os.path.join(BASE, 'openmeteo_weather_avg.csv'), index=False, encoding='utf-8-sig')

# ── 2. SVF / 캐노피 데이터 로드 ────────────────────────────────────────
print("\nSVF / 캐노피 데이터 로드 중...")
svf_df = pd.read_csv(SVF_PATH, encoding='utf-8-sig')
print(f"  링크: {len(svf_df):,}개 | SVF 평균 {svf_df['svf'].mean():.3f}")


# ── 3. 링크별·시간별 UTCI 계산 ─────────────────────────────────────────
print("\n링크별 UTCI 계산 중 (MRT from SOLWEIG 공식 + pythermalcomfort)...")

all_rows = []

for _, wrow in weather.iterrows():
    h    = int(wrow['hour'])
    Tair = float(wrow['Tair'])
    RH   = float(wrow['RH'])
    va   = float(wrow['va'])
    GHI  = float(wrow['GHI'])
    sf   = SOLAR_FACTOR.get(h, 0.0)
    cos_z = cos_solar_zenith(h)

    for _, srow in svf_df.iterrows():
        svf_val    = float(srow['svf'])
        canopy_val = float(srow['canopy_ratio'])

        mrt = compute_mrt(Tair, GHI, svf_val, cos_z)

        try:
            utci_val = float(utci(tdb=Tair, tr=mrt, v=va, rh=RH)['utci'])
        except Exception:
            utci_val = np.nan

        delta_canopy   = CANOPY_COEFF * canopy_val * sf
        utci_corrected = max(utci_val - delta_canopy, 20.0) if not np.isnan(utci_val) else np.nan

        all_rows.append({
            'u':            int(srow['u']),
            'v':            int(srow['v']),
            'hour':         h,
            'Tair':         round(Tair, 2),
            'GHI':          round(GHI, 1),
            'cos_z':        round(cos_z, 3),
            'svf':          round(svf_val, 4),
            'canopy_ratio': round(canopy_val, 4),
            'mrt':          round(mrt, 2),
            'utci_solweig': round(utci_val, 2)  if not np.isnan(utci_val)  else np.nan,
            'delta_canopy': round(delta_canopy, 2),
            'utci_final':   round(utci_corrected, 2) if not np.isnan(utci_corrected) else np.nan,
        })

    if h % 6 == 0:
        print(f"  {h:02d}시 처리 완료 (Tair={Tair:.1f}°C, GHI={GHI:.0f}W/m², cos_z={cos_z:.3f})")

df_out = pd.DataFrame(all_rows)
df_out.to_csv(OUT_PATH, index=False, encoding='utf-8-sig')
print(f"\n저장 완료: {OUT_PATH}")
print(f"  행 수: {len(df_out):,} ({df_out['hour'].nunique()}시간 × {len(svf_df):,}링크)")


# ── 4. 결과 요약 ─────────────────────────────────────────────────────────
print("\n=== SOLWEIG 기반 UTCI 결과 요약 ===")
h13 = df_out[df_out['hour'] == 13].copy()
w13 = weather[weather['hour'] == 13].iloc[0]

print(f"\n[13시 기준 — {START_DATE}~{END_DATE} 7일 평균]")
print(f"  기상: 기온 {w13['Tair']:.1f}°C, 습도 {w13['RH']:.0f}%, "
      f"풍속 {w13['va']:.1f}m/s, 일사량 {w13['GHI']:.0f}W/m²")

print(f"\n  MRT 분포 (SVF에 따른 공간 변화):")
print(f"    min={h13['mrt'].min():.1f}°C  mean={h13['mrt'].mean():.1f}°C  max={h13['mrt'].max():.1f}°C  std={h13['mrt'].std():.2f}")

print(f"\n  UTCI_solweig (캐노피 보정 전):")
print(f"    min={h13['utci_solweig'].min():.1f}°C  mean={h13['utci_solweig'].mean():.1f}°C  max={h13['utci_solweig'].max():.1f}°C")

print(f"\n  UTCI_final (캐노피 보정 후):")
print(f"    min={h13['utci_final'].min():.1f}°C  mean={h13['utci_final'].mean():.1f}°C  max={h13['utci_final'].max():.1f}°C  std={h13['utci_final'].std():.2f}")

n_hot = (h13['utci_final'] >= 38).sum()
print(f"\n  ≥38°C (very strong heat stress) 링크: {n_hot:,}개 ({n_hot/len(h13)*100:.1f}%) → 보행 회피 대상")

# SVF 구간별 요약
bins   = [0, 0.3, 0.5, 0.7, 0.9, 1.01]
labels = ['<0.3 (밀집협곡)', '0.3~0.5 (반폐쇄)', '0.5~0.7 (일반주거)', '0.7~0.9 (준개활)', '0.9~1.0 (개활지)']
h13 = h13.copy()
h13['svf_cat'] = pd.cut(h13['svf'], bins=bins, labels=labels, right=False)

print(f"\n  SVF 구간별 평균 MRT & UTCI_final (13시):")
svf_summary = h13.groupby('svf_cat', observed=True)[['mrt', 'utci_final']].mean().round(1)
svf_summary['count'] = h13.groupby('svf_cat', observed=True).size()
print(svf_summary.to_string())

# 기존 IDW 보정 방법과 비교 (파일 있는 경우)
idw_path = os.path.join(BASE, 'link_utci_corrected.csv')
if os.path.exists(idw_path):
    idw_df = pd.read_csv(idw_path, encoding='utf-8-sig')
    idw_13 = idw_df[idw_df['hour'] == 13].copy()
    print(f"\n=== 기존 IDW+SVF 보정 vs SOLWEIG 비교 (13시) ===")
    print(f"  IDW+SVF 보정:  mean={idw_13['utci_corrected'].mean():.1f}°C  std={idw_13['utci_corrected'].std():.2f}")
    print(f"  SOLWEIG 기반:  mean={h13['utci_final'].mean():.1f}°C         std={h13['utci_final'].std():.2f}")
    n_hot_idw = (idw_13['utci_corrected'] >= 38).sum()
    print(f"  ≥38°C 링크: IDW+SVF={n_hot_idw:,}개({n_hot_idw/len(idw_13)*100:.1f}%) vs SOLWEIG={n_hot:,}개({n_hot/len(h13)*100:.1f}%)")

print("\n=== 완료 ===")
print(f"  주요 출력: {OUT_PATH}")
print("  다음 단계: 20_catchment_solweig.py — SOLWEIG UTCI로 열 캐치먼트 재계산")
