"""
역별 대중교통 접근 가능 범위 감소율 가로 막대 차트 (슬라이드 10용)
데이터: catchment_mrt_summary.json (MRT Hard Cut, 55°C, 15분 시간예산)
13시 기준, 7개 지하철역, 감소율 높은 순 정렬
"""

import os, warnings, json
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.family'] = 'Apple SD Gothic Neo'
matplotlib.rcParams['axes.unicode_minus'] = False

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJ    = os.path.dirname(BASE)
RES_DIR = os.path.join(PROJ, '03_결과물')
FIG_DIR = os.path.join(RES_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

JSON_PATH = os.path.join(RES_DIR, 'catchment_mrt_summary.json')
OUT_PATH  = os.path.join(FIG_DIR, 'station_reduction_chart.png')

# ── 데이터 로드 (MRT Hard Cut 55°C, h13) ──────────────────────────────
with open(JSON_PATH) as f:
    data = json.load(f)

mid = data['mid']  # MRT 55°C
rows = []
for station, hrs in mid.items():
    h = hrs['h13']
    rows.append({
        'station':       station,
        'classic_nodes': h['classic_nodes'],
        'thermal_nodes': h['thermal_nodes'],
        'reduction_pct': h['reduction_pct'],
    })

df = pd.DataFrame(rows).sort_values('reduction_pct', ascending=True)

# ── 색상 (MRT 지도 팔레트와 동일) ────────────────────────────────────────
def bar_color(pct):
    if pct >= 80: return '#7A0000'
    if pct >= 60: return '#FF2200'
    if pct >= 40: return '#FF9933'
    return '#FFCC99'

colors = [bar_color(p) for p in df['reduction_pct']]

# ── 시각화 ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5), dpi=150)

bars = ax.barh(df['station'], df['reduction_pct'], color=colors,
               edgecolor='white', linewidth=0.5, height=0.6)

for bar, pct, classic, thermal in zip(bars, df['reduction_pct'],
                                       df['classic_nodes'], df['thermal_nodes']):
    ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
            f'{pct:.1f}%  ({thermal:,} / {classic:,} 노드)',
            va='center', ha='left', fontsize=10, color='#333333')

ax.axvline(50, color='#CC0000', linewidth=1.0, linestyle='--', alpha=0.6, zorder=0)
ax.text(50.5, -0.6, '50%', fontsize=9, color='#CC0000', va='top')

ax.set_xlim(0, 105)
ax.set_xlabel('접근 가능 범위 감소율 (%)', fontsize=11)
ax.set_title('역별 접근 가능 범위 감소율 (13시, MRT ≥ 55°C Hard Cut)', fontsize=12, fontweight='bold', pad=10)

legend_patches = [
    mpatches.Patch(facecolor='#7A0000', label='≥80%'),
    mpatches.Patch(facecolor='#FF2200', label='60–80%'),
    mpatches.Patch(facecolor='#FF9933', label='40–60%'),
    mpatches.Patch(facecolor='#FFCC99', label='<40%'),
]
ax.legend(handles=legend_patches, title='감소율', loc='lower right',
          fontsize=10, title_fontsize=10, framealpha=0.9, edgecolor='#999')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(axis='y', labelsize=11)
ax.tick_params(axis='x', labelsize=10)
ax.set_facecolor('#FAFAFA')
fig.patch.set_facecolor('white')

plt.tight_layout()
plt.savefig(OUT_PATH, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print(f"저장 완료: {OUT_PATH}")
print(df[['station','reduction_pct']].sort_values('reduction_pct', ascending=False).to_string(index=False))
