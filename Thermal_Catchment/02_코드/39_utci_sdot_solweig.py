"""
Method 3: S-DoT IDW 보간 + SOLWEIG 표준 MRT → UTCI
=====================================================
Method 1 (IDW+SVF 선형 보정)과 Method 2 (SOLWEIG 단독, Open-Meteo)의
한계를 보완:
  - Method 1 한계: UTCI 선형 차감(비물리적), MRT 수식 단순화
  - Method 2 한계: 기상 입력이 단일 지점 → Tair 공간 변이 없음

본 방법:
  - 기상 입력: S-DoT 실측 57개 센서 → IDW 보간 → 링크별 Tair, RH, wind
  - MRT 계산: SOLWEIG 표준 공식 (Lindberg & Grimmond 2011)
  - 일사량(GHI): Open-Meteo archive (S-DoT 동일 기간)
  - UTCI: pythermalcomfort (Bröde et al. 2012)

참고문헌:
  Lindberg & Grimmond (2011) — SOLWEIG MRT 표준 공식
  Thorsson et al. (2007)    — 옥외 MRT 추정 방법론
  Höppe (1992)              — fp=0.308 (서 있는 사람)
  Fanger (1970)             — α_k=0.70
  ISO 7726 (1998)           — ε_p=0.97
  Brutsaert (1975)          — 대기 장파 추정식
  Erbs et al. (1982)        — 직산 분리 모델
  Bröde et al. (2012)       — UTCI 계산

출력:
  link_utci_sdot_solweig.csv  — 링크별·시간별 UTCI (Method 3)
"""

import os
import numpy as np
import pandas as pd
import requests
from pyproj import Transformer
from pythermalcomfort.models import utci
import warnings
warnings.filterwarnings('ignore')

# ── 경로 ──────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR  = os.path.dirname(BASE)
RES_DIR   = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR   = os.path.join(RES_DIR, 'figures')
STP_BASE  = '/Users/jin/석사논문/성동구_STP연구'
os.makedirs(RES_DIR, exist_ok=True)

SDOT_PATH = os.path.join(STP_BASE, '04_분석결과', 'sdot_utci_v3_seongdong.csv')
SVF_PATH  = os.path.join(RES_DIR, 'link_svf_canopy.csv')
NET_PATH  = os.path.join(STP_BASE, '01_네트워크', 'seongdong_walk_network.graphml')
REF1_PATH = os.path.join(RES_DIR, 'link_utci_corrected.csv')    # Method 1
REF2_PATH = os.path.join(RES_DIR, 'link_utci_solweig.csv')      # Method 2
OUT_PATH  = os.path.join(RES_DIR, 'link_utci_sdot_solweig.csv') # Method 3

# S-DoT 데이터 기간 (기상 기간을 맞춤)
START_DATE = '2025-07-28'
END_DATE   = '2025-08-03'

# ── 물리 상수 (Method 2와 동일) ───────────────────────────────────────────
ALPHA_K      = 0.70
EPSILON_P    = 0.97
FP           = 0.308
SIGMA        = 5.67e-8
EPSILON_WALL = 0.90
DELTA_T_WALL = 10.0
CANOPY_COEFF = 2.5
IDW_POWER    = 2

SOLAR_FACTOR = {
    0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00,
    5: 0.05, 6: 0.20, 7: 0.40, 8: 0.60, 9: 0.75,
    10: 0.88, 11: 0.95, 12: 1.00, 13: 1.00, 14: 0.95,
    15: 0.88, 16: 0.75, 17: 0.60, 18: 0.40, 19: 0.20,
    20: 0.05, 21: 0.00, 22: 0.00, 23: 0.00,
}

wgs_to_5186 = Transformer.from_crs('EPSG:4326', 'EPSG:5186', always_xy=True)


