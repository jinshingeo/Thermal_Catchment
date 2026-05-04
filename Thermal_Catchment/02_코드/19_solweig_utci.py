"""
SOLWEIG 기반 링크별 UTCI 계산 (Open-Meteo 기상 입력)
=====================================================
참고문헌:
  Lindberg & Grimmond (2011) — SOLWEIG MRT 표준 공식 (SVF 기반 복사 가중)
  Thorsson et al. (2007)     — 옥외 MRT 추정 방법론 비교
  Höppe (1992)               — 인체 투영면적계수 fp=0.308 (서 있는 사람)
  Fanger (1970)              — 인체 단파 흡수율 α_k=0.70
  ISO 7726 (1998)            — 인체 장파 방사율 ε_p=0.97
  Brutsaert (1975)           — 대기 장파 하향 복사 추정식
  Erbs et al. (1982)         — 전천일사 → 직산 분리 모델
  Bröde et al. (2012)        — UTCI 계산 절차 및 카테고리
  Chen & Ng (2012)           — 수목 캐노피 UTCI 감소 효과
  Oke (1987)                 — 도시 표면 방사율 및 열 특성

MRT 계산 방법론 (표준 공식, Lindberg & Grimmond 2011; Thorsson et al. 2007):

  (MRT + 273.15)^4 = (α_k × K_abs + L_mean) / (ε_p × σ)

  K_abs  = K_dir × fp  +  K_dif × SVF × 0.5         [인체 흡수 단파]
  L_mean = L_sky × SVF  +  L_wall × (1 − SVF)        [SVF 가중 장파]
  L_sky  = ε_sky × σ × Tair_K^4   (Brutsaert 1975)  [대기 장파]
  L_wall = ε_w × σ × T_wall_K^4   (Oke 1987)        [도시 표면 장파]

  물리 상수:
    α_k  = 0.70   인체 단파 흡수율 (Fanger 1970)
    ε_p  = 0.97   인체 장파 방사율 (ISO 7726)
    fp   = 0.308  투영면적계수, 서 있는 사람 (Höppe 1992)
    ε_w  = 0.90   도시 표면 방사율 (Oke 1987)
    σ    = 5.67×10⁻⁸  Stefan-Boltzmann 상수

입력 기상: Open-Meteo archive (2025-07-01 ~ 2025-08-31, 7~8월 전체 시간대별 평균)
출력:
  link_utci_solweig.csv  — 링크별·시간별 MRT 및 UTCI
"""

import os
import numpy as np
import pandas as pd
import requests
from pythermalcomfort.models import utci

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
SVF_PATH = os.path.join(RES_DIR, 'link_svf_canopy.csv')
OUT_PATH = os.path.join(RES_DIR, 'link_utci_solweig.csv')

# 기존 S-DoT/ASOS 분석 기간과 동일하게 맞춤 (v3: 7일 평균)
START_DATE = '2025-07-01'
END_DATE   = '2025-08-31'

# ── 물리 상수 (인용 근거 명시) ────────────────────────────────────────────
ALPHA_K      = 0.70      # 인체 단파 흡수율 (Fanger 1970; ISO 7730)
EPSILON_P    = 0.97      # 인체 장파 방사율 (ISO 7726)
FP           = 0.308     # 투영면적계수, 서 있는 사람 (Höppe 1992)
SIGMA        = 5.67e-8   # Stefan-Boltzmann 상수 (W m⁻² K⁻⁴)
EPSILON_WALL = 0.90      # 도시 표면 장파 방사율 (Oke 1987)
DELTA_T_WALL = 10.0      # 주간 도시 표면 기온 초과분 K (Oke 1982; 서울 여름 추정)
CANOPY_COEFF = 2.5       # 수목 캐노피 최대 UTCI 감소 °C (Chen & Ng 2012)

# 캐노피 보정용 태양고도 가중치 (서울 여름 기준)
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


# ── 직산 분리 (Erbs et al. 1982) ────────────────────────────────────────
def _split_radiation(GHI, cos_z):
    """전천일사 → 직달·산란 분리 (Erbs et al. 1982)"""
    if GHI <= 10 or cos_z < 0.01:
        return 0.0, float(GHI)
    I0 = 1367.0 * cos_z        # 대기권 외 수평면 일사
    kt = min(GHI / I0, 1.0)   # 청명도 지수
    if kt <= 0.22:
        kd = 1.0 - 0.09 * kt
    elif kt <= 0.80:
        kd = max(0.9511 - 0.1604*kt + 4.388*kt**2
                 - 16.638*kt**3 + 12.336*kt**4, 0.1)
    else:
        kd = 0.165
    K_dif = GHI * kd
    K_dir = GHI - K_dif        # 수평면 직달
    return float(K_dir), float(K_dif)


