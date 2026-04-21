"""
지하철 승하차 인원 전처리 — Thermal Catchment Validation 준비
=============================================================
목적:
  Thermal Catchment reduction_pct와의 검증(validation)을 위해
  역별·시간대별 월간 승하차 인원을 정리

입력:
  02_기상데이터/subway_ridership_raw.csv
    - USE_MM: 년월 (YYYYMM)
    - SBWY_ROUT_LN_NM: 호선명 (환승역은 복수 행)
    - STTN: 역명
    - HR_{시간}_GET_ON_NOPE / HR_{시간}_GET_OFF_NOPE: 시간대별 승차/하차

출력:
  1. subway_hourly_station.csv    — 역별·시간대별·월별 총 승하차 (환승 합산)
  2. subway_validation_ready.csv  — 검증용 지표 (역별 정규화 승하차)

검증 논리:
  Thermal Catchment reduction_pct가 높은 역
  → 폭염 시간대(13시)에 실제 보행 접근이 어려워짐
  → 역 내 13시 승하차 비율이 상대적으로 낮을 것
  → reduction_pct ↑ 와 13시 승하차 비율 ↓ 의 음(-)의 상관관계

대상 시간대: 7·10·13·16시 (Thermal Catchment 분석과 동일)
대상 기간:   202307·202308·202407·202408 (폭염 포함 여름)
대상 역:     성동구 7개 역
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(BASE)               # Thermal_Catchment/
RES_DIR  = os.path.join(PROJ_DIR, '03_결과물')
FIG_DIR  = os.path.join(RES_DIR, 'figures')
os.makedirs(RES_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
RAW_PATH  = os.path.join(RES_DIR, '../../02_기상데이터/subway_ridership_raw.csv')
OUT_DIR   = BASE
FIG_DIR   = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

TARGET_HOURS = [7, 10, 13, 16]

# 역명 표준화 매핑 (API 역명 → 논문 역명)
STATION_MAP = {
    '왕십리(성동구청)': '왕십리역',
    '행당':            '행당역',
    '응봉':            '응봉역',
    '뚝섬':            '뚝섬역',
    '성수':            '성수역',
    '서울숲':          '서울숲역',
    '옥수':            '옥수역',
}

# ── 1. 원본 데이터 로드 ──────────────────────────────────────────────────
print("원본 데이터 로드 중...")
df = pd.read_csv(RAW_PATH, encoding='utf-8-sig')
print(f"  {len(df)}행 × {len(df.columns)}컬럼")
print(f"  기간: {sorted(df['USE_MM'].unique())}")
print(f"  역:   {sorted(df['STTN'].unique())}")

# ── 2. 시간대별 총 승하차(승차+하차) 컬럼 생성 ───────────────────────────
print("\n시간대별 총 승하차 컬럼 생성 중...")
for h in TARGET_HOURS:
    on_col  = f'HR_{h}_GET_ON_NOPE'
    off_col = f'HR_{h}_GET_OFF_NOPE'
    df[f'total_h{h:02d}'] = df[on_col].fillna(0) + df[off_col].fillna(0)

# 하루 전체 시간대 총합 (4시~3시)
all_hours = list(range(4, 24)) + list(range(0, 4))
daily_cols = []
for h in all_hours:
    on_col  = f'HR_{h}_GET_ON_NOPE'
    off_col = f'HR_{h}_GET_OFF_NOPE'
    if on_col in df.columns:
        df[f'_tmp_h{h}'] = df[on_col].fillna(0) + df[off_col].fillna(0)
        daily_cols.append(f'_tmp_h{h}')

df['total_daily'] = df[daily_cols].sum(axis=1)
df.drop(columns=daily_cols, inplace=True)

# ── 3. 역 단위 집계 (환승역: 호선별 행 → 역 단위 합산) ──────────────────
print("\n환승역 호선별 합산 중...")
agg_cols = [f'total_h{h:02d}' for h in TARGET_HOURS] + ['total_daily']

station_df = (
    df.groupby(['USE_MM', 'STTN'])[agg_cols]
    .sum()
    .reset_index()
)

# 역명 표준화
station_df['station'] = station_df['STTN'].map(STATION_MAP)
station_df.drop(columns=['STTN'], inplace=True)

print(f"  집계 완료: {len(station_df)}행")
print(f"  {station_df.groupby('station').size().to_dict()}")

# ── 4. 시간대 비율 계산 (정규화) ─────────────────────────────────────────
# 전체 일일 승하차 대비 각 시간대 비율
# → 역 규모(대형역 vs 소형역) 효과 제거
print("\n정규화 지표 계산 중...")
for h in TARGET_HOURS:
    col = f'total_h{h:02d}'
    station_df[f'ratio_h{h:02d}'] = (
        station_df[col] / station_df['total_daily']
    ).round(4)

# ── 5. 폭염 월 평균 계산 ─────────────────────────────────────────────────
# 2023·2024 7~8월 평균 → 역별 대표값
print("\n폭염 월 평균 계산 중...")
heat_avg = (
    station_df
    .groupby('station')[agg_cols + [f'ratio_h{h:02d}' for h in TARGET_HOURS]]
    .mean()
    .reset_index()
)
# 절대값 컬럼은 소수 1자리, 비율 컬럼은 소수 4자리
for col in agg_cols:
    heat_avg[col] = heat_avg[col].round(1)
for h in TARGET_HOURS:
    heat_avg[f'ratio_h{h:02d}'] = heat_avg[f'ratio_h{h:02d}'].round(4)

# 연도별 분리 (연도 간 비교용)
station_df['year'] = (station_df['USE_MM'] // 100).astype(int)
yearly_avg = (
    station_df
    .groupby(['station', 'year'])[agg_cols + [f'ratio_h{h:02d}' for h in TARGET_HOURS]]
    .mean()
    .round(1)
    .reset_index()
)

# ── 6. Thermal Catchment 결과 로드 및 병합 ──────────────────────────────
catchment_path = os.path.join(RES_DIR, 'catchment_solweig_summary.json')
if os.path.exists(catchment_path):
    import json
    print("\nThermal Catchment 결과 병합 중...")
    with open(catchment_path, encoding='utf-8') as f:
        ct = json.load(f)

    ct_rows = []
    for sname in STATION_MAP.values():
        key = sname  # 예: '왕십리역'
        if key in ct:
            for h in TARGET_HOURS:
                hkey = f'h{h:02d}'
                if hkey in ct[key]:
                    ct_rows.append({
                        'station':       key,
                        'hour':          h,
                        'reduction_pct': ct[key][hkey]['reduction_pct'],
                        'classic_nodes': ct[key][hkey]['classic_nodes'],
                        'thermal_nodes': ct[key][hkey]['thermal_nodes'],
                    })

    ct_df = pd.DataFrame(ct_rows)

    # 13시 reduction_pct만 추출해서 validation용 테이블에 합류
    ct_13 = ct_df[ct_df['hour'] == 13][['station', 'reduction_pct']].rename(
        columns={'reduction_pct': 'reduction_pct_13h'}
    )
    validation_df = heat_avg.merge(ct_13, on='station', how='left')

    # 7시도 추가
    ct_7 = ct_df[ct_df['hour'] == 7][['station', 'reduction_pct']].rename(
        columns={'reduction_pct': 'reduction_pct_07h'}
    )
    validation_df = validation_df.merge(ct_7, on='station', how='left')

    print(f"\n=== 검증용 핵심 지표 (역별) ===")
    print(validation_df[['station', 'reduction_pct_13h', 'reduction_pct_07h',
                          'ratio_h13', 'ratio_h07', 'total_daily']].to_string(index=False))
else:
    validation_df = heat_avg.copy()
    print("\n  catchment_solweig_summary.json 없음 — Thermal Catchment 미병합")

# ── 7. 저장 ─────────────────────────────────────────────────────────────
out1 = os.path.join(OUT_DIR, 'subway_hourly_station.csv')
out2 = os.path.join(OUT_DIR, 'subway_validation_ready.csv')
out3 = os.path.join(OUT_DIR, 'subway_yearly_avg.csv')

station_df.to_csv(out1, index=False, encoding='utf-8-sig')
validation_df.to_csv(out2, index=False, encoding='utf-8-sig')
yearly_avg.to_csv(out3, index=False, encoding='utf-8-sig')
print(f"\n저장 완료:")
print(f"  {out1}")
print(f"  {out2}")
print(f"  {out3}")

# ── 8. 시각화: 역별 시간대 승하차 비율 프로파일 ──────────────────────────
print("\n시각화 생성 중...")
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

stations = sorted(heat_avg['station'].dropna().unique())
colors   = plt.cm.Set2(np.linspace(0, 1, len(stations)))

# 좌: 시간대별 절대 승하차
ax = axes[0]
for stn, col in zip(stations, colors):
    row = heat_avg[heat_avg['station'] == stn].iloc[0]
    vals = [row[f'total_h{h:02d}'] for h in TARGET_HOURS]
    ax.plot(TARGET_HOURS, vals, 'o-', label=stn, color=col, linewidth=1.8, markersize=7)
ax.set_xlabel('시각', fontsize=11)
ax.set_ylabel('총 승하차 인원 (월 합산)', fontsize=11)
ax.set_title('역별 시간대별 총 승하차 인원\n(2023·2024 여름 평균)', fontsize=11, fontweight='bold')
ax.set_xticks(TARGET_HOURS)
ax.set_xticklabels([f'{h}시' for h in TARGET_HOURS])
ax.legend(fontsize=9, loc='upper left')
ax.grid(True, alpha=0.3)

# 우: 정규화 비율 (일일 대비)
ax = axes[1]
for stn, col in zip(stations, colors):
    row = heat_avg[heat_avg['station'] == stn].iloc[0]
    vals = [row[f'ratio_h{h:02d}'] * 100 for h in TARGET_HOURS]
    ax.plot(TARGET_HOURS, vals, 'o-', label=stn, color=col, linewidth=1.8, markersize=7)
ax.set_xlabel('시각', fontsize=11)
ax.set_ylabel('일일 대비 승하차 비율 (%)', fontsize=11)
ax.set_title('역별 시간대 승하차 비율 (정규화)\n(2023·2024 여름 평균)', fontsize=11, fontweight='bold')
ax.set_xticks(TARGET_HOURS)
ax.set_xticklabels([f'{h}시' for h in TARGET_HOURS])
ax.legend(fontsize=9, loc='upper left')
ax.grid(True, alpha=0.3)

plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'subway_ridership_profile.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  저장: figures/subway_ridership_profile.png")

# ── 9. 검증 산점도: reduction_pct vs 13시 승하차 비율 ────────────────────
if 'reduction_pct_13h' in validation_df.columns:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, (hour, label) in zip(axes, [(13, '13시 (폭염 피크)'), (7, '7시 (출근 이른 아침)')]):
        r_col = f'reduction_pct_{hour:02d}h'
        s_col = f'ratio_h{hour:02d}'
        if r_col not in validation_df.columns:
            continue

        plot_df = validation_df[['station', r_col, s_col]].dropna()

        for _, row in plot_df.iterrows():
            ax.scatter(row[r_col], row[s_col] * 100,
                       s=120, zorder=5, color='#1E88E5', edgecolors='white', linewidth=0.8)
            ax.annotate(row['station'],
                        (row[r_col], row[s_col] * 100),
                        textcoords='offset points', xytext=(6, 4), fontsize=8)

        # 추세선
        x = plot_df[r_col].values.astype(float)
        y = plot_df[s_col].values.astype(float) * 100
        corr = np.corrcoef(x, y)[0, 1] if np.std(x) > 0 and np.std(y) > 0 else float('nan')
        try:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            xline = np.linspace(x.min(), x.max(), 100)
            ax.plot(xline, p(xline), '--', color='#E53935', linewidth=1.5, alpha=0.8)
        except Exception:
            pass
        corr_str = f'Pearson r = {corr:.3f}' if not np.isnan(corr) else 'r = 계산불가'
        ax.set_title(
            f'Thermal Catchment 감소율 vs {label} 승하차 비율\n{corr_str}',
            fontsize=10, fontweight='bold'
        )

        ax.set_xlabel('Thermal Catchment reduction_pct (%)', fontsize=10)
        ax.set_ylabel(f'{label} 승하차 비율 (%)', fontsize=10)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'validation_scatter.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  저장: figures/validation_scatter.png")

print("\n=== 완료 ===")
print("다음 단계: reduction_pct vs 승하차 비율 상관관계 해석")