# ── 함수 정의 ─────────────────────────────────────────────────────────────
def cos_solar_zenith(hour, lat=37.55, lon=127.04, doy=210):
    lat_r = np.radians(lat)
    decl  = np.radians(23.45 * np.sin(np.radians(360 / 365 * (284 + doy))))
    solar_time = hour + (lon - 135.0) / 15.0
    hour_angle = np.radians(15.0 * (solar_time - 12.0))
    cos_z = (np.sin(lat_r) * np.sin(decl) +
             np.cos(lat_r) * np.cos(decl) * np.cos(hour_angle))
    return float(max(cos_z, 0.0))


def split_radiation(GHI, cos_z):
    """Erbs et al. (1982) 직산 분리"""
    if GHI <= 10 or cos_z < 0.01:
        return 0.0, float(GHI)
    kt = min(GHI / (1367.0 * cos_z), 1.0)
    if kt <= 0.22:
        kd = 1.0 - 0.09 * kt
    elif kt <= 0.80:
        kd = max(0.9511 - 0.1604*kt + 4.388*kt**2
                 - 16.638*kt**3 + 12.336*kt**4, 0.1)
    else:
        kd = 0.165
    return float(GHI * (1 - kd)), float(GHI * kd)


def compute_mrt(Tair, GHI, RH, svf, cos_z):
    """SOLWEIG 표준 MRT (Lindberg & Grimmond 2011; Thorsson et al. 2007)"""
    Tair_K = Tair + 273.15
    K_dir, K_dif = split_radiation(GHI, cos_z)
    K_abs = K_dir * FP + K_dif * svf * 0.5
    ea = (RH / 100.0) * 6.112 * np.exp(17.67 * Tair / (Tair + 243.5))
    eps_sky = float(np.clip(0.575 * ea ** (1.0 / 7.0), 0.70, 1.00))
    L_sky  = eps_sky * SIGMA * Tair_K ** 4
    dT = DELTA_T_WALL if GHI > 50 else 0.0
    L_wall = EPSILON_WALL * SIGMA * (Tair_K + dT) ** 4
    L_mean = L_sky * svf + L_wall * (1.0 - svf)
    mrt_K  = ((ALPHA_K * K_abs + L_mean) / (EPSILON_P * SIGMA)) ** 0.25
    return float(mrt_K - 273.15)


def idw(qx, qy, sx, sy, vals, power=IDW_POWER):
    """역거리 가중 보간"""
    dx, dy = sx - qx, sy - qy
    dist = np.sqrt(dx**2 + dy**2)
    if dist.min() < 1.0:
        return float(vals[dist.argmin()])
    w = 1.0 / dist ** power
    return float(np.sum(w * vals) / np.sum(w))


# ── 1. S-DoT 기상 데이터 로드 ─────────────────────────────────────────────
print("S-DoT 기상 데이터 로드 중...")
sdot = pd.read_csv(SDOT_PATH, encoding='utf-8-sig')
print(f"  {len(sdot):,}행 | 센서 {sdot['serial'].nunique()}개 | {sdot['date'].min()}~{sdot['date'].max()}")

# 센서별·시간대별 평균 (7일 평균)
sensor_avg = (sdot
    .groupby(['serial', 'hour', 'lat', 'lon'])[['temp', 'humi', 'v']]
    .mean()
    .reset_index())

# 센서 좌표 → EPSG:5186
sx_all, sy_all = wgs_to_5186.transform(
    sensor_avg['lon'].values, sensor_avg['lat'].values)
sensor_avg['sx'] = sx_all
sensor_avg['sy'] = sy_all

h13 = sensor_avg[sensor_avg['hour'] == 13]
print(f"  13시 Tair: min={h13['temp'].min():.1f}  mean={h13['temp'].mean():.1f}  "
      f"max={h13['temp'].max():.1f}  std={h13['temp'].std():.2f}°C")