# ── MRT 표준 공식 (Lindberg & Grimmond 2011; Thorsson et al. 2007) ───────
def compute_mrt(Tair, GHI, RH, svf, cos_z):
    """
    (MRT+273.15)^4 = (α_k × K_abs + L_mean) / (ε_p × σ)

    K_abs  = K_dir × fp  +  K_dif × SVF × 0.5   [인체 흡수 단파, Höppe 1992]
    L_mean = L_sky × SVF  +  L_wall × (1−SVF)    [SVF 가중 장파]
    L_sky  = ε_sky × σ × Tair_K^4               [Brutsaert 1975]
    L_wall = ε_wall × σ × T_wall_K^4             [Oke 1987]
    """
    Tair_K = Tair + 273.15

    # 단파: 직산 분리 후 인체 흡수량 계산
    K_dir, K_dif = _split_radiation(GHI, cos_z)
    K_abs = K_dir * FP + K_dif * svf * 0.5

    # 장파: 대기 하향 (Brutsaert 1975)
    ea = (RH / 100.0) * 6.112 * np.exp(17.67 * Tair / (Tair + 243.5))  # hPa
    eps_sky = float(np.clip(0.575 * ea ** (1.0 / 7.0), 0.70, 1.00))
    L_sky = eps_sky * SIGMA * Tair_K ** 4

    # 장파: 도시 표면 (낮에는 가열된 표면 반영)
    dT = DELTA_T_WALL if GHI > 50 else 0.0
    L_wall = EPSILON_WALL * SIGMA * (Tair_K + dT) ** 4

    # SVF 가중 평균 장파
    L_mean = L_sky * svf + L_wall * (1.0 - svf)

    # MRT 역산 (Stefan-Boltzmann)
    mrt_K = ((ALPHA_K * K_abs + L_mean) / (EPSILON_P * SIGMA)) ** 0.25
    return float(mrt_K - 273.15)


# ── 1. Open-Meteo 기상 데이터 취득 → 폭염일만 평균 ──────────────────────
# 폭염일 기준: 일최고기온 Tmax ≥ 33°C (기상청 폭염 기준)
HEAT_THRESHOLD = 33.0

print("Open-Meteo Archive API에서 기상 데이터 취득 중...")
print(f"  기간: {START_DATE} ~ {END_DATE} (7~8월 전체)")
print("  위치: 서울 성동구 중심 (lat=37.550, lon=127.040)")

url = "https://archive-api.open-meteo.com/v1/archive"

# 시간별 데이터
hourly_params = {
    "latitude":   37.550,
    "longitude":  127.040,
    "start_date": START_DATE,
    "end_date":   END_DATE,
    "hourly": ["temperature_2m", "relative_humidity_2m",
               "wind_speed_10m", "shortwave_radiation"],
    "timezone":        "Asia/Seoul",
    "wind_speed_unit": "ms",
}
resp = requests.get(url, params=hourly_params, timeout=30)
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
weather_all['date'] = weather_all['dt'].dt.date

# 일최고기온 계산 → 폭염일 식별
daily_tmax = weather_all.groupby('date')['Tair'].max()
heat_days  = set(daily_tmax[daily_tmax >= HEAT_THRESHOLD].index)
print(f"  전체 일수: {daily_tmax.shape[0]}일 | 폭염일 (Tmax≥{HEAT_THRESHOLD}°C): {len(heat_days)}일")

# 폭염일만 필터링 → 시간대별 평균
weather_heat = weather_all[weather_all['date'].isin(heat_days)].copy()
weather = (weather_heat
           .groupby('hour')[['Tair', 'RH', 'va', 'GHI']]
           .mean()
           .reset_index())
weather['va'] = weather['va'].clip(lower=0.5)

print(f"  취득 완료: {len(weather_heat)}행(폭염일) → 시간대별 평균 {len(weather)}개")
print(f"  기온 평균(폭염일 일간): {weather['Tair'].mean():.1f}°C / 13시: {weather[weather['hour']==13]['Tair'].iloc[0]:.1f}°C")
print(f"  최대 일사(13시): {weather[weather['hour']==13]['GHI'].iloc[0]:.0f} W/m²")

# 7일 평균 기상 요약 저장
weather.to_csv(os.path.join(RES_DIR, 'openmeteo_weather_avg.csv'), index=False, encoding='utf-8-sig')

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

        mrt = compute_mrt(Tair, GHI, RH, svf_val, cos_z)

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
idw_path = os.path.join(RES_DIR, 'link_utci_corrected.csv')
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
