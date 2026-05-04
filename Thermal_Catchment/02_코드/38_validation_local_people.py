"""
LOCAL_PEOPLE 기반 검증 — 폭염일 유동인구 감소율 vs. TARR 상관분석
=================================================================
2025년 7~8월 생활인구 데이터를 이용해 폭염 시 실제 보행 활동 감소 패턴이
TARR 공간 분포와 일치하는지 확인한다.

방법:
  1. Open-Meteo API로 2025년 7~8월 성동구 일별 최고기온 취득
  2. 폭염일 (Tmax ≥ 33°C, 기상청 기준) vs. 평시 주중 구분
  3. 집계구별 14시 유동인구 감소율 = (평시 - 폭염일) / 평시 × 100
  4. 유동인구 감소율 vs. TARR_h14 Pearson/Spearman 상관

출력 (→ 03_결과물/):
  validation_local_people.csv    — 집계구별 감소율 + TARR
  figures/fig13_validation.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

try:
    import requests
except ImportError:
    requests = None

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')

POP_DIR_07 = os.path.join(PROJ_DIR, '01_데이터', '인구', 'LOCAL_PEOPLE_202507')
POP_DIR_08 = os.path.join(PROJ_DIR, '01_데이터', '인구', 'LOCAL_PEOPLE_202508')
GRAVITY_PATH = os.path.join(RES_DIR, 'gravity_results_multihour.csv')

TARGET_HOUR   = 14
HEAT_THRESHOLD = 33.0   # 기상청 폭염일 기준 일최고기온
# 성동구 중심 좌표
LAT, LON = 37.5633, 127.0374


def set_korean_font():
    for path in ['/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                 '/Library/Fonts/NanumGothic.ttf']:
        if os.path.exists(path):
            fm.fontManager.addfont(path)
            plt.rcParams['font.family'] = fm.FontProperties(fname=path).get_name()
            break
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()


# ── 1. 날짜별 일최고기온 취득 (Open-Meteo) ─────────────────────────────────
def fetch_daily_tmax(start='2025-07-01', end='2025-08-31'):
    if requests is None:
        print("  [경고] requests 없음 — 날씨 데이터 수동 입력 필요")
        return {}
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&start_date={start}&end_date={end}"
        f"&daily=temperature_2m_max"
        f"&timezone=Asia%2FSeoul"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()['daily']
        return dict(zip(data['time'], data['temperature_2m_max']))
    except Exception as e:
        print(f"  [경고] 날씨 API 실패: {e}")
        return {}

print("날씨 데이터 취득 중 (Open-Meteo)...")
tmax_dict = fetch_daily_tmax()
if tmax_dict:
    heat_days = {d.replace('-', '') for d, t in tmax_dict.items() if t is not None and t >= HEAT_THRESHOLD}
    print(f"  폭염일 (Tmax ≥ {HEAT_THRESHOLD}°C): {sorted(heat_days)}")
    print(f"  폭염일 수: {len(heat_days)}일")
else:
    print("  [대안] 2025년 7~8월 기상청 공식 폭염 특보일 직접 지정")
    heat_days = set()


# ── 2. LOCAL_PEOPLE 로드 ──────────────────────────────────────────────────
def load_pop_dir(data_dir):
    dfs = []
    for f in sorted(os.listdir(data_dir)):
        if not f.endswith('.csv'):
            continue
        date_str = f.replace('LOCAL_PEOPLE_', '').replace('.csv', '')
        path = os.path.join(data_dir, f)
        try:
            df = pd.read_csv(path, encoding='cp949')
            df.columns = [c.lstrip('?"').rstrip('"') for c in df.columns]
            df['date'] = date_str
            dfs.append(df)
        except Exception as e:
            print(f"  로드 실패 {f}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

print("\n생활인구 데이터 로드 중...")
dfs = []
for pop_dir in [POP_DIR_07, POP_DIR_08]:
    if os.path.isdir(pop_dir):
        df = load_pop_dir(pop_dir)
        if len(df):
            dfs.append(df)
            print(f"  {os.path.basename(pop_dir)}: {df['date'].nunique()}일 로드")

if not dfs:
    raise FileNotFoundError("LOCAL_PEOPLE 데이터 없음")

pop_all = pd.concat(dfs, ignore_index=True)
pop_all['집계구코드'] = pop_all['집계구코드'].astype(str)

# 성동구 집계구 + 14시 필터
pop_sd = pop_all[
    (pop_all['집계구코드'].str.startswith('1104')) &
    (pop_all['시간대구분'] == TARGET_HOUR)
].copy()
print(f"  성동구 14시 레코드: {len(pop_sd):,}개 ({pop_sd['date'].nunique()}일)")


# ── 3. 폭염일 vs. 평시 주중 구분 ─────────────────────────────────────────
pop_sd['date_dt'] = pd.to_datetime(pop_sd['date'], format='%Y%m%d')
pop_sd['weekday'] = pop_sd['date_dt'].dt.dayofweek   # 0=월 ... 6=일

# 날씨 데이터 있는 경우: 폭염일 기준
# 없는 경우: 성동구 14시 평균 기온이 낮은 날들을 평시로 사용
if heat_days:
    pop_sd['is_heat'] = pop_sd['date'].isin(heat_days)
else:
    # 날씨 데이터 없으면 일별 평균 유동인구를 이용해 상대적 구분
    daily_avg = pop_sd.groupby('date')['총생활인구수'].mean()
    median_pop = daily_avg.median()
    heat_days_proxy = set(daily_avg[daily_avg < median_pop * 0.95].index)
    pop_sd['is_heat'] = pop_sd['date'].isin(heat_days_proxy)
    print(f"  [대안] 유동인구 하위 5% 기준 폭염 대리 변수 사용: {len(heat_days_proxy)}일")

# 주중만 사용 (주말 제외: 요일 효과 제거)
pop_weekday = pop_sd[pop_sd['weekday'] < 5].copy()
heat_wk  = pop_weekday[pop_weekday['is_heat']]
norm_wk  = pop_weekday[~pop_weekday['is_heat']]
print(f"  주중 폭염일: {heat_wk['date'].nunique()}일  |  주중 평시: {norm_wk['date'].nunique()}일")

# 집계구별 평균
heat_mean = heat_wk.groupby('집계구코드')['총생활인구수'].mean().rename('pop_heat')
norm_mean = norm_wk.groupby('집계구코드')['총생활인구수'].mean().rename('pop_norm')
pop_by_jibgaegu = pd.concat([heat_mean, norm_mean], axis=1).dropna()

# 유동인구 감소율 (폭염일에 얼마나 줄었는가)
pop_by_jibgaegu['pop_reduction_pct'] = (
    (pop_by_jibgaegu['pop_norm'] - pop_by_jibgaegu['pop_heat'])
    / pop_by_jibgaegu['pop_norm'] * 100
)
print(f"  집계구 수: {len(pop_by_jibgaegu)}개")
print(f"  평균 유동인구 감소율: {pop_by_jibgaegu['pop_reduction_pct'].mean():.2f}%")


# ── 4. TARR 병합 및 상관분석 ─────────────────────────────────────────────
gravity_df = pd.read_csv(GRAVITY_PATH, encoding='utf-8-sig')
gravity_df['집계구코드'] = gravity_df['집계구코드'].astype(float).astype(int).astype(str)
gravity_df = gravity_df[gravity_df['a_classic'] > 0]

val_df = pop_by_jibgaegu.reset_index().merge(
    gravity_df[['집계구코드', 'tarr_h14']], on='집계구코드', how='inner'
).dropna()
print(f"\n분석 집계구 (TARR + 감소율 모두 있는): {len(val_df)}개")

r_p, p_p = stats.pearsonr(val_df['tarr_h14'], val_df['pop_reduction_pct'])
r_s, p_s = stats.spearmanr(val_df['tarr_h14'], val_df['pop_reduction_pct'])

print(f"\n=== 검증 결과 ===")
print(f"  Pearson  r = {r_p:.3f}  (p = {p_p:.4f})")
print(f"  Spearman ρ = {r_s:.3f}  (p = {p_s:.4f})")
sig = '***' if p_p < 0.001 else '**' if p_p < 0.01 else '*' if p_p < 0.05 else '(n.s.)'
print(f"  → 유동인구 감소율과 TARR 상관: r={r_p:.3f} {sig}")


# ── 5. 시각화 ─────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 산점도: TARR vs. 유동인구 감소율
ax = axes[0]
ax.scatter(val_df['tarr_h14'], val_df['pop_reduction_pct'],
           alpha=0.4, s=20, color='#2c7bb6', linewidths=0)
m, b = np.polyfit(val_df['tarr_h14'], val_df['pop_reduction_pct'], 1)
x_line = np.linspace(val_df['tarr_h14'].min(), val_df['tarr_h14'].max(), 100)
ax.plot(x_line, m*x_line+b, color='#d7191c', linewidth=1.5)
ax.set_xlabel('TARR (%, 폭염 피크 14시)', fontsize=11)
ax.set_ylabel('실제 유동인구 감소율 (%)\n(폭염 주중일 vs. 평시 주중일)', fontsize=10)
ax.set_title(f'TARR vs. 유동인구 감소율\n(r={r_p:.3f}{sig}, n={len(val_df)})',
             fontsize=12, fontweight='bold')
ax.axhline(0, color='gray', linewidth=0.5, linestyle='--')
ax.grid(alpha=0.3)

# 분포 비교: 폭염일 vs 평시 유동인구
ax = axes[1]
ax.hist(pop_by_jibgaegu['pop_norm'], bins=30, alpha=0.6, color='#2c7bb6', label='평시 주중 14시')
ax.hist(pop_by_jibgaegu['pop_heat'], bins=30, alpha=0.6, color='#d7191c', label='폭염 주중 14시')
ax.set_xlabel('14시 집계구 유동인구 (명)', fontsize=11)
ax.set_ylabel('집계구 수', fontsize=11)
ax.set_title('폭염일 vs. 평시 14시 유동인구 분포\n(성동구 집계구 570개)', fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(alpha=0.3)

fig.suptitle('LOCAL_PEOPLE 기반 Thermal Catchment 검증 (2025년 7~8월, 성동구)',
             fontsize=13, fontweight='bold')
plt.tight_layout()
path = os.path.join(FIG_DIR, 'fig13_validation.png')
fig.savefig(path, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"\n저장: {path}")

val_df.to_csv(os.path.join(RES_DIR, 'validation_local_people.csv'),
              index=False, encoding='utf-8-sig')
print("저장: validation_local_people.csv")
print("\n=== 검증 분석 완료 ===")