# ── 2. Open-Meteo GHI 취득 (S-DoT 동일 기간) ─────────────────────────────
print("\nOpen-Meteo GHI 취득 중...")
resp = requests.get(
    "https://archive-api.open-meteo.com/v1/archive",
    params={
        "latitude": 37.550, "longitude": 127.040,
        "start_date": START_DATE, "end_date": END_DATE,
        "hourly": ["shortwave_radiation"],
        "timezone": "Asia/Seoul",
    },
    timeout=30,
)
resp.raise_for_status()
raw = resp.json()['hourly']
ghi_df = pd.DataFrame({
    'dt':  pd.to_datetime(raw['time']),
    'GHI': raw['shortwave_radiation'],
})
ghi_df['hour'] = ghi_df['dt'].dt.hour
ghi_hourly = ghi_df.groupby('hour')['GHI'].mean().to_dict()
print(f"  GHI 13시 평균: {ghi_hourly.get(13, 0):.0f} W/m²")


# ── 3. 링크 중심점 좌표 계산 ─────────────────────────────────────────────
print("\n네트워크 링크 중심점 계산 중...")
import networkx as nx
G = nx.read_graphml(NET_PATH)
edge_rows = []
for u, v, d in G.edges(data=True):
    xu, yu = wgs_to_5186.transform(float(G.nodes[u]['x']), float(G.nodes[u]['y']))
    xv, yv = wgs_to_5186.transform(float(G.nodes[v]['x']), float(G.nodes[v]['y']))
    edge_rows.append({
        'u': u, 'v': v,
        'mx': (xu + xv) / 2, 'my': (yu + yv) / 2,
    })
edges_df = pd.DataFrame(edge_rows)
print(f"  링크 수: {len(edges_df):,}개")


# ── 4. SVF 로드 ───────────────────────────────────────────────────────────
print("SVF 데이터 로드 중...")
svf_df = pd.read_csv(SVF_PATH, encoding='utf-8-sig')
svf_dict = {}
for _, row in svf_df.iterrows():
    key = (str(int(row['u'])), str(int(row['v'])))
    svf_dict[key] = (float(row['svf']), float(row['canopy_ratio']))
    svf_dict[(str(int(row['v'])), str(int(row['u'])))] = (float(row['svf']), float(row['canopy_ratio']))
svf_mean = svf_df['svf'].mean()
print(f"  SVF 평균: {svf_mean:.3f}")


# ── 5. 링크별·시간별 IDW + SOLWEIG MRT + UTCI ───────────────────────────
print("\nMethod 3 계산 중 (IDW Tair/RH/wind + SOLWEIG MRT → UTCI)...")
hours = sorted(sensor_avg['hour'].unique())
all_rows = []

for hour in hours:
    h_df   = sensor_avg[sensor_avg['hour'] == hour]
    sx_h   = h_df['sx'].values
    sy_h   = h_df['sy'].values
    t_h    = h_df['temp'].values
    rh_h   = h_df['humi'].values
    v_h    = h_df['v'].values
    GHI    = ghi_hourly.get(hour, 0.0)
    cos_z  = cos_solar_zenith(hour)
    sf     = SOLAR_FACTOR.get(hour, 0.0)

    for _, erow in edges_df.iterrows():
        mx, my = erow['mx'], erow['my']
        u_str, v_str = str(erow['u']), str(erow['v'])

        # IDW 보간
        Tair = idw(mx, my, sx_h, sy_h, t_h)
        RH   = idw(mx, my, sx_h, sy_h, rh_h)
        va   = max(idw(mx, my, sx_h, sy_h, v_h), 0.5)

        # SVF 조회
        svf_val, canopy = svf_dict.get((u_str, v_str),
                          svf_dict.get((v_str, u_str), (svf_mean, 0.0)))

        # SOLWEIG MRT
        mrt = compute_mrt(Tair, GHI, RH, svf_val, cos_z)

        # UTCI
        try:
            utci_val = float(utci(tdb=Tair, tr=mrt, v=va, rh=RH)['utci'])
        except Exception:
            utci_val = np.nan

        # 캐노피 보정
        delta_c = CANOPY_COEFF * canopy * sf
        utci_final = max(utci_val - delta_c, 20.0) if not np.isnan(utci_val) else np.nan

        all_rows.append({
            'u': erow['u'], 'v': erow['v'], 'hour': hour,
            'Tair_idw': round(Tair, 2),
            'RH_idw':   round(RH, 1),
            'va_idw':   round(va, 2),
            'GHI':      round(GHI, 1),
            'svf':      round(svf_val, 4),
            'mrt':      round(mrt, 2),
            'utci_m3':  round(utci_val, 2) if not np.isnan(utci_val) else np.nan,
            'utci_final': round(utci_final, 2) if not np.isnan(utci_final) else np.nan,
        })

    if hour % 6 == 0:
        h_done = sensor_avg[sensor_avg['hour'] == hour]
        print(f"  {hour:02d}시 완료 | Tair IDW mean={h_done['temp'].mean():.1f}°C | GHI={GHI:.0f}W/m²")

