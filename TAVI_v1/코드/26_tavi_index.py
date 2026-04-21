"""
TAVI 지수 산출 — H × E × V 통합
=================================
TAVI(역) = reduction_pct(%) × vulnerability_ratio

  H (Hazard)        : SOLWEIG 기반 UTCI (38°C 임계값)
  E (Exposure)      : Thermal Catchment reduction_pct
                      = (Classic - Thermal) / Classic × 100
  V (Vulnerability) : 역 Catchment 내 취약인구 비율
                      = (65세 이상 + 14세 이하) / 전체 인구

이론 근거:
  - IPCC AR6 (2021): Risk = Hazard × Exposure × Vulnerability
  - Bröde et al. (2012): UTCI 38°C = "very strong heat stress"
  - Moreno et al. (2021): 15분 도보 시간예산
  - Kar, Le & Miller (2023): Hard constraint ↔ H×E, Soft constraint ↔ V

입력:
  catchment_solweig_summary.json   — H×E: 역별·시간대별 reduction_pct
  vulnerability_component.json     — V: 역별 vulnerability_ratio

출력:
  tavi_results.json                — TAVI 지수 (13시 기준)
  tavi_results.csv                 — 역별 TAVI 상세 테이블
  figures/tavi_summary.png         — 최종 시각화
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib
matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE     = os.path.dirname(os.path.abspath(__file__))
CT_PATH  = os.path.join(BASE, 'catchment_solweig_summary.json')
VUL_PATH = os.path.join(BASE, 'vulnerability_component.json')
FIG_DIR  = os.path.join(BASE, 'figures')
OUT_DIR  = BASE
os.makedirs(FIG_DIR, exist_ok=True)


# ── 1. 데이터 로드 ──────────────────────────────────────────────────────
print("데이터 로드 중...")
with open(CT_PATH, encoding='utf-8') as f:
    ct = json.load(f)
with open(VUL_PATH, encoding='utf-8') as f:
    vul = json.load(f)

STATIONS = ['왕십리역', '행당역', '응봉역', '뚝섬역', '성수역', '서울숲역', '옥수역']
HOURS    = [7, 10, 13, 16]

# ── 2. 역별 H×E×V 계산 ──────────────────────────────────────────────────
print("\n=== TAVI 지수 산출 ===")
print(f"{'역':<8} {'V비율':>7} {'E(13시)':>8} {'TAVI(13시)':>11}")
print("-" * 42)

tavi_rows = []
for stn in STATIONS:
    v_ratio = vul.get(stn, {}).get('vulnerability_ratio', np.nan)

    row = {
        'station':            stn,
        'vulnerability_ratio': v_ratio,
        'elderly_ratio':      vul.get(stn, {}).get('elderly_ratio', np.nan),
        'children_ratio':     vul.get(stn, {}).get('children_ratio', np.nan),
        'total_pop_catchment': vul.get(stn, {}).get('total_pop_catchment', np.nan),
    }

    for h in HOURS:
        hkey     = f'h{h:02d}'
        r_pct    = ct.get(stn, {}).get(hkey, {}).get('reduction_pct', np.nan)
        tavi_val = round(r_pct * v_ratio, 4) if not (np.isnan(r_pct) or np.isnan(v_ratio)) else np.nan
        row[f'reduction_pct_h{h:02d}'] = r_pct
        row[f'tavi_h{h:02d}']          = tavi_val

    tavi_rows.append(row)

    # 13시 요약 출력
    print(f"{stn:<8} {v_ratio:>6.3f}  {row['reduction_pct_h13']:>7.1f}%  {row['tavi_h13']:>10.4f}")

tavi_df = pd.DataFrame(tavi_rows)


# ── 3. 시각화 1: TAVI 시간대별 히트맵 ────────────────────────────────────
matrix = np.array([
    [tavi_df[tavi_df['station'] == s][f'tavi_h{h:02d}'].values[0] for h in HOURS]
    for s in STATIONS
])

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 좌: TAVI 히트맵
ax = axes[0]
vmax = np.nanmax(matrix)
im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto', vmin=0, vmax=vmax)
plt.colorbar(im, ax=ax, label='TAVI')
ax.set_xticks(range(len(HOURS)))
ax.set_xticklabels([f'{h}시' for h in HOURS], fontsize=11)
ax.set_yticks(range(len(STATIONS)))
ax.set_yticklabels(STATIONS, fontsize=11)
for i, s in enumerate(STATIONS):
    for j, h in enumerate(HOURS):
        val = matrix[i, j]
        if not np.isnan(val):
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=9, color='white' if val > vmax * 0.6 else 'black',
                    fontweight='bold')
ax.set_title(
    'TAVI = reduction_pct × vulnerability_ratio\n'
    '시간대별 | UTCI ≥ 38°C 하드 컷 | 시간예산 15분',
    fontsize=11, fontweight='bold'
)

# 우: 13시 기준 3개 지표 비교
ax = axes[1]
tavi_13   = tavi_df['tavi_h13'].values
e_13      = tavi_df['reduction_pct_h13'].values / 100   # 0~1 스케일로 정규화
v_vals    = tavi_df['vulnerability_ratio'].values
x = np.arange(len(STATIONS))
w = 0.25

colors_e    = '#EF6C00'
colors_v    = '#1565C0'
colors_tavi = '#6A1B9A'

b_e    = ax.bar(x - w, e_13,    w, label='E: reduction_pct (0~1)', color=colors_e,    alpha=0.85, edgecolor='gray')
b_v    = ax.bar(x,     v_vals,  w, label='V: vulnerability_ratio', color=colors_v,    alpha=0.85, edgecolor='gray')
b_tavi = ax.bar(x + w, tavi_13, w, label='TAVI = E×V (×100)',     color=colors_tavi, alpha=0.85, edgecolor='gray')

# TAVI 값 레이블
for bar, val in zip(b_tavi, tavi_13):
    if not np.isnan(val):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                f'{val:.2f}', ha='center', va='bottom', fontsize=8.5, fontweight='bold',
                color=colors_tavi)

ax.set_xticks(x)
ax.set_xticklabels(STATIONS, fontsize=10, rotation=15, ha='right')
ax.set_ylabel('지수 값', fontsize=11)
ax.set_title('H×E×V 분해 비교 (13시 기준)\nE = reduction_pct/100, V = 취약인구 비율',
             fontsize=11, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.3)

plt.suptitle(
    'TAVI (Thermal Accessibility Vulnerability Index) — 성동구 7개 역\n'
    'IPCC AR6 H×E×V 프레임워크 | SOLWEIG 기반 UTCI | 2025.07~08 기준',
    fontsize=13, fontweight='bold'
)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'tavi_summary.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\n저장: figures/tavi_summary.png")


# ── 4. 시각화 2: TAVI 순위 버블 차트 ─────────────────────────────────────
# X: reduction_pct (E 컴포넌트)
# Y: vulnerability_ratio (V 컴포넌트)
# 버블 크기: TAVI 값
# → 우상단에 위치할수록 고위험

COLORS = {
    '왕십리역': '#E53935', '행당역': '#FB8C00', '응봉역': '#8E24AA',
    '뚝섬역':  '#43A047', '성수역': '#1E88E5', '서울숲역': '#00ACC1',
    '옥수역':  '#6D4C41',
}

fig, ax = plt.subplots(figsize=(10, 8))
for _, row in tavi_df.iterrows():
    stn  = row['station']
    x_v  = row['reduction_pct_h13']
    y_v  = row['vulnerability_ratio']
    tavi = row['tavi_h13']
    c    = COLORS.get(stn, '#555555')
    if np.isnan(x_v) or np.isnan(y_v):
        continue
    size = max(tavi * 8000, 200)   # 버블 크기 비례
    ax.scatter(x_v, y_v, s=size, color=c, alpha=0.75, edgecolors='white',
               linewidth=1.5, zorder=5)
    ax.annotate(
        f'{stn}\nTAVI={tavi:.2f}',
        (x_v, y_v),
        textcoords='offset points', xytext=(10, 5),
        fontsize=9, color=c, fontweight='bold'
    )

# 사분면 기준선 (중앙값)
med_e = np.nanmedian(tavi_df['reduction_pct_h13'])
med_v = np.nanmedian(tavi_df['vulnerability_ratio'])
ax.axvline(med_e, color='gray', linestyle='--', linewidth=1.0, alpha=0.6)
ax.axhline(med_v, color='gray', linestyle='--', linewidth=1.0, alpha=0.6)

ax.text(ax.get_xlim()[1] * 0.98, med_v + 0.003, '중앙값', ha='right',
        color='gray', fontsize=8)
ax.text(med_e + 0.5, ax.get_ylim()[1] * 0.97, '중앙값', ha='left',
        color='gray', fontsize=8, rotation=90)

# 사분면 라벨
xlim = ax.get_xlim()
ylim = ax.get_ylim()
quad = {
    '고E·고V\n(고위험)':    (xlim[1] * 0.85, ylim[1] * 0.93),
    '저E·고V\n(중간위험)':  (xlim[0] * 0.98 + 2, ylim[1] * 0.93),
    '고E·저V\n(중간위험)':  (xlim[1] * 0.85, ylim[0] + 0.005),
    '저E·저V\n(저위험)':    (xlim[0] * 0.98 + 2, ylim[0] + 0.005),
}
for label, (qx, qy) in quad.items():
    ax.text(qx, qy, label, ha='center', va='center', fontsize=8,
            color='#aaaaaa', style='italic')

ax.set_xlabel('E: Thermal Catchment reduction_pct (13시, %)', fontsize=11)
ax.set_ylabel('V: 취약인구 비율 (65세 이상 + 14세 이하)', fontsize=11)
ax.set_title(
    'TAVI 버블 차트 — H×E×V 공간 분포\n'
    '버블 크기 ∝ TAVI 값 | 13시 (폭염 피크) 기준',
    fontsize=11, fontweight='bold'
)
ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'tavi_bubble.png'), dpi=150, bbox_inches='tight')
plt.close()
print("저장: figures/tavi_bubble.png")


# ── 5. 저장 ─────────────────────────────────────────────────────────────
out_json = os.path.join(OUT_DIR, 'tavi_results.json')
out_csv  = os.path.join(OUT_DIR, 'tavi_results.csv')

tavi_dict = {}
for _, row in tavi_df.iterrows():
    tavi_dict[row['station']] = {k: v for k, v in row.items() if k != 'station'}

with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(tavi_dict, f, ensure_ascii=False, indent=2, default=float)
tavi_df.to_csv(out_csv, index=False, encoding='utf-8-sig')

print(f"저장: {out_json}")
print(f"저장: {out_csv}")

# ── 6. 최종 순위 출력 ────────────────────────────────────────────────────
print("\n=== TAVI 최종 순위 (13시 기준) ===")
ranked = tavi_df.sort_values('tavi_h13', ascending=False).reset_index(drop=True)
print(f"{'순위':<4} {'역':<8} {'TAVI':>8} {'reduction_pct':>15} {'V비율':>8}")
print("-" * 50)
for i, row in ranked.iterrows():
    print(f"{i+1:<4} {row['station']:<8} {row['tavi_h13']:>8.4f} "
          f"{row['reduction_pct_h13']:>13.1f}%  {row['vulnerability_ratio']:>7.4f}")

print("\n=== 완료 ===")
print("핵심 해석:")
print("  TAVI가 높은 역 = 폭염 시 도보 접근성 저하(E) + 취약인구 집중(V)")
print("  → 폭염 적응 정책의 우선 투자 대상")