df_out = pd.DataFrame(all_rows)
df_out.to_csv(OUT_PATH, index=False, encoding='utf-8-sig')
print(f"\n저장: {OUT_PATH}")
print(f"  행 수: {len(df_out):,} ({df_out['hour'].nunique()}시간 × {len(edges_df):,}링크)")


# ── 6. 3개 방법 비교 ──────────────────────────────────────────────────────
print("\n=== 방법별 비교 (13시 기준) ===")
h13 = df_out[df_out['hour'] == 13].copy()

print(f"\n[Method 3] S-DoT IDW + SOLWEIG MRT:")
print(f"  Tair IDW — min={h13['Tair_idw'].min():.1f}  mean={h13['Tair_idw'].mean():.1f}  "
      f"max={h13['Tair_idw'].max():.1f}  std={h13['Tair_idw'].std():.2f}°C")
print(f"  MRT      — min={h13['mrt'].min():.1f}  mean={h13['mrt'].mean():.1f}  "
      f"max={h13['mrt'].max():.1f}  std={h13['mrt'].std():.2f}°C")
print(f"  UTCI     — min={h13['utci_final'].min():.1f}  mean={h13['utci_final'].mean():.1f}  "
      f"max={h13['utci_final'].max():.1f}  std={h13['utci_final'].std():.2f}°C")
n_hot = (h13['utci_final'] >= 38).sum()
print(f"  ≥38°C: {n_hot:,}개 ({n_hot/len(h13)*100:.1f}%)")

# Method 1 비교
if os.path.exists(REF1_PATH):
    m1 = pd.read_csv(REF1_PATH, encoding='utf-8-sig')
    m1_13 = m1[m1['hour'] == 13]
    n1 = (m1_13['utci_corrected'] >= 38).sum()
    print(f"\n[Method 1] IDW+SVF 선형 보정:")
    print(f"  UTCI — mean={m1_13['utci_corrected'].mean():.1f}  std={m1_13['utci_corrected'].std():.2f}°C")
    print(f"  ≥38°C: {n1:,}개 ({n1/len(m1_13)*100:.1f}%)")

# Method 2 비교
if os.path.exists(REF2_PATH):
    m2 = pd.read_csv(REF2_PATH, encoding='utf-8-sig')
    m2_13 = m2[m2['hour'] == 13]
    n2 = (m2_13['utci_final'] >= 38).sum()
    print(f"\n[Method 2] SOLWEIG (Open-Meteo 단일 지점):")
    print(f"  UTCI — mean={m2_13['utci_final'].mean():.1f}  std={m2_13['utci_final'].std():.2f}°C")
    print(f"  ≥38°C: {n2:,}개 ({n2/len(m2_13)*100:.1f}%)")

print(f"\n{'='*50}")
bins = [0, 0.3, 0.5, 0.7, 0.9, 1.01]
labels = ['<0.3', '0.3~0.5', '0.5~0.7', '0.7~0.9', '0.9~1.0']
h13 = h13.copy()
h13['svf_cat'] = pd.cut(h13['svf'], bins=bins, labels=labels, right=False)
print("\nSVF 구간별 UTCI_final 평균 (Method 3, 13시):")
print(h13.groupby('svf_cat', observed=True)['utci_final'].agg(['mean','std','count']).round(2).to_string())

print("\n=== Method 3 완료 ===")
